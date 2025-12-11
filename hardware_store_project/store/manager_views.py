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
    Страница заказов конкретного клиента для менеджера.
    Всё работает через прямые SQL-запросы — без представлений.
    """
    try:
        manager = Employees.objects.get(employee_id=employee_id)
        client = Clients.objects.get(client_id=client_id)
    except (Employees.DoesNotExist, Clients.DoesNotExist):
        return render(request, 'store/error.html', {'error': 'Пользователь не найден'})

    # Проверка доступа: у этого менеджера должен быть хотя бы один заказ с этим клиентом
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM orders 
            WHERE client_id = %s AND employee_id = %s 
            LIMIT 1
        """, [client_id, employee_id])
        if not cursor.fetchone():
            return render(request, 'store/error.html', {
                'error': 'У вас нет доступа к заказам этого клиента'
            })

    # Получаем все заказы клиента с красивой суммой и скидкой
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                o.order_id,
                o.order_time,
                o.order_status::text AS order_status,
                o.order_channel,
                -- Сумма без скидки
                COALESCE(get_order_total_amount(o.order_id), 0) AS total_amount,
                -- Финальная сумма с учётом скидки
                ROUND(
                    COALESCE(get_order_total_amount(o.order_id), 0) * 
                    (1 - COALESCE(d.discount_percent, 0) / 100)
                , 2) AS final_amount_with_discount,
                -- Скидка
                o.discount_id,
                COALESCE(d.discount_name, 'Без скидки') AS discount_name,
                COALESCE(d.discount_percent, 0) AS discount_percent,
                -- Отзыв и статус возврата
                COALESCE(o.client_feedback, '') AS client_feedback,
                COALESCE(o.refund_status, 'none') AS refund_status
            FROM orders o
            LEFT JOIN discounts d ON o.discount_id = d.discount_id
            WHERE o.client_id = %s
            ORDER BY o.order_time DESC
        """, [client_id])

        columns = [col[0] for col in cursor.description]
        orders_data = []
        for row in cursor.fetchall():
            order_dict = dict(zip(columns, row))
            # Приводим числа к float для шаблона
            order_dict['total_amount'] = float(order_dict['total_amount'])
            order_dict['final_amount_with_discount'] = float(order_dict['final_amount_with_discount'])
            orders_data.append(order_dict)

    # Все доступные скидки для выпадающего списка
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
    """Обновляет статус заказа напрямую через UPDATE с кастом — без процедуры!"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = int(data.get('order_id'))
            new_status = data.get('new_status')

            valid_statuses = ['new', 'in_progress', 'shipped', 'delivered']
            if new_status not in valid_statuses:
                return JsonResponse({'status': 'error', 'message': 'Недопустимый статус'})

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE orders 
                    SET order_status = %s::ORDER_STATUS
                    WHERE order_id = %s
                """, [new_status, order_id])

                if new_status == 'delivered':
                    cursor.execute("""
                        UPDATE orders 
                        SET order_finished = TRUE 
                        WHERE order_id = %s
                    """, [order_id])

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def manager_process_refund(request):
    """
    Полностью удаляет заказ и возвращает заказ:
    • Товары из quantity_in_transit возвращаются в quantity_current
    • Все позиции заказа удаляются
    • Сам заказ удаляется из таблицы orders
    После этого заказ исчезает и у менеджера, и у клиента
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Метод не разрешён'}, status=405)

    try:
        data = json.loads(request.body)
        order_id = int(data.get('order_id'))

        if not order_id:
            return JsonResponse({'status': 'error', 'message': 'Не передан ID заказа'})

        with connection.cursor() as cursor:
            # 1. Возвращаем товары на склад (из "в пути" → "на складе")
            cursor.execute("""
                UPDATE inventory i
                SET 
                    quantity_current = i.quantity_current + oi.quantity,
                    quantity_in_transit = GREATEST(i.quantity_in_transit - oi.quantity, 0)
                FROM order_items oi
                WHERE oi.order_id = %s 
                  AND oi.lot_id = i.lot_id;
            """, [order_id])

            # 2. Удаляем все товары из заказа
            cursor.execute("DELETE FROM order_items WHERE order_id = %s;", [order_id])

            # 3. Удаляем сам заказ
            cursor.execute("DELETE FROM orders WHERE order_id = %s;", [order_id])

            # Проверяем, что заказ действительно удалён
            cursor.execute("SELECT 1 FROM orders WHERE order_id = %s", [order_id])
            if cursor.fetchone():
                raise Exception("Заказ не был удалён из-за ограничений БД")

        return JsonResponse({
            'status': 'success',
            'message': 'Заказ №{} полностью удалён. Товары возвращены на склад.'.format(order_id)
        })

    except Exception as e:
        # Логируем ошибку (по желанию можно в лог-файл)
        print(f"[REFUND ERROR] Order {data.get('order_id', '???')}: {e}")
        return JsonResponse({
            'status': 'error', 
            'message': 'Ошибка при возврате: ' + str(e)
        }, status=500)


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
