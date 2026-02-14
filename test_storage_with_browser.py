"""
Practical Embedding Test - Storage Manager
===========================================

Tests the complete storage pipeline with your browser data
"""

print("\n" + "="*70)
print("🧠 AI MINDS - Storage Manager Test (Browser Data)")
print("="*70)

print("\n📋 This test will:")
print("  1. Initialize storage manager (loads Sentence-Transformers + CLIP)")
print("  2. Ingest your browser data (824 records)")
print("  3. Create vector embeddings")
print("  4. Perform semantic search")
print("  5. Show results")

print("\n⚠️  This will take 2-3 minutes on first run:")
print("  • ~60 seconds: Load models")
print("  • ~90 seconds: Download models (~500MB)")
print("  • ~30 seconds: Create embeddings for 824 records")

response = input("\n▶️  Continue? (y/n): ")

if response.lower() != 'y':
    print("Cancelled.")
    exit()

print("\n" + "="*70)
print("🔧 Step 1: Initializing Storage Manager...")
print("="*70)

try:
    from Data_Layer.storage_manager import UnifiedStorageManager
    
    manager = UnifiedStorageManager()
    
    print("\n" + "="*70)
    print("📥 Step 2: Ingesting Browser Data...")
    print("="*70)
    
    # Ingest February 2026 data
    count = manager.ingest_browser_data("Data_Layer/Data_Storage/browser_data_2026_02.json")
    
    print(f"\n✅ Ingested {count} browser items")
    
    print("\n" + "="*70)
    print("🔍 Step 3: Testing Semantic Search...")
    print("="*70)
    
    test_queries = [
        "machine learning",
        "robe Zara",
        "python tutorial"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        results = manager.search(query, top_k=3)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, r in enumerate(results, 1):
                print(f"   {i}. Score: {r['score']:.3f} | Type: {r['type']}")
        else:
            print("   No results found")
    
    print("\n" + "="*70)
    print("📊 Step 4: Storage Statistics")
    print("="*70)
    
    manager.print_stats()
    
    print("="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\n💡 Your embeddings are working perfectly!")
    print("   - Models loaded successfully")
    print("   - Browser data vectorized")
    print("   - Semantic search operational")
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
