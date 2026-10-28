import django.core.validators
from django.db import migrations, models


def split_discounts(apps, schema_editor):
    """Discounts so far applied to the whole contract: keep each one on the
    remaining installments and copy it to the first installment."""
    Enrollment = apps.get_model('enrollments', 'Enrollment')
    EnrollmentDiscount = apps.get_model('enrollments', 'EnrollmentDiscount')
    Enrollment.objects.update(first_discount_percent=models.F('remaining_discount_percent'))
    EnrollmentDiscount.objects.bulk_create(
        EnrollmentDiscount(
            enrollment_id=discount.enrollment_id,
            discount_type_id=discount.discount_type_id,
            group='F',
            percentage=discount.percentage,
            observation=discount.observation,
        )
        for discount in EnrollmentDiscount.objects.all()
    )


def merge_discounts(apps, schema_editor):
    EnrollmentDiscount = apps.get_model('enrollments', 'EnrollmentDiscount')
    EnrollmentDiscount.objects.filter(group='F').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0002_enrollment_discounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolyear',
            name='school_days',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Total de dias letivos do ano', null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Dias letivos'),
        ),
        migrations.AddField(
            model_name='schoolyear',
            name='total_hours',
            field=models.PositiveIntegerField(blank=True, help_text='Total de horas oferecidas ao aluno no ano, base da frequência', null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Carga horária (horas)'),
        ),
        migrations.AddConstraint(
            model_name='schoolyear',
            constraint=models.CheckConstraint(condition=models.Q(('school_days__isnull', True), ('school_days__gte', 1), _connector='OR'), name='school_year_school_days_positive'),
        ),
        migrations.AddConstraint(
            model_name='schoolyear',
            constraint=models.CheckConstraint(condition=models.Q(('total_hours__isnull', True), ('total_hours__gte', 1), _connector='OR'), name='school_year_total_hours_positive'),
        ),
        migrations.RenameField(
            model_name='enrollment',
            old_name='discount_percent',
            new_name='remaining_discount_percent',
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='remaining_discount_percent',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Preenchido automáticamente', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Desconto das demais parcelas (%)'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='first_discount_percent',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Preenchido automáticamente', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Desconto da 1ª parcela (%)'),
        ),
        migrations.RemoveConstraint(
            model_name='enrollmentdiscount',
            name='unique_enrollment_discount_type',
        ),
        migrations.AddField(
            model_name='enrollmentdiscount',
            name='group',
            field=models.CharField(choices=[('F', '1ª parcela'), ('R', 'Demais parcelas')], default='R', max_length=1, verbose_name='Parcelas'),
            preserve_default=False,
        ),
        migrations.RunPython(split_discounts, merge_discounts),
        migrations.AlterModelOptions(
            name='enrollmentdiscount',
            options={'ordering': ['enrollment', 'group', 'pk'], 'verbose_name': 'Desconto da matrícula', 'verbose_name_plural': 'Descontos da matrícula'},
        ),
        migrations.AddConstraint(
            model_name='enrollmentdiscount',
            constraint=models.UniqueConstraint(fields=('enrollment', 'group', 'discount_type'), name='unique_enrollment_discount_type'),
        ),
        migrations.AddConstraint(
            model_name='enrollmentdiscount',
            constraint=models.CheckConstraint(condition=models.Q(('group__in', ['F', 'R'])), name='enrollment_discount_group_valid'),
        ),
    ]
