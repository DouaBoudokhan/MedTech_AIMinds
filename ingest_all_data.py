"""
Complete Data Ingestion Pipeline
=================================

Ingests all collected data from Data_Storage into FAISS + SQLite
- Browser history
- Clipboard data
- Calendar events
- Email messages
- File system activity
"""

import json
from pathlib import Path
from datetime import datetime
from Data_Layer.storage_manager import UnifiedStorageManager


class DataIngestionPipeline:
    """Orchestrates ingestion of all data sources"""

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
    
    def __init__(self):
        """Initialize pipeline"""
        print("\n" + "="*70)
        print("🚀 AI MINDS - Complete Data Ingestion Pipeline")
        print("="*70)
        
        self.storage_dir = Path("Data_Layer/Data_Storage")
        self.manager = UnifiedStorageManager()
        self.total_ingested = 0
    
    def ingest_browser_data(self):
        """Ingest all browser history JSON files"""
        print("\n📊 Ingesting Browser Data...")
        print("-" * 70)
        
        browser_files = list(self.storage_dir.glob("browser_data_*.json"))
        
        if not browser_files:
            print("   ⚠️  No browser data files found")
            return 0
        
        count = 0
        for file in browser_files:
            print(f"   Processing: {file.name}")
            n = self.manager.ingest_browser_data(str(file))
            count += n
        
        print(f"   ✅ Ingested {count} browser records")
        return count
    
    def ingest_file_system_data(self):
        """Ingest file system activity"""
        print("\n📁 Ingesting File System Data...")
        print("-" * 70)
        
        fs_file = self.storage_dir / "File_System.json"
        
        if not fs_file.exists():
            print("   ⚠️  No file system data found")
            return 0
        
        try:
            count = 0
            # File_System.json is stored as concatenated pretty-printed JSON objects
            with open(fs_file, 'r', encoding='utf-8') as f:
                raw = f.read()

            decoder = json.JSONDecoder()
            index = 0
            length = len(raw)

            while index < length:
                while index < length and raw[index].isspace():
                    index += 1

                if index >= length:
                    break

                try:
                    item, next_index = decoder.raw_decode(raw, index)
                except json.JSONDecodeError:
                    index += 1
                    continue

                index = next_index

                if not isinstance(item, dict):
                    continue

                event_type = str(item.get('event_type', '')).upper()
                file_extension = str(item.get('file_extension', '')).lower()
                content_type = str(item.get('content_type', '')).lower()

                is_image = file_extension in self.IMAGE_EXTENSIONS or content_type == 'image'

                # Treat image events as visual items (no text embedding for image path events)
                if is_image:
                    image_path = item.get('destination_path') or item.get('full_path')

                    # Only ingest image if file still exists (CREATED/DOWNLOADED typically)
                    if image_path and Path(image_path).exists() and event_type != 'DELETED':
                        visual_id = self.manager.ingest_image(
                            image_path=str(image_path),
                            metadata=item
                        )
                        if visual_id != -1:
                            count += 1
                    continue

                # Create searchable text from file activity
                filename = item.get('filename', '')
                full_path = item.get('full_path', '')
                timestamp = item.get('timestamp', '')

                text = f"{event_type} {filename} {file_extension} {full_path} {timestamp}"

                self.manager.ingest_text(
                    text,
                    source='file_system',
                    metadata=item
                )
                count += 1
            
            print(f"   ✅ Ingested {count} file system events")
            return count
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return 0
    
    def ingest_clipboard_data(self):
        """Ingest clipboard data"""
        print("\n📋 Ingesting Clipboard Data...")
        print("-" * 70)
        
        clipboard_metadata = self.storage_dir / "Clipboard" / "metadata.json"
        
        if not clipboard_metadata.exists():
            print("   ⚠️  No clipboard data found")
            return 0
        
        try:
            with open(clipboard_metadata, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for item in data:
                content_type = item.get('content_type', '')
                content_preview = item.get('content_preview', '')
                timestamp = item.get('timestamp', '')
                
                # Handle different content types
                if content_type == 'text' or content_type == 'url':
                    text = content_preview
                    self.manager.ingest_text(
                        text,
                        source='clipboard',
                        metadata=item
                    )
                    count += 1
                
                elif content_type == 'image':
                    # For images, use file path if available
                    file_path = item.get('file_path', '')
                    if file_path and Path(file_path).exists():
                        # TODO: Add OCR support
                        # For now, just store metadata
                        self.manager.ingest_text(
                            f"Image captured at {timestamp}",
                            source='clipboard_image',
                            metadata=item
                        )
                        count += 1
                
                elif content_type == 'files':
                    # Store file list
                    files_info = item.get('content_preview', '')
                    self.manager.ingest_text(
                        files_info,
                        source='clipboard_files',
                        metadata=item
                    )
                    count += 1
            
            print(f"   ✅ Ingested {count} clipboard items")
            return count
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return 0
    
    def ingest_calendar_data(self):
        """Ingest calendar events"""
        print("\n📅 Ingesting Calendar Data...")
        print("-" * 70)
        
        calendar_metadata = self.storage_dir / "Calendar" / "metadata.json"
        
        if not calendar_metadata.exists():
            print("   ⚠️  No calendar data found")
            return 0
        
        try:
            with open(calendar_metadata, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for item in data:
                # Create searchable text from event
                summary = item.get('summary', '')
                description = item.get('description', '')
                location = item.get('location', '')
                attendees = item.get('attendees', '')
                start_time = item.get('start', '')
                
                text = f"{summary} {description} {location} {attendees} {start_time}"
                
                self.manager.ingest_text(
                    text,
                    source='calendar',
                    metadata=item
                )
                count += 1
            
            print(f"   ✅ Ingested {count} calendar events")
            return count
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return 0
    
    def ingest_email_data(self):
        """Ingest email messages"""
        print("\n📧 Ingesting Email Data...")
        print("-" * 70)
        
        email_metadata = self.storage_dir / "Email" / "metadata.json"
        
        if not email_metadata.exists():
            print("   ⚠️  No email data found")
            return 0
        
        try:
            with open(email_metadata, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for item in data:
                # Create searchable text from email
                subject = item.get('subject', '')
                sender = item.get('sender', '')
                recipients = item.get('recipients', '')
                body_preview = item.get('body_preview', '')
                
                text = f"{subject} from {sender} to {recipients} {body_preview}"
                
                self.manager.ingest_text(
                    text,
                    source='email',
                    metadata=item
                )
                count += 1
            
            print(f"   ✅ Ingested {count} email messages")
            return count
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return 0
    
    def run(self):
        """Run complete ingestion pipeline"""
        print("\n🔄 Starting complete data ingestion...")
        print("="*70)
        
        # Ingest all data sources
        total = 0
        total += self.ingest_browser_data()
        total += self.ingest_file_system_data()
        total += self.ingest_clipboard_data()
        total += self.ingest_calendar_data()
        total += self.ingest_email_data()
        
        # Save indices
        print("\n💾 Saving vector stores...")
        self.manager.save()
        
        # Show final stats
        print("\n" + "="*70)
        print("📊 INGESTION COMPLETE!")
        print("="*70)
        print(f"\n   Total items ingested: {total:,}")
        
        self.manager.print_stats()
        
        print("="*70)
        print("✅ All data embedded and stored in FAISS + SQLite!")
        print("="*70)
        
        print("\n💡 Next steps:")
        print("   - Run: python main.py")
        print("   - Choose option 3: Interactive search")
        print("   - Try searching your data!")
        print()


def main():
    """Main entry point"""
    pipeline = DataIngestionPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
