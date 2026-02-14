"""
Screenshot Watcher for AI MINDS
Monitors and captures screenshots for ingestion into the knowledge base
"""

from pathlib import Path
from typing import Optional
import time
from datetime import datetime


class ScreenshotWatcher:
    """
    Monitor screenshot folder and ingest new screenshots.
    
    Features:
        - Watch Windows screenshot folder
        - Automatic ingestion on new file
        - CLIP visual embedding
        - OCR text extraction
    """
    
    def __init__(self, watch_dir: Optional[Path] = None):
        """
        Initialize screenshot watcher.
        
        Args:
            watch_dir: Directory to watch (default: Windows Screenshots)
        """
        if watch_dir is None:
            # Default Windows screenshot location
            watch_dir = Path.home() / "Pictures" / "Screenshots"
        
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        
        self.known_files = set()
        self._initialize_known_files()
    
    def _initialize_known_files(self):
        """Load existing screenshots to avoid re-processing"""
        if self.watch_dir.exists():
            self.known_files = {f.name for f in self.watch_dir.glob("*.png")}
            self.known_files.update({f.name for f in self.watch_dir.glob("*.jpg")})
    
    def check_new_screenshots(self):
        """
        Check for new screenshots.
        
        Returns:
            List of new screenshot paths
        """
        current_files = set()
        new_screenshots = []
        
        for pattern in ["*.png", "*.jpg", "*.jpeg"]:
            for file in self.watch_dir.glob(pattern):
                current_files.add(file.name)
                
                if file.name not in self.known_files:
                    new_screenshots.append(file)
        
        self.known_files = current_files
        return new_screenshots
    
    def watch(self, callback, interval: int = 5):
        """
        Watch for new screenshots continuously.
        
        Args:
            callback: Function to call with new screenshot paths
            interval: Check interval in seconds
        """
        print(f"Watching for screenshots in: {self.watch_dir}")
        print(f"Press Ctrl+C to stop")
        
        try:
            while True:
                new_files = self.check_new_screenshots()
                
                if new_files:
                    print(f"\nFound {len(new_files)} new screenshot(s)")
                    for file in new_files:
                        callback(file)
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\nScreenshot watcher stopped")


def main():
    """Example usage"""
    def process_screenshot(path: Path):
        print(f"  → New screenshot: {path.name}")
        print(f"    Size: {path.stat().st_size / 1024:.1f} KB")
        print(f"    Time: {datetime.now().strftime('%H:%M:%S')}")
        # TODO: Send to storage_manager for CLIP + OCR processing
    
    watcher = ScreenshotWatcher()
    watcher.watch(process_screenshot, interval=2)


if __name__ == "__main__":
    main()
