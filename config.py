# -*- coding: utf-8 -*-
"""
Configuration centralisée du bot
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charge le fichier .env s'il existe (les vraies variables d'environnement,
# si présentes, restent prioritaires). Sans cet appel, os.getenv() ne voit
# JAMAIS le contenu d'un .env — un fichier .env seul ne suffit pas.
load_dotenv(Path(__file__).parent / ".env")

# ==================== CONFIGURATION BOT ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # Token du bot @BotFather — défini dans .env, JAMAIS en dur ici
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]  # IDs admin, séparés par des virgules dans .env
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@Darkdeku225")  # Propriétaire du bot

# ==================== CHEMINS ====================
BASE_DIR = Path(__file__).parent
COOKIES_DIR = BASE_DIR / "cookies"
USERS_DIR = BASE_DIR / "users"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DATABASE_PATH = BASE_DIR / "database" / "bot.db"

# Création des dossiers nécessaires
for directory in [COOKIES_DIR, USERS_DIR, DOWNLOADS_DIR, DATABASE_PATH.parent]:
    directory.mkdir(parents=True, exist_ok=True)

# ==================== FICHIERS COOKIES ====================
COOKIES_MAP = {
    "youtube": COOKIES_DIR / "m.youtube.com_cookies.txt",
    "facebook": COOKIES_DIR / "m.facebook.com_cookies.txt",
    "instagram": COOKIES_DIR / "m.instagram.com_cookies.txt",
    "tiktok": COOKIES_DIR / "m.tiktok.com_cookies.txt",
}

# ==================== LIMITES UTILISATEURS ====================
# Utilisateur Normal
NORMAL_YOUTUBE_DAILY_LIMIT = 5
NORMAL_OTHER_DAILY_LIMIT = 10
NORMAL_COOLDOWN = 10  # secondes
NORMAL_MAX_QUALITY_YOUTUBE = "360"  # pixels

# Utilisateur Premium
PREMIUM_DURATION_DAYS = 60  # 2 mois
PREMIUM_UNLIMITED = True
PREMIUM_COOLDOWN = 0
PREMIUM_MAX_QUALITY = "2160"  # 4K

# ==================== SYSTÈME DE PARRAINAGE ====================
REFERRAL_POINTS_NORMAL = 2
REFERRAL_POINTS_PREMIUM = 5
POINTS_FOR_1_WEEK = 10
POINTS_FOR_1_MONTH = 30

# ==================== PAIEMENTS ====================
PREMIUM_CHECKOUT_URL = "optionnel"  # legacy, plus utilisé par le flux Premium
DONATION_STARS = [20, 50]  # Montants en Stars

# ==================== PAIEMENTS AUTOMATIQUES (API Atelier) ====================
# Doc API : https://myateliers.store/docs/api
# Clé générée depuis : https://myateliers.store/dashboard/settings/api
# ⚠️ Ne jamais mettre la vraie clé en dur ici : définissez la variable d'environnement
# ATELIER_API_KEY (ex: export ATELIER_API_KEY="atl_live_xxxxx" avant de lancer le bot).
ATELIER_API_KEY = os.getenv("ATELIER_API_KEY", "")
ATELIER_BASE_URL = "https://myateliers.store/api/public/v1"  # api.myateliers.store redirigeait ici (307) — on cible directement la bonne URL

# 🔧 À CONFIGURER : URL publique (HTTPS de préférence) qui reçoit les
# webhooks de paiement, ex: "https://votre-domaine.com/webhooks/atelier"
# ou "http://VOTRE_IP_VPS:8081/webhooks/atelier" en HTTP simple.
# ⚠️ En HTTP simple (pas de nom de domaine ni TLS), le trafic entre l'API
# Atelier et votre serveur n'est pas chiffré. Le webhook n'étant de toute
# façon jamais utilisé seul (on revérifie toujours via GET /v1/payments/{reference}
# avant de créditer le Premium), le risque est limité, mais si possible pointez
# un nom de domaine + certificat TLS (Let's Encrypt) sur ce port.
# Le port WEBHOOK_SERVER_PORT (8081 par défaut) doit être ouvert dans le
# pare-feu du serveur (ex: ufw allow 8081/tcp) pour qu'Atelier puisse l'atteindre.
ATELIER_CALLBACK_URL = os.getenv("ATELIER_CALLBACK_URL", "https://VOTRE-DOMAINE-OU-IP.example/webhooks/atelier")

# Lien vers lequel l'utilisateur est redirigé après paiement
ATELIER_RETURN_URL = os.getenv("ATELIER_RETURN_URL", "https://t.me/MediaDeku_bot")

# 🔧 À CONFIGURER : prix de l'abonnement Premium en Francs CFA (XOF, entier sans décimales)
PREMIUM_PRICE_XOF = int(os.getenv("PREMIUM_PRICE_XOF", "2000"))

# Serveur HTTP interne (webhooks Atelier + page web de téléchargement).
# Sur Render/Railway/Heroku, la plateforme impose son propre port via $PORT :
# on le respecte en priorité, sinon on retombe sur WEBHOOK_SERVER_PORT (VPS).
WEBHOOK_SERVER_HOST = os.getenv("WEBHOOK_SERVER_HOST", "0.0.0.0")
WEBHOOK_SERVER_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_SERVER_PORT", "8081")))

# ==================== APPLICATION WEB (page de téléchargement) ====================
# 🔧 À CONFIGURER : URL publique complète du service (sans slash final), ex:
# "https://mon-bot.onrender.com", "https://mon-bot.up.railway.app", ou
# "http://VOTRE_IP_OU_DOMAINE:8081" sur un VPS.
# Render et Railway exposent automatiquement leur URL via ces variables ;
# on les détecte pour éviter une config manuelle en plus sur ces plateformes.
PUBLIC_BASE_URL = (
    os.getenv("PUBLIC_BASE_URL")
    or (f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}" if os.getenv("RENDER_EXTERNAL_HOSTNAME") else None)
    or (f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}" if os.getenv("RAILWAY_PUBLIC_DOMAIN") else None)
    or "http://localhost:8081"
)

# Nom d'utilisateur du bot (sans @), requis par le widget de connexion Telegram
BOT_USERNAME = os.getenv("BOT_USERNAME", "MediaDeku_bot")

# Clé de signature des sessions web (cookie de connexion). Générez-en une avec :
# python3 -c "import secrets; print(secrets.token_hex(32))"
WEBAPP_SECRET_KEY = os.getenv("WEBAPP_SECRET_KEY", "")

# Taille (Mo) au-delà de laquelle le bot n'essaie plus d'envoyer le fichier
# directement sur Telegram (limite réelle de l'API Bot Telegram standard :
# 50 Mo) et génère à la place un lien de téléchargement direct.
TELEGRAM_UPLOAD_LIMIT_MB = 50

# ==================== SUPPORT & COMMUNAUTÉ ====================
SUPPORT_CHANNEL = "https://t.me/connexiontoutreseaus"

# ==================== TÉLÉCHARGEMENT ====================
DELETE_AFTER_SEND = 60  # Secondes avant suppression automatique (fichiers envoyés directement sur Telegram)
MAX_FILE_SIZE_MB = 2000  # Taille maximale acceptée (au-delà : refusé, même en lien direct)
DOWNLOAD_LINK_EXPIRY = 3600  # Secondes de validité d'un lien de téléchargement direct (>50 Mo)

# ==================== PLATEFORMES SUPPORTÉES ====================
# "autres" : bascule globale pour le repli sur tous les extracteurs yt-dlp
# (voir utils/platform_detector.py) — les ~1750 sites en plus des 6 vedettes.
PLATFORMS_ENABLED = {
    "youtube": True,
    "tiktok": True,
    "instagram": True,
    "facebook": True,
    "pinterest": True,
    "twitter": True,
    "autres": True,
}

# ==================== YT-DLP OPTIONS ====================
YTDLP_BASE_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'socket_timeout': 30,
    'retries': 3,
    'fragment_retries': 3,
    'nocheckcertificate': True,
}

# ==================== LOGS ====================
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "bot.log"
