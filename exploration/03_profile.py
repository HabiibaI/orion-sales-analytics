import pandas as pd
from load_data import load_sales

data = load_sales()

# Turn the list of dictionaries into a table
df = pd.DataFrame(data)

print("Shape (rows, columns):", df.shape)
print()

print("=" * 70)
print("NULLS PER COLUMN")
print("=" * 70)
nulls = df.isnull().sum()
print(pd.DataFrame({
    "nulls": nulls,
    "percent": (nulls / len(df) * 100).round(1)
}))
print()

print("=" * 70)
print("DISTINCT VALUES + DATA TYPE PER COLUMN")
print("=" * 70)
print(pd.DataFrame({
    "distinct": df.nunique(),
    "dtype": df.dtypes
}))