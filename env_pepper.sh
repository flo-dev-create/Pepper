#!/usr/bin/env bash
# env_pepper.sh

SDK_DIR="/home/florian/Documents/Polytech/Projet/Pepper/pynaoqi-python2.7-2.5.7.1-linux64"

export PYTHONPATH="$SDK_DIR/lib/python2.7/site-packages:$PYTHONPATH"
export LD_LIBRARY_PATH="$SDK_DIR/lib:$LD_LIBRARY_PATH"

echo "[OK] Environnement NAOqi Python 2 initialisé."
exec "$@"