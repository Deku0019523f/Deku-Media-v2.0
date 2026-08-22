# -*- coding: utf-8 -*-
"""
Authentification de la page web : l'utilisateur saisit son ID Telegram, le
bot lui envoie un code à 6 chiffres en message privé, il le recopie sur le
site. Nécessite d'avoir déjà démarré une conversation avec le bot (/start) —
sinon Telegram ne permet pas au bot de lui écrire.

Deux mécanismes :
1. generate_login_code() : génère le code à 6 chiffres (stocké en base par
   webapp.py, voir utils/database.py).
2. create_session_token()/verify_session_token() : notre propre cookie de
   session signé, pour garder l'utilisateur connecté sur le site une fois
   le code validé.
"""
import hashlib
import hmac
import time
import logging
import secrets
from typing import Optional
from config import WEBAPP_SECRET_KEY

logger = logging.getLogger(__name__)

# Si aucune clé n'est fournie en variable d'environnement, on en génère une
# aléatoire au démarrage : le site fonctionne quand même, mais les sessions
# ne survivront pas à un redémarrage du bot (l'utilisateur devra se
# reconnecter). Pour des sessions persistantes, définissez WEBAPP_SECRET_KEY.
_SECRET_KEY = WEBAPP_SECRET_KEY
if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "⚠️ WEBAPP_SECRET_KEY non définie : clé de session générée aléatoirement "
        "pour cette exécution (les sessions web ne survivront pas à un redémarrage)."
    )

SESSION_VALID_DAYS = 30
LOGIN_CODE_VALID_SECONDS = 600  # 10 minutes
LOGIN_CODE_MAX_ATTEMPTS = 5
LOGIN_CODE_REQUEST_COOLDOWN = 60  # secondes avant de pouvoir redemander un code pour le même ID


def generate_login_code() -> str:
    """Génère un code de connexion à 6 chiffres"""
    return f"{secrets.randbelow(1_000_000):06d}"


def create_session_token(user_id: int) -> str:
    """Crée un jeton de session signé, valable SESSION_VALID_DAYS jours"""
    expires = int(time.time()) + SESSION_VALID_DAYS * 86400
    payload = f"{user_id}:{expires}"
    sig = hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_session_token(token: str) -> Optional[int]:
    """Vérifie un jeton de session et retourne le user_id s'il est valide, sinon None"""
    try:
        user_id_str, expires_str, sig = token.split(":")
    except ValueError:
        return None

    payload = f"{user_id_str}:{expires_str}"
    expected_sig = hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, sig):
        return None

    try:
        if int(expires_str) < time.time():
            return None
        return int(user_id_str)
    except ValueError:
        return None

