# -*- coding: utf-8 -*-
"""
Gestion de la base de données SQLite
"""
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    async def init_database(self):
        """Initialise toutes les tables de la base de données"""
        async with aiosqlite.connect(self.db_path) as db:
            # Table utilisateurs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_premium BOOLEAN DEFAULT 0,
                    premium_expire TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table paiements validés
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    currency TEXT,
                    payment_type TEXT,
                    validated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    validated_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Table paiements en attente
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pending_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Table paiements automatiques (API Atelier)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS atelier_payments (
                    reference TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    paid_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Table logs téléchargements
            await db.execute("""
                CREATE TABLE IF NOT EXISTS download_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    platform TEXT,
                    url TEXT,
                    quality TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Table statistiques journalières
            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_downloads INTEGER DEFAULT 0,
                    total_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    premium_conversions INTEGER DEFAULT 0
                )
            """)
            
            # Table parrainages
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_id) REFERENCES users (user_id)
                )
            """)
            
            # Table bannissements
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bans (
                    user_id INTEGER PRIMARY KEY,
                    reason TEXT,
                    banned_by INTEGER,
                    banned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
    
    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Ajoute un utilisateur dans la base"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            await db.commit()
    
    async def update_user_activity(self, user_id: int):
        """Met à jour la dernière activité"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET last_active = ? WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            await db.commit()
    
    async def set_premium(self, user_id: int, expire_date: str):
        """Active le premium pour un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET is_premium = 1, premium_expire = ?
                WHERE user_id = ?
            """, (expire_date, user_id))
            await db.commit()
    
    async def add_pending_payment(self, user_id: int, username: str) -> int:
        """Ajoute un paiement en attente"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO pending_payments (user_id, username)
                VALUES (?, ?)
            """, (user_id, username))
            await db.commit()
            return cursor.lastrowid
    
    async def get_pending_payments(self) -> List[Dict]:
        """Récupère tous les paiements en attente"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM pending_payments WHERE status = 'pending'
                ORDER BY created_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def validate_payment(self, payment_id: int, admin_id: int, user_id: int):
        """Valide un paiement en attente"""
        async with aiosqlite.connect(self.db_path) as db:
            # Marque comme validé
            await db.execute("""
                UPDATE pending_payments SET status = 'validated'
                WHERE id = ?
            """, (payment_id,))
            
            # Ajoute dans les paiements validés
            await db.execute("""
                INSERT INTO payments (user_id, amount, currency, payment_type, validated_by)
                VALUES (?, 0, 'EUR', 'manual', ?)
            """, (user_id, admin_id))
            
            await db.commit()
    
    async def reject_payment(self, payment_id: int):
        """Rejette un paiement en attente"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE pending_payments SET status = 'rejected'
                WHERE id = ?
            """, (payment_id,))
            await db.commit()
    
    async def create_atelier_payment(self, reference: str, user_id: int, amount: int):
        """Enregistre un paiement Atelier créé (statut 'pending')"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO atelier_payments (reference, user_id, amount, status)
                VALUES (?, ?, ?, 'pending')
            """, (reference, user_id, amount))
            await db.commit()
    
    async def get_atelier_payment(self, reference: str) -> Optional[Dict]:
        """Récupère un paiement Atelier par sa référence"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM atelier_payments WHERE reference = ?
            """, (reference,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def mark_atelier_payment_paid(self, reference: str) -> bool:
        """
        Marque un paiement Atelier comme payé, de façon idempotente.
        Retourne True si CET appel a effectué le changement (donc le Premium
        doit être crédité), False si le paiement était déjà marqué payé
        (ex: webhook reçu deux fois, ou bouton "Vérifier" cliqué après webhook).
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE atelier_payments SET status = 'paid', paid_at = ?
                WHERE reference = ? AND status != 'paid'
            """, (datetime.now().isoformat(), reference))
            await db.commit()
            return cursor.rowcount > 0
    
    async def add_payment_record(self, user_id: int, amount: int, currency: str, payment_type: str):
        """Ajoute une ligne dans l'historique des paiements validés"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO payments (user_id, amount, currency, payment_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, amount, currency, payment_type))
            await db.commit()
    
    async def log_download(self, user_id: int, platform: str, url: str, 
                          quality: str, success: bool, error: Optional[str] = None):
        """Enregistre un téléchargement"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO download_logs 
                (user_id, platform, url, quality, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, platform, url, quality, success, error))
            await db.commit()
    
    async def add_referral(self, referrer_id: int, referred_id: int):
        """Enregistre un parrainage"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO referrals (referrer_id, referred_id)
                VALUES (?, ?)
            """, (referrer_id, referred_id))
            await db.commit()
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Récupère les statistiques d'un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT COUNT(*) as total_downloads,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_downloads
                FROM download_logs
                WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else {"total_downloads": 0, "successful_downloads": 0}
    
    async def ban_user(self, user_id: int, reason: str, admin_id: int):
        """Bannit un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO bans (user_id, reason, banned_by)
                VALUES (?, ?, ?)
            """, (user_id, reason, admin_id))
            await db.commit()
    
    async def unban_user(self, user_id: int):
        """Débannit un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def is_banned(self, user_id: int) -> bool:
        """Vérifie si un utilisateur est banni"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT 1 FROM bans WHERE user_id = ?
            """, (user_id,)) as cursor:
                return await cursor.fetchone() is not None
    
    async def get_global_stats(self) -> Dict:
        """Récupère les statistiques globales"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Total utilisateurs
            async with db.execute("SELECT COUNT(*) as total FROM users") as cursor:
                total_users = (await cursor.fetchone())['total']
            
            # Utilisateurs premium
            async with db.execute("""
                SELECT COUNT(*) as total FROM users WHERE is_premium = 1
            """) as cursor:
                premium_users = (await cursor.fetchone())['total']
            
            # Téléchargements aujourd'hui
            async with db.execute("""
                SELECT COUNT(*) as total FROM download_logs
                WHERE DATE(downloaded_at) = DATE('now')
            """) as cursor:
                today_downloads = (await cursor.fetchone())['total']
            
            # Total téléchargements
            async with db.execute("SELECT COUNT(*) as total FROM download_logs") as cursor:
                total_downloads = (await cursor.fetchone())['total']
            
            return {
                "total_users": total_users,
                "premium_users": premium_users,
                "today_downloads": today_downloads,
                "total_downloads": total_downloads
            }

# Instance globale
db = Database()