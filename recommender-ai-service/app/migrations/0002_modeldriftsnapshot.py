from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModelDriftSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(default="system", max_length=40)),
                ("review_count", models.IntegerField(default=0)),
                ("average_rating", models.FloatField(default=0.0)),
                ("average_sentiment", models.FloatField(default=0.0)),
                ("divergence", models.FloatField(default=0.0)),
                ("negative_ratio", models.FloatField(default=0.0)),
                ("needs_retrain", models.BooleanField(default=False)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-id"]},
        ),
    ]
