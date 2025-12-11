CREATE TYPE ORDER_STATUS AS ENUM ('new', 'in_progress', 'shipped', 'delivered');
CREATE TYPE REFUND_POSSIBILITY AS ENUM ('yes', 'no');

CREATE TABLE IF NOT EXISTS Categories (
    Category_id SERIAL PRIMARY KEY,
    Category_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Products (
    Product_id SERIAL PRIMARY KEY,
    Product_name VARCHAR(255) NOT NULL,
    Product_price_for_sale NUMERIC(10, 2) NOT NULL CHECK (Product_price_for_sale >= 0),
    Refund_possibility REFUND_POSSIBILITY NOT NULL,
    Category_id INTEGER NOT NULL
        REFERENCES Categories(Category_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Inventory (
    Lot_id SERIAL PRIMARY KEY,
    Product_id INTEGER NOT NULL
        REFERENCES Products(Product_id) ON DELETE CASCADE,
    Quantity_current INTEGER NOT NULL CHECK (Quantity_current >= 0),
    Quantity_in_transit INTEGER NOT NULL CHECK (Quantity_in_transit >= 0),
    Product_date_of_receipt DATE NOT NULL,
    Purchase_price NUMERIC(10, 2) NOT NULL CHECK (Purchase_price >= 0)
);

CREATE TABLE IF NOT EXISTS Clients (
    Client_id SERIAL PRIMARY KEY,
    Client_FIO VARCHAR(255) NOT NULL,
    Client_phone VARCHAR(20) NOT NULL,
    login VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Employees (
    Employee_id SERIAL PRIMARY KEY,
    Employee_name VARCHAR(255) NOT NULL,
    Employee_productivity NUMERIC(5, 2) CHECK (Employee_productivity >= 0 AND Employee_productivity <= 100),
    login VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Redactors (
    Redactor_id SERIAL PRIMARY KEY,
    Redactor_name VARCHAR(255) NOT NULL,
    Redactor_phone VARCHAR(20),
    Redactor_position VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Discounts (
    Discount_id SERIAL PRIMARY KEY,
    Discount_name VARCHAR(255) NOT NULL,
    Discount_percent NUMERIC(5, 2) NOT NULL CHECK (Discount_percent >= 0 AND Discount_percent <= 100)
);

CREATE TABLE IF NOT EXISTS Orders (
    Order_id SERIAL PRIMARY KEY,
    Client_id INTEGER NOT NULL
        REFERENCES Clients(Client_id) ON DELETE CASCADE,
    Order_channel VARCHAR(50) NOT NULL,
    Order_status ORDER_STATUS NOT NULL,
    Employee_id INTEGER
        REFERENCES Employees(Employee_id) ON DELETE SET NULL,
    Discount_id INTEGER
        REFERENCES Discounts(Discount_id) ON DELETE SET NULL,
    Order_finished BOOLEAN NOT NULL DEFAULT FALSE,
    Client_feedback TEXT,
    Refund_status VARCHAR(20) DEFAULT 'none',
    Order_time TIMESTAMP NOT NULL DEFAULT NOW(),
    Redactor_id INTEGER
        REFERENCES Redactors(Redactor_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Order_Items (
    Order_items_id SERIAL PRIMARY KEY,
    Order_id INTEGER NOT NULL
        REFERENCES Orders(Order_id) ON DELETE CASCADE,
    Product_id INTEGER NOT NULL
        REFERENCES Products(Product_id) ON DELETE CASCADE,
    Lot_id INTEGER
        REFERENCES Inventory(Lot_id) ON DELETE SET NULL,
    Quantity INTEGER NOT NULL CHECK (Quantity > 0),
    Price_at_order NUMERIC(10, 2) NOT NULL CHECK (Price_at_order >= 0)
);