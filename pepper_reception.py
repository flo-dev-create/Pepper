#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import base64
import json
import os
import re
import ssl
import sys
import time
import urllib2
from naoqi import ALProxy

# --- Configuration Réseau Pepper & Chemins ---
ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559
INTERNAL_TABLET_URL = "http://198.18.0.1/apps/reception/index.html"


def load_env(filepath=".env"):
    """Parseur léger pour charger la clé API sans dépendance tierce."""
    if not os.path.exists(filepath):
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".env"
        )
        if not os.path.exists(filepath):
            return {}
    env_vars = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars


env = load_env()
GEMINI_API_KEY = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("[ERR] GEMINI_API_KEY introuvable dans le fichier .env")
    sys.exit(1)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent?key="
    + GEMINI_API_KEY
)

SYSTEM_PROMPT = (
    "Tu es Pepper, le robot d'accueil officiel de Polytech Montpellier (Campus Triolet, Bâtiment 31), "
    "rattaché au département MEA (Microélectronique et Automatique).\n"
    "Consignes impératives de dialogue :\n"
    "1. Réponds oralement en français de manière dynamique, concise et polie (1 à 2 phrases courtes maximum).\n"
    "2. Ne répète jamais textuellement tes salutations ou formulations précédentes. Varie ton vocabulaire.\n"
    "3. N'utilise aucun caractère Markdown (pas d'astérisques *, pas de listes ni de dièses).\n"
    "4. Repères dans le Bâtiment 31 :\n"
    "   - Rez-de-chaussée : Grands amphithéâtres (Peytavin, Dumontet).\n"
    "   - 1er étage : Scolarité et bureaux administratifs.\n"
    "   - Étages supérieurs : Salles de cours, laboratoires de CAO et bancs de test du département MEA "
    "(Microélectronique, FPGA, automatique et robotique)."
)

# Mémoire conversationnelle multi-tours pour éviter les répétitions
conversation_history = []


def update_tablet(tablet, status, query, response):
    """Met à jour l'interface HTML hébergée sur la tablette de Pepper."""
    try:
        q = query.replace('"', '\\"').replace("'", "\\'")
        r = response.replace('"', '\\"').replace("'", "\\'")
        s = status.replace('"', '\\"').replace("'", "\\'")
        js = 'updateUI("%s", "%s", "%s");' % (s, q, r)
        tablet.executeJS(js)
    except Exception:
        pass


def ask_gemini_multiturn(audio_base64):
    """Interroge Gemini Flash avec l'enregistrement audio et l'historique."""
    global conversation_history

    user_turn = {
        "role": "user",
        "parts": [
            {
                "inline_data": {
                    "mime_type": "audio/wav",
                    "data": audio_base64,
                }
            },
            {
                "text": "Écoute ma demande et réponds directement sans répéter tes formulations passées."
            },
        ],
    }

    # Fenêtre glissante : conservation des 4 derniers échanges (8 tours)
    payload_contents = list(conversation_history[-8:])
    payload_contents.append(user_turn)

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": payload_contents,
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": 800,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    req = urllib2.Request(
        GEMINI_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        res = urllib2.urlopen(req, context=ctx, timeout=10)
        res_json = json.loads(res.read())
        candidates = res_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                raw_text = parts[0].get("text", "")
                clean = re.sub(r"[\*\#\_]", "", raw_text).strip().encode("utf-8")

                conversation_history.append(
                    {"role": "user", "parts": [{"text": "[Demande vocale visiteur]"}]}
                )
                conversation_history.append(
                    {"role": "model", "parts": [{"text": clean.decode("utf-8")}]}
                )
                return clean

        return "Bienvenue à Polytech ! En quoi puis-je vous aider ?"
    except Exception as e:
        print("[ERR] Erreur Gemini API : %s" % e)
        return "Désolé, j'ai rencontré un souci réseau passager."


def main():
    print("[INFO] Connexion aux services de Pepper sur %s..." % ROBOT_IP)
    try:
        memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
        tts = ALProxy("ALAnimatedSpeech", ROBOT_IP, ROBOT_PORT)
        awareness = ALProxy("ALBasicAwareness", ROBOT_IP, ROBOT_PORT)
        asr = ALProxy("ALSpeechRecognition", ROBOT_IP, ROBOT_PORT)
        audio_recorder = ALProxy("ALAudioRecorder", ROBOT_IP, ROBOT_PORT)
        motion = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
        posture = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)
        tablet = ALProxy("ALTabletService", ROBOT_IP, ROBOT_PORT)
    except Exception as e:
        print("[ERR] Connexion impossible : %s" % e)
        sys.exit(1)

    # 1. Réveil moteur et posture droite
    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)
    motion.setStiffnesses("Head", 1.0)
    tts.setBodyLanguageMode(2)

    # 2. Configuration d'ALBasicAwareness (Suivi automatique de la tête)
    awareness.stopAwareness()
    awareness.setEngagementMode("FullyEngaged")
    awareness.setTrackingMode("Head")
    awareness.setStimulusDetectionEnabled("People", True)
    awareness.setStimulusDetectionEnabled("Movement", False)
    awareness.startAwareness()
    print("[OK] ALBasicAwareness actif (suivi du regard engagé).")

    # 3. Chargement de l'interface MEA sur la tablette
    try:
        tablet.wakeUp()
        time.sleep(0.5)
        tablet.showWebview(INTERNAL_TABLET_URL)
        print("[OK] Interface tablette active : %s" % INTERNAL_TABLET_URL)
    except Exception as e:
        print("[WARN] Tablette non accessible : %s" % e)

    # 4. Configuration ASR pour le mot déclencheur "pepper"
    try:
        asr.unsubscribe("Pepper_WakeWord_ASR")
    except Exception:
        pass
    asr.pause(True)
    asr.setLanguage("French")
    asr.setVocabulary(["pepper"], False)
    asr.pause(False)
    asr.subscribe("Pepper_WakeWord_ASR")

    # 5. Purge préventive des fichiers audio
    remote_wav = "/tmp/reception_query.wav"
    local_wav = "/tmp/reception_local.wav"
    try:
        audio_recorder.stopMicrophonesRecording()
    except Exception:
        pass
    os.system(
        "ssh -o BatchMode=yes -o StrictHostKeyChecking=no nao@%s 'rm -f %s'"
        % (ROBOT_IP, remote_wav)
    )
    os.system("rm -f %s" % local_wav)

    print("\n[OK] Mode Accueil MEA armé et opérationnel.")
    print("     - Suivi du regard : Actif")
    print("     - Déclencheur vocal : Prononcer 'Pepper'")
    print("[INFO] Appuie sur Ctrl+C pour quitter proprement.\n")

    interaction_state = "IDLE"
    last_person_time = 0
    last_greet_time = 0
    GREET_COOLDOWN = 20.0

    memory.insertData("WordRecognized", [])

    try:
        while True:
            current_time = time.time()

            # Détection de présence via PeoplePerception ou FaceDetected
            people_data = memory.getData("PeoplePerception/PeopleDetected")
            is_person_present = bool(
                people_data and len(people_data) >= 2 and len(people_data[1]) > 0
            )

            if not is_person_present:
                face_data = memory.getData("FaceDetected")
                is_person_present = bool(
                    face_data and len(face_data) >= 2 and len(face_data[1]) > 0
                )

            # --- GESTION DU VISITEUR ---
            if is_person_present:
                last_person_time = current_time

                if interaction_state == "IDLE":
                    interaction_state = "VISITOR_PRESENT"
                    if (current_time - last_greet_time) > GREET_COOLDOWN:
                        last_greet_time = current_time
                        print("\n[PRESENCE] Visiteur détecté face à Pepper.")
                        update_tablet(
                            tablet,
                            status="● Dites 'Pepper' pour me parler",
                            query="Visiteur détecté",
                            response="Dites 'Pepper' puis posez votre question.",
                        )
                        tts.say(
                            "^start(animations/Stand/Gestures/Hey_1) Bonjour ! Dites simplement Pepper si vous souhaitez me parler. ^wait(animations/Stand/Gestures/Hey_1)"
                        )

            elif (
                interaction_state == "VISITOR_PRESENT"
                and (current_time - last_person_time) > 6.0
            ):
                interaction_state = "IDLE"
                print("[INFO] Départ du visiteur. Retour posture StandInit.")
                posture.goToPosture("StandInit", 0.5)
                update_tablet(
                    tablet,
                    status="● En veille - Approchez-vous",
                    query="En attente d'un visiteur...",
                    response="Bonjour ! Je suis Pepper, l'hôte d'accueil du département MEA.",
                )

            # --- ÉCOUTE DU MOT-CLÉ "PEPPER" ---
            word_val = memory.getData("WordRecognized")
            if word_val and len(word_val) >= 2:
                word = word_val[0]
                confidence = word_val[1]

                if word == "pepper" and confidence > 0.40:
                    print(
                        "\n[TRIGGER] Wake word 'Pepper' validé (confiance: %.2f)"
                        % confidence
                    )
                    asr.pause(True)

                    update_tablet(
                        tablet,
                        status="● Écoute en cours (4s)...",
                        query="Je vous écoute...",
                        response="Posez votre question maintenant.",
                    )

                    tts.say(
                        "^start(animations/Stand/Gestures/You_1) Oui, je vous écoute ! ^wait(animations/Stand/Gestures/You_1)"
                    )

                    # Purge du WAV avant enregistrement
                    os.system(
                        "ssh -o BatchMode=yes -o StrictHostKeyChecking=no nao@%s 'rm -f %s'"
                        % (ROBOT_IP, remote_wav)
                    )

                    print("[INFO] Enregistrement audio micro (4s)...")
                    audio_recorder.startMicrophonesRecording(
                        remote_wav, "wav", 16000, [0, 0, 1, 0]
                    )
                    time.sleep(4.0)
                    audio_recorder.stopMicrophonesRecording()
                    time.sleep(0.3)

                    # Rapatriement local via SCP
                    os.system("rm -f %s" % local_wav)
                    os.system(
                        "scp -q -o BatchMode=yes -o StrictHostKeyChecking=no nao@%s:%s %s"
                        % (ROBOT_IP, remote_wav, local_wav)
                    )

                    if (
                        os.path.exists(local_wav)
                        and 10000 < os.path.getsize(local_wav) < 600000
                    ):
                        update_tablet(
                            tablet,
                            status="● Réflexion...",
                            query="Traitement de votre question",
                            response="Consultation de la base MEA...",
                        )
                        tts.say(
                            "^start(animations/Stand/Gestures/Thinking_1) Laissez-moi voir... ^wait(animations/Stand/Gestures/Thinking_1)"
                        )

                        with open(local_wav, "rb") as f:
                            enc_audio = base64.b64encode(f.read()).decode(
                                "utf-8"
                            )

                        t0 = time.time()
                        reply = ask_gemini_multiturn(enc_audio)
                        print(
                            "[INFO] Réponse Gemini (en %.2fs) : %s"
                            % (time.time() - t0, reply)
                        )

                        update_tablet(
                            tablet,
                            status="● Réponse MEA",
                            query="Question traitée",
                            response=reply,
                        )
                        tts.say(reply)
                    else:
                        taille = (
                            os.path.getsize(local_wav)
                            if os.path.exists(local_wav)
                            else 0
                        )
                        print(
                            "[WARN] Audio invalide (%s octets). Micro étouffé ou silence."
                            % taille
                        )
                        tts.say(
                            "Je n'ai pas bien capté votre voix. N'hésitez pas à répéter en disant Pepper."
                        )

                    # Réarmement ASR
                    memory.insertData("WordRecognized", [])
                    asr.pause(False)
                    time.sleep(1.0)

                    update_tablet(
                        tablet,
                        status="● Dites 'Pepper' pour me parler",
                        query="En attente...",
                        response="Dites 'Pepper' pour une nouvelle question.",
                    )

            time.sleep(0.15)

    except KeyboardInterrupt:
        print("\n[INFO] Fermeture demandée...")
    finally:
        try:
            awareness.stopAwareness()
            asr.unsubscribe("Pepper_WakeWord_ASR")
            audio_recorder.stopMicrophonesRecording()
            tablet.hideWebview()
        except Exception:
            pass
        print("[INFO] Mise au repos des servomoteurs...")
        motion.rest()
        print("[OK] Nettoyage terminé et moteurs éteints.")


if __name__ == "__main__":
    main()