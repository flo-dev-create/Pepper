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
