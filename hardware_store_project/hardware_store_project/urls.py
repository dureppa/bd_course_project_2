# hardware_store/urls.py

from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('store.urls')),
    path('django-admin/', admin.site.urls),
]
