from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from .models import Employees, Clients, Discounts
from django.views.decorators.csrf import csrf_exempt
import json


def manager_dashboard(request, employee_id):
    """
    Страница менеджера: список его клиентов.
    Клиенты определяются по наличию у них заказов, где employee_id = текущий менеджер.
    """
    try:
        manager = Employees.objects.using(
            'default').get(employee_id=employee_id)
    except Employees.DoesNotExist:
        return render(request, 'store/error.html', {'error': 'Менеджер не найден'})

    with connection.cursor() as cursor:
        # Получаем уникальных клиентов, у которых есть заказы с этим менеджером
        cursor.execute("""
            SELECT DISTINCT c.client_id, c.client_fio, c.client_phone
            FROM clients c
            JOIN orders o ON c.client_id = o.client_id
            WHERE o.employee_id = %s
            ORDER BY c.client_fio;
        """, [employee_id])
        clients = cursor.fetchall()

    client_list = [
        {'client_id': row[0], 'client_fio': row[1], 'client_phone': row[2]}
        for row in clients
    ]

    context = {
        'manager': manager,
        'clients': client_list,
    }
    return render(request, 'store/manager_dashboard.html', context)


def manager_client_orders(request, employee_id, client_id):
    """
    Страница с заказами конкретного клиента для менеджера.
    """
    try:
        manager = Employees.objects.using(
            'default').get(employee_id=employee_id)
        client = Clients.objects.using('default').get(client_id=client_id)
    except (Employees.DoesNotExist, Clients.DoesNotExist):
        return render(request, 'store/error.html', {'error': 'Данные не найдены'})

    # Проверка: есть ли у этого клиента заказы с этим менеджером?
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM orders
            WHERE client_id = %s AND employee_id = %s
            LIMIT 1;
        """, [client_id, employee_id])
        if not cursor.fetchone():
            return render(request, 'store/error.html', {'error': 'У вас нет доступа к заказам этого клиента'})

    # Получаем все заказы клиента через представление orders_with_details
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT o.order_id, o.order_time, o.order_status, o.order_channel, 
                   o.order_finished, o.client_name, o.client_phone, o.handler_name,
                   o.discount_name, o.discount_percent, o.redactor_name, o.total_amount,
                   o.refund_status, o.client_feedback
            FROM orders_with_details o
            WHERE o.client_id = %s
            ORDER BY o.order_time DESC;
        """, [client_id])
        columns = [col[0] for col in cursor.description]
        orders_data = []
        for row in cursor.fetchall():
            order_dict = dict(zip(columns, row))
            order_dict['total_amount'] = float(
                order_dict['total_amount']) if order_dict['total_amount'] else 0.0
            order_dict['discount_percent'] = float(
                order_dict['discount_percent']) if order_dict['discount_percent'] else 0.0
            if not order_dict.get('refund_status'):
                order_dict['refund_status'] = 'none'
            orders_data.append(order_dict)

    # Получаем все скидки
    discounts = Discounts.objects.all()

    context = {
        'manager': manager,
        'client': client,
        'orders_data': orders_data,
        'discounts': discounts,
    }
    return render(request, 'store/manager_client_orders.html', context)


@csrf_exempt
def manager_update_order_status(request):
    """Обновляет статус заказа через SQL-процедуру."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))
            new_status = data.get('new_status')

            valid_statuses = ['new', 'in_progress', 'shipped', 'delivered']
            if new_status not in valid_statuses:
                return JsonResponse({'status': 'error', 'message': 'Недопустимый статус'})

            with connection.cursor() as cursor:
                cursor.execute("CALL update_order_status(%s, %s);", [
                               order_id, new_status])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def manager_process_refund(request):
    """
    Обрабатывает возврат: отменяет списание и возвращает товары на склад.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))

            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT lot_id, quantity
                    FROM order_items
                    WHERE order_id = %s;
                """, [order_id])
                items = cursor.fetchall()

                if not items:
                    return JsonResponse({'status': 'error', 'message': 'Заказ пуст или не найден'})

                for lot_id, quantity in items:
                    cursor.execute("""
                        UPDATE inventory
                        SET quantity_current = quantity_current + %s,
                            quantity_in_transit = GREATEST(quantity_in_transit - %s, 0)
                        WHERE lot_id = %s;
                    """, [quantity, quantity, lot_id])

                cursor.execute("""
                    UPDATE orders
                    SET order_status = 'new', order_finished = FALSE
                    WHERE order_id = %s;
                """, [order_id])

            return JsonResponse({'status': 'success', 'message': 'Возврат обработан. Товары возвращены на склад.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def manager_update_refund_status(request):
    """Обновляет статус возврата через SQL-процедуру."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))
            new_refund_status = data.get('new_refund_status')

            valid_statuses = ['none', 'requested', 'processing', 'completed']
            if new_refund_status not in valid_statuses:
                return JsonResponse({'status': 'error', 'message': 'Недопустимый статус возврата'})

            with connection.cursor() as cursor:
                cursor.execute("CALL update_refund_status(%s, %s);", [
                               order_id, new_refund_status])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def manager_update_discount(request):
    """
    Обновляет скидку для заказа (скидка привязана к заказу, а не к клиенту).
    Ожидает JSON: { "order_id": <int>, "discount_id": <int или null> }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))
            discount_id = data.get('discount_id')

            # Преобразуем discount_id в None, если он пустой/нулевой
            if discount_id in (None, '', 'null', 'None'):
                discount_id = None
            else:
                discount_id = int(discount_id)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE orders
                    SET discount_id = %s
                    WHERE order_id = %s;
                """, [discount_id, order_id])

            return JsonResponse({'status': 'success', 'message': 'Скидка для заказа обновлена'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
