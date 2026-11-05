#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from naoqi import ALProxy

# Paramètres de connexion
ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559

def main():
    # Initialisation du proxy ALTextToSpeech
    tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)

    # Réglages de la voix
    tts.setLanguage("French")
    tts.setVolume(0.8)  # Volume entre 0.0 et 1.0

    # Modification de la vitesse ou du pitch (optionnel)
    # tts.setParameter("speed", 100)  # Vitesse normale = 100
    # tts.setParameter("pitchShift", 1.0)

    # Faire parler Pepper
    phrase = "Bonjour"
    tts.say(phrase)

if __name__ == "__main__":
    main()