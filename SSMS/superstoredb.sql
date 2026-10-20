-- 1. Create Database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'superstore_db')
BEGIN
    CREATE DATABASE superstore_db;
END
GO

USE superstore_db;
GO

-- 2. Create Dimension Tables
IF OBJECT_ID('dim_customer', 'U') IS NOT NULL DROP TABLE dim_customer;
CREATE TABLE dim_customer (
    Customer_ID VARCHAR(50) PRIMARY KEY,
    Customer_Name VARCHAR(255) NOT NULL,
    Segment VARCHAR(100) NOT NULL
);

IF OBJECT_ID('dim_product', 'U') IS NOT NULL DROP TABLE dim_product;
CREATE TABLE dim_product (
    Product_ID VARCHAR(50) PRIMARY KEY,
    Product_Name VARCHAR(255) NOT NULL,
    Category VARCHAR(100) NOT NULL,
    Sub_Category VARCHAR(100) NOT NULL
);

IF OBJECT_ID('dim_location', 'U') IS NOT NULL DROP TABLE dim_location;
CREATE TABLE dim_location (
    Location_ID INT PRIMARY KEY,
    City VARCHAR(100) NOT NULL,
    State VARCHAR(100) NOT NULL,
    Country VARCHAR(100) NOT NULL,
    Market VARCHAR(100) NOT NULL
);

IF OBJECT_ID('dim_date', 'U') IS NOT NULL DROP TABLE dim_date;
CREATE TABLE dim_date (
    Date_Key VARCHAR(10) PRIMARY KEY,
    Date DATE NOT NULL,
    Year INT NOT NULL,
    Quarter INT NOT NULL,
    Month VARCHAR(20) NOT NULL,
    DayOfWeek VARCHAR(20) NOT NULL,
    WeekNum INT NOT NULL
);

-- 3. Create Fact Table with Primary and Foreign Keys
IF OBJECT_ID('fact_sales', 'U') IS NOT NULL DROP TABLE fact_sales;
CREATE TABLE fact_sales (
    Row_ID INT PRIMARY KEY,
    Order_ID VARCHAR(50) NOT NULL,
    Order_Date VARCHAR(10) NOT NULL,
    Ship_Date VARCHAR(10) NOT NULL,
    Customer_ID VARCHAR(50) NOT NULL,
    Product_ID VARCHAR(50) NOT NULL,
    Location_ID INT NOT NULL,
    Ship_Mode VARCHAR(50),
    Order_Priority VARCHAR(50),
    Sales DECIMAL(18, 2),
    Quantity INT,
    Discount DECIMAL(5, 2),
    Profit DECIMAL(18, 2),
    Shipping_Cost DECIMAL(18, 2),
    Profit_Margin DECIMAL(18, 4),
    CONSTRAINT FK_fact_customer FOREIGN KEY (Customer_ID) REFERENCES dim_customer(Customer_ID),
    CONSTRAINT FK_fact_product FOREIGN KEY (Product_ID) REFERENCES dim_product(Product_ID),
    CONSTRAINT FK_fact_location FOREIGN KEY (Location_ID) REFERENCES dim_location(Location_ID),
    CONSTRAINT FK_fact_order_date FOREIGN KEY (Order_Date) REFERENCES dim_date(Date_Key)
);

