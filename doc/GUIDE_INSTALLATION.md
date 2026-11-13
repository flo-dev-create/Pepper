Voici le contenu complet et prêt à copier dans un seul bloc de code, sans coupure :

```markdown
# 🤖 Guide d'Installation et d'Exécution — Pepper Accueil MEA

Ce guide pas à pas permet d'installer les dépendances, configurer l'environnement réseau et lancer l'agent d'accueil autonome **Pepper** (Polytech Montpellier — Département MEA).

---

## 📋 Prérequis matériels et système

* **PC Hôte :** Linux (Arch Linux, Ubuntu/Debian) avec accès Internet (partage 4G/Wi-Fi).
* **Robot :** Pepper (NAOqi 2.5) connecté en réseau local fermé sur le routeur du stand.
* **Paquets système nécessaires sur le PC :**
  * `python2` (pour exécuter le SDK NAOqi hérité)
  * `python3` et `pip` (pour exécuter Whisper)
  * `ffmpeg` (pour le décodage audio)
  * `openssh` et `rsync`

### Installation des paquets

Sur Arch Linux :
```bash
sudo pacman -S python2 python python-pip ffmpeg rsync openssh

```

Sur Ubuntu / Debian :

```bash
sudo apt update
sudo apt install python2 python3 python3-pip ffmpeg rsync openssh-client

```

---

## 1. Installation du SDK Python 2 (pynaoqi)

Pepper tourne sous **NAOqi 2.5**, dont les bibliothèques C++/Python officielles nécessitent **Python 2.7**. Le SDK n'est pas tracké sur Git en raison de son poids (~200 Mo).

1. Récupère l'archive du SDK : `pynaoqi-python2.7-2.5.7.1-linux64.tar.gz`.

`https://web.archive.org/web/*/https://community-static.aldebaran.com/resources/*`
2. Extrais l'archive à la racine du projet :
```bash
tar -xvf pynaoqi-python2.7-2.5.7.1-linux64.tar.gz

```


Tu dois obtenir un dossier nommé `pynaoqi-python2.7-2.5.7.1-linux64` à côté des scripts `.py`.
3. Rends le script de chargement d'environnement exécutable :
```bash
chmod +x env_pepper.sh

```


4. **Test rapide du SDK :**
```bash
./env_pepper.sh python2 -c "import naoqi; print('SDK NAOqi chargé avec succès !')"

```



---

## 2. Installation de Whisper (Transcription locale)

Pour ne pas saturer les quotas de l'API Gemini, la transcription vocale s'exécute localement sur le processeur du PC.

1. Installe Whisper dans l'environnement Python 3 :
```bash
pip install -U openai-whisper

```


2. Rends le helper de transcription exécutable :
```bash
chmod +x transcribe_helper.py

```



---

## 3. Configuration du fichier `.env`

Le script a besoin d'une clé API Gemini (Google AI Studio) pour formuler les réponses d'orientation.

1. Crée un fichier nommé `.env` à la racine du projet :
```bash
nano .env

```


2. Ajoute ta clé API à l'intérieur :
```env
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

```



*(Ne commite jamais ce fichier : il est automatiquement ignoré par Git).*

---

## 4. Configuration des adresses IP et du Réseau

Le routeur dédié attribue des adresses sur le sous-réseau `192.168.2.0/24`.

### Topologie réseau

* **Pepper :** `192.168.2.101` (Port NAOqi : `9559`)
* **PC Hôte :** `192.168.2.100` (Interface Ethernet ou Wi-Fi locale)
* **Tablette de Pepper :** `198.18.0.1` (IP fixe interne entre la tête et la tablette Android)

### Définition des IP dans le code

Si les IP changent, modifie le début de `pepper_reception.py` et `deploy.sh` :

```python
# Dans pepper_reception.py :
ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559

```

### Vérifier la liaison

```bash
ping -c 2 192.168.2.101

```

---

## 5. Liaison SSH sans mot de passe (Indispensable)

Le PC rapatrie les fichiers audio du robot via `scp`. Pour éviter que le robot ne se fige en attendant une saisie terminal :

1. Génère une clé SSH sur ton PC si tu n'en as pas :
```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

```


2. Dépose-la sur Pepper (mot de passe par défaut : `nao`) :
```bash
ssh-copy-id nao@192.168.2.101

```


3. Déverrouille la clé dans ta session :
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

```


4. **Vérification :**
```bash
ssh nao@192.168.2.101 "echo Connexion sans mot de passe OK"

```



---

## 6. Démarrage en une seule commande

Pour synchroniser l'affichage sur la tablette du robot et démarrer l'accueil :

```bash
./deploy.sh

```

### Fonctionnement pendant l'accueil

1. **Veille :** Pepper reste droit et surveille son environnement.
2. **Détection & Suivi :** Dès qu'un visage est repéré, sa tête s'oriente pour le suivre (`ALBasicAwareness`) et il salue brièvement.
3. **Wake Word :** Dis distinctement **« Pepper »** pour déclencher l'enregistrement audio (confirmation par geste et mise à jour de la tablette).
4. **Dialogue :** Pose ta question (4 secondes). Whisper transcrit le texte en local, Gemini génère la réponse et Pepper la prononce avec gestuelle animée.

```

Tu peux créer directement le fichier dans ton dossier `doc/` en exécutant cette commande dans ton terminal :

```bash
mkdir -p doc
cat << 'EOF' > doc/GUIDE_INSTALLATION.md
# 🤖 Guide d'Installation et d'Exécution — Pepper Accueil MEA

Ce guide pas à pas permet d'installer les dépendances, configurer l'environnement réseau et lancer l'agent d'accueil autonome **Pepper** (Polytech Montpellier — Département MEA).

---

## 📋 Prérequis matériels et système

* **PC Hôte :** Linux (Arch Linux, Ubuntu/Debian) avec accès Internet (partage 4G/Wi-Fi).
* **Robot :** Pepper (NAOqi 2.5) connecté en réseau local fermé sur le routeur du stand.
* **Paquets système nécessaires sur le PC :**
  * `python2` (pour exécuter le SDK NAOqi hérité)
  * `python3` et `pip` (pour exécuter Whisper)
  * `ffmpeg` (pour le décodage audio)
  * `openssh` et `rsync`

### Installation des paquets

Sur Arch Linux :
```bash
sudo pacman -S python2 python python-pip ffmpeg rsync openssh

```

Sur Ubuntu / Debian :

```bash
sudo apt update
sudo apt install python2 python3 python3-pip ffmpeg rsync openssh-client

```

---

## 1. Installation du SDK Python 2 (pynaoqi)

Pepper tourne sous **NAOqi 2.5**, dont les bibliothèques C++/Python officielles nécessitent **Python 2.7**. Le SDK n'est pas tracké sur Git en raison de son poids (~200 Mo).

1. Récupère l'archive du SDK : `pynaoqi-python2.7-2.5.7.1-linux64.tar.gz`.
2. Extrais l'archive à la racine du projet :
```bash
tar -xvf pynaoqi-python2.7-2.5.7.1-linux64.tar.gz

```


Tu dois obtenir un dossier nommé `pynaoqi-python2.7-2.5.7.1-linux64` à côté des scripts `.py`.
3. Rends le script de chargement d'environnement exécutable :
```bash
chmod +x env_pepper.sh

```


4. **Test rapide du SDK :**
```bash
./env_pepper.sh python2 -c "import naoqi; print('SDK NAOqi chargé avec succès !')"

```



---

## 2. Installation de Whisper (Transcription locale)

Pour ne pas saturer les quotas de l'API Gemini, la transcription vocale s'exécute localement sur le processeur du PC.

1. Installe Whisper dans l'environnement Python 3 :
```bash
pip install -U openai-whisper

```


2. Rends le helper de transcription exécutable :
```bash
chmod +x transcribe_helper.py

```



---

## 3. Configuration du fichier `.env`

Le script a besoin d'une clé API Gemini (Google AI Studio) pour formuler les réponses d'orientation.

1. Crée un fichier nommé `.env` à la racine du projet :
```bash
nano .env

```


2. Ajoute ta clé API à l'intérieur :
```env
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

```



*(Ne commite jamais ce fichier : il est automatiquement ignoré par Git).*

---

## 4. Configuration des adresses IP et du Réseau

Le routeur dédié attribue des adresses sur le sous-réseau `192.168.2.0/24`.

### Topologie réseau

* **Pepper :** `192.168.2.101` (Port NAOqi : `9559`)
* **PC Hôte :** `192.168.2.100` (Interface Ethernet ou Wi-Fi locale)
* **Tablette de Pepper :** `198.18.0.1` (IP fixe interne entre la tête et la tablette Android)

### Définition des IP dans le code

Si les IP changent, modifie le début de `pepper_reception.py` et `deploy.sh` :

```python
# Dans pepper_reception.py :
ROBOT_IP = "192.168.2.101"
ROBOT_PORT = 9559

```

### Vérifier la liaison

```bash
ping -c 2 192.168.2.101

```

---

## 5. Liaison SSH sans mot de passe (Indispensable)

Le PC rapatrie les fichiers audio du robot via `scp`. Pour éviter que le robot ne se fige en attendant une saisie terminal :

1. Génère une clé SSH sur ton PC si tu n'en as pas :
```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

```


2. Dépose-la sur Pepper (mot de passe par défaut : `nao`) :
```bash
ssh-copy-id nao@192.168.2.101

```


3. Déverrouille la clé dans ta session :
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

```


4. **Vérification :**
```bash
ssh nao@192.168.2.101 "echo Connexion sans mot de passe OK"

```



---

## 6. Démarrage en une seule commande

Pour synchroniser l'affichage sur la tablette du robot et démarrer l'accueil :

```bash
./deploy.sh

```

### Fonctionnement pendant l'accueil

1. **Veille :** Pepper reste droit et surveille son environnement.
2. **Détection & Suivi :** Dès qu'un visage est repéré, sa tête s'oriente pour le suivre (`ALBasicAwareness`) et il salue brièvement.
3. **Wake Word :** Dis distinctement **« Pepper »** pour déclencher l'enregistrement audio (confirmation par geste et mise à jour de la tablette).
4. **Dialogue :** Pose ta question (4 secondes). Whisper transcrit le texte en local, Gemini génère la réponse et Pepper la prononce avec gestuelle animée.
EOF