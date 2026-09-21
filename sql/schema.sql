PRAGMA foreign_keys = ON;

CREATE TABLE product (
    product_key INTEGER PRIMARY KEY,
    product TEXT NOT NULL,
    category TEXT NOT NULL
);
CREATE TABLE customer (
    customer_key INTEGER PRIMARY KEY,
    customer TEXT
);
CREATE TABLE reseller (
    reseller_key INTEGER PRIMARY KEY,
    reseller TEXT
);
CREATE TABLE territory (
    territory_key INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    country TEXT NOT NULL
);
CREATE TABLE order_line (
    order_line_key INTEGER PRIMARY KEY,
    order_number TEXT NOT NULL,
    channel TEXT NOT NULL
);
CREATE TABLE sales (
    order_line_key INTEGER PRIMARY KEY REFERENCES order_line(order_line_key),
    product_key INTEGER NOT NULL REFERENCES product(product_key),
    customer_key INTEGER NOT NULL REFERENCES customer(customer_key),
    reseller_key INTEGER NOT NULL REFERENCES reseller(reseller_key),
    territory_key INTEGER NOT NULL REFERENCES territory(territory_key),
    order_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    ship_date TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    revenue_cents INTEGER NOT NULL,
    cost_cents INTEGER NOT NULL
);
CREATE INDEX sales_order_date_idx ON sales(order_date);
CREATE VIEW sales_detail AS
SELECT s.*, o.order_number, o.channel, p.product, p.category,
       t.region, t.country
FROM sales s
JOIN order_line o USING (order_line_key)
JOIN product p USING (product_key)
JOIN territory t USING (territory_key);
