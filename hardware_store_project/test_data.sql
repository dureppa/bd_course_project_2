-- Очистка
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM inventory;
DELETE FROM products;
DELETE FROM clients WHERE client_id > 1;
DELETE FROM discounts;
DELETE FROM categories;
DELETE FROM employees;
DELETE FROM redactors;

-- Категории
INSERT INTO categories (category_name) VALUES ('Инструменты');

-- Продукты (ENUM 'yes'/'no')
INSERT INTO products (product_name, product_price_for_sale, refund_possibility, category_id)
VALUES ('Молоток', 500.00, 'yes', 1);

-- Инвентарь
INSERT INTO inventory (product_id, quantity_current, quantity_in_transit, product_date_of_receipt, purchase_price)
VALUES (1, 10, 0, '2025-12-01', 300.00);

-- Клиент (пароль задаётся админом)
INSERT INTO clients (client_fio, client_phone) 
VALUES ('Иван Иванов', '+79001234567');

-- Скидка
INSERT INTO discounts (discount_name, discount_percent) VALUES ('Нет скидки', 0.00);

-- Сотрудники (пароли задаются вручную)
INSERT INTO employees (employee_name) 
VALUES ('Менеджер');

-- Администратор (пароль задаётся вручную)
INSERT INTO employees (employee_name, login) 
VALUES ('Администратор', 'admin');

-- Редактор
INSERT INTO redactors (redactor_name) VALUES ('Редактор');

-- Заказ
INSERT INTO orders (client_id, order_channel, order_status, order_finished, order_time, employee_id, discount_id, redactor_id)
VALUES (1, 'website', 'new', FALSE, NOW(), 1, 1, 1);

-- Позиция заказа
INSERT INTO order_items (order_id, product_id, lot_id, quantity, price_at_order)
VALUES (1, 1, 1, 1, 500.00);

-- Обновить инвентарь
UPDATE inventory SET quantity_in_transit = 1 WHERE lot_id = 1;