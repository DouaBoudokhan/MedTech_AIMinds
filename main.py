"""
AI MINDS - Main Entry Point
============================

Orchestrates all data collection modules and storage
"""

import sys
from pathlib import Path
from datetime import datetime

# Add modules to path
sys.path.insert(0, str(Path(__file__) / "Data_Layer"))
sys.path.insert(0, str(Path(__file__) / "Core"))


def collect_browser_data():
    """Collect browser data"""
    print("\n📊 Collecting Browser Data")
    print("=" * 60)
    
    try:
        from Data_Layer.Data_Collection.Browser.browser_ingestion import BrowserDataCollector
        
        collector = BrowserDataCollector()
        collector.export_by_month()
        
        print("✅ Browser data collected")
    except Exception as e:
        print(f"❌ Browser collection error: {e}")


def ingest_data_to_storage():
    """Ingest all collected data into storage"""
    print("\n💾 Ingesting Data to Storage")
    print("=" * 60)
    
    try:
        from Data_Layer.storage_manager import UnifiedStorageManager
        
        manager = UnifiedStorageManager()
        
        # Find and ingest browser data
        storage_dir = Path(__file__).parent / "Data_Layer" / "Data_Storage"
        browser_files = list(storage_dir.glob("browser_data_*.json"))
        
        total = 0
        for file in browser_files:
            count = manager.ingest_browser_data(str(file))
            total += count
        
        print(f"\n✅ Ingested {total} total items")
        
        # Show stats
        manager.print_stats()
        
    except Exception as e:
        print(f"❌ Ingestion error: {e}")


def interactive_search():
    """Interactive search interface"""
    from API.chat_interface import ChatInterface
    
    chat = ChatInterface()
    if chat.setup():
        chat.chat_loop()


def show_menu():
    """Show main menu"""
    print("\n" + "=" * 60)
    print("🧠 AI MINDS - Personal Knowledge Assistant")
    print("=" * 60)
    print("\nOptions:")
    print("  1. Collect browser data")
    print("  2. Ingest data to storage")
    print("  3. Interactive search")
    print("  4. Full pipeline (collect + ingest)")
    print("  5. Show statistics")
    print("  6. Exit")
    print("\n" + "=" * 60)


def show_stats():
    """Show storage statistics"""
    try:
        from Data_Layer.storage_manager import UnifiedStorageManager
        
        manager = UnifiedStorageManager()
        manager.print_stats()
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    while True:
        show_menu()
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            collect_browser_data()
        
        elif choice == '2':
            ingest_data_to_storage()
        
        elif choice == '3':
            interactive_search()
        
        elif choice == '4':
            collect_browser_data()
            ingest_data_to_storage()
        
        elif choice == '5':
            show_stats()
        
        elif choice == '6':
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("❌ Invalid option")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
