import pandas as pd
from load_data import load_sales

df = pd.DataFrame(load_sales())

# Compare the two columns row by row
same = (df["Color"] == df["Subcategory"]).sum()
total = len(df)

print("Rows where Color == Subcategory:", format(same, ","), "of", format(total, ","))
print("Percentage                     :", round(same / total * 100, 2), "%")
print()

print("The 32 distinct values in the 'Color' column:")
print("-" * 60)
for value in sorted(df["Color"].unique()):
    print("  ", value)