import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config.settings import config
from src.scripting.models import VideoScript

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeUploader:
    """
    Manages YouTube Data API v3 resumable chunked uploads (256 KB chunks),
    OAuth token auto-refresh, synthetic media compliance, and daily quota limits.
    """
    def __init__(
        self,
        client_secrets_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        daily_limit: Optional[int] = None
    ):
        self.client_secrets_file = client_secrets_file or config.youtube.client_secrets_file
        self.credentials_file = credentials_file or config.youtube.credentials_storage
        self.daily_limit = daily_limit or config.youtube.daily_upload_limit
        self.history_file = config.base_dir / "data" / "upload_history.json"
        self._ensure_history_file()

    def _ensure_history_file(self):
        if not self.history_file.exists():
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w") as f:
                json.dump({"date": str(date.today()), "count": 0, "uploads": []}, f, indent=2)

    def can_upload_today(self) -> bool:
        with open(self.history_file, "r") as f:
            data = json.load(f)
        today = str(date.today())
        if data.get("date") != today:
            data = {"date": today, "count": 0, "uploads": []}
            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        return data.get("count", 0) < self.daily_limit

    def record_upload(self, video_id: str, title: str):
        with open(self.history_file, "r") as f:
            data = json.load(f)
        today = str(date.today())
        if data.get("date") != today:
            data = {"date": today, "count": 0, "uploads": []}
        data["count"] = data.get("count", 0) + 1
        data["uploads"].append({
            "video_id": video_id,
            "title": title,
            "timestamp": datetime.now().isoformat()
        })
        with open(self.history_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_authenticated_service(self):
        creds = None
        if os.path.exists(self.credentials_file):
            try:
                creds = Credentials.from_authorized_user_file(self.credentials_file, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load credentials from file: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired YouTube OAuth access token...")
                creds.refresh(Request())
                with open(self.credentials_file, "w") as token_file:
                    token_file.write(creds.to_json())
            else:
                if not os.path.exists(self.client_secrets_file):
                    raise FileNotFoundError(
                        f"YouTube OAuth client secrets file not found at: {self.client_secrets_file}. "
                        "Please download client_secrets.json from Google Cloud Console."
                    )
                logger.info("Initiating browser OAuth 2.0 flow for YouTube upload scope...")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=8088, prompt="consent", access_type="offline")
                with open(self.credentials_file, "w") as token_file:
                    token_file.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        video_path: str,
        script: VideoScript,
        privacy_status: Optional[str] = None,
        thumbnail_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes resumable chunked upload with synthetic media policy compliance and optional custom thumbnail.
        """
        if not self.can_upload_today():
            raise RuntimeError(f"Daily upload quota reached ({self.daily_limit} videos today).")

        privacy = privacy_status or config.safety.privacy_status

        body = {
            "snippet": {
                "title": script.title[:100],
                "description": script.description[:5000],
                "tags": script.tags[:50],
                "categoryId": config.youtube.default_category_id
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                # Mandatory YouTube 2026 Altered / Synthetic Media Disclosure
                "containsSyntheticMedia": script.contains_synthetic_media
            }
        }

        # Check if client_secrets.json exists
        if not os.path.exists(self.client_secrets_file) and not os.path.exists(self.credentials_file):
            pending_dir = config.output_dir / "pending_uploads"
            pending_dir.mkdir(parents=True, exist_ok=True)
            meta_path = pending_dir / f"pending_{int(time.time())}.json"
            with open(meta_path, "w") as f:
                json.dump({"video_path": video_path, "body": body}, f, indent=2)
            
            logger.warning(
                f"YouTube OAuth credentials not configured. Video saved and queued at {meta_path}."
            )
            return {
                "status": "queued_offline",
                "message": "Video rendered and validated. Awaiting YouTube OAuth setup to publish.",
                "pending_metadata_file": str(meta_path),
                "body": body
            }

        # Proceed with YouTube API Resumable Upload
        youtube = self.get_authenticated_service()
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            chunksize=256 * 1024,  # Exact 256 KB chunks per specification
            resumable=True
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info(f"Uploading '{script.title}' to YouTube (resumable chunks)...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        logger.info(f"Upload succeeded! Video ID: {video_id}")
        self.record_upload(video_id, script.title)

        # Set custom thumbnail if provided
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                logger.info(f"Uploading custom thumbnail from {thumbnail_path}...")
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                ).execute()
                logger.info("Custom thumbnail set successfully!")
            except Exception as e:
                logger.warning(f"Setting custom thumbnail failed (channel may need phone verification): {e}")

        return {
            "status": "published",
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "privacyStatus": privacy,
            "thumbnail_path": thumbnail_path,
            "response": response
        }
