import json
from docx import Document

def parse_docx(file_path):
    doc = Document(file_path)
    res = []
    for i, table in enumerate(doc.tables):
        t_data = []
        for row in table.rows:
            t_data.append([cell.text.strip().replace('\n', ' ').replace('\r', ' ') for cell in row.cells])
        res.append(t_data)
        if i >= 2: break
    print(json.dumps(res, indent=2))

if __name__ == '__main__':
    parse_docx('c:/Users/ajayj/Downloads/jostel_quiz/Component-I_K1_K2_Template.docx')
