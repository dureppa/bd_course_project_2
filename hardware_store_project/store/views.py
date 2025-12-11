from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from .models import Clients, Products, Orders, OrderItems, Inventory, Discounts, OrdersWithDetails, AvailableLotsForOrder
from django.views.decorators.csrf import csrf_exempt
import json


def get_real_available_quantity(product_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COALESCE(SUM(available_quantity), 0)
            FROM available_lots_for_order
            WHERE product_id = %s;
        """, [product_id])
        real_available = cursor.fetchone()[0] or 0
        return max(0, real_available)


def cart_view(request, client_id):
    cart = request.session.get('cart', {})
    if not cart:
        context = {'client_id': client_id, 'cart_items': [], 'total_price': 0}
        return render(request, 'store/cart.html', context)

    products = AvailableLotsForOrder.objects.filter(product_id__in=cart.keys())

    cart_items = []
    total_price = 0

    for product in products:
        if str(product.product_id) in cart:
            quantity = cart[str(product.product_id)]
            price = float(product.product_price_for_sale)
            subtotal = quantity * price
            total_price += subtotal
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal,
                'available_quantity': product.available_quantity,
            })

    context = {
        'client_id': client_id,
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'store/cart.html', context)


@csrf_exempt
def add_to_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            client_id = data.get('client_id')

            real_available = get_real_available_quantity(product_id)
            if quantity > real_available:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Недостаточно товара на складе. Доступно: {real_available}'
                })

            cart = request.session.get('cart', {})

            if str(product_id) in cart:
                new_quantity = cart[str(product_id)] + quantity
                if new_quantity > real_available:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Недостаточно товара на складе. Доступно: {real_available}'
                    })
                cart[str(product_id)] = new_quantity
            else:
                cart[str(product_id)] = quantity

            request.session['cart'] = cart
            request.session.modified = True

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@csrf_exempt
def update_cart_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            client_id = data.get('client_id')

            real_available = get_real_available_quantity(product_id)
            if quantity > real_available:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Недостаточно товара на складе. Доступно: {real_available}'
                })

            cart = request.session.get('cart', {})
            if str(product_id) in cart:
                cart[str(product_id)] = quantity
                request.session['cart'] = cart
                request.session.modified = True

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@csrf_exempt
def checkout(request, client_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if not cart:
            return JsonResponse({'status': 'error', 'message': 'Корзина пуста'})

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT client_id FROM clients WHERE client_id = %s;", [client_id])
                if not cursor.fetchone():
                    return JsonResponse({'status': 'error', 'message': 'Клиент не найден'})

                cursor.execute(
                    "CALL create_order(%s, 'website', NULL, NULL, NULL);", [client_id])

                cursor.execute(
                    "SELECT MAX(order_id) FROM orders WHERE client_id = %s;", [client_id])
                new_order_id = cursor.fetchone()[0]

                for product_id_str, quantity in cart.items():
                    product_id = int(product_id_str)

                    cursor.execute("""
                        SELECT lot_id, product_price_for_sale
                        FROM available_lots_for_order
                        WHERE product_id = %s
                        ORDER BY product_date_of_receipt ASC
                        LIMIT 1;
                    """, [product_id])

                    row = cursor.fetchone()
                    if not row:
                        raise Exception(f'Товар {product_id} недоступен')

                    lot_id, price_at_order = row

                    cursor.execute("CALL add_order_item(%s, %s, %s, %s);", [
                                   new_order_id, product_id, lot_id, quantity])

            del request.session['cart']
            return JsonResponse({'status': 'success', 'message': 'Заказ успешно оформлен!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def product_catalog(request, client_id):
    context = {'client_id': client_id}
    return render(request, 'store/product_catalog.html', context)


def order_success(request):
    return render(request, 'store/order_success.html')


def client_dashboard(request, client_id):
    try:
        client = Clients.objects.get(client_id=client_id)
    except Clients.DoesNotExist:
        return render(request, 'store/error.html', {'error': 'Клиент не найден'})

    orders_with_items = []
    orders = Orders.objects.filter(client_id=client_id).order_by('-order_time')

    for order in orders:
        items = OrderItems.objects.filter(
            order=order).select_related('product')
        order_data = {
            'order': order,
            'items': items,
            'manager_phone': order.employee.employee_phone if order.employee and hasattr(order.employee, 'employee_phone') else '—',
            'refund_possibility': any(item.product.refund_possibility == 'yes' for item in items) if items else False,
            'can_review': order.order_status == 'delivered' and not order.client_feedback,
        }
        orders_with_items.append(order_data)

    context = {
        'client': client,
        'orders_with_items': orders_with_items,
    }
    return render(request, 'store/client_dashboard.html', context)


@csrf_exempt
def submit_feedback(request, order_id):
    """Добавляет отзыв к заказу."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback = data.get('feedback', '').strip()
            
            if not feedback:
                return JsonResponse({'status': 'error', 'message': 'Отзыв не может быть пустым'})
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE orders
                    SET client_feedback = %s
                    WHERE order_id = %s AND order_status = 'delivered'
                """, [feedback, order_id])
                
                if cursor.rowcount == 0:
                    return JsonResponse({'status': 'error', 'message': 'Заказ не найден или не доставлен'})
            
            return JsonResponse({'status': 'success', 'message': 'Отзыв добавлен'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@csrf_exempt
def remove_from_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            client_id = data.get('client_id')

            cart = request.session.get('cart', {})
            if str(product_id) in cart:
                del cart[str(product_id)]
                request.session['cart'] = cart
                request.session.modified = True

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@csrf_exempt
def available_products_api(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM available_lots_for_order;")
        rows = cursor.fetchall()

    columns = [col[0] for col in cursor.description]
    data = []
    for row in rows:
        item = dict(zip(columns, row))
        item['purchase_price'] = float(item['purchase_price'])
        item['product_price_for_sale'] = float(item['product_price_for_sale'])
        data.append(item)

    return JsonResponse(data, safe=False)
