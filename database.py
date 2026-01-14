import sqlite3
import logging
import os
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="missav.db"):
        self.db_path = db_path
        # Ensure the directory for the database file exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info("Created database directory: %s", db_dir)
            
        self._lock = Lock()
        self.init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Creators table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    platform TEXT NOT NULL, -- onlyfans, twitter, etc.
                    display_name TEXT,
                    avatar_url TEXT,
                    last_post_id TEXT,
                    last_check TEXT,
                    created_time TEXT,
                    UNIQUE(username, platform)
                )
            ''')
            
            # Posts table (Records of scraped posts to avoid duplicates)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT NOT NULL,
                    creator_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    content TEXT,
                    media_urls TEXT, -- JSON array of media URLs
                    is_ppv BOOLEAN DEFAULT 0,
                    price TEXT,
                    created_at TEXT, -- Post original creation time
                    scraped_at TEXT,
                    UNIQUE(post_id, platform),
                    FOREIGN KEY (creator_id) REFERENCES creators (id)
                )
            ''')
            
            # Subscriptions table (User -> Creator mapping)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL, -- Discord User ID
                    creator_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    created_time TEXT,
                    FOREIGN KEY (creator_id) REFERENCES creators (id),
                    UNIQUE(user_id, creator_id)
                )
            ''')
            
            # Auth info table (Admin managed cookies/tokens)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT UNIQUE NOT NULL,
                    username TEXT,
                    auth_json TEXT, -- All credentials stored as JSON
                    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, FAILED
                    updated_time TEXT
                )
            ''')
            
            # Legacy videos table (kept for backward compatibility or deleted if not needed)
            # cursor.execute('DROP TABLE IF EXISTS videos') 
            
            conn.commit()
            logger.info("Database initialized with OnlyFans schema at %s", self.db_path)

    # --- Auth Management ---
    def save_auth(self, platform, username, auth_data):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            import json
            cursor.execute('''
                INSERT OR REPLACE INTO auth_info (platform, username, auth_json, updated_time)
                VALUES (?, ?, ?, ?)
            ''', (platform, username, json.dumps(auth_data), now))
            conn.commit()

    def get_auth(self, platform):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT auth_json FROM auth_info WHERE platform = ? AND status = "ACTIVE"', (platform,))
            row = cursor.fetchone()
            if row:
                import json
                return json.loads(row[0])
            return None

    # --- Creator & Subscription Management ---
    def add_creator(self, username, platform, display_name=None, avatar_url=None):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT OR IGNORE INTO creators (username, platform, display_name, avatar_url, created_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, platform, display_name, avatar_url, now))
            conn.commit()
            cursor.execute('SELECT id FROM creators WHERE username = ? AND platform = ?', (username, platform))
            return cursor.fetchone()[0]

    def subscribe(self, user_id, creator_id, platform):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT OR IGNORE INTO subscriptions (user_id, creator_id, platform, created_time)
                VALUES (?, ?, ?, ?)
            ''', (user_id, creator_id, platform, now))
            conn.commit()

    def unsubscribe(self, user_id, creator_id=None, platform=None):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if creator_id:
                cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND creator_id = ?', (user_id, creator_id))
            else:
                cursor.execute('DELETE FROM subscriptions WHERE user_id = ? AND platform = ?', (user_id, platform))
            conn.commit()

    def get_subscriptions(self, user_id=None):
        with self._lock, self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if user_id:
                cursor.execute('''
                    SELECT s.*, c.username, c.platform 
                    FROM subscriptions s
                    JOIN creators c ON s.creator_id = c.id
                    WHERE s.user_id = ? AND s.enabled = 1
                ''', (user_id,))
            else:
                cursor.execute('SELECT * FROM subscriptions WHERE enabled = 1')
            return [dict(row) for row in cursor.fetchall()]

    def get_subscribers(self, creator_id):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM subscriptions WHERE creator_id = ? AND enabled = 1', (creator_id,))
            return [row[0] for row in cursor.fetchall()]

    # --- Post Management ---
    def is_post_exists(self, post_id, platform):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM posts WHERE post_id = ? AND platform = ?', (post_id, platform))
            return cursor.fetchone() is not None

    def save_post(self, post_data):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            import json
            now = datetime.now().isoformat()
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO posts (
                        post_id, creator_id, platform, content, media_urls, is_ppv, price, created_at, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_data['post_id'],
                    post_data['creator_id'],
                    post_data['platform'],
                    post_data.get('content'),
                    json.dumps(post_data.get('media_urls', [])),
                    post_data.get('is_ppv', 0),
                    post_data.get('price'),
                    post_data.get('created_at'),
                    now
                ))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error("Error saving post %s: %s", post_data.get('post_id'), e)
                return False

    def get_all_creators(self):
        with self._lock, self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM creators')
            return [dict(row) for row in cursor.fetchall()]

    def update_creator_check(self, creator_id, last_post_id=None):
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            if last_post_id:
                cursor.execute('UPDATE creators SET last_post_id = ?, last_check = ? WHERE id = ?', 
                             (last_post_id, now, creator_id))
            else:
                cursor.execute('UPDATE creators SET last_check = ? WHERE id = ?', (now, creator_id))
            conn.commit()
