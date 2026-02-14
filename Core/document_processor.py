"""
Document Processor - Extract text from documents
=================================================

Handles:
- PDF text extraction
- DOCX text extraction  
- TXT files
"""

from typing import Optional
from pathlib import Path


class DocumentProcessor:
    """Process various document formats"""
    
    def __init__(self):
        """Initialize document processor"""
        self.pdf_available = False
        self.docx_available = False
        
        # Check PDF support
        try:
            import PyPDF2
            self.pdf_available = True
            print("✅ PDF support: PyPDF2")
        except ImportError:
            print("⚠️  PyPDF2 not installed")
            print("   Install: uv add pypdf2")
        
        # Check DOCX support
        try:
            import docx
            self.docx_available = True
            print("✅ DOCX support: python-docx")
        except ImportError:
            print("⚠️  python-docx not installed")
            print("   Install: uv add python-docx")
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from document
        
        Args:
            file_path: Path to document
            
        Returns:
            Extracted text
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == '.pdf':
            return self.extract_from_pdf(file_path)
        elif extension in ['.docx', '.doc']:
            return self.extract_from_docx(file_path)
        elif extension == '.txt':
            return self.extract_from_txt(file_path)
        else:
            print(f"⚠️  Unsupported format: {extension}")
            return ""
    
    def extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        if not self.pdf_available:
            return ""
        
        try:
            import PyPDF2
            
            text = []
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for page in reader.pages:
                    text.append(page.extract_text())
            
            return "\n".join(text)
        
        except Exception as e:
            print(f"❌ PDF error for {pdf_path}: {e}")
            return ""
    
    def extract_from_docx(self, docx_path: str) -> str:
        """Extract text from DOCX"""
        if not self.docx_available:
            return ""
        
        try:
            import docx
            
            doc = docx.Document(docx_path)
            text = []
            
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            
            return "\n".join(text)
        
        except Exception as e:
            print(f"❌ DOCX error for {docx_path}: {e}")
            return ""
    
    def extract_from_txt(self, txt_path: str) -> str:
        """Extract text from TXT"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"❌ TXT error for {txt_path}: {e}")
            return ""
    
    def get_metadata(self, file_path: str) -> dict:
        """
        Get document metadata
        
        Args:
            file_path: Path to document
            
        Returns:
            Metadata dictionary
        """
        path = Path(file_path)
        
        try:
            stat = path.stat()
            
            return {
                'name': path.name,
                'extension': path.suffix,
                'size_bytes': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime
            }
        except Exception as e:
            print(f"❌ Metadata error for {file_path}: {e}")
            return {}


def test_document_processor():
    """Test document processing functionality"""
    print("\n🧪 Testing Document Processor\n" + "="*50)
    
    processor = DocumentProcessor()
    
    print("\n✅ Document processor initialized")
    print(f"   PDF support: {processor.pdf_available}")
    print(f"   DOCX support: {processor.docx_available}")
    
    print("\n💡 To extract text:")
    print("   text = processor.extract_text('document.pdf')")
    print("   print(text)")


if __name__ == "__main__":
    test_document_processor()
