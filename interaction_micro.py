#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import time
import sys
from naoqi import ALProxy

ROBOT_IP = "127.0.0.1"
ROBOT_PORT = 9559

def main():
    memory = ALProxy("ALMemory", ROBOT_IP, ROBOT_PORT)
    tts = ALProxy("ALAnimatedSpeech", ROBOT_IP, ROBOT_PORT)
    asr = ALProxy("ALSpeechRecognition", ROBOT_IP, ROBOT_PORT)
    motion = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
    posture = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)

    # Réveil des moteurs et posture d'écoute
    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)
    tts.setBodyLanguageMode(2)

    # Réinitialisation propre de l'ASR
    try:
        asr.unsubscribe("LocalSpeechInteraction")
    except Exception:
        pass

    # Pause obligatoire pour recharger le modèle acoustique/vocabulaire
    asr.pause(True)
    asr.setLanguage("French")
    vocab = ["bonjour", "comment tu t'appelles", "au revoir"]
    asr.setVocabulary(vocab, False)
    asr.pause(False)

    asr.subscribe("LocalSpeechInteraction")

    tts.say("Je t'écoute.")
    print("[OK] Microphones en écoute sur Pepper.")

    memory.insertData("WordRecognized", [])
    last_detected = ""

    try:
        while True:
            val = memory.getData("WordRecognized")
            if val and len(val) >= 2:
                word = val[0]
                confidence = val[1]

                if confidence > 0.40 and word != last_detected:
                    print("-> Reconnu : %s (%.2f)" % (word, confidence))
                    last_detected = word

                    if word == "bonjour":
                        tts.say("^start(animations/Stand/Gestures/Hey_1) Bonjour ! ^wait(animations/Stand/Gestures/Hey_1)")
                    elif word == "comment tu t'appelles":
                        tts.say("^start(animations/Stand/Gestures/Me_1) Je m'appelle Pepper. ^wait(animations/Stand/Gestures/Me_1)")
                    elif word == "au revoir":
                        tts.say("^start(animations/Stand/Gestures/BowShort_1) À bientôt ! ^wait(animations/Stand/Gestures/BowShort_1)")

                    memory.insertData("WordRecognized", [])
                    time.sleep(1.5)
                    last_detected = ""

            time.sleep(0.15)

    except KeyboardInterrupt:
        print("\nArrêt du script...")
    finally:
        try:
            asr.unsubscribe("LocalSpeechInteraction")
        except Exception:
            pass
        motion.rest()
        print("[OK] Moteurs au repos.")

if __name__ == "__main__":
    main()