"""
Simple Chat Interface
=====================

Interactive CLI for querying the AI MINDS system
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Data_Layer"))
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))


class ChatInterface:
    """Simple CLI chat interface"""
    
    def __init__(self):
        """Initialize chat interface"""
        self.storage = None
        self.rag_engine = None
        self.history = []
    
    def setup(self):
        """Setup storage and RAG engine"""
        try:
            from storage_manager import UnifiedStorageManager
            from rag_engine import RAGEngine
            
            print("🔧 Loading storage manager...")
            self.storage = UnifiedStorageManager()
            
            print("🔧 Loading RAG engine...")
            self.rag_engine = RAGEngine(self.storage)
            
            print("✅ System ready!\n")
            return True
        
        except Exception as e:
            print(f"❌ Setup error: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5):
        """
        Search and display results
        
        Args:
            query: Search query
            top_k: Number of results
        """
        if self.storage is None:
            print("❌ Storage not initialized. Run setup() first.")
            return
        
        print(f"\n🔍 Searching: {query}\n")
        
        results = self.storage.search(query, top_k=top_k)
        
        if not results:
            print("No results found.")
            return
        
        print(f"Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] Score: {result['score']:.3f}")
            print(f"    Source: {result.get('source', 'Unknown')}")
            
            # Show text preview
            text = result.get('text', result.get('content', ''))
            preview = text[:200] + "..." if len(text) > 200 else text
            print(f"    {preview}\n")
    
    def chat_loop(self):
        """Run interactive chat loop"""
        print("\n" + "="*60)
        print("🤖 AI MINDS Chat Interface")
        print("="*60)
        print("\nCommands:")
        print("  /search <query>  - Search memory")
        print("  /stats          - Show storage statistics")
        print("  /help           - Show this help")
        print("  /quit           - Exit")
        print("\n" + "="*60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    parts = user_input.split(maxsplit=1)
                    command = parts[0].lower()
                    
                    if command == '/quit':
                        print("\n👋 Goodbye!")
                        break
                    
                    elif command == '/help':
                        print("\nCommands:")
                        print("  /search <query>  - Search memory")
                        print("  /stats          - Show storage statistics")
                        print("  /help           - Show this help")
                        print("  /quit           - Exit\n")
                    
                    elif command == '/stats':
                        if self.storage:
                            self.storage.print_stats()
                        else:
                            print("❌ Storage not initialized")
                    
                    elif command == '/search':
                        if len(parts) < 2:
                            print("Usage: /search <query>")
                        else:
                            query = parts[1]
                            self.search(query)
                    
                    else:
                        print(f"Unknown command: {command}")
                        print("Type /help for available commands")
                
                else:
                    # Regular search
                    self.search(user_input)
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    chat = ChatInterface()
    
    if chat.setup():
        chat.chat_loop()
    else:
        print("\n❌ Failed to initialize. Please check:")
        print("1. storage_manager.py exists in Data_Layer/")
        print("2. Dependencies are installed (uv sync)")
        print("3. Vector store is initialized")


if __name__ == "__main__":
    main()
