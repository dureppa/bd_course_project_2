from django.urls import path, include
from django.shortcuts import redirect
from . import views, manager_views, admin_views, auth_views

urlpatterns = [
    path('', lambda request: redirect('client_login'), name='home'),
    path('login/client/', auth_views.client_login, name='client_login'),
    path('login/manager/', auth_views.manager_login, name='manager_login'),
    path('login/admin/', admin_views.admin_login, name='admin_login'),
    path('logout/', auth_views.logout, name='logout'),
    path('client/<int:client_id>/', views.client_dashboard, name='client_dashboard'),
    path('client/<int:client_id>/catalog/', views.product_catalog, name='product_catalog'),
    path('api/available-products/', views.available_products_api, name='available_products_api'),
    path('api/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('api/checkout/<int:client_id>/', views.checkout, name='checkout'),
    path('cart/<int:client_id>/', views.cart_view, name='cart'),
    path('api/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('api/update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('api/submit-feedback/<int:order_id>/', views.submit_feedback, name='submit_feedback'),
]

urlpatterns += [
    path('manager/<int:employee_id>/', manager_views.manager_dashboard, name='manager_dashboard'),
    path('manager/<int:employee_id>/client/<int:client_id>/',
         manager_views.manager_client_orders, name='manager_client_orders'),
    path('api/manager/update-order-status/',
         manager_views.manager_update_order_status, name='manager_update_order_status'),
    path('api/manager/process-refund/',
         manager_views.manager_process_refund, name='manager_process_refund'),
    path('api/manager/update-refund-status/',
         manager_views.manager_update_refund_status, name='manager_update_refund_status'),
    path('api/manager/update-discount/',
         manager_views.manager_update_discount, name='manager_update_discount'),
]

urlpatterns += [
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/logout/', admin_views.admin_logout, name='admin_logout'),

    path('api/admin/assign-client/', admin_views.admin_assign_client_to_manager,
         name='admin_assign_client_to_manager'),
    path('api/admin/create-client/', admin_views.admin_create_client, name='admin_create_client'),
    path('api/admin/update-client/', admin_views.admin_update_client, name='admin_update_client'),
    path('api/admin/delete-client/', admin_views.admin_delete_client, name='admin_delete_client'),
    path('api/admin/create-order/', admin_views.admin_create_order, name='admin_create_order'),
    path('api/admin/update-order-status/', admin_views.admin_update_order_status, name='admin_update_order_status'),
    path('api/admin/update-order/', admin_views.admin_update_order, name='admin_update_order'),
    path('api/admin/create-product/', admin_views.admin_create_product, name='admin_create_product'),
    path('api/admin/update-product/', admin_views.admin_update_product, name='admin_update_product'),
    path('api/admin/create-category/', admin_views.admin_create_category, name='admin_create_category'),
    path('api/admin/create-manager/', admin_views.admin_create_manager, name='admin_create_manager'),
    path('api/admin/update-manager/', admin_views.admin_update_manager, name='admin_update_manager'),
    path('api/admin/create-discount/', admin_views.admin_create_discount, name='admin_create_discount'),
    path('api/admin/update-discount/', admin_views.admin_update_discount, name='admin_update_discount'),
    path('api/admin/update-inventory/', admin_views.admin_update_inventory, name='admin_update_inventory'),

    path('api/admin/add-shipment/', admin_views.admin_add_shipment, name='admin_add_shipment'),
]