# Generated by Django 5.0.6 on 2024-07-10 03:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("run_it", "0008_remove_personalrecord_race_distance_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="runner",
            name="age",
            field=models.IntegerField(default=18),
        ),
    ]
