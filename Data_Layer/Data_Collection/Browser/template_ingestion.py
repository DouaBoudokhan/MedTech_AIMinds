"""
Template for additional ingestion modules
Copy this file and modify for your specific data source

Team members should create:
- [type]_ingestion.py (main extraction logic)
- test_[type]_ingestion.py (testing)
- Update requirements.txt with any new dependencies
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime
import json


@dataclass
class DataRecord:
    """
    Base record structure
    Modify fields based on your data type
    """
    content: str
    source_type: str  # e.g., 'email', 'screenshot', 'audio', etc.
    timestamp: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class DataExtractor:
    """
    Base extractor class
    Implement your specific extraction logic
    """
    
    def __init__(self):
        """Initialize the extractor"""
        self.source_name = "YOUR_SOURCE_NAME"  # e.g., "email", "screenshots"
    
    def extract(self, **kwargs) -> List[DataRecord]:
        """
        Main extraction method
        
        Args:
            **kwargs: Parameters specific to your data source
            
        Returns:
            List of DataRecord objects
        """
        records = []
        
        # TODO: Implement your extraction logic here
        # Example:
        # for item in your_data_source:
        #     record = DataRecord(
        #         content=item.content,
        #         source_type=self.source_name,
        #         timestamp=datetime.now().isoformat(),
        #         metadata={"key": "value"}
        #     )
        #     records.append(record)
        
        return records
    
    def export_to_json(self, records: List[DataRecord], output_file: str):
        """Export records to JSON file"""
        data = [record.to_dict() for record in records]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(records)} records to {output_file}")


def main():
    """Main function for testing"""
    extractor = DataExtractor()
    
    print("=" * 60)
    print(f"{extractor.source_name.upper()} Data Extraction")
    print("=" * 60)
    
    # Extract data
    records = extractor.extract()
    
    # Print summary
    print(f"\nExtracted {len(records)} records")
    
    # Export if we have data
    if records:
        output_file = f"{extractor.source_name}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        extractor.export_to_json(records, output_file)
        print(f"✓ Data exported to: {output_file}")
    
    return records


if __name__ == "__main__":
    main()
