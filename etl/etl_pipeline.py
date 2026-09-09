"""
Orion sales ETL.

Reads the raw Sales.json and forecast.json, cleans them, and writes a star
schema out to output/ as CSV files and a SQLite database.

Usage:
    python etl/etl_pipeline.py
"""
import json
import os
import sqlite3

import pandas as pd
from pandas.api.types import is_string_dtype

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUTPUT = os.path.join(ROOT, "output")
os.makedirs(OUTPUT, exist_ok=True)

SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS fact_forecast;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_country;
DROP TABLE IF EXISTS dim_brand;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_year;

CREATE TABLE dim_year (
    Year          INTEGER PRIMARY KEY
);

CREATE TABLE dim_brand (
    Brand         TEXT PRIMARY KEY
);

CREATE TABLE dim_country (
    CountryRegion TEXT PRIMARY KEY,
    Continent     TEXT NOT NULL
);

CREATE TABLE dim_date (
    DateKey       INTEGER PRIMARY KEY,
    Date          TEXT    NOT NULL UNIQUE,
    Year          INTEGER NOT NULL,
    Quarter       INTEGER NOT NULL,
    QuarterName   TEXT    NOT NULL,
    YearQuarter   TEXT    NOT NULL,
    MonthNumber   INTEGER NOT NULL,
    MonthName     TEXT    NOT NULL,
    MonthShort    TEXT    NOT NULL,
    MonthYear     TEXT    NOT NULL,
    MonthYearSort INTEGER NOT NULL,
    DayName       TEXT    NOT NULL,
    DayOfWeek     INTEGER NOT NULL,
    IsWeekend     INTEGER NOT NULL,
    FOREIGN KEY (Year) REFERENCES dim_year (Year)
);

CREATE TABLE dim_geography (
    GeographyKey  INTEGER PRIMARY KEY,
    City          TEXT NOT NULL,
    State         TEXT NOT NULL,
    CountryRegion TEXT NOT NULL,
    Continent     TEXT NOT NULL,
    UNIQUE (City, State, CountryRegion),
    FOREIGN KEY (CountryRegion) REFERENCES dim_country (CountryRegion)
);

CREATE TABLE dim_product (
    ProductKey    INTEGER PRIMARY KEY,
    ProductName   TEXT NOT NULL,
    Brand         TEXT NOT NULL,
    Category      TEXT NOT NULL,
    Subcategory   TEXT NOT NULL,
    FOREIGN KEY (Brand) REFERENCES dim_brand (Brand)
);

CREATE TABLE dim_customer (
    CustomerKey   INTEGER PRIMARY KEY,
    CustomerCode  TEXT NOT NULL UNIQUE,
    CustomerName  TEXT,
    CustomerLabel TEXT NOT NULL,
    CustomerType  TEXT NOT NULL,
    Education     TEXT NOT NULL,
    Occupation    TEXT NOT NULL
);

CREATE TABLE fact_sales (
    SalesKey      INTEGER PRIMARY KEY,
    OrderDate     TEXT    NOT NULL,
    ProductKey    INTEGER NOT NULL,
    CustomerKey   INTEGER NOT NULL,
    GeographyKey  INTEGER NOT NULL,
    Quantity      INTEGER NOT NULL CHECK (Quantity > 0),
    NetPrice      REAL    NOT NULL CHECK (NetPrice > 0),
    SalesAmount   REAL    NOT NULL CHECK (SalesAmount > 0),
    FOREIGN KEY (OrderDate)    REFERENCES dim_date      (Date),
    FOREIGN KEY (ProductKey)   REFERENCES dim_product   (ProductKey),
    FOREIGN KEY (CustomerKey)  REFERENCES dim_customer  (CustomerKey),
    FOREIGN KEY (GeographyKey) REFERENCES dim_geography (GeographyKey)
);

CREATE TABLE fact_forecast (
    ForecastKey    INTEGER PRIMARY KEY,
    Year           INTEGER NOT NULL,
    CountryRegion  TEXT    NOT NULL,
    Brand          TEXT    NOT NULL,
    ForecastAmount REAL    NOT NULL,
    UNIQUE (Year, CountryRegion, Brand),
    FOREIGN KEY (Year)          REFERENCES dim_year    (Year),
    FOREIGN KEY (CountryRegion) REFERENCES dim_country (CountryRegion),
    FOREIGN KEY (Brand)         REFERENCES dim_brand   (Brand)
);

CREATE INDEX ix_sales_date     ON fact_sales (OrderDate);
CREATE INDEX ix_sales_product  ON fact_sales (ProductKey);
CREATE INDEX ix_sales_customer ON fact_sales (CustomerKey);
CREATE INDEX ix_sales_geo      ON fact_sales (GeographyKey);
"""


def extract():
    print("=" * 70)
    print("STAGE 1  EXTRACT")
    print("=" * 70)

    with open(os.path.join(DATA, "Sales.json"), encoding="utf-8") as f:
        sales = pd.DataFrame(json.load(f))
    with open(os.path.join(DATA, "forecast.json"), encoding="utf-8") as f:
        forecast = pd.DataFrame(json.load(f))

    print("  Sales.json    :", format(len(sales), ","), "rows,",
          len(sales.columns), "columns")
    print("  forecast.json :", format(len(forecast), ","), "rows,",
          len(forecast.columns), "columns")
    return sales, forecast


def clean(sales):
    print()
    print("=" * 70)
    print("STAGE 2  CLEAN")
    print("=" * 70)

    for col in [c for c in sales.columns if is_string_dtype(sales[c])]:
        sales[col] = sales[col].str.strip()
    print("  trimmed whitespace on text columns")

    # Dates are ambiguous until proven otherwise. If any first component were
    # above 12 the file would have to be day-first and every date we parse
    # below would be silently wrong, so stop rather than guess.
    first_part = sales["OrderDate"].str.split("/").str[0].astype(int)
    if first_part.max() > 12:
        raise ValueError("OrderDate looks like D/M/YYYY, not M/D/YYYY")
    print("  date format confirmed M/D/YYYY (largest first component =",
          first_part.max(), ")")

    sales["OrderDate"] = pd.to_datetime(sales["OrderDate"], format="%m/%d/%Y")
    print("  OrderDate converted to datetime :",
          sales["OrderDate"].min().date(), "->", sales["OrderDate"].max().date())

    # Color holds subcategory names on all 298,246 rows, not colours. Keeping
    # it would let someone chart "sales by colour" and get nonsense.
    identical = (sales["Color"] == sales["Subcategory"]).all()
    sales = sales.drop(columns=["Color"])
    print("  dropped Color (matched Subcategory on every row:", identical, ")")

    sales["SalesAmount"] = (sales["Quantity"] * sales["Net Price"]).round(4)
    print("  created SalesAmount, total $",
          format(sales["SalesAmount"].sum(), ",.2f"))

    # 259 customers never have a name, education or occupation on any row, use
    # CS-prefixed codes, and sit in their own key block. They are store
    # accounts rather than people, so they get labelled instead of blanked.
    is_business = sales["Customer Code"].str.match(r"^CS\d+$", case=False)
    sales["CustomerType"] = is_business.map({True: "Business Account",
                                             False: "Individual"})
    print("  classified customers :",
          sales.loc[is_business, "CustomerKey"].nunique(), "business /",
          sales.loc[~is_business, "CustomerKey"].nunique(), "individual")

    return sales


def build_dimensions(sales):
    print()
    print("=" * 70)
    print("STAGE 3  BUILD DIMENSIONS")
    print("=" * 70)

    dim_product = (
        sales[["ProductKey", "Product Name", "Brand", "Category", "Subcategory"]]
        .drop_duplicates(subset="ProductKey")
        .rename(columns={"Product Name": "ProductName"})
        .sort_values("ProductKey")
        .reset_index(drop=True)
    )

    # Columbus exists in both Ohio and Georgia, so the key has to be the whole
    # city/state/country combination rather than the city name.
    dim_geography = (
        sales[["City", "State", "CountryRegion", "Continent"]]
        .drop_duplicates()
        .sort_values(["CountryRegion", "State", "City"])
        .reset_index(drop=True)
    )
    dim_geography.insert(0, "GeographyKey", range(1, len(dim_geography) + 1))

    dim_customer = (
        sales[["CustomerKey", "Customer Code", "Name", "CustomerType",
               "Education", "Occupation"]]
        .drop_duplicates(subset="CustomerKey")
        .rename(columns={"Customer Code": "CustomerCode", "Name": "CustomerName"})
        .sort_values("CustomerKey")
        .reset_index(drop=True)
    )

    # "Unknown" would be wrong for a shop: it has no education level at all.
    context = dim_customer["CustomerType"].map({"Business Account": "Not Applicable",
                                                "Individual": "Unknown"})
    dim_customer["Education"] = dim_customer["Education"].fillna(context)
    dim_customer["Occupation"] = dim_customer["Occupation"].fillna(context)

    # 8,868 customers share only 8,584 names, so a chart grouped on name alone
    # would merge two different people into one bar.
    name_counts = dim_customer["CustomerName"].value_counts()

    def make_label(row):
        if row["CustomerType"] == "Business Account":
            return "Business " + row["CustomerCode"]
        if pd.isna(row["CustomerName"]):
            return "Unknown " + row["CustomerCode"]
        if name_counts[row["CustomerName"]] > 1:
            return row["CustomerName"] + " (" + row["CustomerCode"] + ")"
        return row["CustomerName"]

    dim_customer["CustomerLabel"] = dim_customer.apply(make_label, axis=1)
    dim_customer["CustomerName"] = dim_customer["CustomerName"].fillna("")
    dim_customer = dim_customer[["CustomerKey", "CustomerCode", "CustomerName",
                                 "CustomerLabel", "CustomerType",
                                 "Education", "Occupation"]]

    # The forecast is by year, brand and country, so it cannot join to the day,
    # product and city dimensions. These three give both fact tables a shared
    # table to hang off at the coarser grain.
    dim_brand = pd.DataFrame({"Brand": sorted(sales["Brand"].unique())})
    dim_country = (dim_geography[["CountryRegion", "Continent"]]
                   .drop_duplicates()
                   .sort_values("CountryRegion")
                   .reset_index(drop=True))

    # Sales only touch 603 of the 731 days in range. The calendar has to hold
    # the missing days too or time intelligence skips empty periods.
    start = pd.Timestamp(sales["OrderDate"].min().year, 1, 1)
    end = pd.Timestamp(sales["OrderDate"].max().year, 12, 31)
    d = pd.DataFrame({"Date": pd.date_range(start, end, freq="D")})
    d["DateKey"] = d["Date"].dt.strftime("%Y%m%d").astype(int)
    d["Year"] = d["Date"].dt.year
    d["Quarter"] = d["Date"].dt.quarter
    d["QuarterName"] = "Q" + d["Quarter"].astype(str)
    d["YearQuarter"] = d["Year"].astype(str) + "-Q" + d["Quarter"].astype(str)
    d["MonthNumber"] = d["Date"].dt.month
    d["MonthName"] = d["Date"].dt.strftime("%B")
    d["MonthShort"] = d["Date"].dt.strftime("%b")
    d["MonthYear"] = d["Date"].dt.strftime("%b %Y")
    # Power BI sorts text alphabetically, so MonthYear needs a numeric partner
    # to sort by or the axis reads Apr, Aug, Dec, Feb.
    d["MonthYearSort"] = d["Year"] * 100 + d["MonthNumber"]
    d["DayName"] = d["Date"].dt.strftime("%A")
    d["DayOfWeek"] = d["Date"].dt.dayofweek + 1
    d["IsWeekend"] = d["DayOfWeek"] >= 6
    dim_date = d[["DateKey", "Date", "Year", "Quarter", "QuarterName", "YearQuarter",
                  "MonthNumber", "MonthName", "MonthShort", "MonthYear",
                  "MonthYearSort", "DayName", "DayOfWeek", "IsWeekend"]]

    dim_year = pd.DataFrame({"Year": sorted(dim_date["Year"].unique())})

    dims = {
        "dim_year": dim_year,
        "dim_brand": dim_brand,
        "dim_country": dim_country,
        "dim_date": dim_date,
        "dim_geography": dim_geography,
        "dim_product": dim_product,
        "dim_customer": dim_customer,
    }
    for name, table in dims.items():
        print("  {:<16}{:>8,} rows".format(name, len(table)))
    print("  dim_date covers", len(dim_date), "days;",
          sales["OrderDate"].nunique(), "of them have sales")
    return dims


def build_facts(sales, forecast, dims):
    print()
    print("=" * 70)
    print("STAGE 4  BUILD FACT TABLES")
    print("=" * 70)

    before = len(sales)
    sales = sales.merge(
        dims["dim_geography"][["GeographyKey", "City", "State", "CountryRegion"]],
        on=["City", "State", "CountryRegion"],
        how="left",
    )
    # A merge against a dimension with duplicate keys silently multiplies rows
    # and inflates revenue, so the count has to be checked, not assumed.
    if len(sales) != before:
        raise ValueError("geography merge changed the row count: {} -> {}".format(
            before, len(sales)))
    unmatched = int(sales["GeographyKey"].isna().sum())
    if unmatched:
        raise ValueError("{} sales rows found no geography".format(unmatched))
    print("  merged GeographyKey,", format(len(sales), ","),
          "rows,", unmatched, "unmatched")

    fact_sales = (sales[["OrderDate", "ProductKey", "CustomerKey", "GeographyKey",
                         "Quantity", "Net Price", "SalesAmount"]]
                  .rename(columns={"Net Price": "NetPrice"})
                  .copy())
    fact_sales.insert(0, "SalesKey", range(1, len(fact_sales) + 1))
    print("  fact_sales    ", format(len(fact_sales), ">8,"), "rows")

    fact_forecast = forecast.rename(columns={"Forecast": "ForecastAmount"}).copy()
    for col in ["CountryRegion", "Brand"]:
        fact_forecast[col] = fact_forecast[col].str.strip()
    fact_forecast = fact_forecast.groupby(
        ["Year", "CountryRegion", "Brand"], as_index=False)["ForecastAmount"].sum()
    fact_forecast.insert(0, "ForecastKey", range(1, len(fact_forecast) + 1))
    print("  fact_forecast ", format(len(fact_forecast), ">8,"), "rows")

    return fact_sales, fact_forecast


def write_csvs(tables):
    print()
    print("=" * 70)
    print("STAGE 5  WRITE CSV FILES")
    print("=" * 70)
    for name, table in tables.items():
        path = os.path.join(OUTPUT, name + ".csv")
        table.to_csv(path, index=False, encoding="utf-8")
        print("  {:<18}{:>8,} rows{:>12,.1f} KB".format(
            name + ".csv", len(table), os.path.getsize(path) / 1024))


def load_database(tables):
    print()
    print("=" * 70)
    print("STAGE 6  LOAD INTO SQLITE")
    print("=" * 70)

    db_path = os.path.join(OUTPUT, "orion_sales.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    # Parents first: a foreign key cannot point at a row that is not there yet.
    order = ["dim_year", "dim_brand", "dim_country", "dim_date", "dim_geography",
             "dim_product", "dim_customer", "fact_forecast", "fact_sales"]
    for name in order:
        table = tables[name].copy()
        for col in table.columns:
            if str(table[col].dtype).startswith("datetime"):
                table[col] = table[col].dt.strftime("%Y-%m-%d")
        table.to_sql(name, conn, if_exists="append", index=False)
        print("  {:<16}{:>8,} rows".format(name, len(table)))

    conn.commit()
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    print("  foreign key violations:", len(violations))
    print("  database size: {:,.1f} KB".format(os.path.getsize(db_path) / 1024))

    with open(os.path.join(OUTPUT, "schema.sql"), "w", encoding="utf-8") as f:
        f.write(SCHEMA.strip() + "\n")

    conn.close()
    return violations


def validate(sales, tables, violations):
    print()
    print("=" * 70)
    print("STAGE 7  VALIDATE")
    print("=" * 70)

    conn = sqlite3.connect(os.path.join(OUTPUT, "orion_sales.db"))

    def value(sql):
        return conn.execute(sql).fetchone()[0]

    checks = [
        ("row count survives the pipeline",
         len(sales), value("SELECT COUNT(*) FROM fact_sales")),
        ("total revenue reconciles",
         round(sales["SalesAmount"].sum(), 2),
         round(value("SELECT SUM(SalesAmount) FROM fact_sales"), 2)),
        ("total quantity reconciles",
         int(sales["Quantity"].sum()),
         value("SELECT SUM(Quantity) FROM fact_sales")),
        ("foreign key violations",
         0, len(violations)),
        ("every sale has a matching calendar day",
         0, value("""SELECT COUNT(*) FROM fact_sales f
                     LEFT JOIN dim_date d ON f.OrderDate = d.Date
                     WHERE d.Date IS NULL""")),
        ("product keys are unique",
         len(tables["dim_product"]),
         value("SELECT COUNT(DISTINCT ProductKey) FROM dim_product")),
        ("customer keys are unique",
         len(tables["dim_customer"]),
         value("SELECT COUNT(DISTINCT CustomerKey) FROM dim_customer")),
        ("geography is keyed on city+state+country",
         len(tables["dim_geography"]),
         value("SELECT COUNT(DISTINCT City || '|' || State || '|' || CountryRegion)"
               " FROM dim_geography")),
        ("no customer is left unclassified",
         len(tables["dim_customer"]),
         value("SELECT COUNT(*) FROM dim_customer WHERE CustomerType IN"
               " ('Individual','Business Account')")),
    ]

    print("{:<46}{:>14}{:>14}   {}".format("CHECK", "EXPECTED", "ACTUAL", ""))
    print("-" * 88)
    failed = 0
    for name, expected, actual in checks:
        ok = expected == actual
        failed += not ok
        print("{:<46}{:>14}{:>14}   {}".format(
            name, format(expected, ",") if isinstance(expected, int) else expected,
            format(actual, ",") if isinstance(actual, int) else actual,
            "pass" if ok else "FAIL"))

    print()
    print("=" * 70)
    print("BUSINESS RECONCILIATION")
    print("=" * 70)
    by_year = pd.read_sql("""
        SELECT d.Year, SUM(f.SalesAmount) AS sales
        FROM fact_sales f JOIN dim_date d ON f.OrderDate = d.Date
        GROUP BY d.Year ORDER BY d.Year""", conn)
    for _, row in by_year.iterrows():
        print("  {} revenue   ${:>16,.2f}".format(int(row["Year"]), row["sales"]))
    print("  {} revenue   ${:>16,.2f}".format("total", by_year["sales"].sum()))

    forecast_total = value(
        "SELECT SUM(ForecastAmount) FROM fact_forecast WHERE Year = 2009")
    actual_2009 = float(by_year.loc[by_year["Year"] == 2009, "sales"].iloc[0])
    print()
    print("  2009 forecast ${:>16,.2f}".format(forecast_total))
    print("  2009 actual   ${:>16,.2f}".format(actual_2009))
    print("  variance      ${:>16,.2f}  ({:+.1%})".format(
        actual_2009 - forecast_total, actual_2009 / forecast_total - 1))

    conn.close()
    print()
    print("  " + ("all checks passed" if failed == 0
                  else "{} CHECK(S) FAILED".format(failed)))
    return failed == 0


if __name__ == "__main__":
    sales, forecast = extract()
    sales = clean(sales)
    dims = build_dimensions(sales)
    fact_sales, fact_forecast = build_facts(sales, forecast, dims)

    tables = dict(dims)
    tables["fact_sales"] = fact_sales
    tables["fact_forecast"] = fact_forecast

    write_csvs(tables)
    violations = load_database(tables)
    validate(sales, tables, violations)