import json

SALES_PATH = r"C:\Users\raafa\Documents\Test\data\Sales.json"
FORECAST_PATH = r"C:\Users\raafa\Documents\Test\data\forecast.json"


def load_sales():
    """Read Sales.json and return it as a list of dictionaries."""
    with open(SALES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_forecast():
    """Read forecast.json and return it as a list of dictionaries."""
    with open(FORECAST_PATH, encoding="utf-8") as f:
        return json.load(f)