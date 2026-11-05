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

# --- Configuration Réseau Pepper ---
ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559


def load_env(filepath=".env"):
    if not os.path.exists(filepath):
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
                env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars


env = load_env()
GEMINI_API_KEY = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("[ERR] GEMINI_API_KEY manquante dans .env")
    sys.exit(1)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent?key="
    + GEMINI_API_KEY
)

SYSTEM_PROMPT = (
    "Tu es Pepper, robot humanoïde de Polytech Montpellier. "
    "L'utilisateur te parle via un extrait audio. Réponds directement à sa question "
    "en français à l'oral, en 1 ou 2 phrases courtes maximum. N'utilise aucun formatage Markdown."
)


def ask_gemini_audio(audio_base64):
    """Envoie l'enregistrement audio directement à Gemini en multimodal."""
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": audio_base64,
                        }
                    },
                    {"text": "Écoute cet audio et réponds à l'utilisateur."},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
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
        res = urllib2.urlopen(req, context=ctx, timeout=12)
        res_json = json.loads(res.read())
        candidates = res_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                clean = re.sub(r"[\*\#\_]", "", parts[0].get("text", "")).strip()
                return clean.encode("utf-8")
        return "Je n'ai pas bien compris ta question."
    except Exception as e:
        print("[ERR] Erreur requête Gemini Audio : %s" % e)
        return "Désolé, j'ai rencontré une erreur d'analyse réseau."


def main():
    print("[INFO] Connexion à Pepper sur %s..." % ROBOT_IP)
    memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
    tts = ALProxy("ALAnimatedSpeech", ROBOT_IP, ROBOT_PORT)
    asr = ALProxy("ALSpeechRecognition", ROBOT_IP, ROBOT_PORT)
    audio_recorder = ALProxy("ALAudioRecorder", ROBOT_IP, ROBOT_PORT)
    motion = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
    posture = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)

    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)
    tts.setBodyLanguageMode(2)

    # Configuration du Wake Word
    try:
        asr.unsubscribe("Pepper_WakeWord")
    except Exception:
        pass

    asr.pause(True)
    asr.setLanguage("French")
    asr.setVocabulary(["pepper"], False)
    asr.pause(False)
    asr.subscribe("Pepper_WakeWord")

    print("\n[OK] En veille. Dis 'Pepper' pour poser une question libre.")
    print("[INFO] Appuie sur Ctrl+C pour quitter.\n")

    memory.insertData("WordRecognized", [])

    try:
        while True:
            val = memory.getData("WordRecognized")
            if val and len(val) >= 2:
                word = val[0]
                confidence = val[1]

                if word == "pepper" and confidence > 0.40:
                    print("\n[TRIGGER] Wake word 'Pepper' détecté (confiance: %.2f)" % confidence)
                    asr.pause(True)  # Pause pour ne pas interférer avec l'enregistrement

                    # Signal sonore/vocal d'écoute
                    tts.say("^start(animations/Stand/Gestures/Hey_1) Oui ? ^wait(animations/Stand/Gestures/Hey_1)")

                    # 1. Enregistrement audio (4 secondes)
                    remote_wav_path = "/tmp/user_query.wav"
                    try:
                        audio_recorder.stopMicrophonesRecording()
                    except Exception:
                        pass

                    print("[INFO] Enregistrement audio en cours (4s)...")
                    # Enregistrement en WAV 16kHz, 1 canal (micro avant)
                    audio_recorder.startMicrophonesRecording(
                        remote_wav_path, "wav", 16000, [0, 0, 1, 0]
                    )
                    time.sleep(4.0)
                    audio_recorder.stopMicrophonesRecording()
                    print("[INFO] Enregistrement terminé.")

                    # 2. Récupération du fichier WAV depuis Pepper via SCP/SSH
                    local_wav_path = "/tmp/pepper_query.wav"
                    scp_cmd = "scp -q nao@%s:%s %s" % (
                        ROBOT_IP,
                        remote_wav_path,
                        local_wav_path,
                    )
                    os.system(scp_cmd)

                    # 3. Traitement et appel Gemini
                    if os.path.exists(local_wav_path):
                        tts.say(
                            "^start(animations/Stand/Gestures/Thinking_1) Laisse-moi chercher... ^wait(animations/Stand/Gestures/Thinking_1)"
                        )
                        with open(local_wav_path, "rb") as f:
                            encoded_audio = base64.b64encode(f.read()).decode("utf-8")

                        print("[INFO] Envoi de l'audio à Gemini Flash...")
                        reply = ask_gemini_audio(encoded_audio)
                        print("[INFO] Réponse Gemini : %s" % reply)
                        tts.say(reply)
                    else:
                        tts.say("Je n'ai pas réussi à récupérer ton enregistrement audio.")

                    # Réarmement de l'écoute du Wake Word
                    memory.insertData("WordRecognized", [])
                    asr.pause(False)
                    print("\n[OK] En attente du mot-clé 'Pepper'...")

            time.sleep(0.15)

    except KeyboardInterrupt:
        print("\n[INFO] Fermeture...")
    finally:
        try:
            asr.unsubscribe("Pepper_WakeWord")
            audio_recorder.stopMicrophonesRecording()
        except Exception:
            pass
        motion.rest()
        print("[OK] Nettoyage terminé.")


if __name__ == "__main__":
    main()