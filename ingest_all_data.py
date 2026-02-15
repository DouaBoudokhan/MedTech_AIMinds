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
import sys
from pathlib import Path
from datetime import datetime
from Data_Layer.storage_manager import UnifiedStorageManager

sys.path.insert(0, str(Path(__file__).parent / "Core"))
from image_processor import ImageProcessor
from document_processor import DocumentProcessor
from audio_processor import AudioProcessor


class DataIngestionPipeline:
    """Orchestrates ingestion of all data sources"""

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
    DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma'}
    NOISY_PATH_PARTS = ['\\venv\\', '\\site-packages\\', '\\__pycache__\\', '\\.git\\']
    
    def __init__(self):
        """Initialize pipeline"""
        print("\n" + "="*70)
        print("🚀 AI MINDS - Complete Data Ingestion Pipeline")
        print("="*70)
        
        self.storage_dir = Path("Data_Layer/Data_Storage")
        self.manager = UnifiedStorageManager()
        self.image_processor = ImageProcessor(ocr_engine="easyocr")
        self.document_processor = DocumentProcessor()
        self.audio_processor = AudioProcessor(model_size="base")
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
            skipped = 0
            processed = 0
            progress_every = 100
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

                processed += 1
                if processed % progress_every == 0:
                    print(f"   ⏳ Processed {processed} file-system records (ok={count}, skipped={skipped})")

                event_type = str(item.get('event_type', '')).upper()
                file_extension = str(item.get('file_extension', '')).lower()
                content_type = str(item.get('content_type', '')).lower()
                full_path = str(item.get('full_path', '') or '')

                # Skip high-volume environment noise
                lowered_path = full_path.lower()
                if any(part in lowered_path for part in self.NOISY_PATH_PARTS):
                    skipped += 1
                    continue

                is_image = file_extension in self.IMAGE_EXTENSIONS or content_type == 'image'
                is_audio = file_extension in self.AUDIO_EXTENSIONS

                # Treat image events as visual items + optional OCR text
                if is_image:
                    image_path = item.get('destination_path') or full_path

                    # Only ingest image if file still exists (CREATED/DOWNLOADED typically)
                    if image_path and Path(image_path).exists() and event_type != 'DELETED':
                        # Run OCR to extract text from image (returns "" if none found)
                        ocr_text = self.image_processor.extract_text(str(image_path))
                        visual_id = self.manager.ingest_image(
                            image_path=str(image_path),
                            ocr_text=ocr_text if ocr_text.strip() else None,
                            metadata=item
                        )
                        if visual_id != -1:
                            count += 1
                            if ocr_text.strip():
                                print(f"      🔤 OCR extracted {len(ocr_text)} chars from {Path(image_path).name}")
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                    continue

                # Ingest actual document content for common document types
                if is_audio and event_type != 'DELETED':
                    audio_path = item.get('destination_path') or full_path

                    if audio_path and Path(audio_path).exists():
                        transcription = self.audio_processor.transcribe(str(audio_path))
                        transcript_text = (transcription.get('text') or '').strip() if isinstance(transcription, dict) else ''

                        if transcript_text:
                            audio_text = f"audio recording {Path(audio_path).name}\n\n{transcript_text}"
                            audio_metadata = {
                                **item,
                                'audio_path': str(audio_path),
                                'transcription_language': transcription.get('language') if isinstance(transcription, dict) else None,
                                'transcript_segments': len(transcription.get('segments', [])) if isinstance(transcription, dict) else 0
                            }

                            if self.manager.ingest_text(
                                audio_text,
                                source='audio',
                                metadata=audio_metadata
                            ) != -1:
                                count += 1
                                print(f"      🎙️ Transcribed and embedded audio: {Path(audio_path).name}")
                            else:
                                skipped += 1
                        else:
                            fallback_text = f"audio file {Path(audio_path).name} {file_extension} {event_type} {item.get('timestamp', '')}".strip()
                            if self.manager.ingest_text(
                                fallback_text,
                                source='audio_event',
                                metadata=item
                            ) != -1:
                                count += 1
                            else:
                                skipped += 1
                    else:
                        skipped += 1
                    continue

                # Ingest actual document content for common document types
                if file_extension in self.DOCUMENT_EXTENSIONS and event_type != 'DELETED':
                    doc_path = full_path
                    if doc_path and Path(doc_path).exists():
                        extracted_text = self.document_processor.extract_text(doc_path)
                        if extracted_text.strip():
                            doc_text = f"{Path(doc_path).name}\n\n{extracted_text}"
                            if self.manager.ingest_text(
                                doc_text,
                                source='file_system_document',
                                metadata=item
                            ) != -1:
                                count += 1
                            else:
                                skipped += 1
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                    continue

                # Create searchable text from file activity
                filename = item.get('filename', '')
                timestamp = item.get('timestamp', '')

                text = f"{event_type} {filename} {file_extension} {full_path} {timestamp}"

                if self.manager.ingest_text(
                    text,
                    source='file_system',
                    metadata=item
                ) != -1:
                    count += 1
                else:
                    skipped += 1
            
            print(f"   ✅ Ingested {count} file system events")
            if skipped:
                print(f"   ⚠️  Skipped {skipped} file system records")
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
                    if self.manager.ingest_text(
                        text,
                        source='clipboard',
                        metadata=item
                    ) != -1:
                        count += 1
                
                elif content_type == 'image':
                    # For images, use file path if available
                    file_path = item.get('file_path', '')
                    if file_path and Path(file_path).exists():
                        # Run OCR to extract text from clipboard image
                        ocr_text = self.image_processor.extract_text(file_path)
                        if self.manager.ingest_image(
                            image_path=file_path,
                            ocr_text=ocr_text if ocr_text.strip() else None,
                            metadata=item
                        ) != -1:
                            count += 1
                        if ocr_text.strip():
                            print(f"      🔤 OCR extracted {len(ocr_text)} chars from clipboard image")
                
                elif content_type == 'files':
                    # Store file list
                    files_info = item.get('content_preview', '')
                    if self.manager.ingest_text(
                        files_info,
                        source='clipboard_files',
                        metadata=item
                    ) != -1:
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

                if self.manager.ingest_text(
                    text,
                    source='calendar',
                    metadata=item
                ) != -1:
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
                # Support both legacy email schema and current EmailWatcher schema
                details = item.get('email_details', {}) if isinstance(item, dict) else {}

                subject = item.get('subject', '') or details.get('subject', '')
                sender = item.get('sender', '') or details.get('from', '')
                recipients = item.get('recipients', '') or details.get('to', '')
                body_preview = item.get('body_preview', '') or item.get('content_preview', '')
                email_date = item.get('date', '') or details.get('date', '')

                text = f"{subject} from {sender} to {recipients} {body_preview} {email_date}".strip()

                if not text:
                    continue

                if self.manager.ingest_text(
                    text,
                    source='email',
                    metadata=item
                ) != -1:
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
