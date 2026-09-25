# Pepper — Projet MEA4

Document de référence regroupant l'infrastructure réseau (routeur Edimax) et la configuration du poste de travail Arch Linux (Python 2 & SDK NAOqi).

---

## Sommaire
- [Partie 1 : Configuration et Appairage du Routeur Edimax](#partie-1--configuration-et-appairage-du-routeur-edimax-naoqi-25)
  - [1. Paramétrage de l'interface Web du Routeur](#1-paramétrage-de-linterface-web-du-routeur-edimax)
  - [2. Procédure de Connexion sur Pepper (Terminal SSH)](#2-procédure-de-connexion-sur-pepper-terminal-ssh)
  - [3. Méthode Alternative : ConnManCTL interactif](#3-méthode-alternative--connmanctl-interactif)
  - [4. Vérification de la Liaison Réseau](#4-vérification-de-la-liaison-réseau)
  - [5. Dépannage Réseau](#5-dépannage-réseau)
- [Partie 2 : Installation et Configuration de Python 2 & du SDK NAOqi](#partie-2--installation-et-configuration-de-python-2--du-sdk-naoqi-arch-linux--omarchy)
  - [1. Prérequis & Contexte](#1-prérequis--contexte)
  - [2. Installation de Python 2](#2-installation-de-python-2)
  - [3. Extraction du SDK NAOqi Python](#3-extraction-du-sdk-naoqi-python)
  - [4. Configuration des Variables d'Environnement](#4-configuration-des-variables-denvironnement)
  - [5. Script de Test : say.py](#5-script-de-test--saypy)
  - [6. Résolution des Problèmes Courants](#6-résolution-des-problèmes-courants)

---

# Partie 1 : Configuration et Appairage du Routeur Edimax (NAOqi 2.5)

Ce chapitre récapitule les étapes de configuration matérielle du routeur Edimax et la procédure d'appairage Wi-Fi pour un robot Pepper opérant sous NAOqi OS 2.5.

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
```

### Méthode Recommandée : Script Python via ALConnectionManager
Le gestionnaire de paquets et de services NAOqi fournit une interface D-Bus directe qui évite d'avoir à manipuler les fichiers protégés en lecture seule (`/var/lib/connman`).

Exécutez la commande suivante en une seule ligne :

```bash
python -c '
from naoqi import ALProxy
import time

c = ALProxy("ALConnectionManager", "127.0.0.1", 9559)
sid = "wifi_48a9d28c6afc_6564696d61785f322e34475f3863_managed_psk"

# 1. Enregistrement de la configuration
config = {
    "ServiceId": sid,
    "Passphrase": "Pepper_2026",
    "AutoConnect": True
}
try:
    c.setServiceConfiguration(config)
    print("[OK] Profil réseau enregistré.")
except Exception as e:
    print("[ERR] Erreur setServiceConfiguration:", e)

# 2. Lancement de la connexion
try:
    c.connect(sid)
    print("[OK] Demande de connexion transmise.")
except Exception as e:
    print("[ERR] Erreur connect:", e)

time.sleep(3)
'
```

---

## 3. Méthode Alternative : ConnManCTL interactif

Si vous préférez utiliser l'utilitaire système `connmanctl` :

1. Lancer l'invite ConnMan :
   ```bash
   connmanctl
   ```

2. Nettoyer les éventuels échecs précédents en cache :
   ```text
   config wifi_48a9d28c6afc_6564696d61785f322e34475f3863_managed_psk --remove
   ```

3. Réactiver l'agent et associer :
   ```text
   agent on
   scan wifi
   connect wifi_48a9d28c6afc_6564696d61785f322e34475f3863_managed_psk
   ```

4. Saisir la clé `Pepper_2026` lorsque l'invite `Passphrase?` apparaît, puis quitter :
   ```text
   quit
   ```

---

## 4. Vérification de la Liaison Réseau

Une fois la commande exécutée, vérifiez l'état de l'interface `wlan0` :

```bash
ip a show wlan0
```

### Critères de validation :
1. Le flag `<NO-CARRIER>` doit disparaître au profit de `<BROADCAST,MULTICAST,UP,LOWER_UP>`.
2. Une adresse IPv4 doit être attribuée :
   ```text
   inet 192.168.2.X/24 brd 192.168.2.255 scope global wlan0
   ```

Pour vérifier que le profil est actif et configuré en reconnexion automatique :
```bash
connmanctl services | grep edimax
```
*(Le préfixe doit afficher `*A` ou `*AO`).*

---

## 5. Dépannage Réseau

* **`Agent ReportError: connect-failed / Operation aborted`** :
  Vérifiez que le WPS est désactivé et que le chiffrement est bien fixé sur **WPA2-PSK (AES)** sans TKIP. Supprimez l'ancien cache via `connmanctl config <service_id> --remove`.
* **`Read-only file system`** :
  La partition racine `/` de Pepper est montée en lecture seule par conception. Ne tentez pas de modifier `/var/lib/connman/` directement avec `nano` ; passez toujours par l'API Python `ALConnectionManager` ou par `connmanctl`.
* **Échec d'oubli d'un ancien point d'accès (`Service Not Found`)** :
  Si `c.forget(...)` lève une exception, le profil a déjà été supprimé de la base locale et ne tentera plus de se reconnecter.

---

# Partie 2 : Installation et Configuration de Python 2 & du SDK NAOqi (Arch Linux / Omarchy)

Ce guide détaille l'installation de Python 2 et la configuration du SDK SoftBank Robotics (`pynaoqi`) sur un poste de travail sous Arch Linux (Omarchy) afin de piloter un robot Pepper (NAOqi OS 2.5) via des scripts Python externes.

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
git clone https://aur.archlinux.org/python2-bin.git
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
  * Vérifiez que le port `9559` est ouvert et que le démon NAOqi tourne sur Pepper.
