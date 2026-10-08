import pandas as pd

try:
    df = pd.read_excel('NPTEL Alternate Final Exam Schedule- course code, name, dno, staff.xlsx')
    print("Columns:", list(df.columns))
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())
except Exception as e:
    print(f"Error: {e}")
