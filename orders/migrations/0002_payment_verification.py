
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stripe_session_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('RETURN_REQUESTED', 'Return Requested'), ('RETURNED', 'Returned')], default='PENDING', max_length=20),
        ),
    ]
