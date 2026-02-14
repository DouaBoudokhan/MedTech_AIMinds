#!/usr/bin/env python3
"""Gmail Watcher - MemoryOS Data Ingestion Module

Monitors Gmail for new emails and stores them in standardized MemoryOS schema.
"""
import os
import json
import hashlib
import base64
import email
from datetime import datetime, timedelta
from pathlib import Path
import pickle
from email.header import decode_header

# Google Gmail API libraries
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'credentials.json'
POLL_INTERVAL = 300  # Check every 5 minutes
LOOKBACK_MINUTES = 10  # Look back 10 minutes for new emails
DATA_STORAGE = Path(__file__).parent.parent.parent / "Data_Storage"
EMAILS_DIR = DATA_STORAGE / "Email" / "emails"
METADATA_FILE = DATA_STORAGE / "Email" / "metadata.json"


class EmailWatcher:
    """Monitors Gmail for new emails and captures them."""

    def __init__(self, base_dir: Path = None):
        """Initialize the email watcher."""
        self.base_dir = base_dir or Path(__file__).parent
        self.emails_dir = EMAILS_DIR
        self.metadata_file = METADATA_FILE
        self.credentials_file = self.base_dir.parent / 'Calendar' / CREDENTIALS_FILE
        self.token_file = self.base_dir / TOKEN_FILE

        self.service = None
        self.seen_emails = {}  # message_id: last_seen_timestamp

        self._setup_directories()
        self._authenticate()

    def _setup_directories(self):
        """Create necessary directories."""
        self.emails_dir.mkdir(parents=True, exist_ok=True)
        print(f"[EmailWatcher] Emails -> {self.emails_dir.absolute()}")
        print(f"[EmailWatcher] Metadata -> {self.metadata_file.absolute()}")

    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None

        # Load existing token if available
        if self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    print("\n" + "="*60)
                    print("CREDENTIALS FILE NOT FOUND")
                    print("="*60)
                    print("\nUsing Calendar credentials for Gmail access...")
                    print("Expected at:", self.credentials_file.absolute())
                    print("\nPress Enter if credentials exist, or Ctrl+C to cancel...")
                    input()

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        print("[EmailWatcher] Authenticated with Gmail")

    def _decode_header(self, header):
        """Decode email header."""
        if not header:
            return ""

        decoded = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                decoded.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                decoded.append(str(part))
        return ''.join(decoded)

    def _is_duplicate(self, message_id: str) -> bool:
        """Check if email has already been captured."""
        if message_id in self.seen_emails:
            return True
        self.seen_emails[message_id] = datetime.now()
        return False

    def _create_email_hash(self, message):
        """Create unique hash for email."""
        hash_data = f"{message.get('id')}{message.get('internalDate')}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    def _get_email_body(self, message):
        """Extract email body from message."""
        body = ""
        payload = message.get('payload', {})

        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part.get('mimeType') == 'text/html':
                    data = part['body'].get('data', '')
                    if data and not body:  # Only use HTML if no plain text
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return body

    def _save_email(self, message):
        """Save email to individual JSON file and update metadata."""
        message_id = message.get('id')
        email_hash = self._create_email_hash(message)
        timestamp = datetime.now().isoformat()

        # Extract email headers
        payload = message.get('payload', {})
        headers = {h['name']: h['value'] for h in payload.get('headers', [])}

        # Parse email data
        email_data = {
            "gmail_message_id": message_id,
            "thread_id": message.get('threadId'),
            "subject": self._decode_header(headers.get('Subject', '')),
            "from": self._decode_header(headers.get('From', '')),
            "to": self._decode_header(headers.get('To', '')),
            "cc": self._decode_header(headers.get('Cc', '')),
            "bcc": self._decode_header(headers.get('Bcc', '')),
            "date": headers.get('Date', ''),
            "snippet": message.get('snippet', ''),
            "body": self._get_email_body(message),
            "label_ids": message.get('labelIds', []),
            "history_id": message.get('historyId'),
            "internal_date": message.get('internalDate'),
        }

        # Save individual email file
        email_filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{email_hash[:8]}.json"
        email_path = self.emails_dir / email_filename

        with open(email_path, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)

        # Create metadata entry (MemoryOS standard schema)
        metadata_entry = {
            "id": email_hash,
            "timestamp": timestamp,
            "content_type": "email",
            "content_preview": f"{email_data['subject']} - from {email_data['from']}",
            "file_path": str(email_path.relative_to(self.base_dir)),
            "source": "gmail",
            "email_details": {
                "subject": email_data['subject'],
                "from": email_data['from'],
                "to": email_data['to'],
                "date": email_data['date'],
                "is_unread": 'UNREAD' in message.get('labelIds', []),
                "has_attachments": 'ATTACHMENT' in message.get('labelIds', []),
                "label_ids": message.get('labelIds', [])
            }
        }

        # Update metadata.json
        self._update_metadata(metadata_entry)

        return email_filename

    def _update_metadata(self, entry):
        """Append entry to metadata.json."""
        metadata = []

        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                try:
                    metadata = json.load(f)
                except json.JSONDecodeError:
                    metadata = []

        metadata.append(entry)

        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _fetch_emails(self):
        """Fetch emails from Gmail."""
        try:
            # Calculate time range (last 10 minutes)
            time_min = (datetime.utcnow() - timedelta(minutes=LOOKBACK_MINUTES)).isoformat() + 'Z'

            # Search for emails in inbox
            results = self.service.users().messages().list(
                userId='me',
                q=f'after:{int((datetime.utcnow() - timedelta(minutes=LOOKBACK_MINUTES)).timestamp())}'
            ).execute()

            messages = results.get('messages', [])

            # Fetch full message details
            full_messages = []
            for msg in messages[:20]:  # Limit to 20 most recent
                msg_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                full_messages.append(msg_detail)

            return full_messages

        except Exception as e:
            print(f"[EmailWatcher] Error fetching emails: {e}")
            return []

    def poll_once(self):
        """Poll Gmail once for new emails."""
        print(f"\n[EmailWatcher] Polling for new emails...")

        messages = self._fetch_emails()
        new_emails = 0

        for message in messages:
            message_id = message.get('id')

            if not self._is_duplicate(message_id):
                email_file = self._save_email(message)
                subject = self._decode_header(
                    {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}.get('Subject', '(No subject)')
                )
                print(f"  -> Captured: {subject}")
                new_emails += 1

        if new_emails == 0:
            print(f"  -> No new emails found")
        else:
            print(f"  -> Total new emails: {new_emails}")

        return new_emails

    def run(self):
        """Run continuous polling loop."""
        print(f"\n[EmailWatcher] Started monitoring Gmail")
        print(f"[EmailWatcher] Poll interval: {POLL_INTERVAL}s")
        print(f"[EmailWatcher] Lookback: {LOOKBACK_MINUTES} minutes")
        print("[EmailWatcher] Press Ctrl+C to stop\n")

        try:
            while True:
                self.poll_once()
                import time
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[EmailWatcher] Stopped by user")
            print(f"[EmailWatcher] Total emails captured: {len(self.seen_emails)}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("GMAIL WATCHER - MemoryOS")
    print("=" * 60)

    watcher = EmailWatcher()
    watcher.run()


if __name__ == "__main__":
    main()
