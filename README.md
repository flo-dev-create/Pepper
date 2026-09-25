# Pepper
Projet MEA4

# Configuration et Appairage du Routeur Edimax pour Pepper (NAOqi 2.5)

Ce document récapitule les étapes de configuration matérielle du routeur Edimax et la procédure d'appairage Wi-Fi pour un robot Pepper opérant sous NAOqi OS 2.5.

---

## 1. Paramétrage de l'interface Web du Routeur Edimax

Les cartes Wi-Fi et la pile réseau `ConnMan / wpa_supplicant` de NAOqi 2.5 exigent des paramètres de sécurité stricts pour éviter les échecs d'association radio (`NO-CARRIER` ou `Operation aborted`).

Accédez à la console d'administration du routeur (généralement via `192.168.2.1` depuis un navigateur) et configurez les sections suivantes :

### A. Paramètres Sans-Fil (Wireless Settings)
* **Bande radio** : 2.4 GHz (recommandé pour une meilleure portée et compatibilité)
* **SSID** : `edimax_2.4G_8c`
* **Canal Wi-Fi** : Fixer un canal fixe (1, 6 ou 11) pour éviter les sauts de fréquence intempestifs.

### B. Paramètres de Sécurité (Crucial)
* **Mode de Sécurité** : `WPA2 - Personnel` (ou `WPA2-PSK`).  
  > **Attention** : Ne pas sélectionner `WPA - Personnel` (WPA1) sous peine de blocage de négociation de clé par Pepper.
* **Chiffrement (Encryption)** : `AES` uniquement.  
  > **Attention** : Éviter les modes hybrides `TKIP` ou `TKIP&AES`.
* **Clé de sécurité (Wireless Password)** : `Pepper_2026`
* **Désactiver le WPS** : Rendez-vous dans le menu **WPS** et passez-le sur **Désactivé (Disabled)** pour empêcher ConnMan de bloquer sur une tentative de négociation par code PIN/bouton.

Validez en cliquant sur **Enregistrer / Appliquer** et attendez le redémarrage du module sans-fil.

---

## 2. Procédure de Connexion sur Pepper (Terminal SSH)

Connectez-vous à Pepper par câble Ethernet ou console locale :

```bash
ssh nao@192.168.2.101


# Installation et Configuration de Python 2 & du SDK NAOqi (Arch Linux / Omarchy)

Ce guide détaille l'installation de Python 2 et la configuration du SDK SoftBank Robotics (`pynaoqi`) sur un poste de travail sous Arch Linux (Omarchy) afin de piloter un robot Pepper (NAOqi OS 2.5) via des scripts Python externes.

---

## 1. Prérequis & Contexte

* **Système d'exploitation hôte** : Arch Linux / Omarchy (x86_64).
* **Version cible de Pepper** : NAOqi OS 2.5.x.
* **Contrainte d'architecture logicielle** : Le SDK `pynaoqi` fourni pour NAOqi 2.5 est compilé exclusivement pour **Python 2.7**. Étant donné que `python2` a été retiré des dépôts officiels (`pacman`), son installation s'effectue via l'AUR.

---

## 2. Installation de Python 2

Pour éviter les temps de compilation longs et les échecs de compilation de vieux codes sources C avec les versions modernes de GCC, privilégiez le paquet binaire précompilé `python2-bin`.

### Méthode A : Avec un helper AUR (`yay` ou `paru`)
```bash
yay -S python2-bin
# ou : paru -S python2-bin
```

### Méthode B : Compilation manuelle via Git & Makepkg
```bash
cd /tmp
git clone [https://aur.archlinux.org/python2-bin.git](https://aur.archlinux.org/python2-bin.git)
cd python2-bin
makepkg -si
```

### Vérification
Assurez-vous que l'interpréteur est bien accessible :
```bash
python2 --version
# Doit renvoyer : Python 2.7.x
```

---

## 3. Extraction du SDK NAOqi Python

Téléchargez l'archive du SDK Python correspondant à votre version (ex. `pynaoqi-python2.7-2.5.7.1-linux64.tar.gz` ou `2.5.10.7`).

1. Placez l'archive dans votre répertoire de projet :
   ```bash
   cd ~/Documents/Polytech/Projet/Pepper
   ```

2. Décompressez l'archive :
   ```bash
   tar -xzf pynaoqi-python2.7-2.5.7.1-linux64.tar.gz
   ```

---

## 4. Configuration des Variables d'Environnement

Pour que Python 2 et le chargeur dynamique du système retrouvent les bibliothèques C++ et les modules Python du SDK, deux variables d'environnement doivent être définies.

### Configuration temporaire (session en cours)
Exécutez dans le terminal avant de lancer votre script (en adaptant le chemin si nécessaire) :

```bash
export SDK_DIR="/home/florian/Documents/Polytech/Projet/Pepper/pynaoqi-python2.7-2.5.7.1-linux64"

export PYTHONPATH="$SDK_DIR/lib/python2.7/site-packages:$PYTHONPATH"
export LD_LIBRARY_PATH="$SDK_DIR/lib:$LD_LIBRARY_PATH"
```

### Configuration persistante (Script wrapper recommandé)
Plutôt que d'altérer l'environnement global d'Arch Linux, créez un script d'environnement `env_pepper.sh` à la racine de votre projet :

```bash
#!/usr/bin/env bash
# env_pepper.sh

SDK_DIR="/home/florian/Documents/Polytech/Projet/Pepper/pynaoqi-python2.7-2.5.7.1-linux64"

export PYTHONPATH="$SDK_DIR/lib/python2.7/site-packages:$PYTHONPATH"
export LD_LIBRARY_PATH="$SDK_DIR/lib:$LD_LIBRARY_PATH"

echo "[OK] Environnement NAOqi Python 2 initialisé."
exec "$@"
```

Rendez-le exécutable :
```bash
chmod +x env_pepper.sh
```

---

## 5. Script de Test : `say.py`

Créez le fichier `say.py` :

```python
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
from naoqi import ALProxy

ROBOT_IP = "192.168.2.101"  # IP Ethernet ou Wi-Fi du robot
ROBOT_PORT = 9559

def main():
    try:
        tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)
        tts.setLanguage("French")
        tts.say("Bonjour ! Le SDK Python 2 fonctionne parfaitement depuis Arch Linux.")
        print("[OK] Message prononcé avec succès.")
    except Exception as e:
        print("[ERR] Erreur lors de l'appel NAOqi : %s" % e)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Exécution du script

* **En utilisant le wrapper :**
  ```bash
  ./env_pepper.sh python2 say.py
  ```

* **Ou directement (si les variables sont déjà exportées) :**
  ```bash
  python2 say.py
  ```

---

## 6. Résolution des Problèmes Courants

* **`ModuleNotFoundError: No module named 'naoqi'`** :
  * La commande exécutée utilise Python 3 au lieu de Python 2. Utilisez impérativement `python2`.
  * La variable `PYTHONPATH` ne pointe pas vers le dossier `.../lib/python2.7/site-packages` du SDK.
* **`ImportError: libqi.so: cannot open shared object file`** :
  * La variable `LD_LIBRARY_PATH` est absente ou ne pointe pas vers le sous-dossier `.../lib` du SDK.
* **`RuntimeError: ... Connection refused`** :
  * Vérifiez que le robot est bien joignable sur l'adresse spécifiée (`ping 192.168.2.101`).
  * Vérifiez que le port `9559` est ouvert et que le service NAOqi tourne sur Pepper.
