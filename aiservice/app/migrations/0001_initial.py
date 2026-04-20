from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.IntegerField()),
                ("book_id", models.IntegerField()),
                ("rating", models.IntegerField()),
                ("comment", models.TextField(blank=True)),
                ("sentiment_label", models.CharField(default="neutral", max_length=16)),
                ("sentiment_score", models.FloatField(default=0.5)),
                ("aspect_tags", models.JSONField(blank=True, default=list)),
                ("advice", models.TextField(blank=True)),
                ("ai_metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="RecommendationSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.IntegerField()),
                ("recommendations", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
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
