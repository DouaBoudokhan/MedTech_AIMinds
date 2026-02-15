#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Action Executor for Clipboard Concierge Agent.

Executes actions based on classified clipboard intent.
All actions are performed locally on the user's machine.
"""
import os
import sys
import webbrowser
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import platform
import re

# Set UTF-8 encoding for Windows console (only if not already wrapped)
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class ActionExecutor:
    """Executes actions based on classified intent with user confirmation."""

    def __init__(self, base_dir: Path = None):
        """Initialize the action executor.

        Args:
            base_dir: Base directory for saving generated files
        """
        self.base_dir = base_dir or Path(__file__).parent.parent.parent / "Data_Storage"
        self.concierge_dir = self.base_dir / "Clipboard_Concierge"
        self.events_dir = self.concierge_dir / "events"
        self.reminders_dir = self.concierge_dir / "reminders"
        self.behavior_file = self.concierge_dir / "behavior.json"

        self._setup_directories()
        self.auto_execute_rules = self._load_auto_execute_rules()
        self.execution_history = []

    def _setup_directories(self):
        """Create necessary directories."""
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.reminders_dir.mkdir(parents=True, exist_ok=True)

    def _load_auto_execute_rules(self) -> Dict:
        """Load auto-execute rules from behavior tracking."""
        if not self.behavior_file.exists():
            return {}

        try:
            with open(self.behavior_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('auto_execute_rules', {})
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_auto_execute_rules(self):
        """Save auto-execute rules to behavior file."""
        # Load existing data
        if self.behavior_file.exists():
            try:
                with open(self.behavior_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                data = {}
        else:
            data = {}

        # Update rules
        data['auto_execute_rules'] = self.auto_execute_rules

        # Save
        self.behavior_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.behavior_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def execute_action(
        self,
        action: str,
        content: str,
        confidence: float = 0.8,
        auto_execute: bool = False,
        data: Dict = None
    ) -> bool:
        """Execute an action with optional confirmation.

        Args:
            action: Action name (e.g., 'search_google')
            content: Clipboard content
            confidence: LLM confidence score
            auto_execute: Skip confirmation and execute directly
            data: Extracted structured data (optional)

        Returns:
            True if executed, False if skipped
        """
        # Check if we should auto-execute based on learned rules
        action_key = f"{action}:{confidence > 0.8}"

        if not auto_execute and action_key in self.auto_execute_rules:
            if self.auto_execute_rules[action_key] >= 3:  # Executed 3+ times before
                auto_execute = True

        # Confirm before executing (unless auto_execute=True)
        if not auto_execute:
            print(f"\n>>> Suggested action: {action}", flush=True)
            print(f">>> Execute this action? (y/n/a=always) ", end='', flush=True)

            try:
                response = input().strip().lower()
                if response == 'n':
                    print(">>> Skipped", flush=True)
                    return False
                elif response == 'a':
                    # Remember to auto-execute this action in future
                    self.auto_execute_rules[action_key] = self.auto_execute_rules.get(action_key, 0) + 1
                    self._save_auto_execute_rules()
                    print(f">>> Will auto-execute '{action}' in future", flush=True)
                elif response != 'y':
                    print(">>> Skipped", flush=True)
                    return False
            except (EOFError, KeyboardInterrupt):
                print("\n>>> Skipped", flush=True)
                return False

        # Execute the action
        try:
            data = data or {}
            success = self._execute(action, data, content)
            if success:
                # Track execution
                self.execution_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'action': action,
                    'content': content[:100]
                })
                print(f">>> ✓ Executed: {action}", flush=True)

                # Increment auto-execute counter
                if action_key not in self.auto_execute_rules:
                    self.auto_execute_rules[action_key] = 0
                self.auto_execute_rules[action_key] += 1
                self._save_auto_execute_rules()

                return True
            else:
                print(f">>> ✗ Failed: {action}", flush=True)
                return False
        except Exception as e:
            print(f">>> ✗ Error executing {action}: {e}", flush=True)
            return False

    def _execute(self, action: str, data: Dict, content: str) -> bool:
        """Execute a specific action."""
        action_map = {
            'create_calendar_event': self.create_calendar_event,
            'set_reminder': self.create_reminder,
            'create_reminder': self.create_reminder,
            'add_to_todo_list': self.add_to_todo_list,
            'search_stackoverflow': self.search_stackoverflow,
            'search_google': self.search_google,
            'search_youtube': self.search_youtube,
            'search_wikipedia': self.search_wikipedia,
            'search_github': self.search_github,
            'search_image': self.search_image,
            'open_in_browser': self.open_url,
            'open_url': self.open_url,
            'open_file': self.open_file,
            'show_in_folder': self.show_in_folder,
            'open_file_location': self.show_in_folder,
            'save_contact': self.save_contact,
            'save_note': self.save_note,
            'send_email': self.send_email,
            'call_phone': self.call_phone,
            'call_contact': self.call_phone,
            'extract_text': self.extract_text_from_image,
        }

        action_func = action_map.get(action)
        if not action_func:
            print(f">>> Unknown action: {action}", flush=True)
            return False

        return action_func(data, content)

    def create_calendar_event(self, data: Dict, content: str) -> bool:
        """Create a calendar event - opens Google Calendar with pre-filled info."""
        title = data.get('title', content).replace('\n', ' ').strip()
        title = title[:100]  # Limit length

        # Open Google Calendar create event page
        encoded_title = title.replace(' ', '+').replace('&', '%26')
        url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={encoded_title}"

        webbrowser.open(url)
        print(f">>> Opening Google Calendar for: {title[:60]}...", flush=True)
        return True

    def create_reminder(self, data: Dict, content: str) -> bool:
        """Create a reminder with Windows notification."""
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')

        reminder_data = {
            "id": f"reminder_{timestamp}",
            "timestamp": now.isoformat(),
            "task": data.get('task', content),
            "created_from": "clipboard",
            "status": "pending"
        }

        # Save to file
        reminder_filename = f"reminder_{timestamp}.json"
        reminder_path = self.reminders_dir / reminder_filename

        with open(reminder_path, 'w', encoding='utf-8') as f:
            json.dump(reminder_data, f, indent=2, ensure_ascii=False)

        print(f">>> Reminder saved: {reminder_data['task'][:60]}...", flush=True)

        # Try to show Windows notification
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                "Clipboard Reminder",
                reminder_data['task'][:200],
                duration=10,
                threaded=True,
                icon_path=None
            )
        except ImportError:
            print(">>> (Install 'win10toast' for popup notifications: pip install win10toast)", flush=True)

        return True

    def add_to_todo_list(self, data: Dict, content: str) -> bool:
        """Add item to todo list.

        Args:
            data: Extracted data
            content: Original clipboard content

        Returns:
            True if successful
        """
        # For now, same as creating a reminder
        return self.create_reminder(data, content)

    def search_stackoverflow(self, data: Dict, content: str) -> bool:
        """Search Stack Overflow for error or question."""
        query = data.get('error_query', content)
        # Clean up the query - remove common prefixes
        query = re.sub(r'^(error:|exception:|traceback)\s*', '', query, flags=re.IGNORECASE)
        encoded_query = query.replace(' ', '+')
        url = f"https://stackoverflow.com/search?q={encoded_query}"
        webbrowser.open(url)
        print(f">>> Searching Stack Overflow for: {query[:50]}...", flush=True)
        return True

    def search_google(self, data: Dict, content: str) -> bool:
        """Search Google."""
        query = data.get('query', content)
        encoded_query = query.replace(' ', '+')
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        print(f">>> Searching Google for: {query[:50]}...", flush=True)
        return True

    def search_wikipedia(self, data: Dict, content: str) -> bool:
        """Search Wikipedia."""
        query = data.get('query', content)
        encoded_query = query.replace(' ', '+')
        url = f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}"
        webbrowser.open(url)
        print(f">>> Searching Wikipedia for: {query[:50]}...", flush=True)
        return True

    def search_github(self, data: Dict, content: str) -> bool:
        """Search GitHub for code issues."""
        query = data.get('error_query', content)
        encoded_query = query.replace(' ', '+')
        url = f"https://github.com/search?q={encoded_query}&type=issues"
        webbrowser.open(url)
        print(f">>> Searching GitHub issues for: {query[:50]}...", flush=True)
        return True

    def search_image(self, data: Dict, content: str) -> bool:
        """Search Google Images.

        Args:
            data: Extracted data
            content: Original clipboard content (should be image description)

        Returns:
            True if successful
        """
        # Note: This would require OCR or image description
        # For now, open Google Images
        url = "https://images.google.com/"
        webbrowser.open(url)
        print(f"[ActionExecutor] Opening Google Images")
        return True

    def open_url(self, data: Dict, content: str) -> bool:
        """Open URL in default browser.

        Args:
            data: Extracted data containing URL
            content: URL to open

        Returns:
            True if successful
        """
        url = data.get('url', content)
        webbrowser.open(url)
        print(f"[ActionExecutor] Opening URL: {url}")
        return True

    def open_file(self, data: Dict, content: str) -> bool:
        """Open file with default application.

        Args:
            data: Extracted data containing file path
            content: File path

        Returns:
            True if successful
        """
        file_path = data.get('path', content)

        if not Path(file_path).exists():
            print(f"[ActionExecutor] File not found: {file_path}")
            return False

        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(['open', file_path])
        else:  # Linux
            subprocess.run(['xdg-open', file_path])

        print(f"[ActionExecutor] Opening file: {file_path}")
        return True

    def show_in_folder(self, data: Dict, content: str) -> bool:
        """Show file in file explorer.

        Args:
            data: Extracted data containing file path
            content: File path

        Returns:
            True if successful
        """
        file_path = data.get('path', content)

        if not Path(file_path).exists():
            print(f"[ActionExecutor] File not found: {file_path}")
            return False

        if platform.system() == "Windows":
            subprocess.run(['explorer', '/select,', file_path])
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(['open', '-R', file_path])
        else:  # Linux
            subprocess.run(['nautilus', file_path])

        print(f"[ActionExecutor] Showing file in folder: {file_path}")
        return True

    def save_contact(self, data: Dict, content: str) -> bool:
        """Parse and save contact information."""
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')

        # Extract contact info from content
        lines = content.strip().split('\n')

        contact_data = {
            "id": f"contact_{timestamp}",
            "timestamp": now.isoformat(),
            "name": data.get('name', lines[0] if lines else 'Unknown'),
            "email": data.get('email', ''),
            "phone": data.get('phone', ''),
            "raw_content": content,
            "created_from": "clipboard"
        }

        # Auto-extract email if not in data
        if not contact_data['email']:
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)
            if email_match:
                contact_data['email'] = email_match.group()

        # Auto-extract phone if not in data
        if not contact_data['phone']:
            phone_match = re.search(r'(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?', content)
            if phone_match:
                contact_data['phone'] = phone_match.group()

        # Save to file
        contact_path = self.concierge_dir / "contacts" / f"contact_{timestamp}.json"
        contact_path.parent.mkdir(parents=True, exist_ok=True)

        with open(contact_path, 'w', encoding='utf-8') as f:
            json.dump(contact_data, f, indent=2, ensure_ascii=False)

        print(f">>> Contact saved: {contact_data['name']}", flush=True)
        if contact_data['email']:
            print(f"    Email: {contact_data['email']}", flush=True)
        if contact_data['phone']:
            print(f"    Phone: {contact_data['phone']}", flush=True)

        return True

    def send_email(self, data: Dict, content: str) -> bool:
        """Open email composer with pre-filled info."""
        # Extract email from content or data
        email = data.get('email', '')
        if not email:
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)
            if email_match:
                email = email_match.group()
            else:
                print(">>> No email address found", flush=True)
                return False

        # Extract subject from first line
        lines = content.strip().split('\n')
        subject = lines[0][:100] if lines else content[:100]

        mailto_link = f"mailto:{email}?subject={subject}"
        webbrowser.open(mailto_link)
        print(f">>> Opening email client for: {email}", flush=True)
        return True

    def call_phone(self, data: Dict, content: str) -> bool:
        """Initiate phone call using tel: protocol."""
        phone = data.get('phone', '')

        # Extract phone if not in data
        if not phone:
            phone_match = re.search(r'(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})', content)
            if phone_match:
                phone = phone_match.group()
            else:
                print(">>> No phone number found", flush=True)
                return False

        # Clean phone number
        phone = phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')

        # Open with tel: protocol
        url = f"tel:{phone}"
        webbrowser.open(url)
        print(f">>> Initiating call to: {phone}", flush=True)
        return True

    def call_contact(self, data: Dict, content: str) -> bool:
        """Alias for call_phone."""
        return self.call_phone(data, content)

    def search_youtube(self, data: Dict, content: str) -> bool:
        """Search YouTube."""
        query = data.get('query', content)
        encoded_query = query.replace(' ', '+')
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        print(f">>> Searching YouTube for: {query[:50]}...", flush=True)
        return True

    def save_note(self, data: Dict, content: str) -> bool:
        """Save a note to a file."""
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')

        note_data = {
            "id": f"note_{timestamp}",
            "timestamp": now.isoformat(),
            "content": content,
            "created_from": "clipboard",
            "tags": []
        }

        # Save to notes file
        notes_dir = self.concierge_dir / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        note_filename = f"note_{timestamp}.json"
        note_path = notes_dir / note_filename

        with open(note_path, 'w', encoding='utf-8') as f:
            json.dump(note_data, f, indent=2, ensure_ascii=False)

        print(f">>> Note saved: {content[:60]}...", flush=True)
        print(f"    Location: {note_path}", flush=True)

        # Also append to a master notes.txt file for easy reading
        notes_txt = notes_dir / "notes.txt"
        with open(notes_txt, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Date: {now.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"{content}\n")

        return True

    def extract_text_from_image(self, data: Dict, content: str) -> bool:
        """Extract text from image using OCR.

        Args:
            data: Extracted data
            content: Original clipboard content

        Returns:
            True if successful
        """
        print(f"[ActionExecutor] OCR not yet implemented")
        print(f"  -> Would extract text from clipboard image")
        return False
