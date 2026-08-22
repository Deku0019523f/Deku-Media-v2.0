# Deku225-média — Bot Telegram de téléchargement multiplateforme

Bot Telegram (**@MediaDeku_bot**) qui télécharge des vidéos depuis YouTube, TikTok, Instagram, Facebook, Pinterest et Twitter/X, avec un système d'abonnement Premium payé automatiquement (Mobile Money / carte bancaire), un programme de parrainage, et un panneau d'administration complet.

Développé par [@Darkdeku225](https://t.me/Darkdeku225).

---

## ✨ Fonctionnalités

- **Téléchargement multiplateforme** via [yt-dlp](https://github.com/yt-dlp/yt-dlp) : YouTube (vidéos & shorts), TikTok, Instagram (reels, posts, stories), Facebook (vidéos, reels), Pinterest, Twitter/X
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
2. Un **petit serveur HTTP** (`aiohttp`) qui reçoit les webhooks de paiement de l'API Atelier sur `/webhooks/atelier`

Quand un paiement est confirmé, le webhook **revérifie toujours** le statut auprès de l'API Atelier (`GET /v1/payments/{reference}`) avant de créditer le Premium — le contenu du webhook seul n'est jamais fait confiance (il n'est pas signé côté Atelier). Un bouton "Vérifier mon paiement" sert de filet de sécurité si le webhook n'arrivait pas.

Les données utilisateur sont stockées à deux endroits complémentaires :
- **SQLite** (`utils/database.py`) : paiements, bannissements, statistiques globales, logs de téléchargement
- **Fichiers JSON par utilisateur** (`utils/user_manager.py`, dossier `users/`) : profil, compteurs quotidiens, statut Premium, points de parrainage

## 📁 Structure du projet

```
.
├── bot.py                     # Point d'entrée : enregistrement des handlers, démarrage
├── webhook_server.py          # Serveur aiohttp qui reçoit les webhooks de paiement
├── config.py                  # Configuration centralisée (lit les variables d'environnement)
├── requirements.txt
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

⚠️ Le port `WEBHOOK_SERVER_PORT` doit être ouvert dans le pare-feu du serveur (`ufw allow 8081/tcp` par exemple) pour qu'Atelier puisse joindre le bot.

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

## 🛠️ Stack technique

[Python](https://www.python.org/) · [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [aiosqlite](https://github.com/omnilib/aiosqlite) · [aiohttp](https://docs.aiohttp.org/) · [APScheduler](https://apscheduler.readthedocs.io/) · [python-dotenv](https://github.com/theskumar/python-dotenv)

## 📄 Licence

Aucune licence open-source explicite — tous droits réservés à [@Darkdeku225](https://t.me/Darkdeku225).
