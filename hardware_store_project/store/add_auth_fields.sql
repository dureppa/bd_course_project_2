-- Добавление полей для аутентификации

-- Добавляем login и password_hash в таблицу clients (если их нет)
DO $$
BEGIN
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
END $$;

-- Добавляем login и password_hash в таблицу employees (если их нет)
DO $$
BEGIN
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

-- Пароли задаются админом при создании клиентов/сотрудников
-- Создаём админа (если его нет) - пароль задаётся вручную
INSERT INTO employees (employee_name, login)
SELECT 'Администратор', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM employees WHERE login = 'admin');

