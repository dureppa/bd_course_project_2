from django.db import models


class Categories(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'categories'

    def __str__(self):
        return self.category_name


class Clients(models.Model):
    client_id = models.AutoField(primary_key=True)
    client_fio = models.CharField(max_length=255)
    client_phone = models.CharField(max_length=20, blank=True, null=True)
    login = models.CharField(
        unique=True, max_length=255, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'clients'

    def __str__(self):
        return self.client_fio


class Discounts(models.Model):
    discount_id = models.AutoField(primary_key=True)
    discount_name = models.CharField(max_length=255)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'discounts'

    def __str__(self):
        return self.discount_name


class Employees(models.Model):
    employee_id = models.AutoField(primary_key=True)
    employee_name = models.CharField(max_length=255)
    employee_productivity = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True)
    employee_phone = models.CharField(
        max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'employees'

    def __str__(self):
        return self.employee_name


class Redactors(models.Model):
    redactor_id = models.AutoField(primary_key=True)
    redactor_name = models.CharField(max_length=255)
    redactor_phone = models.CharField(max_length=20, blank=True, null=True)
    redactor_position = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'redactors'

    def __str__(self):
        return self.redactor_name


class Products(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    product_price_for_sale = models.DecimalField(
        max_digits=10, decimal_places=2)
    refund_possibility = models.CharField(max_length=10)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'products'

    def __str__(self):
        return self.product_name


class Inventory(models.Model):
    lot_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity_current = models.IntegerField()
    quantity_in_transit = models.IntegerField()
    product_date_of_receipt = models.DateField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'inventory'

    def __str__(self):
        return f"{self.product.product_name} - Lot {self.lot_id}"


class Orders(models.Model):
    order_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Clients, on_delete=models.CASCADE)
    order_channel = models.CharField(max_length=50)
    order_status = models.TextField()
    employee = models.ForeignKey(
        Employees, on_delete=models.SET_NULL, blank=True, null=True)
    discount = models.ForeignKey(
        Discounts, on_delete=models.SET_NULL, blank=True, null=True)
    order_finished = models.BooleanField()
    client_feedback = models.TextField(blank=True, null=True)
    refund_status = models.CharField(max_length=20, default='none', blank=True, null=True)
    order_time = models.DateTimeField()
    redactor = models.ForeignKey(
        Redactors, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'orders'

    def get_total_amount(self):
        total = sum(item.quantity *
                    item.price_at_order for item in self.order_items.all())
        return total

    def __str__(self):
        return f"Order #{self.order_id} - {self.client.client_fio}"


class OrderItems(models.Model):
    order_items_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Orders, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    lot = models.ForeignKey(
        Inventory, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name}"


class OrdersWithDetails(models.Model):
    order_id = models.IntegerField(primary_key=True)
    order_time = models.DateTimeField()
    order_status = models.TextField()
    order_channel = models.CharField(max_length=50)
    order_finished = models.BooleanField()
    client_id = models.IntegerField()
    client_name = models.CharField(max_length=255)
    client_phone = models.CharField(max_length=20, blank=True, null=True)
    handler_name = models.CharField(max_length=255, blank=True, null=True)
    discount_name = models.CharField(max_length=255, blank=True, null=True)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True)
    redactor_name = models.CharField(max_length=255, blank=True, null=True)
    refund_status = models.CharField(max_length=20, blank=True, null=True)
    client_feedback = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'orders_with_details'


class AvailableLotsForOrder(models.Model):
    lot_id = models.IntegerField(primary_key=True)
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=255)
    available_quantity = models.IntegerField()
    product_date_of_receipt = models.DateField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_price_for_sale = models.DecimalField(
        max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'available_lots_for_order'
