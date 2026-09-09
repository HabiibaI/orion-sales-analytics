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
