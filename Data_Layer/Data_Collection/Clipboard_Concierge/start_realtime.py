#!/usr/bin/env python3
"""
Start LLM-POWERED clipboard monitoring with intelligent suggestions.

Uses GPT-2 (124M params) for actual AI-powered clipboard analysis.
"""

import subprocess
import sys
import time
from pathlib import Path

print("="*70)
print("  LLM-POWERED CLIPBOARD CONCIERGE")
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

print("Step 2: Starting Better LLM Concierge (Phi-2, 2.7B params)...")
print("Loading model... (first run: ~2 minutes, downloads ~2.8GB)")
print()

# Start LLM concierge
concierge_process = subprocess.Popen(
    [sys.executable, str(llm_concierge)],
    cwd=str(llm_concierge.parent)
)

time.sleep(5)

print()
print("="*70)
print("SYSTEM READY - Copy anything to your clipboard!")
print("="*70)
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
