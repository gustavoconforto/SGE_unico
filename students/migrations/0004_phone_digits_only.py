import re

from django.db import migrations


def strip_phone_formatting(apps, schema_editor):
    for model_name in ("Student", "Guardian"):
        model = apps.get_model("students", model_name)
        for person in model.objects.exclude(phone="", mobile=""):
            person.phone = re.sub(r"\D", "", person.phone)
            person.mobile = re.sub(r"\D", "", person.mobile)
            person.save(update_fields=["phone", "mobile"])


class Migration(migrations.Migration):
    dependencies = [("students", "0003_one_financial_guardian_per_student")]

    operations = [
        migrations.RunPython(strip_phone_formatting, migrations.RunPython.noop)
    ]
