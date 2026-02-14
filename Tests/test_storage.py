"""
Test Storage Manager
Quick test to ingest browser data and perform searches
"""

from pathlib import Path
import sys

# Add Data_Layer to path
sys.path.insert(0, str(Path(__file__).parent / "Data_Layer"))

from storage_manager import UnifiedStorageManager


def main():
    print("="*70)
    print("AI MINDS Storage Manager - Test Script")
    print("="*70)
    
    # Initialize manager
    manager = UnifiedStorageManager()
    
    # Find browser data files
    data_dir = Path(__file__).parent / "Data_Layer" / "Data_Storage"
    browser_files = list(data_dir.glob("browser_data_*.json"))
    
    if not browser_files:
        print("\n❌ No browser data files found in Data_Layer/Data_Storage/")
        print("   Run browser_ingestion.py first to collect data")
        return
    
    print(f"\n📂 Found {len(browser_files)} browser data files:")
    for f in browser_files:
        print(f"   - {f.name}")
    
    # Ingest all files
    print("\n" + "="*70)
    print("INGESTING BROWSER DATA")
    print("="*70)
    
    for file in browser_files:
        result = manager.ingest_browser_data(file)
        print(f"✓ {result['file']}: {result['records_added']} records added")
    
    # Show statistics
    manager.print_stats()
    
    # Perform test searches
    print("="*70)
    print("TEST SEARCHES")
    print("="*70)
    
    test_queries = [
        "robe Zara",
        "recherche",
        "shopping",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 70)
        
        results = manager.search(query, top_k=3, search_images=False)
        
        for i, result in enumerate(results.get('text_results', [])[:3], 1):
            print(f"\n{i}. Similarity: {result['similarity']:.3f}")
            print(f"   Title: {result.get('title', 'No title')[:60]}")
            print(f"   URL: {result.get('url', 'N/A')[:60]}")
            if result.get('search_query'):
                print(f"   Search Query: {result['search_query']}")
            print(f"   Time: {result.get('timestamp', 'N/A')[:19]}")
    
    print("\n" + "="*70)
    print("✓ Test completed successfully!")
    print("="*70)


if __name__ == "__main__":
    main()
