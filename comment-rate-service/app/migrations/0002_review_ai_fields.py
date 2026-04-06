from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="ai_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="review",
            name="advice",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="review",
            name="aspect_tags",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="review",
            name="sentiment_label",
            field=models.CharField(default="neutral", max_length=16),
        ),
        migrations.AddField(
            model_name="review",
            name="sentiment_score",
            field=models.FloatField(default=0.5),
        ),
    ]
