import pandas as pd
import json

try:
    df = pd.read_excel('NPTEL Alternate Final Exam Schedule- course code, name, dno, staff.xlsx', header=None)
    data = df.head(10).fillna("").values.tolist()
    with open('excel_preview.txt', 'w') as f:
        for i, row in enumerate(data):
            f.write(f"Row {i}: {row}\n")
except Exception as e:
    print(f"Error: {e}")
