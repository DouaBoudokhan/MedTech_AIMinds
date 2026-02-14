"""
Browser History and Bookmarks Ingestion Module
Extracts browsing data from Chrome, Firefox, Edge, and Safari
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import shutil
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs, unquote


@dataclass
class BrowserRecord:
    """Represents a single browser history or bookmark record"""
    url: str
    title: str
    visit_count: int
    last_visit_time: str
    record_type: str  # 'history' or 'bookmark'
    browser: str  # 'chrome', 'firefox', 'edge', 'safari'
    folder: Optional[str] = None  # For bookmarks
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None  # Extracted search terms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class BrowserDataExtractor:
    """Extract browsing history and bookmarks from various browsers"""
    
    def __init__(self):
        """Initialize the extractor"""
        self.supported_browsers = ['chrome', 'firefox', 'edge', 'safari']
        
        # Detect all Chrome and Edge profiles
        self.chrome_profiles = self._get_chrome_profiles()
        self.edge_profiles = self._get_edge_profiles()
        
        # Common search query parameters
        self.search_params = ['q', 'query', 'search', 's', 'searchTerm', 'term', 'keyword', 'k']
        
        # Browser database paths (Windows) - now supports multiple profiles
        self.browser_paths = {
            'firefox': {
                'history': Path(os.getenv('APPDATA')) / 'Mozilla' / 'Firefox' / 'Profiles',
                'bookmarks': Path(os.getenv('APPDATA')) / 'Mozilla' / 'Firefox' / 'Profiles'
            },
            'safari': {
                'history': Path.home() / 'Library' / 'Safari' / 'History.db',
                'bookmarks': Path.home() / 'Library' / 'Safari' / 'Bookmarks.plist'
            }
        }
    
    def _get_chrome_profiles(self) -> List[str]:
        """Detect all Chrome profile directories"""
        chrome_base = Path(os.getenv('LOCALAPPDATA')) / 'Google' / 'Chrome' / 'User Data'
        profiles = []
        
        if chrome_base.exists():
            # Add Default profile
            if (chrome_base / 'Default').exists():
                profiles.append('Default')
            
            # Add numbered profiles (Profile 1, Profile 2, etc.)
            for i in range(1, 20):  # Support up to 19 additional profiles
                profile_name = f'Profile {i}'
                if (chrome_base / profile_name).exists():
                    profiles.append(profile_name)
        
        return profiles
    
    def _get_edge_profiles(self) -> List[str]:
        """Detect all Edge profile directories"""
        edge_base = Path(os.getenv('LOCALAPPDATA')) / 'Microsoft' / 'Edge' / 'User Data'
        profiles = []
        
        if edge_base.exists():
            # Add Default profile
            if (edge_base / 'Default').exists():
                profiles.append('Default')
            
            # Add numbered profiles
            for i in range(1, 20):
                profile_name = f'Profile {i}'
                if (edge_base / profile_name).exists():
                    profiles.append(profile_name)
        
        return profiles
    
    def _get_firefox_profile(self) -> Optional[Path]:
        """Get the default Firefox profile path"""
        firefox_profiles = self.browser_paths['firefox']['history']
        
        if firefox_profiles.exists():
            profiles = [p for p in firefox_profiles.iterdir() if p.is_dir() and p.name.endswith('.default-release')]
            if profiles:
                return profiles[0]
        return None
    
    def _extract_search_query(self, url: str) -> Optional[str]:
        """Extract search query from URL if present"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check common search parameters
            for param in self.search_params:
                if param in params and params[param]:
                    query = unquote(params[param][0])
                    return query
            
            return None
        except:
            return None
    
    def extract_chrome_history(self, days_back: int = 30, limit: int = 1000) -> List[BrowserRecord]:
        """Extract Chrome browsing history from all profiles"""
        all_records = []
        
        for profile_name in self.chrome_profiles:
            records = self._extract_chromium_history_from_profile(
                'chrome', profile_name, days_back, limit
            )
            all_records.extend(records)
        
        return all_records
    
    def extract_edge_history(self, days_back: int = 30, limit: int = 1000) -> List[BrowserRecord]:
        """Extract Edge browsing history from all profiles"""
        all_records = []
        
        for profile_name in self.edge_profiles:
            records = self._extract_chromium_history_from_profile(
                'edge', profile_name, days_back, limit
            )
            all_records.extend(records)
        
        return all_records
    
    def _extract_chromium_history_from_profile(
        self, 
        browser: str, 
        profile_name: str, 
        days_back: int, 
        limit: int
    ) -> List[BrowserRecord]:
        """Extract history from a specific Chromium browser profile"""
        records = []
        
        # Determine base path
        if browser == 'chrome':
            base_path = Path(os.getenv('LOCALAPPDATA')) / 'Google' / 'Chrome' / 'User Data'
        else:  # edge
            base_path = Path(os.getenv('LOCALAPPDATA')) / 'Microsoft' / 'Edge' / 'User Data'
        
        history_path = base_path / profile_name / 'History'
        
        if not history_path.exists():
            return records
        
        # Create a temporary copy to avoid database lock issues
        temp_path = Path(f"temp_{browser}_{profile_name.replace(' ', '_')}_history")
        
        try:
            # Copy the database file
            shutil.copy2(history_path, temp_path)
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # Calculate the time threshold
            chrome_epoch = datetime(1601, 1, 1)
            time_threshold = datetime.now() - timedelta(days=days_back)
            threshold_microseconds = int((time_threshold - chrome_epoch).total_seconds() * 1_000_000)
            
            query = """
                SELECT url, title, visit_count, last_visit_time
                FROM urls
                WHERE last_visit_time > ?
                ORDER BY last_visit_time DESC
                LIMIT ?
            """
            
            cursor.execute(query, (threshold_microseconds, limit))
            
            for row in cursor.fetchall():
                url, title, visit_count, last_visit_time = row
                
                # Convert Chrome timestamp to datetime
                visit_datetime = chrome_epoch + timedelta(microseconds=last_visit_time)
                
                # Extract search query if present
                search_query = self._extract_search_query(url)
                
                record = BrowserRecord(
                    url=url,
                    title=title or url,
                    visit_count=visit_count,
                    last_visit_time=visit_datetime.isoformat(),
                    record_type='history',
                    browser=f"{browser} ({profile_name})",
                    search_query=search_query
                )
                records.append(record)
            
            conn.close()
            
        except (PermissionError, sqlite3.DatabaseError) as e:
            # Silently skip if browser is open and database is locked
            pass
        except Exception as e:
            print(f"Error extracting {browser} ({profile_name}) history: {e}")
        finally:
            # Clean up temp file
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
        
        return records
    
    def extract_firefox_history(self, days_back: int = 30, limit: int = 1000) -> List[BrowserRecord]:
        """Extract Firefox browsing history"""
        records = []
        
        profile_path = self._get_firefox_profile()
        if not profile_path:
            return records
        
        history_path = profile_path / 'places.sqlite'
        
        if not history_path.exists():
            return records
        
        temp_path = Path("temp_firefox_history")
        try:
            shutil.copy2(history_path, temp_path)
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # Calculate time threshold (Firefox uses Unix timestamps in microseconds)
            time_threshold = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1_000_000)
            
            query = """
                SELECT url, title, visit_count, last_visit_date
                FROM moz_places
                WHERE last_visit_date > ?
                ORDER BY last_visit_date DESC
                LIMIT ?
            """
            
            cursor.execute(query, (time_threshold, limit))
            
            for row in cursor.fetchall():
                url, title, visit_count, last_visit_time = row
                
                # Convert Firefox timestamp to datetime
                visit_datetime = datetime.fromtimestamp(last_visit_time / 1_000_000) if last_visit_time else datetime.now()
                
                # Extract search query if present
                search_query = self._extract_search_query(url)
                
                record = BrowserRecord(
                    url=url,
                    title=title or url,
                    visit_count=visit_count,
                    last_visit_time=visit_datetime.isoformat(),
                    record_type='history',
                    browser='firefox',
                    search_query=search_query
                )
                records.append(record)
            
            conn.close()
            
        except Exception as e:
            print(f"Error extracting Firefox history: {e}")
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
        
        return records
    
    def extract_chrome_bookmarks(self) -> List[BrowserRecord]:
        """Extract Chrome bookmarks from all profiles"""
        all_records = []
        
        for profile_name in self.chrome_profiles:
            records = self._extract_chromium_bookmarks_from_profile('chrome', profile_name)
            all_records.extend(records)
        
        return all_records
    
    def extract_edge_bookmarks(self) -> List[BrowserRecord]:
        """Extract Edge bookmarks from all profiles"""
        all_records = []
        
        for profile_name in self.edge_profiles:
            records = self._extract_chromium_bookmarks_from_profile('edge', profile_name)
            all_records.extend(records)
        
        return all_records
    
    def _extract_chromium_bookmarks_from_profile(self, browser: str, profile_name: str) -> List[BrowserRecord]:
        """Extract bookmarks from a specific Chromium browser profile"""
        records = []
        
        # Determine base path
        if browser == 'chrome':
            base_path = Path(os.getenv('LOCALAPPDATA')) / 'Google' / 'Chrome' / 'User Data'
        else:  # edge
            base_path = Path(os.getenv('LOCALAPPDATA')) / 'Microsoft' / 'Edge' / 'User Data'
        
        bookmarks_path = base_path / profile_name / 'Bookmarks'
        
        if not bookmarks_path.exists():
            return records
        
        try:
            with open(bookmarks_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Parse bookmark tree
            def parse_bookmark_node(node, folder_path=""):
                if node.get('type') == 'url':
                    # Extract search query if present
                    search_query = self._extract_search_query(node.get('url', ''))
                    
                    record = BrowserRecord(
                        url=node.get('url', ''),
                        title=node.get('name', ''),
                        visit_count=0,
                        last_visit_time=datetime.now().isoformat(),
                        record_type='bookmark',
                        browser=f"{browser} ({profile_name})",
                        folder=folder_path,
                        search_query=search_query
                    )
                    records.append(record)
                elif node.get('type') == 'folder':
                    folder_name = node.get('name', '')
                    new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
                    for child in node.get('children', []):
                        parse_bookmark_node(child, new_path)
            
            # Parse all bookmark roots
            roots = data.get('roots', {})
            for root_name, root_node in roots.items():
                if isinstance(root_node, dict) and 'children' in root_node:
                    for child in root_node['children']:
                        parse_bookmark_node(child, root_name)
        
        except Exception as e:
            print(f"Error extracting {browser} ({profile_name}) bookmarks: {e}")
        
        return records
    
    def extract_firefox_bookmarks(self) -> List[BrowserRecord]:
        """Extract Firefox bookmarks"""
        records = []
        
        profile_path = self._get_firefox_profile()
        if not profile_path:
            return records
        
        bookmarks_path = profile_path / 'places.sqlite'
        
        if not bookmarks_path.exists():
            return records
        
        temp_path = Path("temp_firefox_bookmarks")
        try:
            shutil.copy2(bookmarks_path, temp_path)
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            query = """
                SELECT p.url, p.title, p.visit_count, b.dateAdded, b.parent
                FROM moz_places p
                JOIN moz_bookmarks b ON p.id = b.fk
                WHERE b.type = 1
                ORDER BY b.dateAdded DESC
            """
            
            cursor.execute(query)
            
            for row in cursor.fetchall():
                url, title, visit_count, date_added, parent_id = row
                
                # Convert timestamp
                added_datetime = datetime.fromtimestamp(date_added / 1_000_000) if date_added else datetime.now()
                
                record = BrowserRecord(
                    url=url,
                    title=title or url,
                    visit_count=visit_count or 0,
                    last_visit_time=added_datetime.isoformat(),
                    record_type='bookmark',
                    browser='firefox'
                )
                records.append(record)
            
            conn.close()
            
        except Exception as e:
            print(f"Error extracting Firefox bookmarks: {e}")
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
        
        return records
    
    def extract_all(self, days_back: int = 30, limit_per_browser: int = 500) -> Dict[str, List[BrowserRecord]]:
        """
        Extract all browser data from all available browsers
        
        Args:
            days_back: Number of days to look back
            limit_per_browser: Maximum records per browser
            
        Returns:
            Dictionary mapping browser names to lists of records
        """
        all_data = {}
        
        # Chrome
        print("Extracting Chrome data...")
        chrome_history = self.extract_chrome_history(days_back, limit_per_browser)
        chrome_bookmarks = self.extract_chrome_bookmarks()
        all_data['chrome'] = chrome_history + chrome_bookmarks
        
        # Edge
        print("Extracting Edge data...")
        edge_history = self.extract_edge_history(days_back, limit_per_browser)
        edge_bookmarks = self.extract_edge_bookmarks()
        all_data['edge'] = edge_history + edge_bookmarks
        
        # Firefox
        print("Extracting Firefox data...")
        firefox_history = self.extract_firefox_history(days_back, limit_per_browser)
        firefox_bookmarks = self.extract_firefox_bookmarks()
        all_data['firefox'] = firefox_history + firefox_bookmarks
        
        return all_data
    
    def export_by_month(self, records: List[BrowserRecord]):
        """Export records grouped by month into separate files"""
        # Group by month
        by_month = {}
        
        for record in records:
            # Parse the timestamp to get the month
            timestamp = datetime.fromisoformat(record.last_visit_time)
            month_key = timestamp.strftime('%Y-%m')
            
            if month_key not in by_month:
                by_month[month_key] = []
            
            by_month[month_key].append(record)
        
        # Create output directory if it doesn't exist
        output_dir = Path(__file__).parent.parent.parent / "Data Storage"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export each month to a separate file
        total_files = 0
        for month_key, month_records in by_month.items():
            # Group by day within the month
            by_day = {}
            
            for record in month_records:
                timestamp = datetime.fromisoformat(record.last_visit_time)
                date_key = timestamp.strftime('%Y-%m-%d')
                
                if date_key not in by_day:
                    by_day[date_key] = []
                
                # Add record with exact timestamp
                record_dict = record.to_dict()
                record_dict['exact_timestamp'] = timestamp.isoformat()
                record_dict['time_of_day'] = timestamp.strftime('%H:%M:%S')
                by_day[date_key].append(record_dict)
            
            # Sort each day's records by timestamp
            for date_key in by_day:
                by_day[date_key].sort(key=lambda x: x['exact_timestamp'], reverse=True)
            
            # Create organized output for this month
            year, month = month_key.split('-')
            output_file = output_dir / f"browser_data_{year}_{month}.json"
            
            organized_data = {
                'month': month_key,
                'total_records': len(month_records),
                'last_updated': datetime.now().isoformat(),
                'date_range': {
                    'start': min(by_day.keys()) if by_day else None,
                    'end': max(by_day.keys()) if by_day else None
                },
                'records_by_day': by_day
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(organized_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ {output_file}: {len(month_records)} records ({len(by_day)} days)")
            
            # Print summary for this month
            for date_key in sorted(by_day.keys(), reverse=True):
                count = len(by_day[date_key])
                history_count = sum(1 for r in by_day[date_key] if r['record_type'] == 'history')
                bookmark_count = count - history_count
                search_count = sum(1 for r in by_day[date_key] if r.get('search_query'))
                print(f"  {date_key}: {count} records (History: {history_count}, Bookmarks: {bookmark_count}, Searches: {search_count})")
            
            total_files += 1
        
        print(f"\n✓ Total: {len(records)} records exported to {total_files} monthly files")
        print(f"✓ Files will be updated each time you run this script")


def main():
    """Main function for testing"""
    extractor = BrowserDataExtractor()
    
    print("=" * 60)
    print("Browser History & Bookmarks Extraction")
    print("=" * 60)
    
    # Extract all data
    all_data = extractor.extract_all(days_back=30, limit_per_browser=500)
    
    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    
    total_records = 0
    for browser, records in all_data.items():
        if records:
            history_count = sum(1 for r in records if r.record_type == 'history')
            bookmark_count = sum(1 for r in records if r.record_type == 'bookmark')
            search_count = sum(1 for r in records if r.search_query)
            
            print(f"\n{browser.upper()}:")
            print(f"  History: {history_count} records")
            print(f"  Bookmarks: {bookmark_count} records")
            print(f"  Searches: {search_count} records")
            print(f"  Total: {len(records)} records")
            
            total_records += len(records)
    
    print(f"\nTotal records extracted: {total_records}")
    
    if total_records > 0:
        # Combine all records
        all_records = []
        for records in all_data.values():
            all_records.extend(records)
        
        # Export grouped by month (separate file for each month)
        extractor.export_by_month(all_records)
    
    return all_data


if __name__ == "__main__":
    main()
