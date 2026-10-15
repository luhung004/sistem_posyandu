import pandas as pd, glob, os
for f in sorted(glob.glob(os.path.join("who_source", "*.xlsx"))):
    xl = pd.ExcelFile(f)
    print(os.path.basename(f), "| sheets:", xl.sheet_names)
    df = xl.parse(xl.sheet_names[0], header=None, nrows=6)
    print(df.to_string(max_cols=14))
    print("-" * 110)
