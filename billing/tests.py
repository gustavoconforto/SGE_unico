from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.forms import PaymentForm
from accounts.models import Installment, InstallmentStatus, Payment, PaymentMethod
from base.testing import LoggedInTestCase
from billing import cnab400
from billing.models import (
    BankSettings,
    BankSlip,
    EventStatus,
    Remittance,
    ReturnFile,
    SlipStatus,
)
from billing.services import (
    BillingError,
    create_remittance,
    delete_remittance,
    import_return,
    remittance_candidates,
    write_off_candidates,
)
from enrollments.models import Enrollment, EnrollmentType, SchoolYear
from programs.models import Program
from students.models import Guardian, GuardianAssociation, Relationship, Student

HTMX = {"HTTP_HX_REQUEST": "true"}
COMPANY_CODE = "5242021"


def _put(chars, start, value):
    chars[start - 1 : start - 1 + len(value)] = value


def ret_payload(events, company_code=COMPANY_CODE, file_date=date(2026, 10, 7)):
    """Build a Bradesco return file; each event is a dict of detail fields."""
    header = [" "] * 400
    _put(header, 1, "02RETORNO01COBRANCA")
    _put(header, 27, company_code.zfill(20))
    _put(header, 77, "237BRADESCO")
    _put(header, 95, file_date.strftime("%d%m%y"))
    lines = [header]
    for event in events:
        line = [" "] * 400
        _put(line, 1, "1")
        _put(line, 38, event.get("participant", "").ljust(25))
        _put(line, 71, event["nosso_numero"])
        _put(line, 109, event["code"])
        _put(line, 111, event.get("date", date(2026, 10, 7)).strftime("%d%m%y"))
        for start, key in (
            (153, "title"),
            (241, "discount"),
            (254, "paid"),
            (267, "interest"),
        ):
            _put(line, start, f"{int(Decimal(event.get(key, '0')) * 100):013d}")
        _put(line, 296, event.get("date", date(2026, 10, 7)).strftime("%d%m%y"))
        _put(line, 319, event.get("reasons", "0000000000"))
        lines.append(line)
    lines.append([" "] * 400)
    _put(lines[-1], 1, "9")
    for index, line in enumerate(lines, 1):
        _put(line, 395, f"{index:06d}")
    return b"".join("".join(line).encode() + b"\r\n" for line in lines)


class Cnab400Tests(TestCase):
    def beneficiary(self):
        return cnab400.Beneficiary(
            company_code=COMPANY_CODE,
            name="Unico Educacional",
            carteira="09",
            agency="484",
            account="18360",
            account_digit="1",
        )

    def test_nosso_numero_check_digit(self):
        # Values from files already accepted by the bank.
        self.assertEqual(cnab400.nosso_numero_dv("09", "01000267901"), "7")
        self.assertEqual(cnab400.nosso_numero_dv("009", "01000267375"), "2")
        self.assertEqual(cnab400.nosso_numero_dv("09", "01000241868"), "P")

    def test_remittance_layout(self):
        title = cnab400.Title(
            participant_control="15",
            document_number="321",
            nosso_numero="20000000015",
            due_date=date(2026, 10, 16),
            amount=Decimal("4227.00"),
            issue_date=date(2026, 10, 15),
            payer=cnab400.Payer(
                tax_id="00275010198",
                name="Fernanda Lancini Bello Romualdo",
                address="Condomínio Privê I Quadra 1 Conjunto M Casa 10",
                zip_code="71539070",
            ),
            fine_percent=Decimal(2),
            daily_interest=Decimal("1.41"),
            discount_deadline=date(2026, 10, 16),
            discount_amount=Decimal(90),
        )
        config = cnab400.RemittanceConfig(self.beneficiary(), 2016, date(2026, 10, 15))
        payload = cnab400.generate_remittance(config, [title])

        self.assertTrue(payload.endswith(b"\r\n"))
        lines = payload.decode().split("\r\n")[:-1]
        self.assertEqual([len(line) for line in lines], [400, 400, 400])
        header, detail, trailer = lines
        self.assertEqual(header[:26], "01REMESSA01COBRANCA       ")
        self.assertEqual(header[108:117], "MX0002016")
        self.assertEqual(detail[20:37], "00090048400183601")
        self.assertEqual(detail[65:70], "20200")  # 2% fine
        self.assertEqual(
            detail[70:82], "20000000015" + cnab400.nosso_numero_dv("09", "20000000015")
        )
        self.assertEqual(detail[93], "N")
        self.assertEqual(detail[105], "2")
        self.assertEqual(detail[126:139], "0000000422700")
        self.assertEqual(detail[160:173], "0000000000141")
        self.assertEqual(detail[173:192], "161026" + "0000000009000")
        self.assertEqual(detail[218:234], "0100000275010198")
        # Accents removed and the address cut at 40 characters.
        self.assertEqual(detail[274:314], "CONDOMINIO PRIVE I QUADRA 1 CONJUNTO M C")
        self.assertEqual(detail[326:334], "71539070")
        self.assertEqual(trailer[0] + trailer[394:], "9000003")

    def test_parse_return(self):
        payload = ret_payload(
            [
                {
                    "nosso_numero": "200000000127",
                    "code": "06",
                    "title": "100",
                    "discount": "90",
                    "paid": "10",
                    "participant": "12",
                }
            ]
        )
        data = cnab400.parse_return(payload)
        self.assertEqual(data.company_code.lstrip("0"), COMPANY_CODE)
        self.assertEqual(data.file_date, date(2026, 10, 7))
        (event,) = data.events
        self.assertTrue(event.is_settlement)
        self.assertEqual(event.nosso_numero, "200000000127")
        self.assertEqual(event.participant_control, "12")
        self.assertEqual(event.amount_paid, Decimal(10))
        self.assertEqual(event.discount_amount, Decimal(90))
        self.assertEqual(event.occurrence_date, date(2026, 10, 7))

    def test_parse_return_rejects_broken_files(self):
        payload = ret_payload([{"nosso_numero": "200000000127", "code": "02"}])
        with self.assertRaises(ValueError):
            cnab400.parse_return(payload.replace(b"000002\r\n", b"000005\r\n"))
        with self.assertRaises(ValueError):
            cnab400.parse_return(payload.replace(b"237BRADESCO", b"341ITAU     "))
        with self.assertRaises(ValueError):
            cnab400.parse_return(payload[:-10])

    def test_generated_return_round_trips(self):
        entry = cnab400.ReturnEntry(
            nosso_numero="20000000012P",
            occurrence_code="06",
            occurrence_date=date(2026, 3, 9),
            participant_control="12",
            document_number="345",
            due_date=date(2026, 3, 10),
            title_amount=Decimal("4500.00"),
            amount_paid=Decimal("4410.00"),
            discount_amount=Decimal("90.00"),
            credit_date=date(2026, 3, 10),
            reason_codes=("48",),
        )
        payload = cnab400.generate_return(COMPANY_CODE, date(2026, 3, 10), [entry])
        data = cnab400.parse_return(payload)
        self.assertEqual(data.company_code.lstrip("0"), COMPANY_CODE)
        self.assertEqual(data.file_date, date(2026, 3, 10))
        (event,) = data.events
        self.assertEqual(event.nosso_numero, "20000000012P")
        self.assertEqual(event.occurrence_code, "06")
        self.assertEqual(event.occurrence_date, date(2026, 3, 9))
        self.assertEqual(event.participant_control, "12")
        self.assertEqual(event.document_number, "345")
        self.assertEqual(event.due_date, date(2026, 3, 10))
        self.assertEqual(event.title_amount, Decimal("4500.00"))
        self.assertEqual(event.amount_paid, Decimal("4410.00"))
        self.assertEqual(event.discount_amount, Decimal("90.00"))
        self.assertEqual(event.credit_date, date(2026, 3, 10))
        self.assertEqual(event.reason_codes, ("48",))


class BillingTestMixin:
    @classmethod
    def setUpTestData(cls):
        today = timezone.localdate()
        year = today.year + 1
        school_year = SchoolYear.objects.create(
            begins=date(year, 1, 10),
            ends=date(year, 12, 15),
            bi_1_begins=date(year, 2, 1),
            bi_1_ends=date(year, 4, 17),
            bi_2_begins=date(year, 4, 27),
            bi_2_ends=date(year, 7, 3),
            bi_3_begins=date(year, 7, 27),
            bi_3_ends=date(year, 9, 30),
            bi_4_begins=date(year, 10, 13),
            bi_4_ends=date(year, 12, 15),
        )
        enrollment_type = EnrollmentType.objects.create(
            program=Program.objects.create(name="Pré ENEM"),
            school_year=school_year,
            total_price=Decimal("1200.00"),
            description="Contrato anual",
        )
        student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )
        cls.guardian = Guardian.objects.create(
            name="Maria Souza",
            cpf="00275010198",
            rg="7654321",
            issuing_authority="SSP",
            address="Quadra 1 Conjunto M Casa 10",
            neighborhood="Jardim Botânico",
            zip_code="71539070",
        )
        GuardianAssociation.objects.create(
            student=student,
            guardian=cls.guardian,
            relationship=Relationship.MOTHER,
            is_financial=True,
        )
        enrollment = Enrollment.objects.create(
            student=student,
            enrollment_type=enrollment_type,
            enrolled_at=today,
            due_day=10,
        )
        cls.account = enrollment.account
        cls.account.installments.update(due_date=today + timedelta(days=10))
        cls.settings = BankSettings.objects.create(
            company_code=COMPANY_CODE,
            company_name="Unico Educacional",
            agency="484",
            account="18360",
            account_digit="1",
            last_remittance_number=2015,
        )

    def installments(self):
        return list(self.account.installments.order_by("number"))

    def slip_return(self, slip, code, **fields):
        return {"nosso_numero": f"{slip}".replace("-", ""), "code": code, **fields}


class RemittanceServiceTests(BillingTestMixin, TestCase):
    def test_creates_slips_with_nosso_numero_and_punctuality_discount(self):
        first, second = self.installments()[:2]
        remittance = create_remittance([first.pk, second.pk])

        self.assertEqual(remittance.number, 2016)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.last_remittance_number, 2016)
        slips = list(remittance.slips.order_by("pk"))
        self.assertEqual(len(slips), 2)
        slip = slips[0]
        self.assertEqual(slip.nosso_numero, f"2000{slip.pk:07d}")
        self.assertEqual(
            slip.nosso_numero_dv, cnab400.nosso_numero_dv("09", slip.nosso_numero)
        )
        self.assertEqual(slip.amount, first.amount)
        self.assertEqual(slip.discount, Decimal("90.00"))

        lines = remittance.content.split("\r\n")[:-1]
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[1][70:81], slip.nosso_numero)
        self.assertEqual(lines[1][110:120].strip(), str(first.pk))
        self.assertEqual(remittance.filename, "00002016.REM")

    def test_live_slip_blocks_sending_the_installment_again(self):
        first = self.installments()[0]
        create_remittance([first.pk])
        self.assertNotIn(first, remittance_candidates())
        with self.assertRaises(BillingError):
            create_remittance([first.pk])

    def test_skips_installments_with_payer_problems(self):
        first, second = self.installments()[:2]
        Installment.objects.filter(pk=first.pk).update(
            due_date=timezone.localdate() - timedelta(days=1)
        )
        Guardian.objects.filter(pk=self.guardian.pk).update(zip_code="")
        with self.assertRaises(BillingError):
            create_remittance([first.pk, second.pk])

        Guardian.objects.filter(pk=self.guardian.pk).update(zip_code="71539070")
        remittance = create_remittance([first.pk, second.pk])
        self.assertEqual(
            list(remittance.slips.values_list("installment", flat=True)), [second.pk]
        )

    def test_requires_bank_settings(self):
        BankSettings.objects.all().delete()
        with self.assertRaises(BillingError):
            create_remittance([self.installments()[0].pk])

    def test_delete_unprocessed_remittance_frees_the_number(self):
        remittance = create_remittance([self.installments()[0].pk])
        delete_remittance(remittance)
        self.assertFalse(BankSlip.objects.exists())
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.last_remittance_number, 2015)

    def test_processed_remittance_cannot_be_deleted(self):
        remittance = create_remittance([self.installments()[0].pk])
        remittance.slips.update(status=SlipStatus.REGISTERED)
        with self.assertRaises(BillingError):
            delete_remittance(remittance)


class ReturnServiceTests(BillingTestMixin, TestCase):
    def setUp(self):
        self.installment = self.installments()[0]
        self.slip = create_remittance([self.installment.pk]).slips.get()

    def import_events(self, *events, name="CB081000.RET"):
        return import_return(name, ret_payload(list(events)))

    def test_entry_confirmed_registers_slip(self):
        self.import_events(self.slip_return(self.slip, "02"))
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.REGISTERED)

    def test_settlement_with_punctuality_discount_pays_installment(self):
        paid = self.installment.amount - Decimal(90)
        return_file = self.import_events(
            self.slip_return(
                self.slip, "06", title=self.slip.amount, discount="90", paid=paid
            )
        )
        event = return_file.events.get()
        self.assertEqual(event.status, EventStatus.PROCESSED)
        payment = Payment.objects.get()
        self.assertEqual(event.payment, payment)
        self.assertEqual(payment.amount, paid)
        self.assertEqual(payment.discount, Decimal(90))
        self.assertEqual(payment.method, PaymentMethod.BOLETO)
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.PAID)
        self.assertEqual(
            Installment.objects.with_balance().get(pk=self.installment.pk).outstanding,
            Decimal(0),
        )
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.PAID)

    def test_late_settlement_records_interest(self):
        paid = self.installment.amount + Decimal("3.50")
        self.import_events(
            self.slip_return(
                self.slip, "06", title=self.slip.amount, interest="3.50", paid=paid
            )
        )
        payment = Payment.objects.get()
        self.assertEqual(payment.interest, Decimal("3.50"))
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.PAID)

    def test_settlement_above_balance_is_flagged(self):
        paid = self.installment.amount + Decimal(50)
        event = self.import_events(
            self.slip_return(self.slip, "06", paid=paid)
        ).events.get()
        self.assertEqual(event.status, EventStatus.ERROR)
        self.assertFalse(Payment.objects.exists())

    def test_same_file_or_line_is_not_imported_twice(self):
        settlement = self.slip_return(
            self.slip, "06", discount="90", paid=self.installment.amount - Decimal(90)
        )
        self.import_events(settlement)
        with self.assertRaises(BillingError):
            self.import_events(settlement)
        # Same line in a different file (other header date).
        import_return(
            "other.RET", ret_payload([settlement], file_date=date(2026, 10, 8))
        )
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(ReturnFile.objects.count(), 2)

    def test_reversal_deletes_payment_and_reopens_installment(self):
        self.import_events(
            self.slip_return(
                self.slip,
                "06",
                discount="90",
                paid=self.installment.amount - Decimal(90),
            )
        )
        event = self.import_events(
            self.slip_return(self.slip, "40"), name="r2.RET"
        ).events.get()
        self.assertEqual(event.status, EventStatus.PROCESSED)
        self.assertFalse(Payment.objects.exists())
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.OPEN)
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.REVERSED)

    def test_expired_slip_marks_installment_expired(self):
        self.import_events(self.slip_return(self.slip, "09"))
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.EXPIRED)
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.EXPIRED)
        # Still owed: pending, and can be sent again.
        self.assertIn(self.installment, Installment.objects.pending())
        self.assertIn(self.installment, remittance_candidates())

    def test_expired_installment_stays_expired_until_fully_paid(self):
        self.import_events(self.slip_return(self.slip, "09"))
        self.installment.refresh_from_db()
        Payment.objects.create(
            installment=self.installment, amount=Decimal(10), method=PaymentMethod.CASH
        )
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.EXPIRED)
        Payment.objects.create(
            installment=self.installment,
            amount=self.installment.amount - Decimal(10),
            method=PaymentMethod.CASH,
        )
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.PAID)

    def test_agency_write_off_keeps_installment(self):
        event = self.import_events(self.slip_return(self.slip, "10")).events.get()
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.WRITTEN_OFF)
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.OPEN)
        self.assertIn("ainda possui saldo", event.message)

    def test_rejected_slip_frees_installment(self):
        self.import_events(self.slip_return(self.slip, "03", reasons="4800000000"))
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.REJECTED)
        self.assertIn(self.installment, remittance_candidates())

    def test_unknown_slips(self):
        return_file = self.import_events(
            {"nosso_numero": "01000241868P", "code": "06", "paid": "100"},
            {"nosso_numero": "200099999990", "code": "06", "paid": "100"},
        )
        statuses = list(return_file.events.values_list("status", flat=True))
        self.assertEqual(statuses, [EventStatus.IGNORED, EventStatus.ERROR])

    def test_rejects_other_company(self):
        with self.assertRaises(BillingError):
            import_return(
                "x.RET",
                ret_payload([self.slip_return(self.slip, "02")], company_code="999"),
            )
        self.assertFalse(ReturnFile.objects.exists())


class WriteOffTests(BillingTestMixin, LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.installment = self.installments()[0]
        self.slip = create_remittance([self.installment.pk]).slips.get()
        import_return("confirm.RET", ret_payload([self.slip_return(self.slip, "02")]))

    def pay_cash(self, amount):
        self.installment.refresh_from_db()
        Payment.objects.create(
            installment=self.installment, amount=amount, method=PaymentMethod.CASH
        )

    def request_write_off(self):
        return create_remittance(write_off_slip_ids=[self.slip.pk])

    def test_only_slips_paid_another_way_or_cancelled_are_candidates(self):
        self.assertEqual(write_off_candidates(), [])
        self.pay_cash(self.installment.amount)
        self.assertEqual(write_off_candidates(), [self.slip])

        Payment.objects.all().delete()
        Installment.objects.filter(pk=self.installment.pk).update(
            status=InstallmentStatus.CANCELLED
        )
        self.assertEqual(write_off_candidates(), [self.slip])

    def test_write_off_request_uses_movement_code_02(self):
        self.pay_cash(self.installment.amount)
        remittance = self.request_write_off()

        self.assertEqual(remittance.number, 2017)
        self.assertFalse(remittance.slips.exists())
        detail = remittance.content.split("\r\n")[1]
        self.assertEqual(detail[108:110], "02")
        self.assertEqual(detail[70:81], self.slip.nosso_numero)
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.WRITE_OFF_REQUESTED)
        self.assertEqual(self.slip.write_off_remittance, remittance)
        self.assertEqual(write_off_candidates(), [])

    def test_partial_cash_payment_is_resent_after_bank_confirms(self):
        self.pay_cash(Decimal(40))
        self.request_write_off()
        # Still live until the bank confirms the write-off.
        self.assertNotIn(self.installment, remittance_candidates())

        import_return("baixa.RET", ret_payload([self.slip_return(self.slip, "10")]))
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.WRITTEN_OFF)
        candidate = remittance_candidates().get(pk=self.installment.pk)
        self.assertEqual(candidate.outstanding, self.installment.amount - Decimal(40))

    def test_rejected_write_off_keeps_slip_registered(self):
        self.pay_cash(self.installment.amount)
        self.request_write_off()
        event = import_return(
            "rej.RET", ret_payload([self.slip_return(self.slip, "27")])
        ).events.get()
        self.assertEqual(event.status, EventStatus.PROCESSED)
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.REGISTERED)
        self.assertEqual(write_off_candidates(), [self.slip])

    def test_deleting_the_remittance_reverts_the_request(self):
        self.pay_cash(self.installment.amount)
        delete_remittance(self.request_write_off())
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.REGISTERED)
        self.assertIsNone(self.slip.write_off_remittance)

    def test_remittance_page_lists_and_posts_write_offs(self):
        self.pay_cash(self.installment.amount)
        url = reverse("billing:remittance_add")
        response = self.client.get(url)
        self.assertEqual(response.context["write_offs"], [self.slip])
        self.assertContains(response, "Pedidos de baixa")

        response = self.client.post(url, {"write_offs": [self.slip.pk]})
        self.assertRedirects(response, reverse("billing:remittance_list"))
        self.slip.refresh_from_db()
        self.assertEqual(self.slip.status, SlipStatus.WRITE_OFF_REQUESTED)
        response = self.client.get(reverse("billing:remittance_list"))
        remittance = response.context["remittances"][0]
        self.assertEqual((remittance.slips_count, remittance.write_offs_count), (0, 1))


class PaymentDiscountTests(BillingTestMixin, TestCase):
    def test_discount_counts_towards_principal(self):
        installment = self.installments()[0]
        form = PaymentForm(
            data={
                "installment": installment.pk,
                "paid_at": timezone.localdate().isoformat(),
                "amount": installment.amount - Decimal(90),
                "penalty": "0",
                "interest": "0",
                "monetary_adjust": "0",
                "discount": "90",
                "method": PaymentMethod.CASH,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        installment.refresh_from_db()
        self.assertEqual(installment.status, InstallmentStatus.PAID)

    def test_discount_cannot_exceed_balance(self):
        installment = self.installments()[0]
        form = PaymentForm(
            data={
                "installment": installment.pk,
                "paid_at": timezone.localdate().isoformat(),
                "amount": installment.amount,
                "penalty": "0",
                "interest": "0",
                "monetary_adjust": "0",
                "discount": "90",
                "method": PaymentMethod.CASH,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)


class BillingViewTests(BillingTestMixin, LoggedInTestCase):
    def test_settings_edit_creates_single_row(self):
        BankSettings.objects.all().delete()
        response = self.client.post(
            reverse("billing:bank_settings_edit"),
            {
                "company_code": COMPANY_CODE,
                "company_name": "Unico Educacional",
                "carteira": "09",
                "agency": "484",
                "account": "18360",
                "account_digit": "1",
                "fine_percent": "2",
                "monthly_interest_percent": "1",
                "last_remittance_number": "2015",
            },
        )
        self.assertRedirects(response, reverse("billing:remittance_list"))
        self.assertEqual(BankSettings.load().agency, "484")

    def test_remittance_add_lists_candidates_and_generates(self):
        url = reverse("billing:remittance_add")
        due_to = (timezone.localdate() + timedelta(days=30)).isoformat()
        response = self.client.get(url, {"due_to": due_to})
        self.assertEqual(len(response.context["rows"]), 12)
        self.assertEqual(response.context["ready_count"], 12)

        response = self.client.get(url, {"q": "Maria", "due_to": due_to}, **HTMX)
        self.assertTemplateUsed(
            response, "remittances/partials/remittance_candidates.html"
        )

        first, second = self.installments()[:2]
        response = self.client.post(url, {"installments": [first.pk, second.pk]})
        self.assertRedirects(response, reverse("billing:remittance_list"))
        self.assertEqual(Remittance.objects.get().slips.count(), 2)

    def test_remittance_add_without_selection_shows_error(self):
        url = reverse("billing:remittance_add")
        response = self.client.post(url, {}, follow=True)
        self.assertContains(
            response, "Selecione ao menos uma parcela ou um pedido de baixa."
        )
        self.assertFalse(Remittance.objects.exists())

    def test_remittance_download(self):
        remittance = create_remittance([self.installments()[0].pk])
        response = self.client.get(
            reverse("billing:remittance_download", args=[remittance.pk])
        )
        self.assertEqual(response.content, remittance.content.encode())
        self.assertIn("00002016.REM", response["Content-Disposition"])

    def test_remittance_delete(self):
        remittance = create_remittance([self.installments()[0].pk])
        response = self.client.post(
            reverse("billing:remittance_delete", args=[remittance.pk])
        )
        self.assertRedirects(response, reverse("billing:remittance_list"))
        self.assertFalse(Remittance.objects.exists())

    def test_lists_render_partials_on_htmx(self):
        create_remittance([self.installments()[0].pk])
        for name, partial in (
            ("billing:remittance_list", "remittances/partials/remittance_table.html"),
            ("billing:bank_slip_list", "bank_slips/partials/bank_slip_table.html"),
            (
                "billing:return_file_list",
                "return_files/partials/return_file_table.html",
            ),
        ):
            response = self.client.get(reverse(name), **HTMX)
            self.assertTemplateUsed(response, partial)

    def test_bank_slip_status_filter(self):
        create_remittance([self.installments()[0].pk])
        url = reverse("billing:bank_slip_list")
        response = self.client.get(url, {"status": SlipStatus.GENERATED})
        self.assertEqual(len(response.context["slips"]), 1)
        response = self.client.get(url, {"status": SlipStatus.PAID})
        self.assertEqual(len(response.context["slips"]), 0)

    def test_return_upload_and_detail(self):
        slip = create_remittance([self.installments()[0].pk]).slips.get()
        upload = SimpleUploadedFile(
            "CB081000.RET", ret_payload([self.slip_return(slip, "02")])
        )
        response = self.client.post(
            reverse("billing:return_file_add"), {"file": upload}
        )
        return_file = ReturnFile.objects.get()
        self.assertRedirects(
            response, reverse("billing:return_file_detail", args=[return_file.pk])
        )
        response = self.client.get(response.url)
        self.assertContains(response, "Entrada confirmada")

    def test_return_upload_invalid_file(self):
        upload = SimpleUploadedFile("x.RET", b"not a cnab file")
        response = self.client.post(
            reverse("billing:return_file_add"), {"file": upload}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Arquivo inválido")
        self.assertFalse(ReturnFile.objects.exists())

    def test_full_pages_render(self):
        remittance = create_remittance([self.installments()[0].pk])
        return_file = import_return(
            "r.RET", ret_payload([self.slip_return(remittance.slips.get(), "02")])
        )
        for url in (
            reverse("billing:bank_settings_edit"),
            reverse("billing:remittance_list"),
            reverse("billing:remittance_add"),
            reverse("billing:remittance_delete", args=[remittance.pk]),
            reverse("billing:bank_slip_list"),
            reverse("billing:return_file_list"),
            reverse("billing:return_file_add"),
            reverse("billing:return_file_detail", args=[return_file.pk]),
            reverse(
                "enrollments:enrollment_type_edit",
                args=[self.account.enrollment.enrollment_type_id],
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
