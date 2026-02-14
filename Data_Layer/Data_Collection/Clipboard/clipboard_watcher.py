#!/usr/bin/env python3
"""
MemoryOS - Clipboard Monitoring Module
Automatically captures text, images, HTML, URLs, and files from clipboard for local data ingestion.
Cross-platform: Windows (primary), macOS/Linux fallbacks noted.
"""

import os
import json
import time
import hashlib
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# Core dependencies
import pyperclip
from PIL import ImageGrab, Image

# Windows-specific clipboard formats
try:
    import win32clipboard
    WINDOWS_SUPPORT = True
except ImportError:
    WINDOWS_SUPPORT = False

# Configuration
POLL_INTERVAL = 1.0  # seconds
DEDUP_WINDOW = 5.0  # seconds - skip identical content within this window
DATA_STORAGE = Path(__file__).parent.parent.parent / "Data_Storage"
METADATA_FILE = DATA_STORAGE / "Clipboard" / "metadata.json"
IMAGES_FOLDER = DATA_STORAGE / "Clipboard" / "images"
FILES_FOLDER = DATA_STORAGE / "Clipboard" / "files"
COPIED_FILES_FOLDER = DATA_STORAGE / "Clipboard" / "copied_files"
CONTENT_PREVIEW_LENGTH = 200


class ClipboardWatcher:
    """Monitors system clipboard for text, images, HTML, URLs, and file changes."""

    def __init__(self, base_dir: str = None):
        """Initialize watcher with directory structure."""
        if base_dir is None:
            # Default to script's directory
            self.base_dir = Path(__file__).parent.absolute()
        else:
            self.base_dir = Path(base_dir)

        self.images_dir = IMAGES_FOLDER
        self.files_dir = FILES_FOLDER
        self.copied_files_dir = COPIED_FILES_FOLDER
        self.metadata_path = METADATA_FILE

        # Deduplication tracking: {content_hash: timestamp}
        self.recent_captures = {}

        # Last clipboard state to detect changes
        self.last_text = None
        self.last_image_hash = None
        self.last_files_hash = None

        # Setup directories
        self._setup_directories()

    def _setup_directories(self):
        """Create required folder structure on startup."""
        try:
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.files_dir.mkdir(parents=True, exist_ok=True)
            self.copied_files_dir.mkdir(parents=True, exist_ok=True)

            # Create data/text directory for metadata
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

            # Initialize metadata file if it doesn't exist
            if not self.metadata_path.exists():
                self._write_metadata([])

            print(f"[ClipboardWatcher] Initialized at {self.base_dir}")
            print(f"[ClipboardWatcher] Images -> {self.images_dir}")
            print(f"[ClipboardWatcher] Files -> {self.files_dir}")
            print(f"[ClipboardWatcher] Copied Files -> {self.copied_files_dir}")
            print(f"[ClipboardWatcher] Metadata -> {self.metadata_path}")
        except Exception as e:
            print(f"[ClipboardWatcher] Setup error: {e}")
            raise

    def _generate_content_hash(self, content: str | bytes) -> str:
        """Generate MD5 hash for deduplication."""
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        return hashlib.md5(content_bytes).hexdigest()

    def _read_metadata(self) -> list:
        """Read existing metadata entries."""
        try:
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"[ClipboardWatcher] Error reading metadata: {e}")
            return []

    def _write_metadata(self, entries: list):
        """Write metadata entries to file."""
        try:
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ClipboardWatcher] Error writing metadata: {e}")

    def _append_metadata_entry(self, entry: dict):
        """Append new metadata entry (preserve existing entries)."""
        try:
            entries = self._read_metadata()
            entries.append(entry)
            self._write_metadata(entries)
        except Exception as e:
            print(f"[ClipboardWatcher] Error appending metadata: {e}")

    def _cleanup_old_captures(self):
        """Remove dedup entries older than the window."""
        cutoff = datetime.now() - timedelta(seconds=DEDUP_WINDOW)
        expired = [
            h for h, ts in self.recent_captures.items()
            if ts <= cutoff
        ]
        for h in expired:
            del self.recent_captures[h]

    def _is_duplicate(self, content_hash: str) -> bool:
        """Check if content was captured within dedup window."""
        now = datetime.now()

        # Check if content was captured recently (within dedup window)
        if content_hash in self.recent_captures:
            last_captured = self.recent_captures[content_hash]
            time_since = (now - last_captured).total_seconds()

            # If captured within dedup window, it's a duplicate
            if time_since < DEDUP_WINDOW:
                return True

        # Clean up old entries periodically
        self._cleanup_old_captures()

        # Mark this content as seen NOW to prevent race conditions
        # This ensures that if the same content is checked again
        # within the same poll or in rapid succession, it will be
        # recognized as a duplicate
        self.recent_captures[content_hash] = now
        return False

    def _capture_text(self, text: str) -> dict | None:
        """Capture text from clipboard."""
        if not text or not text.strip():
            return None

        content_hash = self._generate_content_hash(text)

        if self._is_duplicate(content_hash):
            return None

        # Create metadata entry
        entry = {
            "id": content_hash,
            "timestamp": datetime.now().isoformat(),
            "content_type": "text",
            "content_preview": text[:CONTENT_PREVIEW_LENGTH],
            "file_path": None,
            "source": "clipboard"
        }

        self._append_metadata_entry(entry)
        print(f"✅ Captured text: {entry['content_preview'][:100]}...")

        return entry

    def _capture_image(self, image: Image.Image) -> dict | None:
        """Capture image from clipboard."""
        if image is None:
            return None

        # Generate hash from image bytes
        import io
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        image_data = img_bytes.read()

        content_hash = self._generate_content_hash(image_data)

        if self._is_duplicate(content_hash):
            return None

        # Save image file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"clip_{timestamp}.png"
        file_path = self.images_dir / filename

        try:
            image.save(file_path, 'PNG')

            # Get file size
            file_size = file_path.stat().st_size

            # Create metadata entry with image details
            entry = {
                "id": content_hash,
                "timestamp": datetime.now().isoformat(),
                "content_type": "image",
                "content_preview": f"Image captured ({image.width}x{image.height}, {file_size} bytes)",
                "file_path": str(file_path.relative_to(self.base_dir)),
                "source": "clipboard",
                "image_info": {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format or "PNG",
                    "mode": image.mode,
                    "size_bytes": file_size
                }
            }

            self._append_metadata_entry(entry)
            print(f"✅ Captured image: {filename} ({image.width}x{image.height}, {file_size} bytes)")

            return entry

        except Exception as e:
            print(f"[ClipboardWatcher] Error saving image: {e}")
            return None

    def _get_clipboard_image(self) -> Image.Image | None:
        """
        Get image from clipboard.
        Windows: Uses ImageGrab.grabclipboard()
        macOS/Linux: Falls back gracefully (not implemented for this hackathon)
        """
        try:
            # Windows primary method
            image = ImageGrab.grabclipboard()

            # ImageGrab returns None for text, or Image for images
            if isinstance(image, Image.Image):
                return image

            return None

        except Exception as e:
            # Silent failure - permission errors, unsupported platform, etc.
            return None

    def _extract_urls(self, text: str) -> list:
        """Extract URLs from text using regex."""
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls

    def _is_url_only(self, text: str) -> bool:
        """Check if text is ONLY a URL."""
        text = text.strip()
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc]) and not any(c.isspace() for c in text)
        except:
            return False

    def _get_clipboard_files(self) -> list | None:
        """
        Get file paths from clipboard (Windows only).
        Returns list of file paths or None if no files.
        """
        if not WINDOWS_SUPPORT:
            return None

        try:
            win32clipboard.OpenClipboard()
            try:
                # Check for file list format (CF_HDROP = 15)
                if win32clipboard.IsClipboardFormatAvailable(15):
                    file_data = win32clipboard.GetClipboardData(15)

                    # Handle both string and tuple return types
                    if isinstance(file_data, tuple):
                        # Extract the actual data from tuple
                        file_data = file_data[0] if file_data else ""

                    # Parse file list
                    files = file_data.split('\x00')
                    # Remove empty strings and return
                    files = [f for f in files if f and not f.endswith('\x00')]
                    return files if files else None
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            # Silent failure - clipboard may be unavailable
            pass

        return None

    def _capture_url(self, url: str) -> dict | None:
        """Capture URL from clipboard."""
        if not url or not url.strip():
            return None

        content_hash = self._generate_content_hash(url)

        if self._is_duplicate(content_hash):
            return None

        # Create metadata entry (URLs stored in metadata, not separate files)
        entry = {
            "id": content_hash,
            "timestamp": datetime.now().isoformat(),
            "content_type": "url",
            "content_preview": url.strip(),
            "file_path": None,
            "source": "clipboard"
        }

        self._append_metadata_entry(entry)
        print(f"✅ Captured URL: {url.strip()}")

        return entry

    def _capture_files(self, files: list) -> dict | None:
        """Capture file list from clipboard."""
        if not files:
            return None

        # Create hash from sorted file list
        files_str = '\x00'.join(sorted(files))
        content_hash = self._generate_content_hash(files_str)

        if self._is_duplicate(content_hash):
            return None

        # Save file list to JSON file in data/files/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"files_{timestamp}.json"
        file_path = self.files_dir / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "file_paths": files,
                    "count": len(files)
                }, f, indent=2, ensure_ascii=False)

            # Copy actual files to data/copied_files/
            copied_file_paths = []
            for original_path in files:
                try:
                    import shutil
                    original_path_obj = Path(original_path)
                    if original_path_obj.exists():
                        # Create same filename in copied_files directory
                        copied_path = self.copied_files_dir / original_path_obj.name
                        shutil.copy2(original_path_obj, copied_path)
                        copied_file_paths.append(str(copied_path.relative_to(self.base_dir)))
                        print(f"  → Copied: {original_path_obj.name}")
                    else:
                        print(f"  ⚠️  File not found: {original_path}")
                except Exception as e:
                    print(f"  ❌ Error copying {original_path}: {e}")

            # Store file paths as comma-separated string for preview
            files_preview = ', '.join(files[:3])  # First 3 files
            if len(files) > 3:
                files_preview += f' ... and {len(files) - 3} more'

            entry = {
                "id": content_hash,
                "timestamp": datetime.now().isoformat(),
                "content_type": "files",
                "content_preview": f"Files copied: {files_preview}",
                "file_path": str(file_path.relative_to(self.base_dir)),
                "copied_files": copied_file_paths,
                "source": "clipboard"
            }

            self._append_metadata_entry(entry)
            print(f"✅ Captured {len(files)} file(s): {filename}")

            return entry

        except Exception as e:
            print(f"[ClipboardWatcher] Error saving files: {e}")
            return None

    def poll_once(self):
        """Single polling iteration - check clipboard once."""
        # Track if we captured an image this cycle (to skip text capture)
        image_captured = False

        # Check for files first (Windows only)
        if WINDOWS_SUPPORT:
            try:
                current_files = self._get_clipboard_files()
                if current_files:
                    files_str = '\x00'.join(sorted(current_files))
                    files_hash = self._generate_content_hash(files_str)

                    if files_hash != self.last_files_hash:
                        self._capture_files(current_files)
                        self.last_files_hash = files_hash
            except Exception as e:
                pass

        # Check for image BEFORE text (screenshots have both)
        try:
            current_image = self._get_clipboard_image()

            if current_image:
                # Generate quick hash for comparison
                import io
                img_bytes = io.BytesIO()
                current_image.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                current_hash = self._generate_content_hash(img_bytes.read())

                if current_hash != self.last_image_hash:
                    # Always update last_image_hash to prevent repeated checks
                    # The deduplication inside _capture_image will handle actual duplicate prevention
                    result = self._capture_image(current_image)
                    if result:  # Image was successfully captured
                        image_captured = True
                    self.last_image_hash = current_hash

        except Exception as e:
            # Silent failure - clipboard may be unavailable
            pass

        # Check for text/URL (skip if image was just captured)
        if not image_captured:
            try:
                current_text = pyperclip.paste()

                if current_text and current_text != self.last_text:
                    # Check if text is ONLY a URL
                    if self._is_url_only(current_text):
                        self._capture_url(current_text)
                    # Otherwise capture as regular text
                    else:
                        self._capture_text(current_text)

                    self.last_text = current_text

            except Exception as e:
                # Silent failure - clipboard may be unavailable
                pass

    def start(self):
        """Start the clipboard monitoring loop."""
        print(f"[ClipboardWatcher] Monitoring clipboard (interval: {POLL_INTERVAL}s)")
        print("[ClipboardWatcher] Press Ctrl+C to stop")

        try:
            while True:
                self.poll_once()
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[ClipboardWatcher] Stopped by user")
            print(f"[ClipboardWatcher] Total captures: {len(self._read_metadata())}")
        except Exception as e:
            print(f"[ClipboardWatcher] Unexpected error: {e}")


def main():
    """Entry point - runs clipboard watcher."""
    watcher = ClipboardWatcher()
    watcher.start()


if __name__ == "__main__":
    main()
