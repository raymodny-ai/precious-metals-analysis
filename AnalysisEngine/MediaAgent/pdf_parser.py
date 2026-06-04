import PyPDF2
import os

class PDFParser:
    def parse(self, file_path):
        if not os.path.exists(file_path):
            return ""
        try:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PDF parse error: {e}")
            return ""
