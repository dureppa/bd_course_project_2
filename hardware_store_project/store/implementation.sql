-- Удаляем старую версию (если есть)
DROP VIEW IF EXISTS orders_with_details;

-- Создаём правильную версию с discount_id
CREATE OR REPLACE VIEW orders_with_details AS
SELECT
    o.order_id,
    o.order_time,
    o.order_status,
    o.order_channel,
    o.order_finished,
    c.client_id,
    c.client_fio AS client_name,
    c.client_phone,
    e.employee_name AS handler_name,
    d.discount_name,
    d.discount_percent,
    r.redactor_name AS redactor_name,
    o.refund_status,
    o.client_feedback,
    o.discount_id,                                      -- ВАЖНО: вот это поле
    get_order_total_amount(o.order_id) AS total_amount
FROM orders o
JOIN clients c ON o.client_id = c.client_id
LEFT JOIN employees e ON o.employee_id = e.employee_id
LEFT JOIN discounts d ON o.discount_id = d.discount_id
LEFT JOIN redactors r ON o.redactor_id = r.redactor_id;

-- Функция получения общей суммы заказа
CREATE OR REPLACE FUNCTION get_order_total_amount(order_id_param INTEGER)
RETURNS NUMERIC(12, 2) AS $$
DECLARE
    total NUMERIC(12, 2) := 0;
BEGIN
    SELECT COALESCE(SUM(quantity * price_at_order), 0)
    INTO total
    FROM order_items
    WHERE order_id = order_id_param;

    RETURN total;
END;
$$ LANGUAGE plpgsql;

-- Функция получения продуктов с остатками
CREATE OR REPLACE FUNCTION get_products_with_stock()
RETURNS TABLE (
    product_name VARCHAR,
    category_name VARCHAR,
    current_stock INTEGER,
    available_stock INTEGER,
    purchase_price NUMERIC(10, 2),
    sale_price NUMERIC(10, 2),
    refund_possibility VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.product_name,
        c.category_name,
        SUM(i.quantity_current) AS current_stock,
        SUM(i.quantity_current - i.quantity_in_transit) AS available_stock,
        i.purchase_price,
        p.product_price_for_sale,
        p.refund_possibility::VARCHAR
    FROM products p
    JOIN categories c ON p.category_id = c.category_id
    JOIN inventory i ON p.product_id = i.product_id
    GROUP BY p.product_name, c.category_name, i.purchase_price, p.product_price_for_sale, p.refund_possibility;
END;
$$ LANGUAGE plpgsql;

-- Добавляем поле статуса возврата в таблицу Orders (если его нет)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'refund_status'
    ) THEN
        ALTER TABLE orders ADD COLUMN refund_status VARCHAR(20) DEFAULT 'none';
    END IF;
END $$;

-- Добавляем поля login и password_hash в таблицы (если их нет)
DO $$
BEGIN
    -- Для clients
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clients' AND column_name = 'login'
    ) THEN
        ALTER TABLE clients ADD COLUMN login VARCHAR(255) UNIQUE;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clients' AND column_name = 'password_hash'
    ) THEN
        ALTER TABLE clients ADD COLUMN password_hash VARCHAR(255);
    END IF;
    
    -- Для employees
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employees' AND column_name = 'login'
    ) THEN
        ALTER TABLE employees ADD COLUMN login VARCHAR(255) UNIQUE;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employees' AND column_name = 'password_hash'
    ) THEN
        ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255);
    END IF;
END $$;

-- Представление детализированных заказов
CREATE OR REPLACE VIEW orders_with_details AS
SELECT
    o.order_id,
    o.order_time,
    o.order_status,
    o.order_channel,
    o.order_finished,
    c.client_id,
    c.client_fio AS client_name,
    c.client_phone,
    e.employee_name AS handler_name,
    d.discount_name,
    d.discount_percent,
    r.redactor_name AS redactor_name,
    o.refund_status,
    o.client_feedback,
    get_order_total_amount(o.order_id) AS total_amount
FROM orders o
JOIN clients c ON o.client_id = c.client_id
LEFT JOIN employees e ON o.employee_id = e.employee_id
LEFT JOIN discounts d ON o.discount_id = d.discount_id
LEFT JOIN redactors r ON o.redactor_id = r.redactor_id;

-- Представление доступных лотов
CREATE OR REPLACE VIEW available_lots_for_order AS
SELECT
    i.lot_id,
    i.product_id,
    p.product_name,
    (i.quantity_current - i.quantity_in_transit) AS available_quantity,
    i.product_date_of_receipt,
    i.purchase_price,
    p.product_price_for_sale
FROM inventory i
JOIN products p ON i.product_id = p.product_id
WHERE (i.quantity_current - i.quantity_in_transit) > 0
ORDER BY p.product_name, i.product_date_of_receipt;

-- Процедуры CRUD для клиентов
CREATE OR REPLACE PROCEDURE create_client(
    client_fio VARCHAR,
    client_phone VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO clients (client_fio, client_phone)
    VALUES (client_fio, client_phone);
END;
$$;

CREATE OR REPLACE PROCEDURE update_client(
    client_id_param INTEGER,
    new_fio VARCHAR DEFAULT NULL,
    new_phone VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE clients
    SET
        client_fio = COALESCE(new_fio, client_fio),
        client_phone = COALESCE(new_phone, client_phone)
    WHERE client_id = client_id_param;
END;
$$;

CREATE OR REPLACE PROCEDURE delete_client(client_id_param INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM clients WHERE client_id = client_id_param;
END;
$$;

-- Процедура создания заказа
CREATE OR REPLACE PROCEDURE create_order(
    client_id_param INTEGER,
    order_channel_param VARCHAR,
    employee_id_param INTEGER DEFAULT NULL,
    discount_id_param INTEGER DEFAULT NULL,
    redactor_id_param INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    new_order_id INTEGER;
BEGIN
    INSERT INTO orders (
        client_id, order_channel, order_status, employee_id, discount_id, order_finished, order_time, redactor_id
    ) VALUES (
        client_id_param, order_channel_param, 'new', employee_id_param, discount_id_param, FALSE, NOW(), redactor_id_param
    )
    RETURNING order_id INTO new_order_id;

    RAISE NOTICE 'Order created with ID: %', new_order_id;
END;
$$;

-- Процедура обновления статуса заказа
CREATE OR REPLACE PROCEDURE update_order_status(
    order_id_param INTEGER,
    new_status VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE orders
    SET order_status = new_status::ORDER_STATUS
    WHERE order_id = order_id_param;

    IF new_status = 'delivered' THEN
        UPDATE orders
        SET order_finished = TRUE
        WHERE order_id = order_id_param;
    END IF;
END;
$$;

-- Процедура обновления статуса возврата
CREATE OR REPLACE PROCEDURE update_refund_status(
    order_id_param INTEGER,
    new_refund_status VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE orders
    SET refund_status = new_refund_status
    WHERE order_id = order_id_param;
END;
$$;

-- Процедура добавления позиции заказа
CREATE OR REPLACE PROCEDURE add_order_item(
    order_id_param INTEGER,
    product_id_param INTEGER,
    lot_id_param INTEGER,
    quantity_param INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    available_stock INTEGER;
    price_at_order_param NUMERIC(10, 2);
BEGIN
    SELECT product_price_for_sale INTO price_at_order_param
    FROM products
    WHERE product_id = product_id_param;

    SELECT (quantity_current - quantity_in_transit) INTO available_stock
    FROM inventory
    WHERE lot_id = lot_id_param AND product_id = product_id_param;

    IF available_stock < quantity_param THEN
        RAISE EXCEPTION 'Not enough stock available in lot % for product %. Available: %, Requested: %', lot_id_param, product_id_param, available_stock, quantity_param;
    END IF;

    INSERT INTO order_items (
        order_id, product_id, lot_id, quantity, price_at_order
    ) VALUES (
        order_id_param, product_id_param, lot_id_param, quantity_param, price_at_order_param
    );

    UPDATE inventory
    SET quantity_in_transit = quantity_in_transit + quantity_param
    WHERE lot_id = lot_id_param;
END;
$$;

-- Процедура удаления позиции заказа
CREATE OR REPLACE PROCEDURE remove_order_item(order_items_id_param INTEGER)
LANGUAGE plpgsql
AS $$
DECLARE
    item_lot_id INTEGER;
    item_quantity INTEGER;
BEGIN
    SELECT lot_id, quantity INTO item_lot_id, item_quantity
    FROM order_items
    WHERE order_items_id = order_items_id;

    UPDATE inventory
    SET quantity_in_transit = GREATEST(quantity_in_transit - item_quantity, 0)
    WHERE lot_id = item_lot_id;

    DELETE FROM order_items WHERE order_items_id = order_items_id_param;
END;
$$;

-- Ежемесячный отчёт о продажах
CREATE OR REPLACE VIEW sales_report_monthly AS
SELECT
    DATE_TRUNC('month', o.order_time) AS sale_month,
    COUNT(*) AS total_orders,
    SUM(get_order_total_amount(o.order_id)) AS total_revenue,
    AVG(get_order_total_amount(o.order_id)) AS avg_order_value
FROM orders o
WHERE o.order_finished = TRUE AND o.order_status = 'delivered'
GROUP BY DATE_TRUNC('month', o.order_time)
ORDER BY sale_month DESC;

-- Триггер обновления инвентаря при завершении заказа
CREATE OR REPLACE FUNCTION update_inventory_on_order_finish()
RETURNS TRIGGER AS $$
DECLARE
    rec RECORD;
BEGIN
    IF NEW.order_finished = TRUE AND OLD.order_finished = FALSE THEN
        FOR rec IN SELECT lot_id, quantity FROM order_items WHERE order_id = NEW.order_id LOOP
            UPDATE inventory
            SET quantity_current = quantity_current - rec.quantity,
                quantity_in_transit = GREATEST(quantity_in_transit - rec.quantity, 0)
            WHERE lot_id = rec.lot_id
              AND quantity_current >= rec.quantity;
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_inventory_after_order_finish
AFTER UPDATE OF order_finished ON orders
FOR EACH ROW
WHEN (NEW.order_finished = TRUE AND OLD.order_finished = FALSE)
EXECUTE FUNCTION update_inventory_on_order_finish();

-- Функция на другом языке (Python/plpython3u) для расчёта средней стоимости заказа клиента
-- Примечание: для использования plpython3u нужно установить расширение: CREATE EXTENSION plpython3u;
-- Если расширение недоступно, используем альтернативную реализацию на plpgsql
CREATE OR REPLACE FUNCTION calculate_client_avg_order_value(client_id_param INTEGER)
RETURNS NUMERIC(12, 2) AS $$
DECLARE
    avg_value NUMERIC(12, 2);
BEGIN
    SELECT COALESCE(AVG(get_order_total_amount(order_id)), 0)
    INTO avg_value
    FROM orders
    WHERE client_id = client_id_param
      AND order_finished = TRUE;
    
    RETURN avg_value;
END;
$$ LANGUAGE plpgsql;