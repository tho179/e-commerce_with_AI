from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogbook",
            name="category",
            field=models.CharField(default="sach", max_length=32),
        ),
        migrations.AddField(
            model_name="catalogbook",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="catalogbook",
            name="image_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
