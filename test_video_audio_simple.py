# -*- coding: utf-8 -*-
"""
Simple Video Audio Test - Just Transcription
============================================
"""

import sys
import subprocess
from pathlib import Path

# UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add ffmpeg to PATH BEFORE importing whisper
ffmpeg_path = r"C:\Users\bousn\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
import os
os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

print("="*70)
print("VIDEO AUDIO TRANSCRIPTION TEST")
print("="*70)

# Check video file
if len(sys.argv) < 2:
    print("\nNo video file provided!")
    print("\nUsage: python -X utf8 test_video_audio_simple.py video.mp4")
    sys.exit(1)

video_path = sys.argv[1]

if not Path(video_path).exists():
    print(f"\nVideo not found: {video_path}")
    sys.exit(1)

print(f"\nVideo: {Path(video_path).name}")
print(f"Size: {Path(video_path).stat().st_size / 1024 / 1024:.1f} MB")

# Step 1: Extract audio
print("\n" + "="*70)
print("STEP 1: Extracting Audio")
print("="*70)

video_path = Path(video_path)
audio_path = video_path.parent / f"{video_path.stem}_audio.wav"

ffmpeg_path = r"C:\Users\bousn\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"

cmd = [
    ffmpeg_path,
    '-i', str(video_path),
    '-vn',
    '-acodec', 'pcm_s16le',
    '-ar', '16000',
    '-ac', '1',
    '-y',
    str(audio_path)
]

try:
    print(f"Running ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, check=True)
    print(f"Audio extracted: {audio_path}")
except subprocess.CalledProcessError as e:
    print(f"ffmpeg error: {e.stderr.decode()}")
    sys.exit(1)
except FileNotFoundError:
    print("ffmpeg not found! Install from: https://ffmpeg.org/download.html")
    sys.exit(1)

# Step 2: Transcribe
print("\n" + "="*70)
print("STEP 2: Transcribing with Whisper")
print("="*70)

import whisper
import torch

print("Loading Whisper model (tiny)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

model = whisper.load_model('tiny', device=device)

print(f"Transcribing...")
result = model.transcribe(
    str(audio_path),
    language=None,  # Auto-detect
    fp16=(device == "cuda")  # Enable FP16 on GPU
)

print(f"\nTranscription complete!")
print(f"Language: {result.get('language', 'unknown')}")
print(f"Text length: {len(result['text'])} characters")
print(f"Segments: {len(result.get('segments', []))}")

# Show first few segments
print(f"\nFirst 5 segments:")
for i, seg in enumerate(result.get('segments', [])[:5]):
    print(f"  {i+1}. {seg['start']:.1f}s - {seg['end']:.1f}s: {seg['text']}")

# Step 3: Test search
print("\n" + "="*70)
print("STEP 3: Test Search")
print("="*70)

test_words = ['the', 'a', 'is']

for word in test_words:
    matches = []
    for seg in result.get('segments', []):
        if word.lower() in seg['text'].lower():
            matches.append(seg)

    print(f"\nSearch '{word}': {len(matches)} matches")
    for m in matches[:3]:
        print(f"  - {m['start']:.1f}s: {m['text']}")

# Step 4: Save index
print("\n" + "="*70)
print("STEP 4: Saving Index")
print("="*70)

import json

index = {
    'video_path': str(video_path),
    'video_name': video_path.name,
    'language': result.get('language'),
    'text': result['text'],
    'segments': result.get('segments', [])
}

index_path = video_path.parent / f"{video_path.stem}_index.json"

with open(index_path, 'w', encoding='utf-8') as f:
    json.dump(index, f, indent=2, ensure_ascii=False)

print(f"Index saved: {index_path}")

# Cleanup
audio_path.unlink(missing_ok=True)

print("\n" + "="*70)
print("TEST COMPLETE!")
print("="*70)
print("\nWhat you can do now:")
print(f"1. Open {index_path} to see the full transcription")
print("2. Search for any word in the JSON")
print("3. Use the timestamps to jump to specific moments")
print()
