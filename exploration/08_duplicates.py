import pandas as pd
from load_data import load_sales

df = pd.DataFrame(load_sales())

total = len(df)
dupes = df.duplicated().sum()

print("Total rows     :", format(total, ","))
print("Distinct rows  :", format(len(df.drop_duplicates()), ","))
print("Duplicate rows :", format(dupes, ","),
      "(" + str(round(dupes / total * 100, 1)) + "%)")
print()

# Count how many copies of each distinct row exist
copies = df.value_counts(dropna=False).reset_index(name="copies")

print("The 5 most-repeated rows")
print("-" * 78)
print(copies[["copies", "Customer Code", "Product Name",
              "OrderDate", "Quantity", "Net Price"]].head(5).to_string(index=False))
print()

print("How many times does a row repeat?")
print("-" * 78)
print(copies["copies"].value_counts().sort_index().head(10).to_string())