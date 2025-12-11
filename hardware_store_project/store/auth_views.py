# store/auth_views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
import json
import hashlib


def client_login(request):
    """Страница входа для клиента."""
    if request.method == 'POST':
        login = request.POST.get('login')
        password = request.POST.get('password')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT client_id, client_fio, password_hash
                FROM clients
                WHERE login = %s
            """, [login])
            row = cursor.fetchone()
            
            if row:
                client_id, client_fio, stored_hash = row
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if stored_hash == password_hash:
                    request.session['client_id'] = client_id
                    request.session['client_name'] = client_fio
                    return redirect('client_dashboard', client_id=client_id)
        
        return render(request, 'store/client_login.html', {'error': 'Неверный логин или пароль'})
    
    return render(request, 'store/client_login.html')


def manager_login(request):
    """Страница входа для менеджера."""
    if request.method == 'POST':
        login = request.POST.get('login')
        password = request.POST.get('password')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT employee_id, employee_name, password_hash
                FROM employees
                WHERE login = %s
            """, [login])
            row = cursor.fetchone()
            
            if row:
                employee_id, employee_name, stored_hash = row
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if stored_hash == password_hash:
                    request.session['manager_id'] = employee_id
                    request.session['manager_name'] = employee_name
                    return redirect('manager_dashboard', employee_id=employee_id)
        
        return render(request, 'store/manager_login.html', {'error': 'Неверный логин или пароль'})
    
    return render(request, 'store/manager_login.html')


def logout(request):
    """Выход."""
    request.session.flush()
    return redirect('home')

