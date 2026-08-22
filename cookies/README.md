# Dossier cookies/

Ce dossier est créé automatiquement au démarrage du bot (`config.py`) mais reste **vide dans le dépôt** : les fichiers de cookies contiennent des sessions de connexion réelles et ne doivent jamais être commités.

Ils servent à télécharger du contenu qui nécessite d'être connecté (ex : certaines vidéos privées, contenu limité par âge). Sans eux, le bot fonctionne quand même pour tout le contenu public.

## Fichiers attendus

D'après `COOKIES_MAP` dans `config.py`, déposez ici (au format Netscape, celui utilisé par yt-dlp) :

| Fichier | Plateforme |
|---|---|
| `m.youtube.com_cookies.txt` | YouTube |
| `m.facebook.com_cookies.txt` | Facebook |
| `m.instagram.com_cookies.txt` | Instagram |
| `m.tiktok.com_cookies.txt` | TikTok |

## Comment les générer

1. Installez une extension navigateur comme [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge)
2. Connectez-vous au site concerné (idéalement en navigation privée, avec un compte dédié — pas votre compte personnel)
3. Exportez les cookies au format Netscape
4. Renommez le fichier exactement comme dans le tableau ci-dessus et placez-le dans ce dossier

⚠️ Un cookie exporté contient une session de connexion valide — ne le partagez jamais, ne le commitez jamais.
