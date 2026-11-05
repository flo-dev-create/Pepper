#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import os
import re
import ssl
import sys
import time
import urllib2
from naoqi import ALProxy

# --- Configuration Réseau Pepper ---
ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559

# --- Chargement de la clé API depuis .env ---
def load_env(filepath=".env"):
    """Charge les paires CLE=VALEUR depuis un fichier .env sans dépendance tierce."""
    if not os.path.exists(filepath):
        # Tente de chercher dans le répertoire parent si exécuté depuis un sous-dossier
        filepath = os.path.join(os.path.dirname(__file__), ".env")
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
                val = val.strip().strip("'\"")
                env_vars[key.strip()] = val
    return env_vars


env = load_env()
GEMINI_API_KEY = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("[ERR] Variable GEMINI_API_KEY introuvable dans le fichier .env.")
    sys.exit(1)

# Endpoint officiel v1beta (modèle flash rapide pour limiter la latence de dialogue)
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent?key="
    + GEMINI_API_KEY
)

SYSTEM_PROMPT = (
    "Tu es Pepper, un robot humanoïde de Polytech Montpellier. "
    "Réponds à l'oral en français de manière très concise (1 à 2 phrases courtes maximum), "
    "chaleureuse et directe. N'utilise aucun symbole Markdown (pas d'étoiles, pas de listes)."
)


def ask_gemini(prompt_text):
    """Envoie la requête à l'API Gemini via la connexion Internet de ton PC."""
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        },
    }

    data = json.dumps(payload)
    headers = {"Content-Type": "application/json"}

    # Contexte SSL sécurisé pour requêtes HTTPS modernes
    ctx = ssl.create_default_context()

    req = urllib2.Request(GEMINI_URL, data=data, headers=headers)
    try:
        response = urllib2.urlopen(req, context=ctx, timeout=8)
        res_json = json.loads(response.read())

        candidates = res_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                text = parts[0].get("text", "")
                # Nettoyage des résidus de ponctuation/markdown
                clean = re.sub(r"[\*\#\_]", "", text).strip()
                return clean.encode("utf-8")
        return "Je n'ai pas trouvé de réponse à cette question."
    except Exception as e:
        print("[ERR] Requête Gemini échouée : %s" % e)
        return "J'ai eu un problème pour joindre mon serveur d'intelligence."


def main():
    print("[INFO] Connexion à Pepper sur %s..." % ROBOT_IP)
    try:
        memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
        tts = ALProxy("ALAnimatedSpeech", ROBOT_IP, ROBOT_PORT)
        asr = ALProxy("ALSpeechRecognition", ROBOT_IP, ROBOT_PORT)
        motion = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
        posture = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)
    except Exception as e:
        print("[ERR] Impossible de se connecter à Pepper : %s" % e)
        print("[HINT] Vérifie le câble/Wi-Fi Edimax et ping 192.168.2.101.")
        sys.exit(1)

    # Réveil et initialisation physique
    print("[INFO] Réveil des moteurs...")
    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)
    tts.setBodyLanguageMode(2)  # Mouvements corporels contextualisés pendant la parole

    # Réinitialisation propre du module ASR
    try:
        asr.unsubscribe("ClientPC_Gemini")
    except Exception:
        pass

    asr.pause(True)
    asr.setLanguage("French")

    # Dictionnaire de phrases déclencheuses
    vocab = [
        "bonjour",
        "qui es tu",
        "que fais tu a polytech",
        "raconte moi une blague",
        "quel est le sens de la vie",
        "au revoir",
    ]
    asr.setVocabulary(vocab, False)
    asr.pause(False)

    asr.subscribe("ClientPC_Gemini")

    tts.say(
        "^start(animations/Stand/Gestures/Hey_1) Connexion établie avec l'ordinateur et le modèle Gemini. Je t'écoute. ^wait(animations/Stand/Gestures/Hey_1)"
    )

    print("\n[OK] En écoute. Phrases testables :")
    for phrase in vocab:
        print("  - %s" % phrase)
    print("\n[INFO] Appuie sur Ctrl+C pour quitter proprement.\n")

    memory.insertData("WordRecognized", [])
    last_word = ""

    try:
        while True:
            val = memory.getData("WordRecognized")
            if val and len(val) >= 2:
                word = val[0]
                confidence = val[1]

                if confidence > 0.40 and word != last_word:
                    print(
                        "\n-> Micro Pepper : '%s' (Confiance: %.2f)"
                        % (word, confidence)
                    )
                    last_word = word

                    if word == "au revoir":
                        tts.say(
                            "^start(animations/Stand/Gestures/BowShort_1) Au revoir et à la prochaine ! ^wait(animations/Stand/Gestures/BowShort_1)"
                        )
                        break

                    # Feedback vocal court pour masquer la latence de la requête web
                    tts.say(
                        "^start(animations/Stand/Gestures/Thinking_1) Laisse-moi réfléchir... ^wait(animations/Stand/Gestures/Thinking_1)"
                    )

                    print("[INFO] Envoi de la requête à Gemini...")
                    t0 = time.time()
                    answer = ask_gemini(word)
                    print(
                        "[INFO] Réponse reçue en %.2fs : %s"
                        % (time.time() - t0, answer)
                    )

                    # Le robot prononce la réponse avec animations
                    tts.say(answer)

                    # Purge de la mémoire et pause anti-rebond
                    memory.insertData("WordRecognized", [])
                    time.sleep(1.2)
                    last_word = ""

            time.sleep(0.15)

    except KeyboardInterrupt:
        print("\n[INFO] Interruption manuelle...")
    finally:
        try:
            asr.unsubscribe("ClientPC_Gemini")
        except Exception:
            pass
        print("[INFO] Mise au repos des moteurs...")
        motion.rest()
        print("[OK] Session terminée.")


if __name__ == "__main__":
    main()