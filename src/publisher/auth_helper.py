import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate():
    client_secrets = Path("client_secrets.json")
    credentials_storage = Path("oauth_credentials.json")

    if not client_secrets.exists():
        print("❌ Error: client_secrets.json not found in the current working directory.")
        return

    print("🔑 Starting YouTube OAuth 2.0 Authorization Flow...")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    
    # Run local server; on macOS this will automatically open the browser to authenticate
    creds = flow.run_local_server(port=8088, prompt="consent", access_type="offline")
    
    with open(credentials_storage, "w") as token_file:
        token_file.write(creds.to_json())
        
    print(f"✅ Authorization successful! Credentials saved to {credentials_storage}")
    print("🚀 Video Autopilot can now publish directly to your YouTube channel autonomously!")

if __name__ == "__main__":
    authenticate()
