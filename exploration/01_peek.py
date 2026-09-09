import os

path = r"C:\Users\raafa\Documents\Test\data\Sales.json"


size_mb = os.path.getsize(path) / 1024 / 1024
print("File size:", round(size_mb, 1), "MB")
print("-" * 60)


with open(path, encoding="utf-8") as f:
    print(f.read(1200))