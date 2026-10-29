"""Development database with a full school year of data, sized to stress the UI.

Default: 31 high-school classes (11 first-year, 10 second-year, 10 third-year)
of 45 students each = 1395 students with their guardians, enrollments,
installments, incidents, delays and bathroom permissions, Q&A sessions
(plantões), pathways (itinerários) with their members, lessons, attendance and
grades, a weekly timetable and class diary for every class, grades (the concept
and extra grades computed like the app does), bank slips (remittances and
return files run through billing/services.py), counter payments, other
receivables and payables.

Data is generated for the current school year by default, so bimesters,
due dates and payments are spread around today's date. To fill a future year
as if it were already under way, pass a reference date with --today
(e.g. `full_seed --year 2027 --today 2027-11-20`).

Every run starts by flushing the database, so it always seeds from empty.
"""

import math
import random
import re
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from accounts.models import (
    ZERO,
    Account,
    AccountPayable,
    AccountReceivable,
    AccountType,
    Direction,
    Installment,
    Payment,
    PaymentMethod,
    Supplier,
)
from accounts.services import build_installments
from billing.cnab400 import ReturnEntry, generate_return
from billing.models import (
    BankSettings,
    BankSlip,
    Occurrence,
    Remittance,
    ReturnEvent,
    ReturnFile,
)
from billing.services import (
    create_remittance,
    daily_interest,
    import_return,
    write_off_candidates,
)
from classes.models import Class, Shift
from departments.models import Department
from employees.models import Employee, EmployeeRoleType
from enrollments.models import (
    DiscountGroup,
    DiscountType,
    Enrollment,
    EnrollmentDiscount,
    EnrollmentNeededDocument,
    EnrollmentStatus,
    EnrollmentType,
    NeededDocumentType,
    SchoolYear,
)
from grades.models import (
    Bimester,
    ExamKind,
    ExamType,
    Grade,
    GradeLevelSubject,
    Subject,
)
from incidents.models import (
    BathroomPermission,
    Incident,
    IncidentType,
    StudentDelay,
    StudentDelayType,
)
from incidents.services import bimester_range, concept_grades
from lessons.models import (
    Lecture,
    TimetableSlot,
    Weekday,
    lecture_teachers,
    weekday_periods,
)
from pathways.models import (
    AttendanceStatus,
    ExtraGradeSettings,
    Pathway,
    PathwayAttendance,
    PathwayEnrollment,
    PathwayGrade,
    PathwayOffering,
    PathwaySession,
)
from pathways.services import extra_grades
from programs.models import Program
from q_and_a.models import QandA
from students.models import (
    Guardian,
    GuardianAssociation,
    MaritalStatus,
    Relationship,
    Student,
)

DEV_PASSWORD = "73823789"
CENT = Decimal("0.01")

HIGH_SCHOOL = "Ensino Médio"

# Class names are unique per (year, program), so every series has its own.
CLASSES = {
    1: [
        "Aplicação",
        "Brio",
        "Criatividade",
        "Dedicação",
        "Empenho",
        "Fé",
        "Garra",
        "Harmonia",
        "Integridade",
        "Justiça",
        "Liberdade",
    ],
    2: [
        "Inspiração",
        "Lealdade",
        "Nobreza",
        "Mérito",
        "Ousadia",
        "Perseverança",
        "Respeito",
        "Sabedoria",
        "Coragem",
        "Disciplina",
    ],
    3: [
        "Talento",
        "Única",
        "Vitória",
        "Zelo",
        "Esperança",
        "Firmeza",
        "Generosidade",
        "Honra",
        "Prudência",
        "Serenidade",
    ],
}
CLASS_SHIFTS = {1: Shift.MORNING, 2: Shift.AFTERNOON, 3: Shift.MORNING}

# Annual contract price per series; next year's contracts are 6% higher.
ENROLLMENT_PRICES = {
    "1": Decimal("52800.00"),
    "2": Decimal("54000.00"),
    "3": Decimal("57600.00"),
}
NEXT_YEAR_INCREASE = Decimal("1.06")

DEPARTMENT_SUBJECTS = {
    "Cadeira de Física": "Física",
    "Cadeira de Biologia": "Biologia",
    "Cadeira de Química": "Química",
    "Cadeira de Matemática": "Matemática",
    "Cadeira de Língua Portuguesa": "Português",
    "Cadeira de Língua Estrangeira": "Inglês",
    "Cadeira de História": "História",
    "Cadeira de Geografia": "Geografia",
    "Cadeira de Filosofia": "Filosofia",
    "Cadeira de Sociologia": "Sociologia",
}
WEEKLY_CLASSES = {
    "Física": Decimal(3),
    "Biologia": Decimal(3),
    "Química": Decimal(3),
    "Matemática": Decimal(5),
    "Português": Decimal(5),
    "Inglês": Decimal(2),
    "História": Decimal(2),
    "Geografia": Decimal(2),
    "Filosofia": Decimal(1),
    "Sociologia": Decimal(1),
}
# Most periods a week per teacher; sets how many teachers each subject needs.
TEACHER_WEEKLY_PERIODS = 25
SECOND_DEPARTMENT_CHANCE = 0.1

# (code, name, kind, max_score); list order is the report card column order.
EXAM_TYPES = [
    ("PS", "Prova de sala", ExamKind.REGULAR, Decimal(3)),
    ("PB", "Prova bimestral", ExamKind.REGULAR, Decimal(6)),
    ("C", "Conceito", ExamKind.REGULAR, Decimal(1)),
    ("EX", "Nota extra", ExamKind.BONUS, Decimal(5)),
    ("A", "Ajuste", ExamKind.RECOVERY, Decimal(10)),
]
ADJUSTMENT_CHANCE = 0.7  # of the bimesters below the passing grade
PASSING_GRADE = Decimal(6)

# (type, penalty) subtracted from the 1-point concept grade of the bimester.
INCIDENT_TYPES = [
    ("Conversa excessiva", Decimal("0.1")),
    ("Uniforme incompleto", Decimal("0.1")),
    ("Uso de celular em sala", Decimal("0.2")),
    ("Não realização de tarefa", Decimal("0.1")),
    ("Saída de sala sem autorização", Decimal("0.3")),
    ("Cola em avaliação", Decimal("0.5")),
    ("Desrespeito ao professor", Decimal("0.5")),
    ("Dano ao patrimônio", Decimal("0.7")),
    ("Briga", Decimal("1.0")),
]
# Average records per student per bimester; a few students get most incidents.
TROUBLEMAKER_SHARE = 0.12
INCIDENTS_PER_BIMESTER = {"troublemaker": 3.0, "other": 0.3}
DELAYS_PER_BIMESTER = 2.5
UNACCEPTABLE_DELAY_CHANCE = 0.25
BATHROOM_PERMISSIONS_PER_BIMESTER = 6.0
CLASS_PERIODS = 6
# Timetables are filled from the first periods; later ones only if needed.
EARLY_PERIODS = 6
# Q&A sessions per student per bimester; regulars attend most of them.
Q_AND_A_REGULAR_SHARE = 0.25
Q_AND_AS_PER_BIMESTER = {"regular": 2.0, "other": 0.2}
# National holidays (month, day) inside the bimesters: no lessons or records.
HOLIDAYS = [(4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20)]

# (name, description, max grade per bimester (0: no extra grade), groups)
PATHWAYS = [
    ("Robótica", "Montagem e programação de robôs.", Decimal("1.00"), 2),
    ("Programação", "Lógica de programação e desenvolvimento web.", Decimal("1.00"), 2),
    ("Iniciação científica", "Projetos de pesquisa orientados.", Decimal("1.50"), 1),
    ("Olimpíadas de matemática", "Preparação para OBMEP e OBM.", Decimal("1.50"), 1),
    ("Redação avançada", "Produção de textos para o ENEM.", Decimal("1.00"), 2),
    ("Debate e oratória", "Argumentação e falar em público.", Decimal("1.00"), 1),
    ("Educação financeira", "Orçamento, investimentos e consumo.", Decimal("0.75"), 2),
    ("Teatro", "Expressão corporal e montagem de peças.", Decimal("0.50"), 1),
    # Pathways that never give an extra grade.
    ("Música", "Canto coral e prática instrumental.", Decimal(0), 1),
    ("Xadrez", "Aberturas, táticas e torneios internos.", Decimal(0), 1),
]
# Groups of a pathway with two; students pick the one outside their class shift.
PATHWAY_TIMES = {"Manhã": "8h às 9h40", "Tarde": "14h às 15h40", "": "17h às 18h40"}
SHIFT_GROUPS = {Shift.MORNING: "Manhã", Shift.AFTERNOON: "Tarde"}
PATHWAY_CAPACITY = 50
PATHWAYS_PER_STUDENT = [60, 32, 8]  # weights of joining 0, 1 or 2 pathways
PATHWAY_LEAVE_CHANCE = 0.08
PATHWAY_GRADE_CHANCE = 0.95  # of the members in a complete bimester

# Lectures are copied from the timetable; a few have a substitute teacher and
# a few days of the diary were never filled in.
SUBSTITUTION_CHANCE = 0.02
MISSING_LECTURE_CHANCE = 0.02
# Each series goes through its four topics over the school year.
LECTURE_TOPICS = {
    "Física": {
        1: [
            "Cinemática",
            "Leis de Newton",
            "Trabalho e energia",
            "Quantidade de movimento",
        ],
        2: ["Termologia", "Termodinâmica", "Óptica geométrica", "Ondulatória"],
        3: ["Eletrostática", "Eletrodinâmica", "Magnetismo", "Física moderna"],
    },
    "Biologia": {
        1: ["Citologia", "Bioquímica celular", "Divisão celular", "Embriologia"],
        2: ["Histologia", "Fisiologia humana", "Botânica", "Zoologia"],
        3: ["Genética", "Evolução", "Ecologia", "Biotecnologia"],
    },
    "Química": {
        1: [
            "Estrutura atômica",
            "Tabela periódica",
            "Ligações químicas",
            "Funções inorgânicas",
        ],
        2: ["Estequiometria", "Soluções", "Termoquímica", "Cinética química"],
        3: [
            "Equilíbrio químico",
            "Eletroquímica",
            "Química orgânica",
            "Reações orgânicas",
        ],
    },
    "Matemática": {
        1: ["Conjuntos", "Funções", "Função quadrática", "Exponencial e logaritmo"],
        2: [
            "Trigonometria",
            "Matrizes e determinantes",
            "Sistemas lineares",
            "Análise combinatória",
        ],
        3: [
            "Geometria analítica",
            "Geometria espacial",
            "Probabilidade e estatística",
            "Polinômios",
        ],
    },
    "Português": {
        1: [
            "Fonética e ortografia",
            "Morfologia",
            "Trovadorismo e Humanismo",
            "Classicismo e Barroco",
        ],
        2: [
            "Sintaxe do período simples",
            "Arcadismo",
            "Romantismo",
            "Realismo e Naturalismo",
        ],
        3: [
            "Sintaxe do período composto",
            "Parnasianismo e Simbolismo",
            "Modernismo",
            "Redação dissertativa",
        ],
    },
    "Inglês": {
        1: [
            "Simple present",
            "Simple past",
            "Present continuous",
            "Reading strategies",
        ],
        2: [
            "Present perfect",
            "Future forms",
            "Modal verbs",
            "Comparatives and superlatives",
        ],
        3: [
            "Passive voice",
            "Conditionals",
            "Reported speech",
            "Interpretação de textos",
        ],
    },
    "História": {
        1: [
            "Pré-história",
            "Antiguidade clássica",
            "Idade Média",
            "Renascimento e Reforma",
        ],
        2: [
            "Brasil colonial",
            "Revoluções burguesas",
            "Independência do Brasil",
            "Brasil Império",
        ],
        3: [
            "Primeira Guerra Mundial",
            "Era Vargas",
            "Guerra Fria",
            "Ditadura militar no Brasil",
        ],
    },
    "Geografia": {
        1: ["Cartografia", "Geologia e relevo", "Clima", "Hidrografia"],
        2: ["População", "Urbanização", "Agropecuária", "Indústria e energia"],
        3: [
            "Globalização",
            "Geopolítica mundial",
            "Blocos econômicos",
            "Questões ambientais",
        ],
    },
    "Filosofia": {
        1: [
            "Origem da filosofia",
            "Pré-socráticos",
            "Sócrates e Platão",
            "Aristóteles",
        ],
        2: ["Filosofia medieval", "Racionalismo", "Empirismo", "Kant"],
        3: [
            "Ética",
            "Filosofia política",
            "Existencialismo",
            "Filosofia contemporânea",
        ],
    },
    "Sociologia": {
        1: ["Introdução à sociologia", "Durkheim", "Weber", "Marx"],
        2: [
            "Cultura e identidade",
            "Estratificação social",
            "Trabalho e sociedade",
            "Movimentos sociais",
        ],
        3: [
            "Cidadania e direitos",
            "Estado e democracia",
            "Globalização e desigualdade",
            "Violência e sociedade",
        ],
    },
}
LECTURE_ACTIVITIES = ["{}", "{}", "{}", "Exercícios: {}", "Revisão: {}"]

STAFF_ROLES = {"Coordenador": 3, "Fiscal": 6, "Orientadora": 2, "Secretária": 4}
TEACHER_ROLE = "Professor"

DISCOUNT_TYPES = [
    ("ALUNO ANTIGO", Decimal(20)),
    ("ALUNO DESTAQUE", Decimal(25)),
    ("IRMÃOS", Decimal(10)),
    ("FILHO DE FUNCIONÁRIO", Decimal(50)),
]

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
DOCUMENT_DELIVERED_CHANCE = 0.85

# Share of families paying tuition by bank slip; the others pay at the counter.
BOLETO_FAMILIES = 0.8
COUNTER_METHODS = [
    PaymentMethod.PIX,
    PaymentMethod.PIX,
    PaymentMethod.PIX,
    PaymentMethod.CREDIT_CARD,
    PaymentMethod.DEBIT_CARD,
    PaymentMethod.CASH,
    PaymentMethod.TRANSFER,
    PaymentMethod.CHECK,
]
SUPPLIER_METHODS = [PaymentMethod.BOLETO, PaymentMethod.TRANSFER, PaymentMethod.PIX]
LATE_PENALTY = Decimal("0.02")
LATE_INTEREST_PER_DAY = Decimal("0.00033")
BANK_EXPIRES_AFTER_DAYS = 30

# (category, value, installments, share of enrollments)
OTHER_RECEIVABLES = [
    ("Material didático", Decimal("1800.00"), 3, 0.7),
    ("Uniforme", Decimal("420.00"), 2, 0.4),
]

MONTHLY_EXPENSES = [
    ("Aluguel", "Imobiliária Planalto", Decimal("18000.00")),
    ("Energia elétrica", "Neoenergia Brasília", Decimal("3200.00")),
    ("Água", "CAESB", Decimal("900.00")),
    ("Internet", "Vivo Empresas", Decimal("450.00")),
    ("Limpeza", "Limpa DF Serviços", Decimal("5600.00")),
]
ONE_OFF_EXPENSE_CATEGORIES = [
    "Material de escritório",
    "Manutenção predial",
    "Equipamentos de informática",
    "Material de limpeza",
    "Eventos",
    "Serviços gráficos",
]
ONE_OFF_SUPPLIERS = 20
ONE_OFF_EXPENSES = 80

CITIES = [
    "Brasília",
    "Taguatinga",
    "Ceilândia",
    "Águas Claras",
    "Guará",
    "Sobradinho",
    "Gama",
    "Samambaia",
    "Lago Sul",
    "Lago Norte",
    "Sudoeste",
    "Vicente Pires",
]


def next_month(day):
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


class Command(BaseCommand):
    help = "Populate the database with a full school year of development data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--students-per-class",
            type=int,
            default=45,
            help="Students in each of the 31 classes (default 45 = 1395 students)",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.localdate().year,
            help="School year to fill (default: the current one)",
        )
        parser.add_argument(
            "--today",
            type=date.fromisoformat,
            default=None,
            help="Reference date (YYYY-MM-DD) for grades and payments (default: today)",
        )
        parser.add_argument(
            "--random-seed", type=int, default=42, help="Seed for reproducible data"
        )

    def handle(self, *args, **options):
        random.seed(options["random_seed"])
        Faker.seed(options["random_seed"])
        self.fake = Faker("pt_BR")
        self.today = options["today"] or timezone.localdate()
        self.year = options["year"]
        self.students_per_class = options["students_per_class"]

        with transaction.atomic():
            with self.step("Deleting existing data"):
                # Same atomic block as the seed: a failed run keeps the old data
                call_command("flush", interactive=False, verbosity=0)
            with self.step("Reference data"):
                self.seed_groups()
                self.seed_admin_users()
                program = Program.objects.get_or_create(name=HIGH_SCHOOL)[0]
                school_years = self.seed_school_years()
                classes = self.seed_classes(program, school_years[self.year])
                enrollment_types = self.seed_enrollment_types(program, school_years)
                self.seed_needed_document_types()
                discount_types = self.seed_discount_types()
                exam_types = self.seed_exam_types()
                incident_types = self.seed_incident_types()
                subjects = self.seed_departments_and_subjects()
                pathways = self.seed_pathways(school_years[self.year])
                bank_settings = self.seed_bank_settings()

            if Student.objects.exists():
                self.stdout.write(
                    self.style.WARNING(
                        "Students already exist; skipping fake data. Start from an "
                        "empty database to generate it."
                    )
                )
                return

            with self.step("Employees and teacher users"):
                teachers = self.seed_employees(subjects, len(classes))
                self.seed_teacher_users(teachers)
                class_subjects = self.seed_grade_level_subjects(teachers, classes)
            with self.step("Students and guardians"):
                students = self.seed_families(len(classes) * self.students_per_class)
            with self.step("Enrollments, accounts and installments"):
                enrollments = self.seed_enrollments(
                    students, classes, enrollment_types, discount_types
                )
                self.seed_documents()
            with self.step("Incidents, delays and bathroom permissions"):
                self.seed_incidents(
                    enrollments, incident_types, school_years[self.year]
                )
            with self.step("Q&A sessions"):
                self.seed_q_and_as(enrollments, school_years[self.year])
            with self.step("Pathways: offerings, members, lessons and grades"):
                offerings = self.seed_pathway_offerings(
                    pathways, school_years[self.year], teachers
                )
                self.seed_pathway_enrollments(
                    enrollments, offerings, school_years[self.year]
                )
                self.seed_pathway_sessions(offerings, school_years[self.year])
                self.seed_pathway_grades(offerings, school_years[self.year])
            with self.step("Grades"):
                self.seed_grades(enrollments, exam_types, school_years[self.year])
            with self.step("Timetables and class diary"):
                self.seed_timetables(class_subjects)
                self.seed_lectures(school_years[self.year])
            with self.step("Tuition: payments, remittances and bank returns"):
                self.seed_tuition(enrollments, bank_settings)
                self.finish_enrollments(enrollments)
            with self.step("Other receivables and payables"):
                self.seed_other_receivables(enrollments)
                self.seed_payables()

        self.print_summary()

    @contextmanager
    def step(self, label):
        """Report progress; the whole run takes about a minute."""
        self.stdout.write(f"{label}...", ending="")
        self.stdout.flush()
        started = time.monotonic()
        yield
        self.stdout.write(
            self.style.SUCCESS(f" ok ({time.monotonic() - started:.1f}s)")
        )

    # ------------------------------------------------------------------ fixed data

    def seed_groups(self):
        groups = {
            "Professor": {
                Grade: ["add_grade", "change_grade", "delete_grade", "view_grade"],
                Student: ["view_student"],
                # needed to pick the enrollment when entering a grade
                Enrollment: ["view_enrollment"],
                Class: ["view_class"],  # needed to open the class grade report
                TimetableSlot: ["view_timetableslot"],
                Lecture: [
                    "add_lecture",
                    "change_lecture",
                    "delete_lecture",
                    "view_lecture",
                ],
                PathwayEnrollment: ["view_pathwayenrollment"],
                PathwaySession: [
                    "add_pathwaysession",
                    "change_pathwaysession",
                    "view_pathwaysession",
                ],
                PathwayAttendance: [
                    "add_pathwayattendance",
                    "change_pathwayattendance",
                    "view_pathwayattendance",
                ],
                PathwayGrade: [
                    "add_pathwaygrade",
                    "change_pathwaygrade",
                    "view_pathwaygrade",
                ],
            },
        }

        for name, model_perms in groups.items():
            group = Group.objects.get_or_create(name=name)[0]
            for model, perms in model_perms.items():
                content_type = ContentType.objects.get_for_model(model)
                for perm in perms:
                    group.permissions.add(
                        Permission.objects.get(codename=perm, content_type=content_type)
                    )

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
            user.groups.set(Group.objects.filter(name__in=usr["groups"]))

    def seed_school_years(self):
        """The filled year, plus the next one so its contracts can be sold."""
        return {
            year: SchoolYear.objects.update_or_create(
                begins__year=year,
                defaults={
                    "begins": date(year, 2, 1),
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
            for year in [self.year]
        }

    def seed_classes(self, program, school_year):
        return [
            Class.objects.update_or_create(
                name=name,
                year=school_year,
                program=program,
                defaults={
                    "grade_level": grade_level,
                    "shift": CLASS_SHIFTS[grade_level],
                    "capacity": self.students_per_class,
                },
            )[0]
            for grade_level, names in CLASSES.items()
            for name in names
        ]

    def seed_enrollment_types(self, program, school_years):
        """Keyed by (year, level)."""
        enrollment_types = {}
        for year, school_year in school_years.items():
            for level, price in ENROLLMENT_PRICES.items():
                if year > self.year:
                    price = (price * NEXT_YEAR_INCREASE).quantize(Decimal(1))
                enrollment_types[(year, level)] = (
                    EnrollmentType.objects.update_or_create(
                        program=program,
                        school_year=school_year,
                        level=level,
                        defaults={
                            "total_price": price,
                            "description": f"Contrato anual da {level}ª série do {HIGH_SCHOOL} para o ano letivo de {year}.",
                        },
                    )[0]
                )
        return enrollment_types

    def seed_needed_document_types(self):
        for document in NEEDED_DOCUMENTS:
            NeededDocumentType.objects.get_or_create(description=document)

    def seed_discount_types(self):
        return [
            DiscountType.objects.update_or_create(
                description=description, defaults={"percentage": percentage}
            )[0]
            for description, percentage in DISCOUNT_TYPES
        ]

    def seed_exam_types(self):
        return {
            code: ExamType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "kind": kind,
                    "max_score": max_score,
                    "order": order,
                },
            )[0]
            for order, (code, name, kind, max_score) in enumerate(EXAM_TYPES, 1)
        }

    def seed_incident_types(self):
        return [
            IncidentType.objects.update_or_create(
                type=name, defaults={"penalty": penalty}
            )[0]
            for name, penalty in INCIDENT_TYPES
        ]

    def seed_departments_and_subjects(self):
        subjects = []
        for department_name, subject_name in DEPARTMENT_SUBJECTS.items():
            department = Department.objects.get_or_create(name=department_name)[0]
            subjects.append(
                Subject.objects.update_or_create(
                    name=subject_name, defaults={"department": department}
                )[0]
            )
        return subjects

    def seed_pathways(self, school_year):
        """The catalog, {pathway: groups}, and the year's extra grade rules."""
        ExtraGradeSettings.for_school_year(school_year)
        return {
            Pathway.objects.update_or_create(
                name=name,
                defaults={"description": description, "extra_points": points},
            )[0]: groups
            for name, description, points, groups in PATHWAYS
        }

    def seed_bank_settings(self):
        return BankSettings.objects.get_or_create(
            pk=1,
            defaults={
                "company_code": "5242021",
                "company_name": "Escola de Desenvolvimento",
                "agency": "484",
                "account": "18360",
                "account_digit": "1",
                "last_remittance_number": 2015,
            },
        )[0]

    # ------------------------------------------------------------------ people

    def digits(self, value):
        return re.sub(r"\D", "", value)

    def phone(self, mobile=True):
        ddd = random.choice(["61", "62", "11"])
        prefix = (
            f"9{random.randint(1000, 9999)}"
            if mobile
            else f"3{random.randint(100, 999)}"
        )
        return f"({ddd}) {prefix}-{random.randint(1000, 9999)}"

    def rg(self):
        return str(self.fake.unique.random_int(1_000_000, 9_999_999))

    def birth_date(self, age):
        """Born `age` years before the school year."""
        return date(self.year - age, 1, 1) + timedelta(days=random.randint(0, 364))

    def address(self):
        return {
            "address": self.fake.street_address(),
            "neighborhood": self.fake.bairro()[:100],
            "city": random.choice(CITIES),
            "state": "DF",
            "zip_code": self.digits(self.fake.postcode()),
        }

    def first_name(self, sex):
        return (
            self.fake.first_name_male() if sex == "M" else self.fake.first_name_female()
        )

    def make_employee(self, role):
        sex = random.choice("MF")
        return Employee(
            name=f"{self.first_name(sex)} {self.fake.last_name()} {self.fake.last_name()}",
            role=role,
            sex=sex,
            cpf=self.digits(self.fake.unique.cpf()),
            rg=self.rg(),
            issuing_authority="SSP/DF",
            birth_date=self.birth_date(random.randint(24, 62)),
            nationality="Brasileira",
            phone=self.phone(mobile=False),
            mobile=self.phone(),
            email=self.fake.free_email(),
            **self.address(),
        )

    def teacher_count(self, subject, class_count):
        """Teachers needed to give every class its weekly periods of the subject."""
        periods = class_count * int(WEEKLY_CLASSES[subject.name])
        return math.ceil(periods / TEACHER_WEEKLY_PERIODS)

    def seed_employees(self, subjects, class_count):
        """Staff plus enough teachers per subject, in its department.

        Returns {subject: [teachers]}.
        """
        roles = {
            name: EmployeeRoleType.objects.get_or_create(role=name)[0]
            for name in [TEACHER_ROLE, *STAFF_ROLES]
        }
        staff = [
            self.make_employee(roles[name])
            for name, count in STAFF_ROLES.items()
            for _ in range(count)
        ]
        teachers = {
            subject: [
                self.make_employee(roles[TEACHER_ROLE])
                for _ in range(self.teacher_count(subject, class_count))
            ]
            for subject in subjects
        }
        Employee.objects.bulk_create(
            staff + [teacher for group in teachers.values() for teacher in group]
        )

        for subject, group in teachers.items():
            subject.department.teachers.add(*group)
            # Some teachers also belong to another department.
            for teacher in group:
                if random.random() < SECOND_DEPARTMENT_CHANCE:
                    other = random.choice([s for s in subjects if s != subject])
                    other.department.teachers.add(teacher)
        return teachers

    def seed_teacher_users(self, teachers):
        """A login in the Professor group for each teacher."""
        password = make_password(DEV_PASSWORD)  # hash once, not once per user
        users, taken = [], set(User.objects.values_list("username", flat=True))
        for group in teachers.values():
            for teacher in group:
                first, *_, last = teacher.name.split()
                base = slugify(f"{first} {last}").replace("-", ".")
                username, suffix = base, 1
                while username in taken:
                    suffix += 1
                    username = f"{base}{suffix}"
                taken.add(username)
                users.append(
                    User(
                        username=username,
                        first_name=first,
                        last_name=last,
                        email=teacher.email,
                        password=password,
                    )
                )
        users = User.objects.bulk_create(users)
        professor = Group.objects.get(name="Professor")
        User.groups.through.objects.bulk_create(
            User.groups.through(user_id=user.pk, group_id=professor.pk)
            for user in users
        )

    def seed_grade_level_subjects(self, teachers, classes):
        """Split each subject's classes, in series order, evenly among its
        teachers, so each teaches one or two series and stays within
        TEACHER_WEEKLY_PERIODS.

        Returns {class: [(grade level subject, the class's teacher)]}.
        """
        classes = sorted(classes, key=lambda school_class: school_class.grade_level)
        class_subjects = defaultdict(list)
        for subject, group in teachers.items():
            per_teacher = math.ceil(len(classes) / len(group))
            by_level = defaultdict(list)
            for index, school_class in enumerate(classes):
                by_level[school_class.grade_level].append(
                    (school_class, group[index // per_teacher])
                )
            for level, assignments in by_level.items():
                grade_level_subject = GradeLevelSubject.objects.update_or_create(
                    grade_level=level,
                    subject=subject,
                    defaults={"weekly_classes": WEEKLY_CLASSES[subject.name]},
                )[0]
                grade_level_subject.teachers.set({t for _, t in assignments})
                for school_class, teacher in assignments:
                    class_subjects[school_class].append((grade_level_subject, teacher))
        return class_subjects

    def make_guardian(self, sex, family_name):
        return Guardian(
            name=f"{self.first_name(sex)} {self.fake.last_name()} {family_name}",
            sex=sex,
            cpf=self.digits(self.fake.unique.cpf()),
            rg=self.rg(),
            issuing_authority="SSP/DF",
            birth_date=self.birth_date(random.randint(33, 60)),
            nationality="Brasileira",
            place_of_birth=random.choice(
                ["Brasília", "Goiânia", "São Paulo", "Rio de Janeiro"]
            ),
            marital_status=random.choice(MaritalStatus.values),
            phone=self.phone(mobile=False) if random.random() < 0.3 else "",
            mobile=self.phone(),
            email=self.fake.free_email(),
            **self.address(),
        )

    def seed_families(self, student_count):
        guardians, students, links = [], [], []

        while len(students) < student_count:
            family_name = self.fake.last_name()
            home = self.address()

            parents = []
            if random.random() < 0.9:
                parents.append(
                    (self.make_guardian("F", family_name), Relationship.MOTHER)
                )
            if random.random() < 0.75 or not parents:
                parents.append(
                    (self.make_guardian("M", family_name), Relationship.FATHER)
                )
            if random.random() < 0.08:
                grandparent = self.make_guardian(random.choice("MF"), family_name)
                grandparent.birth_date = self.birth_date(random.randint(60, 78))
                parents.append((grandparent, Relationship.GRANDPARENT))
            # parents usually share the children's address
            for guardian, _ in parents[:2]:
                for field, value in home.items():
                    setattr(guardian, field, value)
            guardians.extend(guardian for guardian, _ in parents)

            children_count = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
            for _ in range(min(children_count, student_count - len(students))):
                sex = random.choice("MF")
                social_name = self.fake.first_name() if random.random() < 0.03 else ""
                students.append(
                    Student(
                        name=f"{self.first_name(sex)} {self.fake.last_name()} {family_name}",
                        social_name=social_name,
                        use_social_name=bool(social_name),
                        registration="",  # filled in once the series is known
                        sex=sex,
                        cpf=self.digits(self.fake.unique.cpf()),
                        rg=self.rg(),  # unique and required, so every student gets one
                        issuing_authority="SSP/DF",
                        nationality="Brasileira",
                        place_of_birth=random.choice(
                            ["Brasília", "Brasília", "Brasília", "Goiânia", "São Paulo"]
                        ),
                        mobile=self.phone() if random.random() < 0.85 else "",
                        email=self.fake.free_email() if random.random() < 0.6 else "",
                        **home,
                    )
                )

                financial = random.choice(parents[:2])[0]
                for guardian, relationship in parents:
                    links.append(
                        GuardianAssociation(
                            student=students[-1],
                            guardian=guardian,
                            relationship=relationship,
                            is_financial=guardian is financial,
                            is_primary_contact=guardian is parents[0][0],
                            living_with=relationship != Relationship.GRANDPARENT
                            or random.random() < 0.3,
                            pick_up=True,
                        )
                    )

        Guardian.objects.bulk_create(guardians)
        for index, student in enumerate(students):
            student.registration = f"TMP{index:06d}"
        Student.objects.bulk_create(students)
        GuardianAssociation.objects.bulk_create(links)
        return students

    # ------------------------------------------------------------------ enrollments

    def planned_status(self):
        if self.year < self.today.year:
            return EnrollmentStatus.COMPLETED
        return random.choices(
            [
                EnrollmentStatus.ACTIVE,
                EnrollmentStatus.TRANSFERRED,
                EnrollmentStatus.DROPPED,
            ],
            weights=[94, 3, 3],
        )[0]

    @classmethod
    def random_discounts(cls, discount_types):
        """Discounts of the first installment and of the remaining ones.
        Usually the same in both groups; sometimes the remaining installments
        get other discounts or none."""
        first = cls.random_group_discounts(discount_types, DiscountGroup.FIRST)
        roll = random.random()
        if roll < 0.8:
            remaining = [
                EnrollmentDiscount(
                    discount_type=discount.discount_type,
                    group=DiscountGroup.REMAINING,
                    percentage=discount.percentage,
                    observation=discount.observation,
                )
                for discount in first
            ]
        elif roll < 0.9:
            remaining = cls.random_group_discounts(
                discount_types, DiscountGroup.REMAINING
            )
        else:
            remaining = []
        return first + remaining

    @staticmethod
    def random_group_discounts(discount_types, group):
        """Most students pay full price; some get one or two discount types
        and a few a custom discount allowed by the director."""
        count = random.choices([0, 1, 2], weights=[80, 16, 4])[0]
        discounts = [
            EnrollmentDiscount(
                discount_type=discount_type,
                group=group,
                percentage=discount_type.percentage,
            )
            for discount_type in random.sample(discount_types, count)
        ]
        if random.random() < 0.03:
            discounts.append(
                EnrollmentDiscount(
                    group=group,
                    percentage=Decimal(random.choice([5, 15, 30])),
                    observation="Desconto autorizado pela direção",
                )
            )
        if sum(d.percentage for d in discounts) > 100:
            return []
        return discounts

    def seed_enrollments(self, students, classes, enrollment_types, discount_types):
        """One enrollment per student, filling every class seat.

        Saved one by one (not bulk_create) so the post_save signal builds the
        account, installments and documents. All start active; the planned
        final status is applied by finish_enrollments() after the payments.
        """
        seats = [
            school_class
            for school_class in classes
            for _ in range(self.students_per_class)
        ]
        random.shuffle(seats)  # siblings end up in different classes and series

        enrollments, sequence = [], defaultdict(int)
        for student, school_class in zip(students, seats):
            level = school_class.grade_level
            student.birth_date = self.birth_date(
                14 + level + random.choice([0, 0, 0, 1])
            )
            # Matrícula = first school year + sequential number within that year
            start_year = self.year - level + 1
            sequence[start_year] += 1
            student.registration = f"{start_year}{sequence[start_year]:05d}"

            enrollment = Enrollment(
                student=student,
                enrollment_type=enrollment_types[(self.year, str(level))],
                school_class=school_class,
                enrolled_at=date(self.year - 1, 11, 1)
                + timedelta(days=random.randint(0, 60)),
                due_day=random.choice([5, 10, 15]),
            )
            enrollment.save_with_discounts(self.random_discounts(discount_types))
            enrollment.planned_status = self.planned_status()
            # those leaving during the year only attend the first bimesters
            enrollment.bimesters_attended = (
                4
                if enrollment.planned_status
                in (EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED)
                else random.randint(1, 2)
            )
            enrollments.append(enrollment)

        Student.objects.bulk_update(students, ["registration", "birth_date"])
        return enrollments

    def seed_documents(self):
        ids = list(EnrollmentNeededDocument.objects.values_list("pk", flat=True))
        delivered = random.sample(ids, k=int(len(ids) * DOCUMENT_DELIVERED_CHANCE))
        for start in range(0, len(delivered), 5000):
            EnrollmentNeededDocument.objects.filter(
                pk__in=delivered[start : start + 5000]
            ).update(is_delivered=True)

    def finish_enrollments(self, enrollments):
        """Apply the planned status; the signal cancels future installments."""
        for enrollment in enrollments:
            if enrollment.planned_status != EnrollmentStatus.ACTIVE:
                enrollment.status = enrollment.planned_status
                enrollment.save(update_fields=["status", "updated_at"])

    # ------------------------------------------------------------------ grades

    def bimesters_to_grade(self, school_year):
        """{bimester: complete}; the running bimester only has its PS so far."""
        bimesters = {}
        for bimester in Bimester.values:
            begins = getattr(school_year, f"bi_{bimester}_begins")
            ends = getattr(school_year, f"bi_{bimester}_ends")
            if ends < self.today:
                bimesters[bimester] = True
            elif begins <= self.today:
                bimesters[bimester] = False
        return bimesters

    def score(self, max_score, ability, step=Decimal("0.1")):
        value = min(1.0, max(0.0, random.gauss(ability, 0.15))) * float(max_score)
        return (Decimal(str(value)) / step).quantize(Decimal(1)) * step

    def seed_grades(self, enrollments, exam_types, school_year):
        ps, pb, concept, extra, adjustment = (
            exam_types[code] for code, *_ in EXAM_TYPES
        )
        bimesters = self.bimesters_to_grade(school_year)
        subjects_by_level = defaultdict(list)
        for grade_level_subject in GradeLevelSubject.objects.select_related("subject"):
            subjects_by_level[grade_level_subject.grade_level].append(
                grade_level_subject.subject
            )

        # The concept grade comes from the bimester's incidents and delays.
        concepts = {
            bimester: concept_grades(enrollments, bimester)
            for bimester, complete in bimesters.items()
            if complete
        }
        # The extra grade comes from pathways and Q&A sessions, zero included.
        extras = {
            bimester: extra_grades(enrollments, bimester, extra)
            for bimester, complete in bimesters.items()
            if complete
        }

        grades = []
        for enrollment in enrollments:
            graded = {
                bimester: complete
                for bimester, complete in bimesters.items()
                if bimester <= enrollment.bimesters_attended
            }
            ability = random.gauss(0.68, 0.14)
            for subject in subjects_by_level[enrollment.school_class.grade_level]:
                subject_ability = ability + random.gauss(0, 0.08)
                for bimester, complete in graded.items():
                    scores = {ps: self.score(ps.max_score, subject_ability)}
                    if complete:
                        scores[pb] = self.score(pb.max_score, subject_ability)
                        scores[concept] = concepts[bimester][enrollment.pk]
                        if (
                            sum(scores.values()) < PASSING_GRADE
                            and random.random() < ADJUSTMENT_CHANCE
                        ):
                            scores[adjustment] = self.score(
                                adjustment.max_score, subject_ability + 0.1
                            )
                        scores[extra] = extras[bimester][enrollment.pk]
                    grades.extend(
                        Grade(
                            enrollment=enrollment,
                            subject=subject,
                            exam_type=exam_type,
                            bimester=bimester,
                            score=score,
                        )
                        for exam_type, score in scores.items()
                    )

        Grade.objects.bulk_create(grades, batch_size=2000)

    # ------------------------------------------------------------------ incidents

    def school_days(self, school_year, saturdays=False):
        """{bimester: weekdays (and Saturdays, if asked) of the bimester up to
        today, but holidays}."""
        last_weekday = Weekday.SATURDAY if saturdays else Weekday.FRIDAY
        days = {}
        for bimester in Bimester.values:
            day = getattr(school_year, f"bi_{bimester}_begins")
            ends = min(getattr(school_year, f"bi_{bimester}_ends"), self.today)
            days[bimester] = []
            while day <= ends:
                if (
                    day.isoweekday() <= last_weekday
                    and (day.month, day.day) not in HOLIDAYS
                ):
                    days[bimester].append(day)
                day += timedelta(days=1)
        return days

    def record_count(self, average):
        """Records in a bimester: a Poisson draw around the average."""
        count, limit = 0, random.expovariate(1)
        while limit < average:
            count += 1
            limit += random.expovariate(1)
        return count

    def seed_incidents(self, enrollments, incident_types, school_year):
        """Conduct records on school days of the bimesters attended so far.

        Light incidents are more common. A share of the students are
        troublemakers who get most of them and arrive late more often.
        """
        days = self.school_days(school_year)
        type_weights = [1 / float(t.penalty) for t in incident_types]
        incidents, delays, permissions = [], [], []
        for enrollment in enrollments:
            troublemaker = random.random() < TROUBLEMAKER_SHARE
            incidents_average = INCIDENTS_PER_BIMESTER[
                "troublemaker" if troublemaker else "other"
            ]
            delays_average = DELAYS_PER_BIMESTER * (2 if troublemaker else 1)
            for bimester in range(1, enrollment.bimesters_attended + 1):
                if not days[bimester]:
                    continue
                for _ in range(self.record_count(incidents_average)):
                    incidents.append(
                        Incident(
                            enrollment=enrollment,
                            incident_type=random.choices(
                                incident_types, weights=type_weights
                            )[0],
                            incident_date=random.choice(days[bimester]),
                        )
                    )
                for _ in range(self.record_count(delays_average)):
                    delays.append(
                        StudentDelay(
                            enrollment=enrollment,
                            delay_type=StudentDelayType.UNACCEPTABLE
                            if random.random() < UNACCEPTABLE_DELAY_CHANCE
                            else StudentDelayType.ACCEPTABLE,
                            incident_date=random.choice(days[bimester]),
                        )
                    )
                for _ in range(self.record_count(BATHROOM_PERMISSIONS_PER_BIMESTER)):
                    permissions.append(
                        BathroomPermission(
                            enrollment=enrollment,
                            class_period=random.randint(1, CLASS_PERIODS),
                            incident_date=random.choice(days[bimester]),
                        )
                    )

        # Inserted in date order, so created_at follows incident_date.
        for model, records in [
            (Incident, incidents),
            (StudentDelay, delays),
            (BathroomPermission, permissions),
        ]:
            records.sort(key=lambda record: record.incident_date)
            model.objects.bulk_create(records, batch_size=2000)

    def seed_q_and_as(self, enrollments, school_year):
        """Q&A sessions on school days of the bimesters attended so far, in
        subjects of the student's series."""
        days = self.school_days(school_year)
        subjects_by_level = defaultdict(list)
        for grade_level_subject in GradeLevelSubject.objects.select_related("subject"):
            subjects_by_level[grade_level_subject.grade_level].append(
                grade_level_subject.subject
            )
        q_and_as = []
        for enrollment in enrollments:
            subjects = subjects_by_level[enrollment.school_class.grade_level]
            if not subjects:
                continue
            average = Q_AND_AS_PER_BIMESTER[
                "regular" if random.random() < Q_AND_A_REGULAR_SHARE else "other"
            ]
            # Students who need help tend to need it in the same few subjects.
            struggles = random.sample(subjects, k=min(2, len(subjects)))
            for bimester in range(1, enrollment.bimesters_attended + 1):
                if not days[bimester]:
                    continue
                for _ in range(self.record_count(average)):
                    q_and_as.append(
                        QandA(
                            enrollment=enrollment,
                            subject=random.choice(struggles)
                            if random.random() < 0.7
                            else random.choice(subjects),
                            q_and_a_date=random.choice(days[bimester]),
                        )
                    )

        # Inserted in date order, so created_at follows q_and_a_date.
        q_and_as.sort(key=lambda record: record.q_and_a_date)
        QandA.objects.bulk_create(q_and_as, batch_size=2000)

    # ------------------------------------------------------------------ pathways

    def seed_pathway_offerings(self, pathways, school_year, teachers):
        """The year's groups of each pathway, each meeting on one weekday."""
        all_teachers = [teacher for group in teachers.values() for teacher in group]
        offerings = []
        for pathway, groups in pathways.items():
            for name in list(SHIFT_GROUPS.values())[:groups] if groups > 1 else [""]:
                weekday = random.choice(Weekday.values)
                offering = PathwayOffering.objects.create(
                    pathway=pathway,
                    school_year=school_year,
                    name=name,
                    capacity=PATHWAY_CAPACITY,
                    schedule=f"{Weekday(weekday).label}, {PATHWAY_TIMES[name]}",
                )
                offering.teachers.set(
                    random.sample(all_teachers, k=random.choice([1, 1, 2]))
                )
                offering.weekday = weekday
                offerings.append(offering)
        return offerings

    def seed_pathway_enrollments(self, enrollments, offerings, school_year):
        """Most members join in the first days of the year, a few later. Some
        leave, and so does everyone whose enrollment ends during the year."""
        days = [
            day
            for bimester in self.school_days(school_year).values()
            for day in bimester
        ]
        by_pathway = defaultdict(list)
        for offering in offerings:
            by_pathway[offering.pathway_id].append(offering)
        seats, members = Counter(), []
        for enrollment in enrollments:
            last_day = getattr(school_year, f"bi_{enrollment.bimesters_attended}_ends")
            attended = [day for day in days if day <= last_day]
            if not attended:
                continue
            count = random.choices([0, 1, 2], weights=PATHWAYS_PER_STUDENT)[0]
            for pathway_id in random.sample(sorted(by_pathway), k=count):
                groups = [o for o in by_pathway[pathway_id] if seats[o.pk] < o.capacity]
                other_shift = [
                    o
                    for o in groups
                    if o.name != SHIFT_GROUPS.get(enrollment.school_class.shift)
                ]
                if not groups:
                    continue  # full: the student goes without it
                offering = random.choice(other_shift or groups)
                seats[offering.pk] += 1
                joined_at = random.choice(
                    attended[:10] if random.random() < 0.85 else attended
                )
                left_at = None
                if last_day <= self.today and enrollment.bimesters_attended < 4:
                    left_at = last_day
                elif random.random() < PATHWAY_LEAVE_CHANCE:
                    later = [day for day in attended if day > joined_at]
                    left_at = random.choice(later) if later else None
                members.append(
                    PathwayEnrollment(
                        enrollment=enrollment,
                        offering=offering,
                        joined_at=joined_at,
                        left_at=left_at,
                    )
                )
        PathwayEnrollment.objects.bulk_create(members, batch_size=2000)

    def seed_pathway_sessions(self, offerings, school_year):
        """A lesson every week on the offering's weekday, with its roll call.

        Each member has their own commitment; a quarter of the absences are
        excused.
        """
        members = defaultdict(list)
        for member in PathwayEnrollment.objects.filter(offering__in=offerings):
            member.commitment = min(1.0, max(0.3, random.gauss(0.88, 0.12)))
            members[member.offering_id].append(member)

        sessions = []
        for offering in offerings:
            for bimester, days in self.school_days(school_year).items():
                lessons = [day for day in days if day.isoweekday() == offering.weekday]
                for number, day in enumerate(lessons, 1):
                    sessions.append(
                        PathwaySession(
                            offering=offering,
                            date=day,
                            topic=f"Módulo {bimester}: encontro {number}"
                            if random.random() < 0.8
                            else "",
                        )
                    )
        # Inserted in date order, so created_at follows the lesson date.
        sessions.sort(key=lambda session: session.date)
        PathwaySession.objects.bulk_create(sessions, batch_size=2000)

        attendances = []
        for session in sessions:
            for member in members[session.offering_id]:
                if not member.is_member_on(session.date):
                    continue
                if random.random() < member.commitment:
                    status = AttendanceStatus.PRESENT
                elif random.random() < 0.25:
                    status = AttendanceStatus.EXCUSED
                else:
                    status = AttendanceStatus.ABSENT
                attendances.append(
                    PathwayAttendance(
                        session=session, pathway_enrollment=member, status=status
                    )
                )
        PathwayAttendance.objects.bulk_create(attendances, batch_size=2000)

    def seed_pathway_grades(self, offerings, school_year):
        """The teacher's grade for the members of each complete bimester of
        the pathways that give one, up to the pathway's maximum."""
        complete = [
            bimester
            for bimester, done in self.bimesters_to_grade(school_year).items()
            if done
        ]
        grades = []
        members = PathwayEnrollment.objects.filter(
            offering__in=offerings, offering__pathway__extra_points__gt=0
        ).select_related("offering__pathway")
        for member in members:
            ability = random.gauss(0.78, 0.12)
            for bimester in complete:
                begins, ends = bimester_range(school_year, bimester)
                if (
                    member.joined_at <= ends
                    and (member.left_at is None or member.left_at >= begins)
                    and random.random() < PATHWAY_GRADE_CHANCE
                ):
                    grades.append(
                        PathwayGrade(
                            pathway_enrollment=member,
                            bimester=bimester,
                            score=self.score(
                                member.offering.pathway.extra_points,
                                ability,
                                Decimal("0.05"),
                            ),
                        )
                    )
        PathwayGrade.objects.bulk_create(grades, batch_size=2000)

    # ------------------------------------------------------------------ lessons

    def seed_timetables(self, class_subjects):
        """Each class gets its subjects' weekly periods, spread over the week
        (as few of a subject per day as possible, Saturdays included), mostly
        in the first EARLY_PERIODS periods, with no teacher in two classes of a shift at the same time.

        A period that doesn't fit is left out and shows as a weekly load
        warning on the timetable page.
        """
        busy, slots = set(), []
        for school_class, subjects in class_subjects.items():
            shift = school_class.shift
            free = {
                (weekday, period)
                for weekday in Weekday.values
                for period, _ in weekday_periods(weekday)
            }
            # The subjects with most periods first: they're the hardest to fit.
            for subject, teacher in sorted(
                subjects, key=lambda pair: -pair[0].weekly_classes
            ):
                per_day = Counter()
                for _ in range(int(subject.weekly_classes)):
                    options = sorted(
                        slot for slot in free if (shift, teacher.pk, *slot) not in busy
                    )
                    early = [slot for slot in options if slot[1] <= EARLY_PERIODS]
                    options = early or options
                    if not options:
                        continue
                    fewest = min(per_day[weekday] for weekday, _ in options)
                    weekday, period = random.choice(
                        [slot for slot in options if per_day[slot[0]] == fewest]
                    )
                    free.discard((weekday, period))
                    busy.add((shift, teacher.pk, weekday, period))
                    per_day[weekday] += 1
                    slots.append(
                        TimetableSlot(
                            school_class=school_class,
                            weekday=weekday,
                            period=period,
                            subject=subject,
                            teacher=teacher,
                        )
                    )
        TimetableSlot.objects.bulk_create(slots, batch_size=2000)

    def seed_lectures(self, school_year):
        """The class diary: the timetable's lectures on every school day up
        to today, with the series' topic of that part of the year."""
        days = [
            day
            for bimester in self.school_days(school_year, saturdays=True).values()
            for day in bimester
        ]
        length = (school_year.ends - school_year.begins).days
        substitutes = {}
        timetables = defaultdict(list)
        for slot in TimetableSlot.objects.filter(
            school_class__year=school_year
        ).select_related("school_class", "subject__subject"):
            timetables[(slot.school_class_id, slot.weekday)].append(slot)
            if slot.subject_id not in substitutes:
                substitutes[slot.subject_id] = list(
                    lecture_teachers(slot.subject).values_list("pk", flat=True)
                )

        lectures = []
        for day in days:
            part = (day - school_year.begins).days / length
            for (_, weekday), slots in timetables.items():
                if weekday != day.isoweekday():
                    continue
                for slot in slots:
                    if random.random() < MISSING_LECTURE_CHANCE:
                        continue
                    teacher_id = slot.teacher_id
                    if random.random() < SUBSTITUTION_CHANCE:
                        teacher_id = random.choice(substitutes[slot.subject_id])
                    topics = LECTURE_TOPICS[slot.subject.subject.name][
                        slot.school_class.grade_level
                    ]
                    topic = topics[min(int(part * len(topics)), len(topics) - 1)]
                    lectures.append(
                        Lecture(
                            school_class_id=slot.school_class_id,
                            date=day,
                            period=slot.period,
                            subject_id=slot.subject_id,
                            teacher_id=teacher_id,
                            topic=random.choice(LECTURE_ACTIVITIES).format(topic),
                        )
                    )
        Lecture.objects.bulk_create(lectures, batch_size=2000)

    # ------------------------------------------------------------------ tuition

    def counter_payment(self, installment, paid_at, principal=None):
        """Payment at the school; late ones pay penalty and daily interest."""
        principal = principal or installment.amount
        penalty = interest = ZERO
        days_late = (paid_at - installment.due_date).days
        if days_late > 0:
            penalty = (principal * LATE_PENALTY).quantize(CENT)
            interest = (principal * LATE_INTEREST_PER_DAY * days_late).quantize(CENT)
        return Payment(
            installment=installment,
            paid_at=paid_at,
            amount=principal + penalty + interest,
            penalty=penalty,
            interest=interest,
            method=random.choice(COUNTER_METHODS),
        )

    def save_payments(self, payments):
        for payment in sorted(payments, key=lambda p: p.paid_at):
            # A return file may have changed the status since it was loaded.
            payment.installment.refresh_from_db(fields=["status"])
            payment.save()  # refreshes the installment status

    def queue_payment(self, payment):
        if payment.paid_at <= self.today:
            day = payment.paid_at
            self.payment_queue[(day.year, day.month)].append(payment)

    def queue_event(self, slip, code, day, **fields):
        if day <= self.today:
            self.event_queue[(day.year, day.month)].append(
                ReturnEntry(
                    nosso_numero=f"{slip.nosso_numero}{slip.nosso_numero_dv}",
                    occurrence_code=code,
                    occurrence_date=day,
                    participant_control=str(slip.pk),
                    document_number=str(slip.installment_id),
                    due_date=slip.due_date,
                    title_amount=slip.amount,
                    **fields,
                )
            )

    def seed_tuition(self, enrollments, bank_settings):
        """Pay the tuition installments month by month, up to today.

        The first installment is paid at the counter on enrollment. Most
        families get bank slips for the rest: each month a remittance on day
        20 sends next month's installments (and write-off requests), and the
        month's return file reports registrations, payments and expirations.
        The other families pay at the counter.
        """
        self.payment_queue = defaultdict(list)
        self.event_queue = defaultdict(list)

        installments = Installment.objects.filter(
            account__enrollment__in=enrollments
        ).select_related("account")
        guardians = sorted({i.account.guardian_id for i in installments})
        boleto_guardians = set(
            random.sample(guardians, k=int(len(guardians) * BOLETO_FAMILIES))
        )

        first_payments, boleto_by_month = [], defaultdict(list)
        for installment in installments:
            if installment.number == 1:
                if random.random() < 0.97:
                    first_payments.append(
                        self.counter_payment(installment, installment.due_date)
                    )
            elif installment.account.guardian_id in boleto_guardians:
                due = installment.due_date
                boleto_by_month[(due.year, due.month)].append(installment.pk)
            else:
                self.plan_counter_payment(installment)
        self.save_payments(first_payments)

        month = date(self.year, 1, 1)
        while month <= min(self.today, date(self.year, 12, 31)):
            key = (month.year, month.month)
            generated_at = month.replace(day=20)
            if generated_at <= self.today:
                following = next_month(month)
                installment_ids = boleto_by_month[(following.year, following.month)]
                write_off_ids = [slip.pk for slip in write_off_candidates()]
                if installment_ids or write_off_ids:
                    remittance = create_remittance(
                        installment_ids, write_off_ids, generation_date=generated_at
                    )
                    self.plan_bank_events(remittance, bank_settings)
            self.import_bank_return(key, bank_settings)
            self.save_payments(self.payment_queue.pop(key, []))
            month = next_month(month)

    def plan_counter_payment(self, installment):
        roll = random.random()
        due = installment.due_date
        if roll < 0.88:
            paid_at = due - timedelta(random.randint(0, 5))
            self.queue_payment(self.counter_payment(installment, paid_at))
        elif roll < 0.95:
            paid_at = due + timedelta(random.randint(1, 40))
            self.queue_payment(self.counter_payment(installment, paid_at))
        elif roll < 0.97:
            half = (installment.amount / 2).quantize(CENT)
            self.queue_payment(self.counter_payment(installment, due, half))
        # else: never paid, stays overdue

    def plan_bank_events(self, remittance, bank_settings):
        """What the bank will report about a new remittance."""
        confirmed_at = remittance.generated_at + timedelta(days=1)
        for slip in remittance.slips.select_related("installment"):
            due = slip.due_date
            roll = random.random()
            if roll < 0.01:
                self.queue_event(
                    slip, Occurrence.ENTRY_REJECTED, confirmed_at, reason_codes=("48",)
                )
                continue
            self.queue_event(slip, Occurrence.ENTRY_CONFIRMED, confirmed_at)

            if roll < 0.80:  # on time, with the punctuality discount
                paid_at = max(confirmed_at, due - timedelta(random.randint(0, 4)))
                self.queue_event(
                    slip,
                    Occurrence.PAID,
                    paid_at,
                    amount_paid=slip.amount - slip.discount,
                    discount_amount=slip.discount,
                    credit_date=paid_at + timedelta(days=1),
                )
                if random.random() < 0.005:
                    self.queue_event(
                        slip, Occurrence.PAYMENT_REVERSED, paid_at + timedelta(days=3)
                    )
            elif roll < 0.90:  # late, with fine and interest
                paid_at = due + timedelta(random.randint(1, 25))
                fine = (slip.amount * bank_settings.fine_percent / 100).quantize(CENT)
                interest = fine + (paid_at - due).days * daily_interest(
                    slip.amount, bank_settings.monthly_interest_percent
                )
                self.queue_event(
                    slip,
                    Occurrence.PAID,
                    paid_at,
                    amount_paid=slip.amount + interest,
                    interest_amount=interest,
                    credit_date=paid_at + timedelta(days=1),
                )
            elif roll < 0.94:  # paid at the counter, so the slip gets written off
                half = (slip.installment.amount / 2).quantize(CENT)
                self.queue_payment(
                    self.counter_payment(
                        slip.installment,
                        max(confirmed_at, due - timedelta(random.randint(0, 3))),
                        half if random.random() < 0.3 else None,
                    )
                )
            else:  # unpaid: the bank expires it, and some pay later at the counter
                expired_at = due + timedelta(days=BANK_EXPIRES_AFTER_DAYS)
                self.queue_event(slip, Occurrence.EXPIRED, expired_at)
                if random.random() < 0.5:
                    paid_at = expired_at + timedelta(random.randint(3, 20))
                    self.queue_payment(self.counter_payment(slip.installment, paid_at))

        for slip in remittance.write_off_slips.all():
            self.queue_event(
                slip,
                Occurrence.WRITTEN_OFF,
                remittance.generated_at + timedelta(days=2),
            )

    def import_bank_return(self, key, bank_settings):
        entries = sorted(
            self.event_queue.pop(key, []),
            key=lambda entry: (entry.occurrence_date, entry.occurrence_code),
        )
        if not entries:
            return
        file_date = entries[-1].occurrence_date
        payload = generate_return(bank_settings.company_code, file_date, entries)
        import_return(f"CB{file_date:%d%m}01.RET", payload)

    # ------------------------------------------------------------------ other finance

    def pay_installments(self, installments, methods=COUNTER_METHODS):
        """Most past installments paid on time, some late, a few left overdue."""
        payments = []
        for installment in installments:
            if installment.due_date > self.today:
                continue
            roll = random.random()
            if roll < 0.9:
                paid_at = installment.due_date - timedelta(random.randint(0, 5))
            elif roll < 0.96:
                paid_at = installment.due_date + timedelta(random.randint(1, 30))
            else:
                continue
            payment = self.counter_payment(installment, min(paid_at, self.today))
            payment.method = random.choice(methods)
            payments.append(payment)
        self.save_payments(payments)

    def seed_other_receivables(self, enrollments):
        for category_name, value, count, share in OTHER_RECEIVABLES:
            category = AccountType.objects.get_or_create(
                name=category_name, defaults={"direction": Direction.RECEIVABLE}
            )[0]
            installments = []
            for enrollment in enrollments:
                if random.random() >= share:
                    continue
                account = AccountReceivable.objects.create(
                    description=f"{category_name} {self.year} - {enrollment.student}"[
                        :200
                    ],
                    category=category,
                    student_id=enrollment.student_id,
                    guardian_id=enrollment.account.guardian_id,
                    issue_date=date(self.year, 1, 15),
                    gross_value=value,
                )
                installments += build_installments(
                    account, count, date(self.year, 2, 15)
                )
            self.pay_installments(Installment.objects.bulk_create(installments))

    def seed_payables(self):
        installments = []
        for category_name, supplier_name, value in MONTHLY_EXPENSES:
            category = AccountType.objects.get_or_create(
                name=category_name, defaults={"direction": Direction.PAYABLE}
            )[0]
            supplier = Supplier.objects.get_or_create(
                name=supplier_name,
                defaults={
                    "document": self.digits(self.fake.unique.cnpj()),
                    "phone": self.phone(mobile=False),
                    "email": self.fake.company_email(),
                },
            )[0]
            account = AccountPayable.objects.create(
                description=f"{category_name} {self.year}",
                category=category,
                supplier=supplier,
                issue_date=date(self.year, 1, 1),
                gross_value=value * 12,
            )
            installments += build_installments(account, 12, date(self.year, 1, 5))

        categories = [
            AccountType.objects.get_or_create(
                name=name, defaults={"direction": Direction.PAYABLE}
            )[0]
            for name in ONE_OFF_EXPENSE_CATEGORIES
        ]
        suppliers = Supplier.objects.bulk_create(
            Supplier(
                name=self.fake.unique.company(),
                document=self.digits(self.fake.unique.cnpj()),
                phone=self.phone(mobile=False),
                email=self.fake.company_email(),
                notes=self.fake.sentence() if random.random() < 0.3 else "",
            )
            for _ in range(ONE_OFF_SUPPLIERS)
        )
        first_day = date(self.year, 1, 1)
        last_day = min(self.today, date(self.year, 12, 31))
        if last_day < first_day:
            # A future year: spread the expenses over the whole year
            last_day = date(self.year, 12, 31)
        for _ in range(ONE_OFF_EXPENSES):
            gross = Decimal(random.randint(300, 25000))
            issued = first_day + timedelta(
                random.randint(0, (last_day - first_day).days)
            )
            category = random.choice(categories)
            account = AccountPayable.objects.create(
                description=f"{category.name} - NF {random.randint(1000, 99999)}",
                category=category,
                supplier=random.choice(suppliers),
                issue_date=issued,
                gross_value=gross,
                discount_value=(gross * Decimal("0.05")).quantize(CENT)
                if random.random() < 0.2
                else ZERO,
            )
            installments += build_installments(
                account, random.randint(1, 6), issued + timedelta(days=30)
            )
        self.pay_installments(
            Installment.objects.bulk_create(installments), SUPPLIER_METHODS
        )

    # ------------------------------------------------------------------ summary

    def print_summary(self):
        for model in [
            User,
            Group,
            EmployeeRoleType,
            Employee,
            Department,
            Subject,
            GradeLevelSubject,
            ExamType,
            Program,
            SchoolYear,
            Class,
            Guardian,
            Student,
            GuardianAssociation,
            EnrollmentType,
            DiscountType,
            NeededDocumentType,
            Enrollment,
            EnrollmentDiscount,
            EnrollmentNeededDocument,
            Grade,
            IncidentType,
            Incident,
            StudentDelay,
            BathroomPermission,
            QandA,
            Pathway,
            PathwayOffering,
            PathwayEnrollment,
            PathwaySession,
            PathwayAttendance,
            PathwayGrade,
            ExtraGradeSettings,
            TimetableSlot,
            Lecture,
            AccountType,
            Supplier,
            Account,
            Installment,
            Payment,
            BankSettings,
            Remittance,
            BankSlip,
            ReturnFile,
            ReturnEvent,
        ]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{model._meta.verbose_name_plural}: {model.objects.count()}"
                )
            )
