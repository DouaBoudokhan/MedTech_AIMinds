#!/usr/bin/env python3
"""Google Calendar Watcher - MemoryOS Data Ingestion Module

Monitors Google Calendar for events and stores them in standardized MemoryOS schema.
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import pickle

# Google Calendar API libraries
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'credentials.json'
POLL_INTERVAL = 300  # Check every 5 minutes (300 seconds)
LOOKAHEAD_DAYS = 30  # Look ahead 30 days for events
DATA_STORAGE = Path(__file__).parent.parent.parent / "Data_Storage"
EVENTS_DIR = DATA_STORAGE / "Calendar" / "events"
METADATA_FILE = DATA_STORAGE / "Calendar" / "metadata.json"


class CalendarWatcher:
    """Monitors Google Calendar and captures events."""

    def __init__(self, base_dir: Path = None):
        """Initialize the calendar watcher."""
        self.base_dir = base_dir or Path(__file__).parent
        self.events_dir = EVENTS_DIR
        self.metadata_file = METADATA_FILE
        self.credentials_file = self.base_dir / CREDENTIALS_FILE
        self.token_file = self.base_dir / TOKEN_FILE

        self.service = None
        self.seen_events = {}  # event_id: last_seen_timestamp

        self._setup_directories()
        self._authenticate()

    def _setup_directories(self):
        """Create necessary directories."""
        self.events_dir.mkdir(parents=True, exist_ok=True)
        print(f"[CalendarWatcher] Events -> {self.events_dir.absolute()}")
        print(f"[CalendarWatcher] Metadata -> {self.metadata_file.absolute()}")

    def _authenticate(self):
        """Authenticate with Google Calendar API."""
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
                    print("\nTo set up Google Calendar API access:")
                    print("1. Go to: https://console.cloud.google.com/")
                    print("2. Create a new project")
                    print("3. Enable Google Calendar API")
                    print("4. Create OAuth 2.0 credentials (Desktop app)")
                    print("5. Download credentials.json")
                    print("6. Save it to:", self.credentials_file.absolute())
                    print("\nPress Enter when credentials.json is ready...")
                    input()

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('calendar', 'v3', credentials=creds)
        print("[CalendarWatcher] Authenticated with Google Calendar")

    def _get_calendar_id(self):
        """Get the primary calendar ID."""
        try:
            calendar_list = self.service.calendarList().list().execute()
            for calendar in calendar_list.get('items', []):
                if calendar.get('primary'):
                    return calendar['id']
            return 'primary'  # Default to primary
        except Exception as e:
            print(f"[CalendarWatcher] Error getting calendar: {e}")
            return 'primary'

    def _is_duplicate(self, event_id: str, event_hash: str) -> bool:
        """Check if event has already been captured."""
        if event_id in self.seen_events:
            return True
        self.seen_events[event_id] = datetime.now()
        return False

    def _create_event_hash(self, event):
        """Create unique hash for event to detect changes."""
        hash_data = f"{event.get('id')}{event.get('updated')}{event.get('summary')}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    def _save_event(self, event, calendar_id: str):
        """Save event to individual JSON file and update metadata."""
        event_id = event.get('id', 'unknown')
        event_hash = self._create_event_hash(event)
        timestamp = datetime.now().isoformat()

        # Extract event data
        event_data = {
            "google_event_id": event_id,
            "calendar_id": calendar_id,
            "title": event.get('summary', 'No Title'),
            "description": event.get('description', ''),
            "location": event.get('location', ''),
            "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
            "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
            "status": event.get('status', 'confirmed'),
            "created": event.get('created'),
            "updated": event.get('updated'),
            "attendees": event.get('attendees', []),
            "creator": event.get('creator', {}),
            "organizer": event.get('organizer', {}),
            "hangout_link": event.get('hangoutLink', ''),
            "conference_data": event.get('conferenceData', {}),
            "transparency": event.get('transparency', ''),
            "visibility": event.get('visibility', ''),
        }

        # Save individual event file
        event_filename = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{event_hash[:8]}.json"
        event_path = self.events_dir / event_filename

        with open(event_path, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, indent=2, ensure_ascii=False)

        # Create metadata entry (MemoryOS standard schema)
        metadata_entry = {
            "id": event_hash,
            "timestamp": timestamp,
            "content_type": "calendar_event",
            "content_preview": f"{event.get('summary', 'No Title')} - {event_data['start']}",
            "file_path": str(event_path.relative_to(self.base_dir)),
            "source": "google_calendar",
            "event_details": {
                "title": event.get('summary', 'No Title'),
                "start": event_data['start'],
                "end": event_data['end'],
                "location": event.get('location', ''),
                "attendee_count": len(event.get('attendees', [])),
                "has_description": bool(event.get('description'))
            }
        }

        # Update metadata.json
        self._update_metadata(metadata_entry)

        return event_filename

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

    def _fetch_events(self):
        """Fetch events from Google Calendar."""
        calendar_id = self._get_calendar_id()

        # Calculate time range
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=LOOKAHEAD_DAYS)).isoformat() + 'Z'

        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])

        except Exception as e:
            print(f"[CalendarWatcher] Error fetching events: {e}")
            return []

    def poll_once(self):
        """Poll calendar once for new events."""
        print(f"\n[CalendarWatcher] Polling for events...")

        events = self._fetch_events()
        new_events = 0

        for event in events:
            event_id = event.get('id')
            event_hash = self._create_event_hash(event)

            if not self._is_duplicate(event_id, event_hash):
                event_file = self._save_event(event, self._get_calendar_id())
                print(f"  -> Captured: {event.get('summary', 'No Title')} ({event.get('start', {}).get('dateTime', 'No date')})")
                new_events += 1

        if new_events == 0:
            print(f"  -> No new events found")
        else:
            print(f"  -> Total new events: {new_events}")

        return new_events

    def run(self):
        """Run continuous polling loop."""
        print(f"\n[CalendarWatcher] Started monitoring calendar")
        print(f"[CalendarWatcher] Poll interval: {POLL_INTERVAL}s")
        print(f"[CalendarWatcher] Lookahead: {LOOKAHEAD_DAYS} days")
        print("[CalendarWatcher] Press Ctrl+C to stop\n")

        try:
            while True:
                self.poll_once()
                import time
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[CalendarWatcher] Stopped by user")
            print(f"[CalendarWatcher] Total events captured: {len(self.seen_events)}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("GOOGLE CALENDAR WATCHER - MemoryOS")
    print("=" * 60)

    watcher = CalendarWatcher()
    watcher.run()


if __name__ == "__main__":
    main()
