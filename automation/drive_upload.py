#!/usr/bin/env python3
"""Upload a file to a Google Drive folder using a service account.

Usage:
    DRIVE_SA_JSON='{...service account key...}' DRIVE_FOLDER_ID=xxx \\
        python3 drive_upload.py path/to/video.mp4 "My Reel.mp4"

Env:
    DRIVE_SA_JSON     full service-account JSON key (as a single string)
    DRIVE_FOLDER_ID   target folder id (from the share link: drive/folders/<ID>)

Requires: pip install google-api-python-client google-auth  (stdlib cannot do
Google OAuth/JWT signing). GitHub Actions runners install them in one step.

The service account must be added as an Editor on the shared Drive folder:
    Google Cloud Console -> IAM & Admin -> Service Accounts -> create ->
    Keys -> Add key -> JSON. Copy the JSON, then open the Drive folder ->
    Share -> paste the service account email (e.g. xyz@project.iam.gserviceaccount.com).

Prints: {"file_id": "...", "name": "...", "webViewLink": "..."}
"""

import json
import os
import sys


def main() -> int:
    sa_json = os.environ.get("DRIVE_SA_JSON", "").strip()
    folder_id = os.environ.get("DRIVE_FOLDER_ID", "").strip()
    if len(sys.argv) < 3:
        print("usage: drive_upload.py <file_path> <drive_file_name>", file=sys.stderr)
        return 2
    file_path, file_name = sys.argv[1], sys.argv[2]
    if not sa_json:
        print("error: DRIVE_SA_JSON env is missing (service account key)", file=sys.stderr)
        return 1
    if not folder_id:
        print("error: DRIVE_FOLDER_ID env is missing", file=sys.stderr)
        return 1

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("error: google-api-python-client not installed. Run: pip install google-api-python-client google-auth", file=sys.stderr)
        return 1

    info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    mime = "video/mp4" if file_path.lower().endswith((".mp4", ".m4v")) else "application/octet-stream"
    metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype=mime, resumable=True)
    f = service.files().create(body=metadata, media_body=media, fields="id,name,webViewLink").execute()

    result = {"file_id": f.get("id"), "name": f.get("name"), "webViewLink": f.get("webViewLink")}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
