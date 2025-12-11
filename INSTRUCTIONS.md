# Инструкция по настройке БД

## Добавление полей для аутентификации

Выполните SQL-скрипт для добавления полей login и password_hash:

```bash
psql -U olgalukyanenko -d hardware_store_db -f hardware_store_project/store/add_auth_fields.sql
```

Или в psql:
```sql
\i hardware_store_project/store/add_auth_fields.sql
```

## Логины и пароли

После выполнения скрипта будут созданы следующие учётные записи:

### Клиенты:
- **Логин**: `client1`, `client2`, ... (автоматически для каждого клиента)
- **Пароль**: `client123`

### Менеджеры:
- **Логин**: `manager1`, `manager2`, ... (автоматически для каждого менеджера)
- **Пароль**: `manager123`

### Администратор:
- **Логин**: `admin`
- **Пароль**: `admin123`

## Проверка изменений в БД

Все изменения фиксируются в БД через процедуры и триггеры:

1. **Создание заказа** → запись в таблице `orders` и `order_items`
2. **Изменение статуса заказа** → обновление в таблице `orders`
3. **Изменение статуса возврата** → обновление поля `refund_status` в `orders`
4. **Добавление отзыва** → обновление поля `client_feedback` в `orders`
5. **Назначение менеджера клиенту** → обновление `employee_id` в `orders`
6. **Завершение заказа** → триггер автоматически обновляет `inventory`

### Полезные SQL-запросы:

```sql
-- Все заказы с деталями
SELECT * FROM orders_with_details;

-- Отзывы клиентов
SELECT order_id, client_fio, client_feedback, order_time 
FROM orders_with_details 
WHERE client_feedback IS NOT NULL;

-- Ежемесячный отчёт о продажах
SELECT * FROM sales_report_monthly;

-- Продукты с остатками
SELECT * FROM get_products_with_stock();

-- Средняя стоимость заказов клиента
SELECT calculate_client_avg_order_value(1);
```

