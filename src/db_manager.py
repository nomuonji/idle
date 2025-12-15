import sqlite3
import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="db/mv_data.db"):
        # Ensure db directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Table for storing video information and current status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                artist TEXT,
                view_count INTEGER,
                last_updated TIMESTAMP
            )
        ''')

        # Table for storing milestones actions to prevent double posting
        # action_type: 'achieved' or 'support'
        # milestone_value: e.g. 1000000 (1M)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                action_type TEXT, 
                milestone_value INTEGER,
                posted_at TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(video_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def update_video_stats(self, video_id, title, artist, view_count):
        """Update or insert video stats."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now()
        
        cursor.execute('''
            INSERT INTO videos (video_id, title, artist, view_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                view_count = excluded.view_count,
                last_updated = excluded.last_updated,
                title = excluded.title
        ''', (video_id, title, artist, view_count, now))
        
        conn.commit()
        conn.close()

    def get_video(self, video_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def check_history(self, video_id, action_type, milestone_value):
        """Check if we have already posted about this milestone."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM post_history 
            WHERE video_id = ? AND action_type = ? AND milestone_value = ?
        ''', (video_id, action_type, milestone_value))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def add_history(self, video_id, action_type, milestone_value):
        """Record that we posted about this milestone."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now()
        cursor.execute('''
            INSERT INTO post_history (video_id, action_type, milestone_value, posted_at)
            VALUES (?, ?, ?, ?)
        ''', (video_id, action_type, milestone_value, now))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Test
    db = DatabaseManager(db_path="../db/mv_data.db")
    db.update_video_stats("test_vid", "Test MV", "Snow Man", 100)
    print("DB Initialized and test run complete.")
