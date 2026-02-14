# 🧠 AI MINDS - Personal Knowledge Assistant

**Multimodal personal knowledge system** that converts your digital footprint into searchable, structured memory.

## 🎯 Overview

AI MINDS ingests data from multiple sources (browser, screenshots, clipboard, calendar, emails, documents) with dual-vector embeddings (text 384d + visual 512d).

**Architecture**: Text → Sentence-Transformers → Faiss | Images → CLIP → Faiss | Storage → SQLite + Faiss

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete system design.

## Project Structure

```
ai-minds/
├── Data_Layer/
│   └── Data_Collection/
│       ├── Browser/              # Browser history extraction
│       ├── File_System/          # File system monitoring
│       ├── Clipboard/            # Clipboard monitoring (text, URLs, images, files)
│       ├── Calendar/             # Google Calendar integration
│       └── Email/                # Gmail monitoring
├── pyproject.toml               # Project dependencies (using UV)
├── .gitignore
└── README.md
```

## Quick Start

### 1. Install Dependencies

Using UV (recommended):

```bash
uv sync
```

Or using pip:

```bash
pip install -e .
```

### 2. Run Individual Modules

Each module runs independently:

**Browser History Extraction:**

```bash
cd Data_Layer/Data_Collection/Browser
python browser_ingestion.py
```

**Clipboard Monitoring:**

```bash
cd Data_Layer/Data_Collection/Clipboard
python clipboard_watcher.py
```

**Calendar Monitoring:**

```bash
cd Data_Layer/Data_Collection/Calendar
python calendar_watcher.py
```

**Email Monitoring:**

```bash
cd Data_Layer/Data_Collection/Email
python email_watcher.py
```

## Module Status

| Module      | Status      | Description                                       |
| ----------- | ----------- | ------------------------------------------------- |
| Browser     | ✅ Complete | Extracts browser history                          |
| File_System | ✅ Complete | Monitors file system activity                     |
| Clipboard   | ✅ Complete | Captures text, URLs, images, files from clipboard |
| Calendar    | ✅ Complete | Google Calendar event monitoring                  |
| Email       | ✅ Complete | Gmail monitoring                                  |

## Module Details

### Browser (by Roua)

Extracts browsing history from major browsers for search and discovery.

**Features:**

- Multi-browser support (Chrome, Firefox, Edge)
- History extraction with timestamps
- URL and title metadata

### File_System (by Roua)

Monitors file system activity and document access patterns.

**Features:**

- File change detection
- Document access tracking
- Activity logging

### Clipboard (by Sarra)

Monitors clipboard for copied content and automatically captures it.

**Features:**

- Text capture
- URL detection
- Image capture (screenshots)
- File copy detection and duplication
- 5-second deduplication window
- Silent background operation

### Calendar (by Sarra)

Monitors Google Calendar for upcoming events and meetings.

**Features:**

- Event capture (title, description, time, location)
- Attendee information
- Meeting links (Google Meet, etc.)
- 5-minute polling interval
- Looks ahead 30 days
- OAuth 2.0 authentication

**Setup:** See [Data_Layer/Data_Collection/Calendar/README.md](Data_Layer/Data_Collection/Calendar/README.md) for Google Cloud setup instructions.

### Email (by Sarra)

Monitors Gmail for new emails and captures them automatically.

**Features:**

- Email capture (subject, sender, recipients, body)
- Headers and metadata (labels, attachments, read/unread status)
- 5-minute polling interval
- Looks back 10 minutes for new emails
- Shared OAuth authentication with Calendar watcher
- Thread and message ID tracking

## Standardized Metadata Schema

All modules use the same metadata schema for ChromaDB compatibility:

```json
{
  "id": "unique_hash",
  "timestamp": "2026-02-14T18:54:07.332950",
  "content_type": "text|url|image|files|calendar_event|browser_history",
  "content_preview": "Brief description",
  "file_path": "path/to/detail/file.json",
  "source": "clipboard|google_calendar|browser",
  "...": "module-specific fields"
}
```

## Data Storage

Each module stores data in its own folder:

```
Data_Layer/Data_Collection/
├── Browser/data/              # Browser history data
├── File_System/data/          # File system activity
├── Clipboard/data/
│   ├── text/metadata.json     # All clipboard events
│   ├── images/                # Captured screenshots
│   ├── files/                 # File lists
│   └── copied_files/          # Duplicated files
└── Calendar/data/
    ├── events/                # Individual calendar events
    └── metadata.json          # All calendar events metadata
```

## Security & Privacy

- ✅ **Local storage** - all data stays on your machine
- ✅ **No external APIs** (except Google Calendar OAuth)
- ✅ **Read-only access** - modules don't modify your data
- ✅ **Credentials protected** - excluded from Git

## For Hackathon Judges

- Each module runs independently as a background service
- All data stored locally for privacy
- Ready for ChromaDB vector database ingestion
- Cross-platform support (Windows primary, macOS/Linux partial)
- Silent operation with minimal resource usage
- Standardized metadata schema across all modules

## Development

To add a new data collection module:

1. Create new folder: `Data_Layer/Data_Collection/YourModule/`
2. Create `your_module.py` with standard MemoryOS schema
3. Add dependencies to `pyproject.toml`
4. Create individual `README.md` for your module
5. Update this README with module status

## Team

- **Roua Khalfet** - Browser & File_System modules
- **Sarra Bousnina** - Clipboard & Calendar modules

## License

MIT License - AI MINDS Hackathon Team 2026
