from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='GroceryProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('image_url', models.URLField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('stock', models.IntegerField(default=0)),
                ('brand', models.CharField(blank=True, max_length=100)),
                ('unit', models.CharField(blank=True, max_length=30)),
                ('expiry_days', models.IntegerField(default=180)),
                ('origin_country', models.CharField(blank=True, max_length=60)),
                ('organic', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-id']},
        ),
    ]
