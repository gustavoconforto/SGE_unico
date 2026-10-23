import django.db.models.deletion
from django.db import migrations, models


def link_incidents_to_enrollments(apps, schema_editor):
    """Point each incident at its student's enrollment, preferring the active
    one and then the most recent school year."""
    Incident = apps.get_model("incidents", "Incident")
    Enrollment = apps.get_model("enrollments", "Enrollment")
    for incident in Incident.objects.all():
        enrollment = (
            Enrollment.objects.filter(student_id=incident.student_id)
            .order_by(
                models.Case(models.When(status="A", then=0), default=1),
                "-enrollment_type__school_year__begins",
            )
            .first()
        )
        if enrollment is None:
            raise RuntimeError(
                f"Incident {incident.pk}: student {incident.student_id} has no "
                "enrollment. Enroll the student or delete the incident first."
            )
        incident.enrollment = enrollment
        incident.save(update_fields=["enrollment"])


class Migration(migrations.Migration):
    dependencies = [
        ("enrollments", "0001_initial"),
        ("incidents", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="incident",
            old_name="incident_data",
            new_name="incident_date",
        ),
        migrations.AddField(
            model_name="incident",
            name="enrollment",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incidents",
                to="enrollments.enrollment",
                verbose_name="Matrícula",
            ),
        ),
        migrations.RunPython(link_incidents_to_enrollments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="incident",
            name="student",
        ),
        migrations.AlterField(
            model_name="incident",
            name="enrollment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incidents",
                to="enrollments.enrollment",
                verbose_name="Matrícula",
            ),
        ),
    ]
