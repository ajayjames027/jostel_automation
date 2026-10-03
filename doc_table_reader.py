from docx import Document
import sys

def parse_docx(file_path):
    doc = Document(file_path)
    for i, table in enumerate(doc.tables):
        print(f"Table {i+1}:")
        for row in table.rows:
            print(" | ".join([cell.text.replace('\n', ' ').strip() for cell in row.cells]))
        print("-" * 40)
        if i >= 5: break

if __name__ == '__main__':
    parse_docx('c:/Users/ajayj/Downloads/jostel_quiz/Component-I_K1_K2_Template.docx')
