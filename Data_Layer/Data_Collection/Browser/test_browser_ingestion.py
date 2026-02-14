"""
Test script for browser ingestion module
Run this to verify your browser data extraction works correctly
"""

from browser_ingestion import BrowserDataExtractor, BrowserRecord
from datetime import datetime


def test_chrome():
    """Test Chrome extraction"""
    print("\n" + "=" * 60)
    print("Testing Chrome Extraction")
    print("=" * 60)
    
    extractor = BrowserDataExtractor()
    
    # Test history
    print("\nExtracting Chrome history (last 7 days, max 10 records)...")
    history = extractor.extract_chrome_history(days_back=7, limit=10)
    
    if history:
        print(f"✓ Found {len(history)} history records")
        print("\nSample record:")
        print(f"  URL: {history[0].url}")
        print(f"  Title: {history[0].title}")
        print(f"  Visits: {history[0].visit_count}")
        print(f"  Last visit: {history[0].last_visit_time}")
    else:
        print("✗ No Chrome history found")
    
    # Test bookmarks
    print("\nExtracting Chrome bookmarks...")
    bookmarks = extractor.extract_chrome_bookmarks()
    
    if bookmarks:
        print(f"✓ Found {len(bookmarks)} bookmarks")
        print("\nSample bookmark:")
        print(f"  Title: {bookmarks[0].title}")
        print(f"  URL: {bookmarks[0].url}")
        print(f"  Folder: {bookmarks[0].folder}")
    else:
        print("✗ No Chrome bookmarks found")
    
    return len(history) + len(bookmarks) > 0


def test_edge():
    """Test Edge extraction"""
    print("\n" + "=" * 60)
    print("Testing Edge Extraction")
    print("=" * 60)
    
    extractor = BrowserDataExtractor()
    
    # Test history
    print("\nExtracting Edge history (last 7 days, max 10 records)...")
    history = extractor.extract_edge_history(days_back=7, limit=10)
    
    if history:
        print(f"✓ Found {len(history)} history records")
    else:
        print("✗ No Edge history found (Edge might not be installed)")
    
    # Test bookmarks
    print("\nExtracting Edge bookmarks...")
    bookmarks = extractor.extract_edge_bookmarks()
    
    if bookmarks:
        print(f"✓ Found {len(bookmarks)} bookmarks")
    else:
        print("✗ No Edge bookmarks found")
    
    return len(history) + len(bookmarks) > 0


def test_firefox():
    """Test Firefox extraction"""
    print("\n" + "=" * 60)
    print("Testing Firefox Extraction")
    print("=" * 60)
    
    extractor = BrowserDataExtractor()
    
    # Test history
    print("\nExtracting Firefox history (last 7 days, max 10 records)...")
    history = extractor.extract_firefox_history(days_back=7, limit=10)
    
    if history:
        print(f"✓ Found {len(history)} history records")
    else:
        print("✗ No Firefox history found (Firefox might not be installed)")
    
    # Test bookmarks
    print("\nExtracting Firefox bookmarks...")
    bookmarks = extractor.extract_firefox_bookmarks()
    
    if bookmarks:
        print(f"✓ Found {len(bookmarks)} bookmarks")
    else:
        print("✗ No Firefox bookmarks found")
    
    return len(history) + len(bookmarks) > 0


def test_full_extraction():
    """Test full extraction from all browsers"""
    print("\n" + "=" * 60)
    print("Testing Full Extraction (All Browsers)")
    print("=" * 60)
    
    extractor = BrowserDataExtractor()
    all_data = extractor.extract_all(days_back=7, limit_per_browser=20)
    
    total = sum(len(records) for records in all_data.values())
    
    if total > 0:
        print(f"\n✓ Successfully extracted {total} total records across all browsers")
        
        # Show breakdown
        for browser, records in all_data.items():
            if records:
                print(f"  {browser}: {len(records)} records")
    else:
        print("\n✗ No data extracted from any browser")
    
    return total > 0


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("BROWSER INGESTION MODULE - TEST SUITE")
    print("=" * 60)
    
    results = {
        'Chrome': test_chrome(),
        'Edge': test_edge(),
        'Firefox': test_firefox(),
        'Full Extraction': test_full_extraction()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed! Your browser ingestion module is working correctly.")
    elif total_passed > 0:
        print("\n⚠ Some tests passed. Check which browsers are installed on your system.")
    else:
        print("\n❌ All tests failed. Please check browser paths and permissions.")


if __name__ == "__main__":
    run_all_tests()
