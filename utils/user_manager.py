# -*- coding: utf-8 -*-
"""
Gestion des données utilisateurs individuelles (JSON)
"""
import json
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import USERS_DIR, PREMIUM_DURATION_DAYS

class UserManager:
    def __init__(self):
        self.users_dir = USERS_DIR
    
    def _get_user_file(self, user_id: int) -> Path:
        """Retourne le chemin du fichier JSON de l'utilisateur"""
        return self.users_dir / f"{user_id}.json"
    
    async def get_user(self, user_id: int) -> Dict:
        """Récupère les données d'un utilisateur"""
        user_file = self._get_user_file(user_id)
        
        if not user_file.exists():
            # Créer un nouvel utilisateur
            user_data = {
                "id": user_id,
                "username": None,
                "lang": "fr",
                "premium": False,
                "premium_expire": None,
                "downloads_youtube_today": 0,
                "downloads_other_today": 0,
                "last_download_time": 0,
                "points": 0,
                "referrer": None,
                "invited_users": [],
                "last_reset_date": datetime.now().date().isoformat()
            }
            await self.save_user(user_id, user_data)
            return user_data
        
        async with aiofiles.open(user_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            user_data = json.loads(content)
        
        # Vérifier et réinitialiser les compteurs si nouveau jour
        await self._check_daily_reset(user_id, user_data)
        
        # Vérifier expiration premium
        await self._check_premium_expiration(user_id, user_data)
        
        return user_data
    
    async def save_user(self, user_id: int, user_data: Dict):
        """Sauvegarde les données d'un utilisateur"""
        user_file = self._get_user_file(user_id)
        async with aiofiles.open(user_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(user_data, indent=2, ensure_ascii=False))
    
    async def _check_daily_reset(self, user_id: int, user_data: Dict):
        """Réinitialise les compteurs quotidiens si nécessaire"""
        today = datetime.now().date().isoformat()
        last_reset = user_data.get("last_reset_date", today)
        
        if last_reset != today:
            user_data["downloads_youtube_today"] = 0
            user_data["downloads_other_today"] = 0
            user_data["last_reset_date"] = today
            await self.save_user(user_id, user_data)
    
    async def _check_premium_expiration(self, user_id: int, user_data: Dict):
        """Vérifie si le premium a expiré"""
        if user_data.get("premium") and user_data.get("premium_expire"):
            expire_date = datetime.fromisoformat(user_data["premium_expire"])
            if datetime.now() > expire_date:
                user_data["premium"] = False
                user_data["premium_expire"] = None
                await self.save_user(user_id, user_data)
    
    async def set_language(self, user_id: int, lang: str):
        """Change la langue de l'utilisateur"""
        user_data = await self.get_user(user_id)
        user_data["lang"] = lang
        await self.save_user(user_id, user_data)
    
    async def increment_download(self, user_id: int, is_youtube: bool):
        """Incrémente le compteur de téléchargements"""
        user_data = await self.get_user(user_id)
        if is_youtube:
            user_data["downloads_youtube_today"] += 1
        else:
            user_data["downloads_other_today"] += 1
        user_data["last_download_time"] = datetime.now().timestamp()
        await self.save_user(user_id, user_data)
    
    async def set_premium(self, user_id: int, days: int = PREMIUM_DURATION_DAYS):
        """Active le premium pour un utilisateur"""
        user_data = await self.get_user(user_id)
        expire_date = datetime.now() + timedelta(days=days)
        user_data["premium"] = True
        user_data["premium_expire"] = expire_date.isoformat()
        await self.save_user(user_id, user_data)
    
    async def add_points(self, user_id: int, points: int):
        """Ajoute des points de parrainage"""
        user_data = await self.get_user(user_id)
        user_data["points"] = user_data.get("points", 0) + points
        await self.save_user(user_id, user_data)
    
    async def redeem_points(self, user_id: int, points: int, days: int):
        """Échange des points contre du premium"""
        user_data = await self.get_user(user_id)
        if user_data.get("points", 0) >= points:
            user_data["points"] -= points
            
            # Étendre le premium
            if user_data.get("premium") and user_data.get("premium_expire"):
                expire_date = datetime.fromisoformat(user_data["premium_expire"])
                new_expire = expire_date + timedelta(days=days)
            else:
                new_expire = datetime.now() + timedelta(days=days)
            
            user_data["premium"] = True
            user_data["premium_expire"] = new_expire.isoformat()
            await self.save_user(user_id, user_data)
            return True
        return False
    
    async def reset_daily_limits(self, user_id: int):
        """Remet à zéro les compteurs de téléchargements quotidiens (action admin)"""
        user_data = await self.get_user(user_id)
        user_data["downloads_youtube_today"] = 0
        user_data["downloads_other_today"] = 0
        await self.save_user(user_id, user_data)

    async def set_referrer(self, user_id: int, referrer_id: int):
        """Définit le parrain d'un utilisateur"""
        user_data = await self.get_user(user_id)
        if user_data.get("referrer") is None:
            user_data["referrer"] = referrer_id
            await self.save_user(user_id, user_data)
            
            # Ajouter l'invité à la liste du parrain
            referrer_data = await self.get_user(referrer_id)
            if user_id not in referrer_data.get("invited_users", []):
                referrer_data.setdefault("invited_users", []).append(user_id)
                await self.save_user(referrer_id, referrer_data)
            
            return True
        return False

# Instance globale
user_manager = UserManager()
