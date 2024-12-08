from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import pickle
import os
import io
from typing import Optional, Dict, List, Union
from config.settings import Settings

settings = Settings()


class GoogleDriveManager:
    def __init__(self):
        # If modifying these scopes, delete the file token.pickle
        self.SCOPES = ["https://www.googleapis.com/auth/drive.file"]
        self.creds = None

    def authenticate(self):
        """Handle Google Drive authentication"""
        # Load existing credentials if available
        pickle_path = os.path.join(settings.CREDENTIALS_DIR, "token.pickle")
        if os.path.exists(pickle_path):
            with open(pickle_path, "rb") as token:
                self.creds = pickle.load(token)

        # If credentials are invalid or don't exist, get new ones
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                creditials_path = os.path.join(
                    settings.CREDENTIALS_DIR, "credentials.json"
                )
                flow = InstalledAppFlow.from_client_secrets_file(
                    creditials_path, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(pickle_path, "wb") as token:
                pickle.dump(self.creds, token)

        return build("drive", "v3", credentials=self.creds)

    def upload_file(self, file_path, share_publicly=True):
        """
        Upload a video or CSV file to Google Drive and optionally make it public.
        Returns: File ID and shareable link.
        """
        try:
            # Authenticate with Google Drive API
            service = self.authenticate()

            # Get file extension
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()

            # Determine MIME type and file metadata
            if file_extension in [".mp4", ".avi", ".mov", ".mkv"]:
                mime_type = "video/*"
            elif file_extension == ".csv":
                mime_type = "text/csv"
            else:
                raise ValueError(
                    "Unsupported file type. Only video and CSV files are allowed."
                )

            file_metadata = {"name": os.path.basename(file_path)}

            # Create media file upload object
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

            # Upload the file
            print("Uploading file...")
            file = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )

            file_id = file.get("id")

            # Make the file public if requested
            if share_publicly:
                permission = {"type": "anyone", "role": "reader"}
                service.permissions().create(fileId=file_id, body=permission).execute()

                # Get the sharing link
                file = (
                    service.files().get(fileId=file_id, fields="webViewLink").execute()
                )
                return {"file_id": file_id, "sharing_link": file["webViewLink"]}

            return {"file_id": file_id}

        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None

    def download_video(self, file_id, save_path):
        """
        Download a video from Google Drive using file ID
        """
        try:
            service = self.authenticate()

            # Create download request
            request = service.files().get_media(fileId=file_id)

            # Create a bytes IO stream
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            # Download the file
            print("Downloading video...")
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    print(f"Download Progress: {int(status.progress() * 100)}%")

            # Save the file
            fh.seek(0)
            with open(save_path, "wb") as f:
                f.write(fh.read())
                f.flush()

            return True

        except Exception as e:
            print(f"Error downloading video: {str(e)}")
            return False

    def list_video_files(self, page_size=10):
        """List video files in Google Drive"""
        try:
            service = self.authenticate()

            # Search for video files
            query = "mimeType contains 'video/'"
            results = (
                service.files()
                .list(
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, mimeType, webViewLink, createdTime)",
                    q=query,
                )
                .execute()
            )

            return results.get("files", [])

        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []

    def make_file_public(self, file_id):
        """Make a file public and return its public link"""
        try:
            service = self.authenticate()

            # Create public permission
            permission = {"type": "anyone", "role": "reader"}

            # Apply the permission to the file
            service.permissions().create(fileId=file_id, body=permission).execute()

            return True
        except Exception as e:
            print(f"Error making file public: {str(e)}")
            return False

    def get_download_link(self, file_id):
        """
        Generate direct download link for a file
        Returns both direct download link and web view link
        """
        try:
            service = self.authenticate()

            # Make sure the file is public first
            if not self.make_file_public(file_id):
                raise Exception("Failed to make file public")

            # Get file metadata
            file = (
                service.files()
                .get(fileId=file_id, fields="webViewLink, webContentLink")
                .execute()
            )

            # Generate direct download link
            direct_download_link = (
                f"https://drive.google.com/uc?export=download&id={file_id}"
            )

            return {
                "direct_download_link": direct_download_link,
                "web_view_link": file.get("webViewLink"),
                "web_content_link": file.get("webContentLink"),
            }

        except Exception as e:
            print(f"Error generating download link: {str(e)}")
            return None

    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.

        Args:
            file_id: The ID of the file to delete

        Returns:
            bool: True if deletion was successful, False otherwise

        Raises:
            Exception: If deletion fails
        """
        try:
            service = self.authenticate()
            service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            raise Exception(f"Error deleting file: {str(e)}")

    def delete_multiple_files(self, file_ids: List[str]) -> Dict[str, List[str]]:
        """
        Delete multiple files from Google Drive.

        Args:
            file_ids: List of file IDs to delete

        Returns:
            Dict containing lists of successfully and failed deletions
        """
        results = {"succeeded": [], "failed": []}

        for file_id in file_ids:
            try:
                if self.delete_file(file_id):
                    results["succeeded"].append(file_id)
            except Exception:
                results["failed"].append(file_id)

        return results
