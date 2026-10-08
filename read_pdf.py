import sys

try:
    import PyPDF2
    with open('sample time table_existing.pdf', 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for i in range(min(2, len(reader.pages))):
            text += reader.pages[i].extract_text() + "\n"
        print(text[:2000])
except ImportError:
    print("PyPDF2 not installed. Try fitz/PyMuPDF if installed...")
    try:
        import fitz
        doc = fitz.open('sample time table_existing.pdf')
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        print(text[:2000])
    except ImportError:
        print("No PDF library installed.")
except Exception as e:
    print(f"Error: {e}")
