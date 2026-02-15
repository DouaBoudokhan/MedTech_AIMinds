#!/usr/bin/env python3
"""
Start LLM-POWERED Clipboard Concierge Agent.

This is now a TRUE AGENT that executes actions, not just suggests them!
Uses Microsoft Phi-2 (2.7B params) for AI-powered clipboard analysis.
"""

import subprocess
import sys
import time
from pathlib import Path

print("="*70)
print("  LLM-POWERED CLIPBOARD CONCIERGE AGENT")
print("  (Now executes actions - not just suggestions!)")
print("="*70)
print()

# Get the project root
project_root = Path(__file__).parent.parent.parent.parent
clipboard_watcher = project_root / "Data_Layer" / "Data_Collection" / "Clipboard" / "clipboard_watcher.py"
llm_concierge = project_root / "Data_Layer" / "Data_Collection" / "Clipboard_Concierge" / "llm_concierge_v2.py"

print(f"Starting: {clipboard_watcher.name}")
print(f"Starting: Phi-2 LLM (2.7B params - 22x smarter than GPT-2!)")
print()

print("Step 1: Starting Clipboard Watcher...")
# Start clipboard watcher
watcher_process = subprocess.Popen(
    [sys.executable, str(clipboard_watcher)],
    cwd=str(clipboard_watcher.parent)
)

time.sleep(2)

print("Step 2: Starting Clipboard Concierge Agent...")
print("Loading Phi-2 model... (first run: ~2 minutes, downloads ~2.8GB)")
print()

# Start LLM concierge
concierge_process = subprocess.Popen(
    [sys.executable, str(llm_concierge)],
    cwd=str(llm_concierge.parent)
)

time.sleep(5)

print()
print("="*70)
print("AGENT READY - Copy anything to your clipboard!")
print("="*70)
print()
print("Features:")
print("  [+] LLM classification (Phi-2, 2.7B params)")
print("  [+] Multiple action suggestions - choose which to execute")
print("  [+] Windows toast notifications for reminders")
print("  [+] Auto-learns your preferences")
print()
print("Try copying:")
print("  * 'ERROR: ValueError' -> Search Stack Overflow")
print("  * 'forgot dentist' -> Set reminder")
print("  * 'meeting tomorrow 3pm' -> Add to calendar")
print("  * 'https://youtube.com' -> Open URL")
print("  * 'note: buy milk' -> Save note")
print()
print("Press Ctrl+C to stop")
print("="*70)

try:
    watcher_process.wait()
except KeyboardInterrupt:
    print("\nStopping...")
    watcher_process.terminate()
    concierge_process.terminate()
    watcher_process.wait(timeout=5)
    concierge_process.wait(timeout=5)
    print("Stopped")
