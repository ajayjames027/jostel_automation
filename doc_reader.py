import zipfile
import xml.etree.ElementTree as ET

def extract_text_from_docx(path):
    try:
        docx = zipfile.ZipFile(path)
        content = docx.read('word/document.xml')
        tree = ET.fromstring(content)
        
        # Define the namespaces
        namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        paragraphs = tree.findall('.//w:p', namespaces)
        
        text = []
        for p in paragraphs:
            texts = [node.text for node in p.findall('.//w:t', namespaces) if node.text]
            if texts:
                text.append(''.join(texts))
        return '\n'.join(text)
    except Exception as e:
        return str(e)

print(extract_text_from_docx('c:/Users/ajayj/Downloads/jostel_quiz/Component-I_K1_K2_Template.docx'))
