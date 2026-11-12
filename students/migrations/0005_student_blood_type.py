from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0004_phone_digits_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="blood_type",
            # Existing students get "" and must fill it in on their next edit.
            field=models.CharField(
                choices=[
                    ("A+", "A+"),
                    ("A-", "A-"),
                    ("B+", "B+"),
                    ("B-", "B-"),
                    ("AB+", "AB+"),
                    ("AB-", "AB-"),
                    ("O+", "O+"),
                    ("O-", "O-"),
                ],
                default="",
                max_length=3,
                verbose_name="Tipo sanguíneo",
            ),
            preserve_default=False,
        ),
    ]
