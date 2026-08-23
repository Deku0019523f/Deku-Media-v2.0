# -*- coding: utf-8 -*-
"""
Planificateur de tâches automatiques
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from pathlib import Path
import json
import asyncio

class BotScheduler:
    """Gestionnaire de tâches planifiées pour le bot"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    async def reset_daily_limits(self):
        """Réinitialise les compteurs quotidiens à minuit"""
        try:
            print(f"🔄 Réinitialisation des limites quotidiennes - {datetime.now()}")
            
            from config import USERS_DIR
            
            counter = 0
            for user_file in USERS_DIR.glob("*.json"):
                try:
                    # Lire le fichier utilisateur
                    with open(user_file, 'r', encoding='utf-8') as f:
                        user_data = json.load(f)
                    
                    # Réinitialiser les compteurs
                    user_data["downloads_youtube_today"] = 0
                    user_data["downloads_other_today"] = 0
                    user_data["last_reset_date"] = datetime.now().date().isoformat()
                    
                    # Sauvegarder
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(user_data, f, indent=2, ensure_ascii=False)
                    
                    counter += 1
                    
                except Exception as e:
                    print(f"Erreur reset user {user_file.stem}: {e}")
            
            print(f"✅ Réinitialisation terminée - {counter} utilisateurs mis à jour")
            
        except Exception as e:
            print(f"❌ Erreur dans reset_daily_limits: {e}")

    async def cleanup_expired_download_links(self):
        """Supprime les liens de téléchargement direct expirés et leurs fichiers"""
        try:
            from utils.database import db

            expired = await db.get_expired_download_links()
            for link in expired:
                file_path = link.get("file_path")
                if file_path:
                    try:
                        path = Path(file_path)
                        if path.exists():
                            path.unlink()
                    except Exception as e:
                        print(f"Erreur suppression fichier {file_path}: {e}")
                await db.delete_download_link(link["token"])

            if expired:
                print(f"🧹 {len(expired)} lien(s) de téléchargement expiré(s) nettoyé(s)")

        except Exception as e:
            print(f"❌ Erreur dans cleanup_expired_download_links: {e}")

    async def self_ping(self):
        """
        Auto-ping périodique sur /health, pour éviter la mise en veille des
        plans gratuits (Render endort un service web après ~15 min sans
        requête entrante). Inoffensif ailleurs (VPS, Railway...) : ça se
        contente de vérifier que le serveur répond.
        """
        try:
            import aiohttp
            from config import PUBLIC_BASE_URL

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(f"{PUBLIC_BASE_URL}/health") as resp:
                    if resp.status == 200:
                        print(f"💓 Keep-alive OK ({PUBLIC_BASE_URL}/health)")
                    else:
                        print(f"⚠️ Keep-alive : statut inattendu {resp.status}")
        except Exception as e:
            print(f"⚠️ Keep-alive échoué (pas forcément grave, ex: en dev local) : {e}")
    
    def start(self):
        """Démarre le planificateur"""
        try:
            # Réinitialisation quotidienne à 00:00
            self.scheduler.add_job(
                self.reset_daily_limits,
                CronTrigger(hour=0, minute=0),
                id="daily_reset",
                replace_existing=True,
                misfire_grace_time=3600  # 1 heure de tolérance
            )

            # Nettoyage des liens de téléchargement expirés, toutes les 15 minutes
            self.scheduler.add_job(
                self.cleanup_expired_download_links,
                IntervalTrigger(minutes=15),
                id="cleanup_download_links",
                replace_existing=True,
                misfire_grace_time=600
            )

            # Auto-ping toutes les 10 minutes (< 15 min = seuil de mise en
            # veille des plans gratuits Render)
            self.scheduler.add_job(
                self.self_ping,
                IntervalTrigger(minutes=10),
                id="self_ping",
                replace_existing=True,
                misfire_grace_time=120
            )
            
            self.scheduler.start()
            print("✅ Planificateur de tâches démarré")
            
        except Exception as e:
            print(f"❌ Erreur démarrage planificateur: {e}")
    
    def stop(self):
        """Arrête le planificateur"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                print("🛑 Planificateur arrêté")
        except Exception as e:
            print(f"❌ Erreur arrêt planificateur: {e}")

# Instance globale
bot_scheduler = BotScheduler()
