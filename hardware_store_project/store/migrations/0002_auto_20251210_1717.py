from django.db import migrations
import os
from django.conf import settings


def load_sql_file(filename):
    """Загружает содержимое SQL-файла."""
    path = os.path.join(settings.BASE_DIR, 'store', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            load_sql_file('implementation.sql'),
            reverse_sql="""
                DROP TRIGGER IF EXISTS trigger_update_inventory_after_order_finish ON Orders;
                DROP FUNCTION IF EXISTS update_inventory_on_order_finish();
                DROP FUNCTION IF EXISTS calculate_lot_profitability(INTEGER);
                DROP VIEW IF EXISTS Available_Lots_For_Order;
                DROP VIEW IF EXISTS Sales_Report_Monthly;
                DROP PROCEDURE IF EXISTS remove_order_item(INTEGER);
                DROP PROCEDURE IF EXISTS add_order_item(INTEGER, INTEGER, INTEGER, INTEGER);
                DROP PROCEDURE IF EXISTS update_order_status(INTEGER, VARCHAR);
                DROP PROCEDURE IF EXISTS create_order(INTEGER, VARCHAR, INTEGER, INTEGER, INTEGER);
                DROP PROCEDURE IF EXISTS delete_client(INTEGER);
                DROP PROCEDURE IF EXISTS update_client(INTEGER, VARCHAR, VARCHAR);
                DROP PROCEDURE IF EXISTS create_client(VARCHAR, VARCHAR);
                DROP VIEW IF EXISTS Orders_With_Details;
                DROP FUNCTION IF EXISTS get_products_with_stock();
                DROP FUNCTION IF EXISTS get_order_total_amount(INTEGER);
                DROP EXTENSION IF EXISTS plpython3u;
            """
        ),
    ]
