from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('book_app', '0002_promotion'),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="category",
            field=models.CharField(
                choices=[
                    ("sach", "Sach"),
                    ("quan_ao", "Quan ao"),
                    ("gia_dung", "Do gia dung"),
                    ("dien_tu", "Thiet bi dien tu"),
                ],
                default="sach",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="book",
            name="image_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
