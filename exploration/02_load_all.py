import json
import time
import tracemalloc          # measures how much memory Python uses

path = r"C:\Users\raafa\Documents\Test\data\Sales.json"

tracemalloc.start()
start = time.time()

# Load the ENTIRE file into memory
with open(path, encoding="utf-8") as f:
    data = json.load(f)

elapsed = time.time() - start
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print("Records loaded :", format(len(data), ","))
print("Time taken     :", round(elapsed, 1), "seconds")
print("Peak memory    :", round(peak / 1024 / 1024), "MB")