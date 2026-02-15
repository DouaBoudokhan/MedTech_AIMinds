import time
import json
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ActivityMonitor(FileSystemEventHandler):
    """Monitors file system activity and logs all changes."""
    
    # File extensions that are meaningful for user activity tracking
    RELEVANT_EXTENSIONS = {
        # Documents
        '.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt',".m4a",
        # Spreadsheets
        '.xls', '.xlsx', '.csv', '.ods',
        # Presentations
        '.ppt', '.pptx', '.odp',
        # Code & Scripts
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs',
        '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.sql',
        # Images & Media
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav',
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz',
        # Other useful formats
        '.md', '.log', '.config', '.ini', '.toml'
    }
    
    # System/temp files to ignore
    IGNORE_PATTERNS = {
        'desktop.ini', 'thumbs.db', '.ds_store', '~$',
        '.tmp', '.temp', '.cache'
    }
    
    # Browser download temp extensions (track completion, not creation)
    DOWNLOAD_TEMP_EXTENSIONS = {'.crdownload', '.part'}

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
    
    # Database/system extensions to ignore
    IGNORE_EXTENSIONS = {
        '.nlb', '.msb', '.ctl', '.trc', '.trm', '.dmp', '.dbf',
        '.ora', '.bak', '.swp', '.swo', '.lock'
    }
    
    def __init__(self, log_file_path):
        self.log_file_path = str(Path(log_file_path).resolve())
        self.recent_events = {}  # For deduplication
        # Ensure the parent directory exists before opening the file
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        self.log_file = open(log_file_path, 'a', encoding='utf-8')
    
    def _should_ignore(self, path):
        """Check if the path should be ignored."""
        if str(Path(path).resolve()) == self.log_file_path:
            return True
        
        path_obj = Path(path)
        filename = path_obj.name.lower()
        extension = path_obj.suffix.lower()
        
        # Ignore system files
        for pattern in self.IGNORE_PATTERNS:
            if pattern in filename:
                return True
        
        # Ignore browser temp files (in progress downloads)
        if extension in self.DOWNLOAD_TEMP_EXTENSIONS:
            return True
        
        # Ignore system/database extensions
        if extension in self.IGNORE_EXTENSIONS:
            return True
        
        # Only allow relevant extensions (if not a directory)
        if extension and extension not in self.RELEVANT_EXTENSIONS:
            return True
        
        return False
    
    def _log_event(self, event_type, path, dest_path=None):
        """Log event with deduplication in JSON format."""
        event_key = f"{event_type}:{path}"
        current_time = time.time()
        
        # Deduplicate rapid successive events (within 2 seconds)
        if event_key in self.recent_events:
            if current_time - self.recent_events[event_key] < 2:
                return
        
        self.recent_events[event_key] = current_time
        
        # Create JSON log entry
        path_obj = Path(path)
        extension = path_obj.suffix.lower()
        content_type = "image" if extension in self.IMAGE_EXTENSIONS else "file"
        log_entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "event_type": event_type,
            "filename": path_obj.name,
            "file_extension": path_obj.suffix,
            "full_path": str(path_obj.resolve()),
            "content_type": content_type
        }
        
        if dest_path:
            dest_obj = Path(dest_path)
            log_entry["destination_filename"] = dest_obj.name
            log_entry["destination_path"] = str(dest_obj.resolve())
        
        # Write JSON line to file
        json_line = json.dumps(log_entry, ensure_ascii=False, indent=4)
        self.log_file.write(json_line + '\n')
        self.log_file.flush()
        
        # Console output
        if dest_path:
            print(f"{log_entry['timestamp']} - [{event_type}] {log_entry['filename']} -> {log_entry['destination_filename']}")
        else:
            print(f"{log_entry['timestamp']} - [{event_type}] {log_entry['filename']} ({log_entry['file_extension']})")
    
    def on_modified(self, event):
        if not event.is_directory and not self._should_ignore(event.src_path):
            # Skip MODIFIED events for newly created files (they'll have CREATED)
            pass
    
    def on_created(self, event):
        if self._should_ignore(event.src_path):
            return
        if not event.is_directory:
            self._log_event("CREATED", event.src_path)
        else:
            path_obj = Path(event.src_path)
            log_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "event_type": "FOLDER_CREATED",
                "folder_name": path_obj.name,
                "full_path": str(path_obj.resolve())
            }
            json_line = json.dumps(log_entry, ensure_ascii=False, indent=4)
            self.log_file.write(json_line + '\n')
            self.log_file.flush()
            print(f"{log_entry['timestamp']} - [FOLDER CREATED] {log_entry['folder_name']}")
    
    def on_deleted(self, event):
        if self._should_ignore(event.src_path):
            return
        if not event.is_directory:
            self._log_event("DELETED", event.src_path)
        else:
            path_obj = Path(event.src_path)
            log_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "event_type": "FOLDER_DELETED",
                "folder_name": path_obj.name,
                "full_path": str(path_obj.resolve())
            }
            json_line = json.dumps(log_entry, ensure_ascii=False, indent=4)
            self.log_file.write(json_line + '\n')
            self.log_file.flush()
            print(f"{log_entry['timestamp']} - [FOLDER DELETED] {log_entry['folder_name']}")
    
    def on_moved(self, event):
        # Special case: browser download completion (temp -> final file)
        src_ext = Path(event.src_path).suffix.lower()
        if src_ext in self.DOWNLOAD_TEMP_EXTENSIONS and not self._should_ignore(event.dest_path):
            # Download completed! Log as DOWNLOADED instead of MOVED
            dest_obj = Path(event.dest_path)
            extension = dest_obj.suffix.lower()
            content_type = "image" if extension in self.IMAGE_EXTENSIONS else "file"
            log_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "event_type": "DOWNLOADED",
                "filename": dest_obj.name,
                "file_extension": dest_obj.suffix,
                "full_path": str(dest_obj.resolve()),
                "content_type": content_type
            }
            json_line = json.dumps(log_entry, ensure_ascii=False, indent=4)
            self.log_file.write(json_line + '\n')
            self.log_file.flush()
            print(f"{log_entry['timestamp']} - [DOWNLOADED] {log_entry['filename']} ({log_entry['file_extension']})")
            return
        
        if self._should_ignore(event.src_path) or self._should_ignore(event.dest_path):
            return
        if not event.is_directory:
            self._log_event("MOVED", event.src_path, event.dest_path)
        else:
            src_obj = Path(event.src_path)
            dest_obj = Path(event.dest_path)
            log_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "event_type": "FOLDER_MOVED",
                "folder_name": src_obj.name,
                "destination_folder": dest_obj.name,
                "source_path": str(src_obj.resolve()),
                "destination_path": str(dest_obj.resolve())
            }
            json_line = json.dumps(log_entry, ensure_ascii=False, indent=4)
            self.log_file.write(json_line + '\n')
            self.log_file.flush()
            print(f"{log_entry['timestamp']} - [FOLDER MOVED] {log_entry['folder_name']} -> {log_entry['destination_folder']}")

def start_monitoring(paths, log_file='../../Data_Storage/File_System.json'):
    """Start monitoring the specified paths."""
    log_file_path = Path(log_file).resolve()
    
    # Validate paths
    valid_paths = []
    for path in paths:
        path = Path(path).resolve()
        if path.exists():
            valid_paths.append(path)
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Monitoring: {path}")
        else:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Path does not exist (skipping): {path}")
    
    if not valid_paths:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ERROR: No valid paths to monitor")
        return
    
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Excluding from monitoring: {log_file_path}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Press Ctrl+C to stop monitoring")
    print("-" * 80)
    
    event_handler = ActivityMonitor(log_file_path)
    observer = Observer()
    
    # Schedule observer for each path
    for path in valid_paths:
        observer.schedule(event_handler, str(path), recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("-" * 80)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Stopping activity monitor...")
        observer.stop()
    
    observer.join()
    event_handler.log_file.close()
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Activity monitor stopped")

if __name__ == "__main__":
    # Monitor specific folders only
    user_profile = Path.home()
    monitor_paths = [
        user_profile / "Downloads",
        user_profile / "Documents",
        user_profile / "Desktop",
        user_profile / "Pictures" / "Camera Roll",
        user_profile / "Videos",
    ]
    start_monitoring(monitor_paths)
