import pandas as pd

try:
    df = pd.read_excel('NPTEL Alternate Final Exam Schedule- course code, name, dno, staff.xlsx', header=None)
    for i in range(5):
        print(f"Row {i}:", df.iloc[i].tolist())
except Exception as e:
    print(f"Error: {e}")
