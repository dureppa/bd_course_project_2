# store/admin_views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from .models import Employees, Clients, Discounts, Categories, Products, Inventory
from django.views.decorators.csrf import csrf_exempt
import json


def admin_login(request):
    return redirect('admin_dashboard')


def admin_logout(request):
    return redirect('home')


def admin_dashboard(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT order_id, order_time, client_name, order_status, total_amount
            FROM orders_with_details
            ORDER BY order_time DESC;
        """)
        columns = [col[0] for col in cursor.description]
        all_orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for o in all_orders:
            o['total_amount'] = float(
                o['total_amount']) if o['total_amount'] else 0.0

    clients = list(Clients.objects.all())
    managers = list(Employees.objects.all())
    discounts = list(Discounts.objects.all())
    categories = list(Categories.objects.all())

    products = Products.objects.select_related('category').all()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT i.lot_id, p.product_name, i.quantity_current, i.quantity_in_transit, 
                   i.product_date_of_receipt, i.purchase_price
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id;
        """)
        columns = [col[0] for col in cursor.description]
        inventory = []
        for row in cursor.fetchall():
            d = dict(zip(columns, row))
            d['purchase_price'] = float(d['purchase_price'])
            inventory.append(d)

    # Клиенты для каждого менеджера (через заказы)
    manager_clients = {}
    for manager in managers:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT c.client_id, c.client_fio, c.client_phone
                FROM clients c
                JOIN orders o ON c.client_id = o.client_id
                WHERE o.employee_id = %s
                ORDER BY c.client_fio;
            """, [manager.employee_id])
            clients_data = cursor.fetchall()
            manager_clients[manager.employee_id] = [
                {'client_id': row[0], 'client_fio': row[1],
                    'client_phone': row[2]}
                for row in clients_data
            ]

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                c.category_name,
                COALESCE(SUM(oi.quantity * oi.price_at_order), 0) AS revenue
            FROM categories c
            LEFT JOIN products p ON c.category_id = p.category_id
            LEFT JOIN order_items oi ON p.product_id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_status = 'delivered' AND o.order_finished = TRUE
            GROUP BY c.category_id, c.category_name
            ORDER BY revenue DESC;
        """)
        category_revenue = [
            {'category_name': row[0], 'revenue': float(
                row[1]) if row[1] else 0.0}
            for row in cursor.fetchall()
        ]

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                DATE_TRUNC('month', order_time) AS sale_month,
                COUNT(*) AS total_orders,
                SUM(total_amount) AS total_revenue,
                AVG(total_amount) AS avg_order_value
            FROM orders_with_details
            GROUP BY sale_month
            ORDER BY sale_month DESC;
        """)
        columns = [col[0] for col in cursor.description]
        sales_report = []
        for row in cursor.fetchall():
            d = dict(zip(columns, row))
            d['total_revenue'] = float(
                d['total_revenue']) if d['total_revenue'] else 0.0
            d['avg_order_value'] = float(
                d['avg_order_value']) if d['avg_order_value'] else 0.0
            sales_report.append(d)

    context = {
        'all_orders': all_orders,
        'clients': clients,
        'managers': managers,
        'discounts': discounts,
        'products': products,
        'inventory': inventory,
        'categories': categories,
        'sales_report': sales_report,
        'category_revenue': category_revenue,
        'manager_clients': manager_clients,
    }
    return render(request, 'store/admin_dashboard.html', context)


@csrf_exempt
def admin_create_client(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fio = data.get('client_fio')
            phone = data.get('client_phone')
            login = data.get('login')
            password = data.get('password')

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO clients (client_fio, client_phone, login, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING client_id;
                """, [fio, phone, login, password])
                client_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'client_id': client_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_client(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            client_id = int(data.get('client_id'))
            new_fio = data.get('new_fio')
            new_phone = data.get('new_phone')

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE clients
                    SET client_fio = %s, client_phone = COALESCE(%s, client_phone)
                    WHERE client_id = %s;
                """, [new_fio, new_phone, client_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_delete_client(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            client_id = int(data.get('client_id'))

            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM clients WHERE client_id = %s;", [client_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_create_manager(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('employee_name')
            login = data.get('login')
            password = data.get('password')

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO employees (employee_name, login, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING employee_id;
                """, [name, login, password])
                employee_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'employee_id': employee_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_manager(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee_id = int(data.get('employee_id'))
            name = data.get('employee_name')
            login = data.get('login')

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE employees
                    SET employee_name = %s, login = COALESCE(%s, login)
                    WHERE employee_id = %s;
                """, [name, login, employee_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_assign_client_to_manager(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            client_id = int(data.get('client_id'))
            employee_id = data.get('employee_id')
            if employee_id in (None, '', 'null'):
                employee_id = None
            else:
                employee_id = int(employee_id)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE orders
                    SET employee_id = %s
                    WHERE client_id = %s;
                """, [employee_id, client_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_create_category(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('category_name')

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO categories (category_name)
                    VALUES (%s)
                    RETURNING category_id;
                """, [name])
                category_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'category_id': category_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_create_product(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('product_name')
            price = float(data.get('price'))
            category_id = int(data.get('category_id'))
            refund = data.get('refund_possibility', 'no')

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO products (product_name, product_price_for_sale, category_id, refund_possibility)
                    VALUES (%s, %s, %s, %s)
                    RETURNING product_id;
                """, [name, price, category_id, refund])
                product_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'product_id': product_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_product(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = int(data.get('product_id'))
            name = data.get('product_name')
            price = float(data.get('price'))
            category_id = int(data.get('category_id'))
            refund = data.get('refund_possibility', 'no')

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE products
                    SET product_name = %s, product_price_for_sale = %s, category_id = %s, refund_possibility = %s
                    WHERE product_id = %s;
                """, [name, price, category_id, refund, product_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_create_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            client_id = int(data.get('client_id'))
            channel = data.get('order_channel', 'admin')

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO orders (client_id, order_channel, order_status)
                    VALUES (%s, %s, 'new')
                    RETURNING order_id;
                """, [client_id, channel])
                order_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'order_id': order_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_order_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))
            new_status = data.get('new_status')

            valid = ['new', 'in_progress', 'shipped', 'delivered']
            if new_status not in valid:
                return JsonResponse({'status': 'error', 'message': 'Invalid status'})

            with connection.cursor() as cursor:
                cursor.execute("CALL update_order_status(%s, %s);", [
                               order_id, new_status])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))
            discount_id = data.get('discount_id')
            if discount_id in (None, '', 'null'):
                discount_id = None
            else:
                discount_id = int(discount_id)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE orders
                    SET discount_id = %s
                    WHERE order_id = %s;
                """, [discount_id, order_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_create_discount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('discount_name')
            percent = float(data.get('discount_percent'))

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO discounts (discount_name, discount_percent)
                    VALUES (%s, %s)
                    RETURNING discount_id;
                """, [name, percent])
                discount_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'discount_id': discount_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_discount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            discount_id = int(data.get('discount_id'))
            name = data.get('discount_name')
            percent = float(data.get('discount_percent'))

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE discounts
                    SET discount_name = %s, discount_percent = %s
                    WHERE discount_id = %s;
                """, [name, percent, discount_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_update_inventory(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lot_id = int(data.get('lot_id'))
            quantity_current = int(data.get('quantity_current'))
            quantity_in_transit = int(data.get('quantity_in_transit'))
            purchase_price = float(data.get('purchase_price'))

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE inventory
                    SET quantity_current = %s, quantity_in_transit = %s, purchase_price = %s
                    WHERE lot_id = %s;
                """, [quantity_current, quantity_in_transit, purchase_price, lot_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def admin_add_shipment(request):
    """Добавление новой партии (поставки) на склад."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = int(data.get('product_id'))
            quantity_current = int(data.get('quantity_current'))
            quantity_in_transit = int(data.get('quantity_in_transit'))
            date_of_receipt = data.get(
                'product_date_of_receipt')  # формат: YYYY-MM-DD
            purchase_price = float(data.get('purchase_price'))

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO inventory (product_id, quantity_current, quantity_in_transit, product_date_of_receipt, purchase_price)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING lot_id;
                """, [product_id, quantity_current, quantity_in_transit, date_of_receipt, purchase_price])
                lot_id = cursor.fetchone()[0]

            return JsonResponse({'status': 'success', 'lot_id': lot_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
