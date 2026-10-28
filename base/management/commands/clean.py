from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from classes.models import Class, Shift
from employees.models import EmployeeRoleType
from enrollments.models import (
    DiscountType,
    EnrollmentType,
    LevelTypes,
    NeededDocumentType,
    SchoolYear,
)
from programs.models import Program

DEV_PASSWORD = "73823789"

PROGRAMS = ["Ensino Médio", "Pré UNB", "Pré ENEM"]

HIGH_SCHOOL_CLASSES = {
    "Aplicação": 1,
    "Brio": 1,
    "Criatividade": 1,
    "Inspiração": 2,
    "Lealdade": 2,
    "Nobreza": 2,
    "Talento": 3,
    "Única": 3,
    "Vitória": 3,
}

ENROLLMENT_PRICES = {
    "Ensino Médio": Decimal("54000.00"),
    "Pré UNB": Decimal("7200.00"),
    "Pré ENEM": Decimal("6600.00"),
}

DISCOUNT_TYPES = [
    ("ALUNO ANTIGO", 20),
    ("ALUNO DESTAQUE", 25),
]

EMPLOYEES_ROLES = ["PROFESSOR", "COORDENADOR", "FISCAL", "ORIENTADORA"]


class Command(BaseCommand):
    help = "Populate database with development data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--students", type=int, default=10, help="Number of fake students to create"
        )
        parser.add_argument(
            "--random-seed", type=int, default=42, help="Seed for reproducible data"
        )

    def handle(self, *args, **options):
        self.current_year = timezone.localdate().year
        self.school_years = list(range(self.current_year, self.current_year + 2))

        with transaction.atomic():
            self.seed_admin_users()
            programs = self.seed_programs()
            school_years = self.seed_school_years()
            classes = self.seed_classes(programs, school_years)
            enrollment_types = self.seed_enrollment_types(programs)
            self.seed_enrollment_needed_document_types()
            self.seed_discount_types()
            self.seed_employee_role_types()

    def seed_admin_users(self):
        users = [
            {
                "username": "conforto",
                "first_name": "Gustavo",
                "last_name": "Conforto",
                "is_superuser": True,
                "groups": [],
            },
            {
                "username": "teste",
                "first_name": "Teste",
                "last_name": "De autorização",
                "is_superuser": False,
                "groups": ["Professor"],
            },
        ]

        for usr in users:
            user = User.objects.update_or_create(
                username=usr["username"],
                defaults={
                    "email": "email@email.com.br",
                    "first_name": usr["first_name"],
                    "last_name": usr["last_name"],
                    "is_staff": True,
                    "is_superuser": usr["is_superuser"],
                },
            )[0]
            user.set_password(DEV_PASSWORD)
            user.save()

    def seed_programs(self):
        return {name: Program.objects.get_or_create(name=name)[0] for name in PROGRAMS}

    def seed_classes(self, programs, school_years):
        classes = []
        for year in school_years.values():
            for name, grade_level in HIGH_SCHOOL_CLASSES.items():
                classes.append(
                    Class.objects.update_or_create(
                        name=name,
                        year=year,
                        program=programs["Ensino Médio"],
                        defaults={
                            "grade_level": grade_level,
                            "shift": Shift.MORNING,
                            "capacity": 40,
                        },
                    )[0]
                )
            for program_name in PROGRAMS:
                if program_name == "Ensino Médio":
                    continue
                for name in ["Galileo", "Copérnico"]:
                    classes.append(
                        Class.objects.update_or_create(
                            name=name,
                            year=year,
                            program=programs[program_name],
                            defaults={"shift": Shift.MORNING, "capacity": 50},
                        )[0]
                    )
        return classes

    def seed_school_years(self):
        return {
            year: SchoolYear.objects.update_or_create(
                begins=date(year, 1, 10),
                defaults={
                    "ends": date(year, 12, 15),
                    "bi_1_begins": date(year, 2, 1),
                    "bi_1_ends": date(year, 4, 17),
                    "bi_2_begins": date(year, 4, 27),
                    "bi_2_ends": date(year, 7, 3),
                    "bi_3_begins": date(year, 7, 27),
                    "bi_3_ends": date(year, 9, 30),
                    "bi_4_begins": date(year, 10, 13),
                    "bi_4_ends": date(year, 12, 15),
                    "school_days": 200,
                    "total_hours": 1000,
                },
            )[0]
            for year in self.school_years
        }

    def seed_enrollment_types(self, programs):
        school_years = SchoolYear.objects.all()
        enrollment_types = {}
        for school_year in school_years:
            for program_name, program in programs.items():
                if program.name != "Ensino Médio":
                    enrollment_types[(school_year.begins.year, program.pk)] = (
                        EnrollmentType.objects.update_or_create(
                            program=program,
                            school_year=school_year,
                            defaults={
                                "total_price": ENROLLMENT_PRICES[program_name],
                                "description": f"Contrato anual do curso {program_name} para o ano letivo de {school_year.begins.year}.",
                            },
                        )[0]
                    )
                else:
                    for level in [
                        LevelTypes.GRADE_1,
                        LevelTypes.GRADE_2,
                        LevelTypes.GRADE_3,
                    ]:
                        enrollment_types[
                            (school_year.begins.year, program.pk, level)
                        ] = EnrollmentType.objects.update_or_create(
                            program=program,
                            school_year=school_year,
                            level=level,
                            defaults={
                                "total_price": ENROLLMENT_PRICES[program_name],
                                "description": f"Contrato anual do curso {program_name} para o ano letivo de {school_year.begins.year}.",
                            },
                        )[0]
        return enrollment_types

    def seed_discount_types(self):
        for discount in DISCOUNT_TYPES:
            DiscountType.objects.create(description=discount[0], percentage=discount[1])

    def seed_enrollment_needed_document_types(self):
        NEEDED_DOCUMENTS = [
            "CERTIDÃO DE NASCIMENTO",
            "COMPROVANTE DE RESIDÊNCIA",
            "CPF DO ALUNO",
            "CPF DO RESPONSÁVEL",
            "DECLARAÇÃO DE ESCOLARIDADE",
            "DECLARAÇÃO DE TRANSFERÊNCIA",
            "HISTÓRICO ESCOLAR ENSINO FUNDAMENTAL",
            "HISTÓRICO ESCOLAR ENSINO MÉDIO",
            "RG DO ALUNO",
            "RG DO RESPONSÁVEL",
        ]
        return [
            NeededDocumentType.objects.update_or_create(description=document)[0]
            for document in NEEDED_DOCUMENTS
        ]

    def seed_employee_role_types(self):
        for role in EMPLOYEES_ROLES:
            EmployeeRoleType.objects.create(role=role)
