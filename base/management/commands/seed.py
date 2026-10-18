import random
import re
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

# from grades.models import Evaluation, Grade, Subject
# from incidents.models import Incident, IncidentType
from accounts.models import (
    AccountType,
    Installment,
    Payment,
    Supplier,
)
from classes.models import Class, Shift
from employees.models import Employee, EmployeeRoleType
from enrollments.models import (
    Enrollment,
    EnrollmentStatus,
    EnrollmentType,
    LevelTypes,
    NeededDocumentType,
    SchoolYear,
)
from programs.models import Program
from students.models import (
    Guardian,
    GuardianAssociation,
    MaritalStatus,
    Relationship,
    Student,
)

DEV_PASSWORD = "73823789"

HIGH_SCHOOL = "Ensino Médio"
PREP_PROGRAMS = ["Pré UNB", "Pré ENEM"]

ENROLLMENT_PRICES = {
    HIGH_SCHOOL: Decimal("54000.00"),
    "Pré UNB": Decimal("7200.00"),
    "Pré ENEM": Decimal("6600.00"),
}

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

SUBJECTS = [
    "Português",
    "Matemática",
    "Física",
    "Química",
    "Biologia",
    "História",
    "Geografia",
    "Língua estrangeira",
    "Filosofia",
    "Sociologia",
]

# EVALUATIONS = [
#     Evaluation.PS1,
#     Evaluation.PS2,
#     Evaluation.PS3,
#     Evaluation.PB,
#     Evaluation.C,
# ]
EXTRA_CHANCE = 0.2
BIMESTERS = range(1, 5)

INCIDENT_TYPES = {
    "Atraso": 0.5,
    "Uso de celular em sala": 1.0,
    "Uniforme incompleto": 0.5,
    "Falta sem justificativa": 1.0,
    "Desrespeito ao professor": 3.0,
    "Briga": 5.0,
    "Dano ao patrimônio": 4.0,
    "Saída sem autorização": 2.0,
    "Cola em avaliação": 3.0,
    "Conversa excessiva": 0.5,
}

MONTHLY_EXPENSES = [
    ("Aluguel", "Imobiliária Planalto", Decimal("18000.00")),
    ("Energia elétrica", "Neoenergia Brasília", Decimal("3200.00")),
    ("Água", "CAESB", Decimal("900.00")),
    ("Internet", "Vivo Empresas", Decimal("450.00")),
    ("Limpeza", "Limpa DF Serviços", Decimal("5600.00")),
]
LATE_PENALTY = Decimal("0.02")
LATE_INTEREST_PER_DAY = Decimal("0.00033")

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
        random.seed(options["random_seed"])
        Faker.seed(options["random_seed"])
        self.fake = Faker("pt_BR")
        self.current_year = timezone.localdate().year
        self.school_years = list(range(self.current_year, self.current_year + 2))

        with transaction.atomic():
            self.seed_groups()
            self.seed_admin_users()
            programs = self.seed_programs()
            school_years = self.seed_school_years()
            classes = self.seed_classes(programs, school_years)
            enrollment_types = self.seed_enrollment_types(programs, school_years)
            # incident_types = self.seed_incident_types()
            # subjects = self.seed_subjects()
            self.seed_enrollment_needed_document_types()

            if Student.objects.exists():
                self.stdout.write(
                    self.style.WARNING(
                        "Students already exist; skipping fake data. Run reset_dev.py to start over."
                    )
                )
                return

            self.seed_employees()
            students = self.seed_families(options["students"])
            self.seed_enrollments(students, programs, classes, enrollment_types)
            # self.seed_grades(subjects)
            # self.seed_incidents(students, incident_types)
            # self.seed_enrollment_accounts()
            # self.seed_payables()
            # self.seed_payments()

        self.print_summary()

    # ------------------------------------------------------------------ fixed data

    def seed_groups(self):
        groups = {
            "Professor": {
                # Grade: ["add_grade", "change_grade", "delete_grade", "view_grade"],
                Student: ["view_student"],
                Enrollment: [
                    "view_enrollment"
                ],  # needed to pick the enrollment when entering a grade
                Class: ["view_class"],  # needed to open the class grade report
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

    def seed_programs(self):
        return {
            name: Program.objects.get_or_create(name=name)[0]
            for name in [*PREP_PROGRAMS, HIGH_SCHOOL]
        }

    def seed_classes(self, programs, school_years):
        classes = []
        for year in school_years.values():
            for name, grade_level in HIGH_SCHOOL_CLASSES.items():
                classes.append(
                    Class.objects.update_or_create(
                        name=name,
                        year=year,
                        program=programs[HIGH_SCHOOL],
                        defaults={
                            "grade_level": grade_level,
                            "shift": Shift.MORNING,
                            "capacity": 40,
                        },
                    )[0]
                )
            for program_name in PREP_PROGRAMS:
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
                begins=date(year, 2, 1),
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
                },
            )[0]
            for year in self.school_years
        }

    def seed_enrollment_types(self, programs, school_years):
        """Keyed by (year, program pk, level); level is "" for prep programs."""
        enrollment_types = {}
        for year, school_year in school_years.items():
            for program_name, program in programs.items():
                levels = LevelTypes.values if program_name == HIGH_SCHOOL else [""]
                for level in levels:
                    enrollment_types[(year, program.pk, level)] = (
                        EnrollmentType.objects.update_or_create(
                            program=program,
                            school_year=school_year,
                            level=level,
                            defaults={
                                "total_price": ENROLLMENT_PRICES[program_name],
                                "description": f"Contrato anual do curso {program_name} para o ano letivo de {year}.",
                            },
                        )[0]
                    )
        return enrollment_types

    # def seed_subjects(self):
    #     return [Subject.objects.get_or_create(name=name)[0] for name in SUBJECTS]

    # def seed_incident_types(self):
    #     return [
    #         IncidentType.objects.update_or_create(
    #             type=name, defaults={"penalty": penalty}
    #         )[0]
    #         for name, penalty in INCIDENT_TYPES.items()
    #     ]

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

    # ------------------------------------------------------------------ fake data

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
        year = self.current_year - age
        return date(year, 1, 1) + timedelta(days=random.randint(0, 364))

    def address(self):
        return {
            "address": self.fake.street_address(),
            "neighborhood": self.fake.bairro()[:100],
            "city": random.choice(CITIES),
            "state": "DF",
            "zip_code": self.digits(self.fake.postcode()),
        }

    def seed_employees(self):
        role_types = {
            name: EmployeeRoleType.objects.get_or_create(role=name)[0]
            for name in ["Professor", "Fiscal", "Coordenador"]
        }
        roles = (
            [role_types["Professor"]] * 5
            + [role_types["Fiscal"]] * 3
            + [role_types["Coordenador"]] * 2
        )

        employees = []
        for role in roles:
            sex = random.choice("MF")
            first_name = (
                self.fake.first_name_male()
                if sex == "M"
                else self.fake.first_name_female()
            )
            last_name = self.fake.last_name()

            employees.append(
                Employee(
                    name=f"{first_name} {last_name} {self.fake.last_name()}",
                    role=role,
                    sex=sex,
                    cpf=self.digits(self.fake.unique.cpf()),
                    rg=self.rg(),
                    issuing_authority="SSP/DF",
                    birth_date=self.birth_date(random.randint(24, 62)),
                    nationality="Brasileira",
                    phone=self.phone(mobile=False),
                    mobile=self.phone(),
                )
            )
        Employee.objects.bulk_create(employees)

    def make_guardian(self, sex, family_name):
        first_name = (
            self.fake.first_name_male() if sex == "M" else self.fake.first_name_female()
        )
        return Guardian(
            name=f"{first_name} {self.fake.last_name()} {family_name}",
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
            for guardian, _ in parents[
                :2
            ]:  # parents usually share the children's address
                for field, value in home.items():
                    setattr(guardian, field, value)
            guardians.extend(guardian for guardian, _ in parents)

            children_count = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
            for _ in range(min(children_count, student_count - len(students))):
                sex = random.choice("MF")
                first_name = (
                    self.fake.first_name_male()
                    if sex == "M"
                    else self.fake.first_name_female()
                )
                student = Student(
                    name=f"{first_name} {self.fake.last_name()} {family_name}",
                    social_name=self.fake.first_name()
                    if random.random() < 0.03
                    else "",
                    registration="",  # filled in once the first enrollment year is known
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
                students.append(student)

                financial = random.choice(parents[:2])[0]
                for guardian, relationship in parents:
                    links.append(
                        GuardianAssociation(
                            student=student,
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

    def enrollment_status(self, year):
        if year >= self.current_year:
            return random.choices(
                [
                    EnrollmentStatus.ACTIVE,
                    EnrollmentStatus.TRANSFERRED,
                    EnrollmentStatus.DROPPED,
                ],
                weights=[94, 3, 3],
            )[0]
        return EnrollmentStatus.COMPLETED

    def seed_enrollments(self, students, programs, classes, enrollment_types):
        classes_by_key = {}
        for school_class in classes:
            classes_by_key.setdefault(
                (
                    school_class.year_id,
                    school_class.program_id,
                    school_class.grade_level,
                ),
                [],
            ).append(school_class)

        enrollments = []
        for student in students:
            start_year = random.choice(self.school_years)
            in_high_school = random.random() < 0.7

            if in_high_school:
                program = programs[HIGH_SCHOOL]
                grade_level = random.choices([1, 2, 3], weights=[60, 25, 15])[0]
                student.birth_date = self.birth_date(
                    14 + grade_level + (self.current_year - start_year)
                )
                years = []
                for year in range(start_year, max(start_year, self.current_year) + 1):
                    years.append((year, grade_level))
                    grade_level += 1
                    if grade_level > 3:
                        break
            else:
                program = programs[random.choice(PREP_PROGRAMS)]
                student.birth_date = self.birth_date(
                    random.randint(16, 19) + (self.current_year - start_year)
                )
                years = [(start_year, None)]

            for index, (year, grade_level) in enumerate(years):
                status = self.enrollment_status(year)
                enrollment_type = enrollment_types[
                    (year, program.pk, str(grade_level) if grade_level else "")
                ]
                enrollments.append(
                    Enrollment(
                        student=student,
                        enrollment_type=enrollment_type,
                        school_class=random.choice(
                            classes_by_key[
                                (
                                    enrollment_type.school_year_id,
                                    program.pk,
                                    grade_level,
                                )
                            ]
                        ),
                        status=status,
                        enrolled_at=date(year - 1, 12, 1)
                        + timedelta(days=random.randint(0, 60)),
                        discount_percent=random.choices(
                            [Decimal(0), Decimal(10), Decimal(20)],
                            weights=[75, 20, 5],
                        )[0],
                        due_day=random.choice([5, 10, 15]),
                    )
                )
                if status not in (EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED):
                    break

            student.start_year = start_year

        # Matrícula = first school year + sequential number within that year
        sequence = {}
        for student in students:
            start_year = student.start_year
            sequence[start_year] = sequence.get(start_year, 0) + 1
            student.registration = f"{start_year}{sequence[start_year]:05d}"
        Student.objects.bulk_update(students, ["registration", "birth_date"])
        # Save one by one (not bulk_create) so the post_save signal builds the
        # account, installments and documents. Each starts active and then moves
        # to its final status, so the signal cancels future installments of
        # dropped or transferred enrollments like the real workflow does.
        for enrollment in enrollments:
            final_status = enrollment.status
            enrollment.status = EnrollmentStatus.ACTIVE
            enrollment.save()
            if final_status != EnrollmentStatus.ACTIVE:
                enrollment.status = final_status
                enrollment.save(update_fields=["status"])

        # def score(self, ability):
        #     value = min(10.0, max(0.0, random.gauss(ability, 1.3)))
        #     return Decimal(str(round(value * 2) / 2))  # round to the nearest 0.5

        # def seed_grades(self, subjects):
        #     """Grades for every enrollment active in the current year."""
        #     grades = []
        #     active = Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE)
        #     for enrollment in active:
        #         ability = random.gauss(7.0, 1.4)
        #         for subject in subjects:
        #             for bimester in BIMESTERS:
        #                 for evaluation in EVALUATIONS:
        #                     grades.append(
        #                         Grade(
        #                             enrollment=enrollment,
        #                             subject=subject,
        #                             evaluation=evaluation,
        #                             bimester=bimester,
        #                             score=self.score(ability),
        #                         )
        #                     )
        #                 if random.random() < EXTRA_CHANCE:
        #                     grades.append(
        #                         Grade(
        #                             enrollment=enrollment,
        #                             subject=subject,
        #                             evaluation=Evaluation.EX,
        #                             bimester=bimester,
        #                             score=Decimal(
        #                                 random.choice(["0.50", "1.00", "1.50", "2.00"])
        #                             ),
        #                         )
        #                     )
        #     Grade.objects.bulk_create(grades, batch_size=2000)

        # def seed_incidents(self, students, incident_types, count=180):
        #     troublemakers = random.sample(students, k=max(1, len(students) // 8))
        #     type_weights = [
        #         1 / penalty for penalty in INCIDENT_TYPES.values()
        #     ]  # light incidents are more common

        #     incidents = Incident.objects.bulk_create(
        #         [
        #             Incident(
        #                 student=random.choice(
        #                     troublemakers if random.random() < 0.6 else students
        #                 ),
        #                 incident_type=random.choices(incident_types, weights=type_weights)[
        #                     0
        #                 ],
        #             )
        #             for _ in range(count)
        #         ]
        #     )

        # created_at is auto_now_add, so backdate it after insert
        # start = timezone.make_aware(datetime(self.current_year, 2, 1, 7))
        # span = (timezone.now() - start).total_seconds()
        # for incident in incidents:
        #     incident.created_at = start + timedelta(seconds=random.uniform(0, span))
        # Incident.objects.bulk_update(incidents, ["created_at"])

    # ------------------------------------------------------------------ finance

    # def seed_enrollment_accounts(self):
    #     """bulk_create skips the post_save signal, so build each contract's receivable here."""
    #     category = tuition_category()
    #     for enrollment in Enrollment.objects.select_related(
    #         "enrollment_type", "student"
    #     ):
    #         create_enrollment_account(enrollment, category=category)

    # def seed_payables(self):
    #     today = timezone.localdate()
    #     for category_name, supplier_name, value in MONTHLY_EXPENSES:
    #         category = AccountType.objects.get_or_create(
    #             name=category_name, defaults={"direction": Direction.PAYABLE}
    #         )[0]
    #         supplier = Supplier.objects.get_or_create(name=supplier_name)[0]
    #         account = AccountPayable.objects.create(
    #             description=f"{category_name} {today.year}",
    #             category=category,
    #             supplier=supplier,
    #             issue_date=date(today.year, 1, 1),
    #             gross_value=value * 12,
    #         )
    #         Installment.objects.bulk_create(
    #             build_installments(account, 12, date(today.year, 1, 5))
    #         )

    # def seed_payments(self):
    #     """Most past installments are paid on time, some late with charges; a few stay overdue."""
    #     today = timezone.localdate()
    #     installments = Installment.objects.filter(
    #         due_date__lt=today, status=InstallmentStatus.OPEN
    #     )
    #     payments, paid = [], []
    #     for installment in installments:
    #         roll = random.random()
    #         if roll < 0.06:
    #             continue  # still overdue
    #         paid_at = installment.due_date - timedelta(days=random.randint(0, 5))
    #         penalty = interest = Decimal("0.00")
    #         if roll < 0.2:
    #             paid_at = min(
    #                 today, installment.due_date + timedelta(days=random.randint(1, 40))
    #             )
    #             penalty = (installment.amount * LATE_PENALTY).quantize(Decimal("0.01"))
    #             interest = (
    #                 installment.amount
    #                 * LATE_INTEREST_PER_DAY
    #                 * (paid_at - installment.due_date).days
    #             ).quantize(Decimal("0.01"))
    #         payments.append(
    #             Payment(
    #                 installment=installment,
    #                 paid_at=paid_at,
    #                 amount=installment.amount + penalty + interest,
    #                 penalty=penalty,
    #                 interest=interest,
    #                 method=random.choice(
    #                     [
    #                         PaymentMethod.PIX,
    #                         PaymentMethod.PIX,
    #                         PaymentMethod.BOLETO,
    #                         PaymentMethod.CREDIT_CARD,
    #                     ]
    #                 ),
    #             )
    #         )
    #         installment.status = InstallmentStatus.PAID
    #         paid.append(installment)
    #     # bulk_create skips Payment.save(), so set the status in bulk too
    #     Payment.objects.bulk_create(payments, batch_size=2000)
    #     Installment.objects.bulk_update(paid, ["status"], batch_size=2000)

    # ------------------------------------------------------------------ summary

    def print_summary(self):
        for model in [
            User,
            Employee,
            Program,
            Class,
            Guardian,
            Student,
            GuardianAssociation,
            SchoolYear,
            EnrollmentType,
            Enrollment,
            # Subject,
            # Grade,
            # IncidentType,
            # Incident,
            AccountType,
            Supplier,
            Installment,
            Payment,
        ]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{model._meta.verbose_name_plural}: {model.objects.count()}"
                )
            )
