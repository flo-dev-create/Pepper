#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import sys
import time
from naoqi import ALProxy

ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559

# Fichier local de sauvegarde du chemin de la carte et des coordonnées A / B
CONFIG_FILE = "map_config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "map_path": "",
        "point_a": [0.0, 0.0, 0.0],
        "point_b": [1.5, 0.0, 0.0],  # Par défaut : 1.5m devant le point A
    }


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


def prepare_robot(motion, posture, life, awareness):
    """Désactive AutonomousLife et prépare la posture pour autoriser le déplacement."""
    print("[INFO] Préparation physique du robot pour la navigation...")
    try:
        if life.getState() != "disabled":
            print("[INFO] Désactivation de ALAutonomousLife (requis pour débloquer les roues)...")
            life.setState("disabled")
    except Exception:
        pass

    try:
        awareness.stopAwareness()
    except Exception:
        pass

    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)
    # Verrouille la tête bien droite pour ne pas fausser la perception frontale
    motion.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.0], 0.2)


def display_map_on_tablet(navigation, tablet):
    """Récupère la matrice MetricalMap de Pepper et l'affiche sur sa tablette."""
    try:
        import numpy as np
        import cv2

        result_map = navigation.getMetricalMap()
        # Structure : [mpp, width, height, [origin_x, origin_y], data]
        width = result_map[1]
        height = result_map[2]
        map_data = result_map[4]

        img = np.array(map_data, dtype=np.uint8).reshape((height, width))
        # Redimensionnement pour un affichage net sur l'écran de Pepper
        img_resized = cv2.resize(img, (600, 600), interpolation=cv2.INTER_NEAREST)
        _, buffer = cv2.imencode(".png", img_resized)
        b64_img = base64.b64encode(buffer).decode("utf-8")

        tablet.wakeUp()
        tablet.showImage("data:image/png;base64," + b64_img)
        print("[OK] Carte SLAM affichée sur la tablette de Pepper.")
    except ImportError:
        print("[INFO] (Optionnel) Installe numpy et opencv-python2 pour voir la carte sur la tablette.")
    except Exception as e:
        print("[WARN] Impossible d'afficher la carte sur la tablette : %s" % e)


def run_mapping(navigation, motion, posture, tts, tablet, radius):
    """Phase 1 : Exploration SLAM autour du Point A."""
    cfg = load_config()

    tts.say("Attention, je vais commencer la cartographie de la zone. Écartez-vous s'il vous plaît.")
    print("\n[SLAM] Démarrage de l'exploration sur un rayon de %.1f mètres..." % radius)
    print("[INFO] L'emplacement actuel est défini comme Point A [0.0, 0.0, 0.0].")

    try:
        navigation.stopLocalization()
    except Exception:
        pass

    # Lancement du SLAM (bloquant pendant l'exploration)
    error_code = navigation.explore(float(radius))
    if error_code != 0:
        print("[WARN] Code retour exploration : %s (zone restreinte ou obstacle proche)" % error_code)

    # Sauvegarde sur le stockage interne de Pepper
    map_path = navigation.saveExploration()
    print("[OK] Exploration terminée ! Carte enregistrée sur Pepper : %s" % map_path)

    # Retour au point d'origine A (0, 0)
    print("[NAV] Démarrage de la localisation et retour au Point A...")
    navigation.startLocalization()
    navigation.navigateToInMap([0.0, 0.0, 0.0])
    navigation.stopLocalization()

    # Sauvegarde dans map_config.json
    cfg["map_path"] = map_path
    cfg["point_a"] = [0.0, 0.0, 0.0]
    save_config(cfg)
    print("[OK] Configuration sauvegardée dans %s" % CONFIG_FILE)

    display_map_on_tablet(navigation, tablet)
    tts.say("Cartographie terminée et enregistrée avec succès.")


def record_point_b(navigation, motion, tts):
    """Permet de pousser Pepper du Point A au Point B pour relever les coordonnées exactes."""
    cfg = load_config()
    if not cfg.get("map_path"):
        print("[ERR] Aucune carte trouvée dans %s. Lance d'abord avec --map." % CONFIG_FILE)
        sys.exit(1)

    print("\n[CALIBRATION] Chargement de la carte : %s" % cfg["map_path"])
    navigation.stopLocalization()
    navigation.loadExploration(str(cfg["map_path"]))
    navigation.guessPoseFromOdometry([0.0, 0.0, 0.0])
    navigation.startLocalization()

    tts.say("Placez-moi au point A, puis appuyez sur Entrée dans le terminal.")
    raw_input("\n>>> 1. Place Pepper exactement au POINT A, puis appuie sur [Entrée]...")
    navigation.relocalizeInMap([0.0, 0.0, 0.0])

    # Déverrouillage des roues uniquement pour pouvoir pousser Pepper à la main
    motion.setStiffnesses("Wheel", 0.0)
    tts.say("Mes roues sont libres. Poussez-moi doucement jusqu'au point B.")
    raw_input(">>> 2. Pousse Pepper jusqu'au POINT B souhaité, puis appuie sur [Entrée]...")

    # Reverrouillage des roues et lecture de la pose dans la carte
    motion.setStiffnesses("Wheel", 1.0)
    pose_and_uncertainty = navigation.getRobotPositionInMap()
    point_b = list(pose_and_uncertainty[0])  # [x, y, theta]

    navigation.stopLocalization()

    cfg["point_b"] = point_b
    save_config(cfg)

    print("\n[OK] Coordonnées du Point B enregistrées : X=%.2fm, Y=%.2fm, Theta=%.2frad" % (
        point_b[0], point_b[1], point_b[2]
    ))
    tts.say("Le point B est enregistré.")


def go_a_to_b(navigation, tts, target_override=None):
    """Phase 2 : Navigation autonome du Point A vers le Point B."""
    cfg = load_config()
    map_path = cfg.get("map_path")
    if not map_path:
        print("[ERR] Aucune carte enregistrée. Lance d'abord : python2 pepper_navigation.py --map")
        sys.exit(1)

    point_a = cfg.get("point_a", [0.0, 0.0, 0.0])
    point_b = target_override if target_override else cfg.get("point_b", [1.5, 0.0, 0.0])

    print("\n[NAV] Chargement de la carte : %s" % map_path)
    try:
        navigation.stopLocalization()
    except Exception:
        pass

    navigation.loadExploration(str(map_path))
    navigation.startLocalization()

    # Initialisation de la position au Point A
    print("[NAV] Relocalisation au Point A : %s" % point_a)
    navigation.relocalizeInMap(point_a)
    time.sleep(1.0)

    # Déplacement vers le Point B
    print("[NAV] Départ vers le Point B : X=%.2fm, Y=%.2fm, Theta=%.2frad..." % (
        point_b[0], point_b[1], point_b[2]
    ))
    tts.say("Je me déplace vers le point B.")
    navigation.navigateToInMap(point_b)

    pos_finale = navigation.getRobotPositionInMap()[0]
    print("[OK] Arrivé au Point B ! Position estimée : [%.2f, %.2f, %.2f]" % (
        pos_finale[0], pos_finale[1], pos_finale[2]
    ))
    tts.say("Je suis arrivé à destination.")

    time.sleep(2.0)

    # Optionnel : Retour au Point A
    ans = raw_input("\n>>> Veux-tu que Pepper retourne au Point A ? (o/n) : ").strip().lower()
    if ans == "o":
        print("[NAV] Retour au Point A...")
        tts.say("Je retourne à mon point de départ.")
        navigation.navigateToInMap(point_a)
        tts.say("Je suis de retour au point A.")

    navigation.stopLocalization()


def main():
    parser = argparse.ArgumentParser(description="Cartographie SLAM et Navigation A -> B sur Pepper")
    parser.add_argument("--map", action="store_true", help="Générer une nouvelle carte autour du Point A")
    parser.add_argument("--radius", type=float, default=2.0, help="Rayon d'exploration en mètres (défaut: 2.0)")
    parser.add_argument("--record-b", action="store_true", help="Enregistrer le Point B en poussant le robot")
    parser.add_argument("--go", action="store_true", help="Aller du Point A au Point B enregistré")
    parser.add_argument("--coords", nargs=3, type=float, metavar=("X", "Y", "THETA"),
                        help="Spécifier manuellement les coordonnées du Point B (ex: --coords 1.5 0.5 0.0)")
    args = parser.parse_args()

    if not (args.map or args.record_b or args.go):
        parser.print_help()
        sys.exit(0)

    try:
        navigation = ALProxy("ALNavigation", ROBOT_IP, ROBOT_PORT)
        motion = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
        posture = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)
        life = ALProxy("ALAutonomousLife", ROBOT_IP, ROBOT_PORT)
        awareness = ALProxy("ALBasicAwareness", ROBOT_IP, ROBOT_PORT)
        tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)
        tablet = ALProxy("ALTabletService", ROBOT_IP, ROBOT_PORT)
    except Exception as e:
        print("[ERR] Connexion impossible à Pepper (%s) : %s" % (ROBOT_IP, e))
        sys.exit(1)

    try:
        prepare_robot(motion, posture, life, awareness)

        if args.map:
            run_mapping(navigation, motion, posture, tts, tablet, args.radius)
        elif args.record_b:
            record_point_b(navigation, motion, tts)
        elif args.go:
            go_a_to_b(navigation, tts, target_override=args.coords)

    except KeyboardInterrupt:
        print("\n[STOP] Interruption d'urgence demandée !")
        navigation.stopExploration()
        navigation.stopLocalization()
        motion.stopMove()
    finally:
        motion.stopMove()
        print("[OK] Opération terminée.")


if __name__ == "__main__":
    main()