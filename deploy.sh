#!/usr/bin/env bash
# ==============================================================================
# deploy.sh - Déploiement tablette et démarrage de l'agent d'accueil MEA Pepper
# Polytech Montpellier - Département MEA
# ==============================================================================

set -e

ROBOT_IP="192.168.2.101"
REMOTE_USER="nao"
REMOTE_PATH="/home/nao/.local/share/PackageManager/apps/reception/html"
INTERNAL_URL="http://198.18.0.1/apps/reception/index.html"
SSH_KEY="$HOME/.ssh/id_ed25519"

echo "--------------------------------------------------------"
echo "  🚀 Déploiement de l'Accueil MEA sur Pepper ($ROBOT_IP)"
echo "--------------------------------------------------------"

# 1. Vérification et chargement de la clé SSH dans l'agent
if [ -f "$SSH_KEY" ]; then
    if ! ssh-add -l 2>/dev/null | grep -q "$(ssh-keygen -lf "$SSH_KEY" | awk '{print $2}')"; then
        echo "[1/5] 🔑 Déverrouillage de la clé SSH pour Pepper..."
        eval "$(ssh-agent -s)" >/dev/null 2>&1 || true
        ssh-add "$SSH_KEY"
    else
        echo "[1/5] 🔑 Clé SSH déjà active dans l'agent."
    fi
fi

# 2. Test de joignabilité réseau
echo "[2/5] 📡 Vérification de la liaison avec Pepper..."
if ! ping -c 1 -W 2 "$ROBOT_IP" >/dev/null 2>&1; then
    echo "❌ Erreur: Impossible de joindre Pepper sur $ROBOT_IP. Vérifie la connexion Wi-Fi/Ethernet."
    exit 1
fi

# 3. Synchronisation des fichiers Web de la tablette
echo "[3/5] 📂 Synchronisation de tablet/ vers le stockage interne..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "$REMOTE_USER@$ROBOT_IP" "mkdir -p '$REMOTE_PATH'"

if command -v rsync >/dev/null 2>&1; then
    rsync -avz -e "ssh -o BatchMode=yes -o StrictHostKeyChecking=no" tablet/ "$REMOTE_USER@$ROBOT_IP:$REMOTE_PATH/"
else
    scp -q -o BatchMode=yes -o StrictHostKeyChecking=no -r tablet/* "$REMOTE_USER@$ROBOT_IP:$REMOTE_PATH/"
fi

# 4. Réveil tablette et purge audio
echo "[4/5] 🖥️  Réveil de la tablette et préchargement de la page..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "$REMOTE_USER@$ROBOT_IP" bash << 'REMOTECMD'
    # Réveil et affichage de la page
    qicli call ALTabletService.wakeUp >/dev/null 2>&1 || true
    qicli call ALTabletService.showWebview "http://198.18.0.1/apps/reception/index.html" >/dev/null 2>&1 || true
    # Purge d'anciens enregistrements bloqués
    rm -f /tmp/reception_query.wav
REMOTECMD

# 5. Démarrage de l'agent d'accueil
echo "[5/5] 🤖 Lancement de pepper_reception.py..."
echo "--------------------------------------------------------"

if [ -f "./env_pepper.sh" ]; then
    ./env_pepper.sh python2 pepper_reception.py
else
    python2 pepper_reception.py
fi
