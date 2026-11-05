https://web.archive.org/web/*/https://community-static.aldebaran.com/resources/*

tar -xzf pynaoqi-python2.7-2.5.10.7-linux64.tar.gz -C ~/Documents/Polytech/Projet/Pepper/

// sous arch-linux
yay -S python2-bin

python2 --version

cd ~/Documents/Polytech/Projet/Pepper/say

export PYTHONPATH=$PYTHONPATH:/home/florian/Documents/Polytech/Projet/Pepper/pynaoqi-python2.7-2.5.7.1-linux64/lib/python2.7/site-packages
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/florian/Documents/Polytech/Projet/Pepper/pynaoqi-python2.7-2.5.7.1-linux64/lib

python2 say.py