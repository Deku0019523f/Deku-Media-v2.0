# Deku225-média — Bot Telegram de téléchargement multiplateforme

Bot Telegram (**@MediaDeku_bot**) qui télécharge des vidéos depuis YouTube, TikTok, Instagram, Facebook, Pinterest et Twitter/X, avec un système d'abonnement Premium payé automatiquement (Mobile Money / carte bancaire), un programme de parrainage, une page web de téléchargement, et un panneau d'administration complet.

Développé par [@Darkdeku225](https://t.me/Darkdeku225).

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Deku0019523f/Deku-Media-v2.0)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/Deku0019523f/Deku-Media-v2.0)

---

## ✨ Fonctionnalités

- **Téléchargement multiplateforme** via [yt-dlp](https://github.com/yt-dlp/yt-dlp) : YouTube (vidéos & shorts), TikTok, Instagram (reels, posts, stories), Facebook (vidéos, reels), Pinterest, Twitter/X — **et environ 1750 autres sites supportés par yt-dlp en repli automatique** (Vimeo, Dailymotion, SoundCloud, Twitch, Reddit, etc.), activable/désactivable globalement depuis le panneau admin
- **Page web de téléchargement**, liée à l'identité Telegram (connexion par code à 6 chiffres envoyé par le bot) — utile pour les fichiers volumineux ou pour télécharger depuis un ordinateur
- **Liens de téléchargement direct** générés automatiquement pour les fichiers dépassant 50 Mo (limite réelle de l'API Bot Telegram), envoyés en message à la place du fichier
- **Abonnement Premium** : téléchargements illimités, qualité jusqu'à 4K, pas de cooldown
- **Paiement automatique** des abonnements via l'[API Atelier](https://myateliers.store/docs/api) (Mobile Money, carte bancaire) — génération du lien de paiement, vérification du statut, webhook, et activation automatique du Premium
- **Programme de parrainage** : points par ami invité, convertibles en jours de Premium
- **Dons Telegram Stars**
- **Panneau d'administration** : statistiques, gestion des utilisateurs, validation des paiements manuels, broadcast, bannissement, logs, activation/désactivation des plateformes
- **Bilingue** français / anglais
- **Limites quotidiennes** configurables pour les utilisateurs non-Premium (par plateforme)

## 🏗️ Architecture

Le bot tourne en un seul processus Python asyncio, qui fait vivre **deux services en parallèle** dans la même boucle d'événements :

1. Le **bot Telegram** lui-même (long polling via `python-telegram-bot`)
2. Un **serveur HTTP** (`aiohttp`) qui sert trois choses sur le même port :
   - les webhooks de paiement de l'API Atelier (`/webhooks/atelier`)
   - la page web de téléchargement (`/`, `/app`, voir `webapp.py`)
   - les liens de téléchargement direct (`/dl/{token}`)

Quand un paiement est confirmé, le webhook **revérifie toujours** le statut auprès de l'API Atelier (`GET /v1/payments/{reference}`) avant de créditer le Premium — le contenu du webhook seul n'est jamais fait confiance (il n'est pas signé côté Atelier). Un bouton "Vérifier mon paiement" sert de filet de sécurité si le webhook n'arrivait pas.

La page web utilise le même principe de vérification côté serveur : l'utilisateur entre son ID Telegram, le bot lui envoie un code à 6 chiffres en message privé (ce qui prouve qu'il contrôle bien ce compte, puisque seul le vrai propriétaire reçoit le message), et le code est vérifié avant d'ouvrir une session — limitée en tentatives et avec anti-spam sur les demandes répétées.

Les données utilisateur sont stockées à deux endroits complémentaires :
- **SQLite** (`utils/database.py`) : paiements, bannissements, statistiques globales, logs de téléchargement, liens de téléchargement direct, codes de connexion web
- **Fichiers JSON par utilisateur** (`utils/user_manager.py`, dossier `users/`) : profil, compteurs quotidiens, statut Premium, points de parrainage

## 📁 Structure du projet

```
.
├── bot.py                     # Point d'entrée : enregistrement des handlers, démarrage
├── webhook_server.py          # Serveur aiohttp (webhooks paiement + monte webapp.py)
├── webapp.py                  # Page web de téléchargement + connexion par code Telegram
├── config.py                  # Configuration centralisée (lit les variables d'environnement)
├── requirements.txt
├── render.yaml                 # Déploiement Render (Blueprint)
├── railway.json / Procfile     # Déploiement Railway
├── .env.example                # Modèle des variables d'environnement à définir
│
├── handlers/
│   ├── start.py                # /start, vérification ban, message d'accueil
│   ├── download.py             # Détection de lien + téléchargement
│   ├── premium.py              # Abonnement Premium + flux de paiement automatique
│   ├── referral.py             # Parrainage et points
│   ├── payment.py              # Dons via Telegram Stars
│   ├── language.py             # Changement de langue
│   ├── stats.py                # Statistiques utilisateur
│   └── admin.py                # Panneau d'administration complet
│
├── utils/
│   ├── database.py             # Accès SQLite (paiements, bans, stats)
│   ├── user_manager.py         # Profils utilisateur (JSON)
│   ├── atelier_client.py       # Client HTTP vers l'API de paiement Atelier
│   ├── premium_payments.py     # Logique partagée de vérification/activation Premium
│   ├── telegram_auth.py        # Codes de connexion + sessions signées pour la page web
│   ├── downloader.py           # Wrapper yt-dlp
│   ├── platform_detector.py    # Détection de la plateforme depuis une URL
│   ├── limits.py               # Règles de limites quotidiennes / qualité
│   └── scheduler.py            # Tâches planifiées (APScheduler)
│
└── locales/
    ├── fr.py                   # Textes français
    └── en.py                   # Textes anglais
```

## ⚙️ Prérequis

- Python 3.12+
- Un token de bot Telegram ([@BotFather](https://t.me/BotFather))
- Un compte [Atelier](https://myateliers.store) avec une clé API (pour les paiements automatiques)
- Un serveur avec une IP/domaine public et un port ouvert (pour recevoir les webhooks de paiement)

## 🚀 Installation

```bash
git clone https://github.com/Deku0019523f/Deku-Media-v2.0.git
cd Deku-Media-v2.0

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

## 🔧 Configuration

Copiez `.env.example` en `.env` et remplissez les valeurs :

```bash
cp .env.example .env
```

| Variable | Obligatoire | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token du bot, via @BotFather |
| `ADMIN_IDS` | ✅ | IDs Telegram des admins, séparés par des virgules |
| `ATELIER_API_KEY` | ✅ | Clé API Atelier (tableau de bord → Settings → API) |
| `ATELIER_CALLBACK_URL` | ✅ | URL publique qui reçoit les webhooks de paiement |
| `ATELIER_RETURN_URL` | ✅ | Lien de redirection après paiement (ex: `https://t.me/VotreBot`) |
| `PREMIUM_PRICE_XOF` | Optionnel | Prix de l'abonnement en XOF (défaut : 2000) |
| `OWNER_USERNAME` | Optionnel | Affiché dans le message `/start` |
| `WEBHOOK_SERVER_HOST` / `PORT` | Optionnel | Interface/port du serveur de webhook (défaut : `0.0.0.0:8081`) |
| `BOT_USERNAME` | Optionnel | Nom d'utilisateur du bot, affiché sur la page web (défaut : `MediaDeku_bot`) |
| `PUBLIC_BASE_URL` | Optionnel | URL publique du service. Auto-détectée sur Render/Railway |
| `WEBAPP_SECRET_KEY` | Recommandé en prod | Clé de signature des sessions web — sans elle, les sessions ne survivent pas à un redémarrage |

⚠️ Le port `WEBHOOK_SERVER_PORT` doit être ouvert dans le pare-feu du serveur (`ufw allow 8081/tcp` par exemple) pour qu'Atelier puisse joindre le bot.

## 🌍 Déploiement

En un clic, sur une plateforme qui garde le process actif en continu (**pas Vercel** — inadapté à un bot en long polling) :

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Deku0019523f/Deku-Media-v2.0)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/Deku0019523f/Deku-Media-v2.0)

Après le premier déploiement, complétez les variables d'environnement manquantes dans le tableau ci-dessus depuis le tableau de bord de la plateforme (`ATELIER_CALLBACK_URL` notamment, une fois l'URL publique connue) puis relancez le service.

Fonctionne aussi sur un simple VPS (voir la section PM2 plus bas) ou toute plateforme équivalente exécutant du Python en continu.

## ▶️ Lancer le bot

**En développement :**
```bash
python bot.py
```

**En production (24/7, avec redémarrage automatique)**, via [PM2](https://pm2.keymetrics.io/) :
```bash
npm install -g pm2
pm2 start bot.py --name deku-media-bot --interpreter /chemin/vers/venv/bin/python3
pm2 save
pm2 startup   # active le démarrage automatique au boot du serveur
```

```bash
pm2 logs deku-media-bot       # logs en direct
pm2 restart deku-media-bot    # après une mise à jour du code
```

## 👑 Commandes admin

Réservées aux IDs listés dans `ADMIN_IDS`.

| Commande | Effet |
|---|---|
| `/admin` | Ouvre le panneau d'administration |
| `/setpremium USER_ID JOURS` | Offre le Premium à un utilisateur |
| `/ban USER_ID RAISON` | Bannit un utilisateur |
| `/unban USER_ID` | Débannit un utilisateur |
| `/resetlimits USER_ID` | Réinitialise les compteurs de téléchargement quotidiens |

Le panneau (`/admin`) donne aussi accès aux statistiques, à la liste des paiements en attente (validation manuelle), à la gestion des utilisateurs, au broadcast, aux logs et à l'activation/désactivation de chaque plateforme.

## 💳 Paiements automatiques

1. L'utilisateur clique sur **Abonnement** → le bot crée un paiement via l'API Atelier et renvoie un lien de paiement (Mobile Money / carte)
2. Une fois le paiement effectué, Atelier notifie le bot via webhook (`ATELIER_CALLBACK_URL`)
3. Le bot revérifie le statut auprès de l'API avant de créditer le Premium (idempotent — un webhook reçu deux fois ne crédite qu'une fois)
4. Si le webhook n'arrive pas, le bouton **Vérifier mon paiement** relance manuellement la même vérification

## 🌐 Page web de téléchargement

Accessible à la racine du service (`PUBLIC_BASE_URL`) :

1. L'utilisateur entre son ID Telegram (visible via [@userinfobot](https://t.me/userinfobot) par exemple)
2. Le bot lui envoie un code à 6 chiffres en message privé — **il faut donc avoir déjà envoyé `/start` au bot** pour pouvoir le recevoir
3. Le code est valable 10 minutes, 5 essais maximum, et une seule demande par minute par ID (anti-spam)
4. Une fois validé, une session de 30 jours s'ouvre (cookie signé) et la page de téléchargement (`/app`) devient accessible — même statut Premium et mêmes limites quotidiennes que sur le bot

## 📎 Fichiers volumineux (>50 Mo)

L'API Bot Telegram standard limite l'envoi de fichiers par un bot à 50 Mo. Au-delà, le bot ne tente plus d'envoyer le fichier (ce qui échouerait silencieusement) : il génère un lien de téléchargement direct (`/dl/{token}`, servi par le même serveur web) et l'envoie en message à la place. Le lien reste valide 1h (nettoyage automatique périodique des liens expirés).

## 🛠️ Stack technique

[Python](https://www.python.org/) · [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [aiosqlite](https://github.com/omnilib/aiosqlite) · [aiohttp](https://docs.aiohttp.org/) · [APScheduler](https://apscheduler.readthedocs.io/) · [python-dotenv](https://github.com/theskumar/python-dotenv)

## 🌐 Nos sites

- **[Premium225.shop](https://premium225.shop)** — plateforme de vente en ligne
- **[Boostapi.store](https://boostapi.store)** — abonnés, likes & vues
- **[Mrateliers.store](https://mrateliers.store)** — crée ta boutique en ligne

## 📄 Licence

Voir [LICENSE](./LICENSE) — tous droits réservés à [@Darkdeku225](https://t.me/Darkdeku225). Le code est visible publiquement à titre de démonstration, mais aucune réutilisation n'est autorisée sans accord préalable.
