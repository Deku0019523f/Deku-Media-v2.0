# -*- coding: utf-8 -*-
"""
Planificateur de tâches automatiques
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
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
