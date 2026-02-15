#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real LLM-powered Clipboard Concierge using better models.

Uses Microsoft Phi-2 (2.7B params) - much smarter than GPT-2!
"""
import json
import time
import sys
import torch
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Import transformers
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[LLM] transformers not installed. Run: pip install transformers torch")

# Configuration
CLIPBOARD_METADATA = Path(__file__).parent.parent.parent / "Data_Storage" / "Clipboard" / "metadata.json"
BEHAVIOR_TRACKER = Path(__file__).parent.parent.parent / "Data_Storage" / "Clipboard_Concierge" / "behavior.json"
POLL_INTERVAL = 2

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    sys.stdout.reconfigure(line_buffering=True)


class BetterLLMClassifier:
    """LLM-based classification using Phi-2 (2.7B params)."""

    def __init__(self, model_name: str = "microsoft/phi-2"):
        """Initialize Phi-2 model."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers is required")

        self.model_name = model_name  # 2.7B parameters - much smarter!
        print(f"[LLM] Loading {model_name}...")
        print(f"[LLM] This may take 1-2 minutes on first run...")
        start_time = time.time()

        try:
            # Load Phi-2 tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                device_map="cpu"
            )

            # Set pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            load_time = time.time() - start_time
            print(f"[LLM] Model loaded in {load_time:.2f}s")
            print(f"[LLM] Model: {model_name} (2.7B params)")

        except Exception as e:
            print(f"[LLM] Error loading model: {e}")
            print(f"[LLM] Falling back to GPT-2...")
            # Fall back to GPT-2
            from transformers import GPT2Tokenizer, GPT2LMHeadModel
            self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
            self.model = GPT2LMHeadModel.from_pretrained("gpt2")
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            print(f"[LLM] Using GPT-2 (124M params) as fallback")

    def classify(self, content: str, content_type: str = "text") -> Dict:
        """Classify clipboard content using LLM."""
        if not content or len(content.strip()) == 0:
            return self._no_action_response()

        if content_type != "text":
            return self._fallback_response(content, content_type)

        # Use LLM generation for classification
        return self._llm_classify(content)

    def _llm_classify(self, content: str) -> Dict:
        """Use LLM to classify content."""
        # Create a classification prompt
        prompt = f"""Classify this clipboard text and determine the intent.

Text: "{content}"

Choose one: calendar, reminder, error, search, contact, file, none

Intent:"""

        try:
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt")

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=20,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            # Decode
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract the intent
            response = generated_text[len(prompt):].strip().lower()

            # Parse response
            return self._parse_intent(response, content)

        except Exception as e:
            print(f"[LLM] Error: {e}")
            return self._smart_fallback(content)

    def _parse_intent(self, llm_response: str, content: str) -> Dict:
        """Parse LLM response and map to intent."""
        # Extract just the first word/intent
        intent_word = llm_response.split()[0] if llm_response else ""

        # Map to our intents
        intent_map = {
            'calendar': ('calendar', ['create_calendar_event', 'set_reminder']),
            'reminder': ('reminder', ['create_reminder', 'add_to_todo_list']),
            'error': ('error', ['search_stackoverflow', 'search_google']),
            'search': ('search', ['search_google', 'search_wikipedia']),
            'contact': ('contact', ['save_contact', 'call_contact']),
            'file': ('file', ['open_file', 'show_in_folder']),
            'none': ('none', []),
        }

        if intent_word in intent_map:
            intent, actions = intent_map[intent_word]
            return {
                'intent': intent,
                'confidence': 0.90,
                'reasoning': f'LLM ({self.model_name}) classified as: {intent_word}',
                'suggested_actions': actions,
                'method': 'llm_phi2'
            }

        # If unclear, use smart fallback
        return self._smart_fallback(content)

    def _smart_fallback(self, content: str) -> Dict:
        """Smart pattern-based fallback."""
        import re
        content_lower = content.lower()

        # Check for keywords
        if any(kw in content_lower for kw in ['forgot', 'remember', 'reminder', 'rendez', 'appointment']):
            return {
                'intent': 'reminder',
                'confidence': 0.80,
                'reasoning': 'Detected reminder/appointment keywords',
                'suggested_actions': ['create_reminder', 'add_to_todo_list'],
                'method': 'smart_fallback'
            }

        if any(kw in content_lower for kw in ['error', 'exception', 'traceback', 'failed']):
            return {
                'intent': 'error',
                'confidence': 0.85,
                'reasoning': 'Detected error keywords',
                'suggested_actions': ['search_stackoverflow', 'search_google'],
                'method': 'smart_fallback'
            }

        if any(kw in content_lower for kw in ['meeting', 'call', 'zoom']) and any(kw in content_lower for kw in ['today', 'tomorrow', 'am', 'pm']):
            return {
                'intent': 'calendar',
                'confidence': 0.82,
                'reasoning': 'Detected meeting with time',
                'suggested_actions': ['create_calendar_event', 'set_reminder'],
                'method': 'smart_fallback'
            }

        if re.match(r'^call\s+\w+', content_lower.strip()):
            return {
                'intent': 'contact',
                'confidence': 0.85,
                'reasoning': 'Detected "call [person]" pattern',
                'suggested_actions': ['call_contact', 'save_contact'],
                'method': 'smart_fallback'
            }

        if content.strip().endswith('?'):
            return {
                'intent': 'search',
                'confidence': 0.75,
                'reasoning': 'Detected question format',
                'suggested_actions': ['search_google'],
                'method': 'smart_fallback'
            }

        return self._no_action_response()

    def _no_action_response(self) -> Dict:
        return {
            'intent': 'none',
            'confidence': 0.0,
            'reasoning': 'No clear intent detected',
            'suggested_actions': [],
            'method': 'llm_phi2'
        }

    def _fallback_response(self, content: str, content_type: str) -> Dict:
        """Handle non-text content."""
        if content_type == "url":
            return {'intent': 'search', 'confidence': 1.0, 'suggested_actions': ['open_url'], 'method': 'fallback'}
        elif content_type == "file":
            return {'intent': 'file', 'confidence': 1.0, 'suggested_actions': ['open_file'], 'method': 'fallback'}
        elif content_type == "image":
            return {'intent': 'none', 'confidence': 0.0, 'suggested_actions': [], 'method': 'fallback'}
        return self._no_action_response()


class BetterLLMConcierge:
    """Better LLM-powered clipboard concierge."""

    def __init__(self):
        """Initialize the better LLM concierge."""
        print("[BetterLLM] Initializing with Phi-2 (2.7B params)...")
        self.classifier = BetterLLMClassifier()
        self.behavior_file = BEHAVIOR_TRACKER
        self.behavior_data = self._load_behavior()
        self.processed_clipboard_ids = set()
        self._setup_directories()

    def _setup_directories(self):
        """Create necessary directories."""
        self.behavior_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"[BetterLLM] Behavior tracker initialized")

    def _load_behavior(self) -> Dict:
        """Load tracked user behavior."""
        if not self.behavior_file.exists():
            return {
                "clipboard_events": [],
                "llm_classifications": [],
                "patterns": {}
            }

        try:
            with open(self.behavior_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "llm_classifications" not in data:
                data["llm_classifications"] = []

            return data
        except (json.JSONDecodeError, IOError):
            return {
                "clipboard_events": [],
                "llm_classifications": [],
                "patterns": {}
            }

    def _save_behavior(self):
        """Save tracked behavior."""
        with open(self.behavior_file, 'w', encoding='utf-8') as f:
            json.dump(self.behavior_data, f, indent=2, ensure_ascii=False)

    def track_classification(self, content: str, classification: Dict):
        """Track LLM classification."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "content": content[:200],
            "intent": classification.get("intent"),
            "confidence": classification.get("confidence"),
            "method": classification.get("method", "llm_phi2"),
            "actions": classification.get("suggested_actions", [])
        }

        self.behavior_data["llm_classifications"].append(event)

        if len(self.behavior_data["llm_classifications"]) > 500:
            self.behavior_data["llm_classifications"] = self.behavior_data["llm_classifications"][-500:]

        self._save_behavior()

    def process_clipboard_entry(self, entry: Dict):
        """Process a clipboard entry with LLM."""
        clipboard_id = entry.get('id')
        content_preview = entry.get('content_preview', '')
        content_type = entry.get('content_type', 'text')

        print(f"\n{'='*70}", flush=True)
        print(f">>> {content_preview[:80]}", flush=True)
        print(f"{'='*70}", flush=True)

        # Classify using LLM
        classification = self.classifier.classify(content_preview, content_type)
        intent = classification.get('intent')

        if intent == 'none':
            print(f">>> No clear intent detected", flush=True)
            return

        # Track classification
        self.track_classification(content_preview, classification)

        # Display results
        confidence = classification.get('confidence', 0.0)
        reasoning = classification.get('reasoning', '')

        print(f">>> LLM detected: {intent.upper()} (confidence: {confidence:.0%})", flush=True)
        if reasoning:
            print(f"    🧠 {reasoning}", flush=True)
        print(f">>> Suggested actions:", flush=True)

        actions = classification.get('suggested_actions', [])
        action_labels = {
            'create_calendar_event': 'Add to Calendar',
            'set_reminder': 'Set Reminder',
            'search_stackoverflow': 'Search Stack Overflow',
            'search_google': 'Google Search',
            'search_github': 'Search GitHub',
            'search_wikipedia': 'Wikipedia',
            'open_file': 'Open File',
            'show_in_folder': 'Show in Folder',
            'run_python_file': 'Run Python File',
            'save_contact': 'Save Contact',
            'send_email': 'Send Email',
            'add_to_todo_list': 'Add to Todo',
            'open_url': 'Open URL',
            'call_contact': 'Call Contact',
        }

        for action in actions[:5]:
            label = action_labels.get(action, action)
            print(f"   🤖 {label}", flush=True)

    def monitor(self):
        """Monitor clipboard with LLM."""
        print("="*70, flush=True)
        print("LLM-POWERED CLIPBOARD CONCIERGE (Phi-2, 2.7B params)", flush=True)
        print("="*70, flush=True)
        print(f"[BetterLLM] Using PyTorch: {torch.__version__}", flush=True)
        print(f"[BetterLLM] Press Ctrl+C to stop\n", flush=True)

        while not CLIPBOARD_METADATA.exists():
            print(f"[BetterLLM] Waiting for clipboard metadata...", flush=True)
            time.sleep(5)

        print(f"[BetterLLM] Started monitoring\n", flush=True)

        try:
            while True:
                # Load clipboard metadata
                try:
                    with open(CLIPBOARD_METADATA, 'r', encoding='utf-8') as f:
                        clipboard_entries = json.load(f)
                except (json.JSONDecodeError, IOError):
                    clipboard_entries = []

                # Process new entries
                for entry in clipboard_entries:
                    entry_id = entry.get('id')

                    if entry_id and entry_id not in self.processed_clipboard_ids:
                        self.process_clipboard_entry(entry)
                        self.processed_clipboard_ids.add(entry_id)

                # Sleep before next poll
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[BetterLLM] Stopped by user", flush=True)
            total_classifications = len(self.behavior_data.get("llm_classifications", []))
            print(f"[BetterLLM] Total LLM classifications: {total_classifications}", flush=True)


def main():
    """Main entry point."""
    try:
        concierge = BetterLLMConcierge()
        concierge.monitor()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
