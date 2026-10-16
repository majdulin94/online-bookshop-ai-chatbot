
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('authors', models.CharField(blank=True, max_length=255)),
                ('published_date', models.CharField(blank=True, max_length=20, null=True)),
                ('publisher', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('thumbnail', models.URLField(blank=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('book_type', models.CharField(blank=True, choices=[('educational', 'Educational'), ('novel', 'Novel')], max_length=50)),
                ('topic_tag', models.CharField(blank=True, max_length=100)),
                ('slug', models.SlugField(blank=True, max_length=100, unique=True)),
                ('raw_categories', models.TextField(blank=True)),
                ('stock_status', models.CharField(blank=True, choices=[('In Stock', 'In Stock'), ('Limited Stock', 'Limited Stock'), ('Out of Stock', 'Out of Stock')], default='In Stock', max_length=20)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='books', to='books.category')),
            ],
        ),
    ]
