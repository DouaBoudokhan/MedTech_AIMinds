# Gmail Watcher - MemoryOS Data Ingestion Module

Monitors Gmail for new emails and stores them in standardized MemoryOS schema.

## Quick Start

### Prerequisites

This module uses the same Google OAuth credentials as the Calendar watcher. Make sure you have:

1. Set up Google Cloud project (see Calendar module setup)
2. Created OAuth credentials
3. Saved `credentials.json` in `Data_Layer/Data_Collection/Calendar/`

### Install and Run

```bash
# Navigate to root directory
cd c:\Users\bousn\data_ingestion

# Activate shared virtual environment
venv\Scripts\activate

# Run email watcher
cd Data_Layer/Data_Collection/Email
python email_watcher.py
```

**First run:** If you haven't authenticated with Calendar yet, a browser window will open for Google authentication. The email watcher will share the same token.

## What It Captures

- **Email headers**: Subject, From, To, Cc, Bcc, Date
- **Email body**: Plain text or HTML content
- **Metadata**: Labels, attachments flag, read/unread status
- **Thread information**: Thread ID, message ID, history ID

## Features

- **Automatic polling:** Checks Gmail every 5 minutes
- **Deduplication:** Only captures new emails
- **Incremental capture:** Looks back 10 minutes for new emails
- **Silent operation:** Runs in background
- **Standardized schema:** Compatible with other MemoryOS modules
- **Shared authentication:** Uses same OAuth as Calendar watcher

## Output Structure

```
Email/
├── email_watcher.py        # Main script
├── README.md               # This file
├── .gitignore              # Excludes data folder
└── data/
    ├── emails/             # Individual email JSON files
    │   ├── email_20260214_143022_12345678.json
    │   └── email_20260214_150125_87654321.json
    └── metadata.json       # All emails (MemoryOS schema)
```

## Metadata Schema

All emails are logged to `data/metadata.json`:

```json
{
  "id": "unique_hash",
  "timestamp": "2026-02-14T18:54:07.332950",
  "content_type": "email",
  "content_preview": "Meeting Tomorrow - from sender@example.com",
  "file_path": "data/emails/email_20260214_143022_12345678.json",
  "source": "gmail",
  "email_details": {
    "subject": "Meeting Tomorrow",
    "from": "sender@example.com",
    "to": "recipient@example.com",
    "date": "Fri, 14 Feb 2026 18:54:07 +0000",
    "is_unread": true,
    "has_attachments": false,
    "label_ids": ["INBOX", "UNREAD"]
  }
}
```

Individual email files contain full details:

```json
{
  "gmail_message_id": "1234567890",
  "thread_id": "1234567890",
  "subject": "Meeting Tomorrow",
  "from": "Sender Name <sender@example.com>",
  "to": "Recipient <recipient@example.com>",
  "date": "Fri, 14 Feb 2026 18:54:07 +0000",
  "snippet": "Hi, just wanted to remind you...",
  "body": "Full email content here...",
  "label_ids": ["INBOX", "UNREAD"],
  "history_id": "1234567",
  "internal_date": "1739568847000"
}
```

## Configuration

Edit constants in `email_watcher.py`:

```python
POLL_INTERVAL = 300      # Poll every 5 minutes
LOOKBACK_MINUTES = 10    # Look back 10 minutes for new emails
```

## Security & Privacy

- ✅ **Read-only access** - never modifies your emails
- ✅ **Local storage** - all emails stored on your machine
- ✅ **Shared credentials** - uses same OAuth as Calendar (secure)
- ✅ **No external APIs** - only Gmail API access

## Troubleshooting

**"credentials.json not found"**
- Make sure Calendar watcher is set up (has credentials.json)
- The email watcher shares credentials with Calendar module

**No emails captured**
- Check your Gmail inbox has new emails in last 10 minutes
- Verify you're using the correct Google account
- Check that Gmail API is enabled in Google Cloud Console

**Authentication error**
- If Calendar watcher works, Email should work too (same token)
- Try deleting `token.pickle` and re-authenticating

**Rate limiting**
- Gmail API has quotas (usually 250 quota units per day)
- The watcher is designed to stay within limits
- Adjust `POLL_INTERVAL` if needed

## How It Works

1. **Authentication**: Uses shared OAuth token with Calendar watcher
2. **Polling**: Every 5 minutes, fetches recent emails
3. **Deduplication**: Tracks message IDs to avoid duplicates
4. **Capture**: Saves new emails to individual JSON files
5. **Metadata**: Appends email info to `data/metadata.json`

## Demo Output

```
[EmailWatcher] Emails -> C:\...\Email\data\emails
[EmailWatcher] Metadata -> C:\...\Email\data\metadata.json
[EmailWatcher] Authenticated with Gmail
[EmailWatcher] Started monitoring Gmail
[EmailWatcher] Poll interval: 300s
[EmailWatcher] Lookback: 10 minutes

[EmailWatcher] Polling for new emails...
  -> Captured: Meeting Reminder
  -> Captured: Your order has shipped
  -> Total new emails: 2

[EmailWatcher] Polling for new emails...
  -> No new emails found
```

## Dependencies

- **google-api-python-client** (>=2.100.0): Gmail API client
- **google-auth-oauthlib** (>=1.0.0): OAuth authentication
- **google-auth-httplib2** (>=0.2.0): HTTP transport

Note: These are already installed if you set up the Calendar watcher!

## Team Integration

This module outputs metadata in the **standardized MemoryOS schema** for compatibility with:
- `Clipboard/`
- `Calendar/`
- `Browser/`
- `File_System/`

All modules append to their respective `metadata.json` files for downstream ChromaDB ingestion.

## Notes

- **Gmail API**: Uses Gmail REST API v1
- **Scopes**: Read-only access to Gmail
- **Shared auth**: Uses same OAuth flow as Calendar watcher
- **Body extraction**: Prioritizes plain text over HTML
- **Attachments**: Currently only marks presence, doesn't download files
- **Labels**: Captures all Gmail labels (INBOX, UNREAD, IMPORTANT, etc.)
