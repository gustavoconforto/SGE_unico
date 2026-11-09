"""Light development database: reference data and people, no school-year records.

Rebuilds the SQLite database like full_seed, then creates the users, school
years, the 31 classes, enrollment, discount, exam and incident types,
departments and subjects, pathways, bank settings, employees (with teacher
users and class subjects), students with their guardians, and suppliers. No
enrollments, so you can enroll students yourself and watch the accounts,
installments and documents appear.
"""

import random

from django.db import transaction
from django.utils import timezone
from faker import Faker

from accounts.models import AccountType, Direction, Supplier
from programs.models import Program
from students.models import Student

from .full_seed import HIGH_SCHOOL, MONTHLY_EXPENSES
from .full_seed import Command as FullSeedCommand

CLASS_CAPACITY = 45


class Command(FullSeedCommand):
    help = "Populate the database with reference data, staff and students"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.set_defaults(students_per_class=3)

    def handle(self, *args, **options):
        random.seed(options["random_seed"])
        Faker.seed(options["random_seed"])
        self.fake = Faker("pt_BR")
        self.today = options["today"] or timezone.localdate()
        self.year = options["year"]
        self.students_per_class = options["students_per_class"]
        self.class_capacity = CLASS_CAPACITY

        with transaction.atomic():
            with self.step("Reference data"):
                self.seed_groups()
                self.seed_admin_users()
                program = Program.objects.get_or_create(name=HIGH_SCHOOL)[0]
                school_years = self.seed_school_years()
                classes = self.seed_classes(program, school_years[self.year])
                self.seed_enrollment_types(program, school_years)
                self.seed_needed_document_types()
                self.seed_discount_types()
                self.seed_exam_types()
                self.seed_incident_types()
                subjects = self.seed_departments_and_subjects()
                self.seed_pathways(school_years[self.year])
                self.seed_bank_settings()
            with self.step("Employees and teacher users"):
                teachers = self.seed_employees(subjects)
                self.seed_teacher_users(teachers)
                self.seed_grade_level_subjects(teachers, classes)
            with self.step("Students and guardians"):
                self.seed_students(len(classes) * self.students_per_class)
            with self.step("Suppliers"):
                self.seed_suppliers()

        self.print_summary()

    def seed_students(self, count):
        """Students as if already enrolled once: real registration and age."""
        students = self.seed_families(count)
        sequence = {}
        for student in students:
            level = random.randint(1, 3)
            student.birth_date = self.birth_date(14 + level + random.choice([0, 0, 1]))
            start_year = self.year - level + 1
            sequence[start_year] = sequence.get(start_year, 0) + 1
            student.registration = f"{start_year}{sequence[start_year]:05d}"
        Student.objects.bulk_update(students, ["registration", "birth_date"])

    def seed_suppliers(self):
        for category_name, supplier_name, _ in MONTHLY_EXPENSES:
            AccountType.objects.get_or_create(
                name=category_name, defaults={"direction": Direction.PAYABLE}
            )
            Supplier.objects.get_or_create(
                name=supplier_name,
                defaults={
                    "document": self.digits(self.fake.unique.cnpj()),
                    "phone": self.phone(mobile=False),
                    "email": self.fake.company_email(),
                },
            )
