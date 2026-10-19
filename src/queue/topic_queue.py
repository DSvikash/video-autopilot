import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from config.settings import config

logger = logging.getLogger(__name__)

class TopicQueue:
    """
    SQLite-backed persistent topic queue matching n8n shorts_topic_queue table.
    Enables queuing topics via Web Form, API, or CLI, with automatic status progression:
    'queued' -> 'processing' -> 'uploaded_private' (or 'failed').
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (config.base_dir / "data" / "shorts_topic_queue.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shorts_topic_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    genre TEXT DEFAULT 'explainer',
                    status TEXT DEFAULT 'queued',
                    video_title TEXT DEFAULT '',
                    youtube_video_id TEXT DEFAULT '',
                    video_path TEXT DEFAULT '',
                    altered_content_needed BOOLEAN DEFAULT 1,
                    error_message TEXT DEFAULT '',
                    source TEXT DEFAULT 'cli',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            """)
            conn.commit()

    def enqueue(self, topic: str, genre: str = "explainer", source: str = "form") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO shorts_topic_queue (topic, genre, status, source) VALUES (?, ?, 'queued', ?)",
                (topic, genre, source)
            )
            conn.commit()
            return cursor.lastrowid

    def get_next_queued(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shorts_topic_queue WHERE status = 'queued' ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def mark_processing(self, row_id: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE shorts_topic_queue SET status = 'processing' WHERE id = ?",
                (row_id,)
            )
            conn.commit()

    def mark_uploaded(self, row_id: int, video_title: str, youtube_video_id: str, video_path: str):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE shorts_topic_queue
                SET status = 'uploaded_private',
                    video_title = ?,
                    youtube_video_id = ?,
                    video_path = ?,
                    processed_at = ?
                WHERE id = ?
            """, (video_title, youtube_video_id, video_path, datetime.now().isoformat(), row_id))
            conn.commit()

    def mark_failed(self, row_id: int, error_message: str):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE shorts_topic_queue
                SET status = 'failed',
                    error_message = ?,
                    processed_at = ?
                WHERE id = ?
            """, (error_message, datetime.now().isoformat(), row_id))
            conn.commit()

    def list_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shorts_topic_queue ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]
