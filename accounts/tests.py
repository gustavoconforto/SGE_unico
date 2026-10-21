from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from accounts.models import (
    AccountPayable,
    AccountReceivable,
    AccountType,
    Direction,
    InstallmentStatus,
    Payment,
    Supplier,
)
from base.testing import LoggedInTestCase

HTMX = {"HTTP_HX_REQUEST": "true"}


class AccountViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.income = AccountType.objects.create(
            name="Mensalidade", direction=Direction.RECEIVABLE
        )
        cls.expense = AccountType.objects.create(
            name="Aluguel", direction=Direction.PAYABLE
        )
        cls.supplier = Supplier.objects.create(name="Imobiliária Centro")

    def create_receivable(self, description="Mensalidade avulsa", count=3, **extra):
        data = {
            "description": description,
            "category": self.income.pk,
            "issue_date": timezone.localdate().isoformat(),
            "gross_value": "300.00",
            "discount_value": "0",
            "installments_count": count,
            "first_due_date": timezone.localdate().isoformat(),
            **extra,
        }
        return self.client.post(reverse("accounts:receivable_add"), data)

    def test_create_receivable_generates_installments(self):
        response = self.create_receivable()
        self.assertRedirects(response, reverse("accounts:receivable_list"))
        account = AccountReceivable.objects.get()
        self.assertEqual(account.direction, Direction.RECEIVABLE)
        self.assertEqual(account.installments.count(), 3)
        self.assertEqual(
            sum(i.amount for i in account.installments.all()), Decimal("300.00")
        )

    def test_receivable_form_rejects_payable_category(self):
        response = self.create_receivable(category=self.expense.pk)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AccountReceivable.objects.exists())

    def test_lists_are_separated_by_direction(self):
        self.create_receivable("Receita X")
        AccountPayable.objects.create(
            description="Despesa Y",
            category=self.expense,
            supplier=self.supplier,
            gross_value=Decimal(50),
        )
        receivables = self.client.get(reverse("accounts:receivable_list"))
        payables = self.client.get(reverse("accounts:payable_list"))
        self.assertContains(receivables, "Receita X")
        self.assertNotContains(receivables, "Despesa Y")
        self.assertContains(payables, "Despesa Y")
        self.assertNotContains(payables, "Receita X")

    def test_htmx_search_and_status_filter_return_partial(self):
        self.create_receivable("Receita aberta")
        self.create_receivable("Receita vencida")
        AccountReceivable.objects.get(description="Receita vencida").installments.update(
            due_date=timezone.localdate() - timedelta(days=5)
        )
        url = reverse("accounts:receivable_list")

        response = self.client.get(url, {"q": "aberta"}, **HTMX)
        self.assertTemplateUsed(response, "accounts/partials/account_table.html")
        self.assertTemplateNotUsed(response, "accounts/account_list.html")
        self.assertContains(response, "Receita aberta")
        self.assertNotContains(response, "Receita vencida")

        response = self.client.get(url, {"status": "overdue"}, **HTMX)
        self.assertContains(response, "Receita vencida")
        self.assertNotContains(response, "Receita aberta")

        response = self.client.get(url, {"category": self.income.pk, "status": "paid"})
        self.assertContains(response, "Nenhum registro encontrado")

    def test_delete_blocked_when_account_has_payments(self):
        self.create_receivable(count=1)
        account = AccountReceivable.objects.get()
        Payment.objects.create(
            installment=account.installments.get(), amount=Decimal(10), method="PIX"
        )
        self.client.post(reverse("accounts:receivable_delete", args=[account.pk]))
        self.assertTrue(AccountReceivable.objects.filter(pk=account.pk).exists())

    def test_delete_removes_installments(self):
        self.create_receivable()
        account = AccountReceivable.objects.get()
        self.client.post(reverse("accounts:receivable_delete", args=[account.pk]))
        self.assertFalse(AccountReceivable.objects.exists())


class PaymentViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        category = AccountType.objects.create(
            name="Mensalidade", direction=Direction.RECEIVABLE
        )
        cls.account = AccountReceivable.objects.create(
            description="Mensalidade outubro",
            category=category,
            gross_value=Decimal(100),
        )
        cls.installment = cls.account.installments.create(
            number=1, due_date=timezone.localdate(), amount=Decimal(100)
        )
        expense = AccountType.objects.create(name="Aluguel", direction=Direction.PAYABLE)
        supplier = Supplier.objects.create(
            name="Imobiliária Centro", document="12345678000199"
        )
        cls.payable_installment = (
            AccountPayable.objects.create(
                description="Aluguel outubro",
                category=expense,
                supplier=supplier,
                gross_value=Decimal(100),
            )
            .installments.create(
                number=1, due_date=timezone.localdate(), amount=Decimal(100)
            )
        )

    def post_payment(self, amount, **extra):
        data = {
            "installment": self.installment.pk,
            "paid_at": timezone.localdate().isoformat(),
            "amount": amount,
            "penalty": "0",
            "interest": "0",
            "monetary_adjust": "0",
            "method": "PIX",
            **extra,
        }
        return self.client.post(reverse("accounts:payment_add"), data)

    def test_payment_updates_installment_status(self):
        self.assertRedirects(self.post_payment("40"), reverse("accounts:payment_list"))
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.PARTIAL)
        self.post_payment("65", penalty="5")
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.PAID)

    def test_payment_cannot_exceed_balance(self):
        response = self.post_payment("150")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Payment.objects.exists())

    def test_edit_payment_allows_its_own_amount(self):
        self.post_payment("100")
        payment = Payment.objects.get()
        response = self.client.post(
            reverse("accounts:payment_edit", args=[payment.pk]),
            {
                "installment": self.installment.pk,
                "paid_at": timezone.localdate().isoformat(),
                "amount": "90",
                "penalty": "0",
                "interest": "0",
                "monetary_adjust": "0",
                "method": "DIN",
            },
        )
        self.assertRedirects(response, reverse("accounts:payment_list"))
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, InstallmentStatus.PARTIAL)

    def test_add_prefills_from_installment_param(self):
        response = self.client.get(
            reverse("accounts:payment_add"), {"installment": self.installment.pk}
        )
        self.assertEqual(response.context["form"].initial["amount"], Decimal(100))

    def test_payable_installment_is_rejected(self):
        response = self.post_payment("10", installment=self.payable_installment.pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("installment"))
        self.assertFalse(Payment.objects.exists())

    def test_add_ignores_payable_installment_param(self):
        response = self.client.get(
            reverse("accounts:payment_add"), {"installment": self.payable_installment.pk}
        )
        self.assertNotIn("installment", response.context["form"].initial)

    def test_installment_lookup_searches_pending_installments(self):
        paid = self.account.installments.create(
            number=2,
            due_date=timezone.localdate(),
            amount=Decimal(50),
            status=InstallmentStatus.PAID,
        )
        self.post_payment("40")
        url = reverse("accounts:receivable_installment_lookup")

        response = self.client.get(url, {"q": "mensalidade"}, **HTMX)
        self.assertTemplateUsed(response, "payments/partials/installment_options.html")
        self.assertContains(response, f'data-pk="{self.installment.pk}"')
        self.assertContains(response, 'data-balance="60.00"')
        self.assertNotContains(response, f'data-pk="{paid.pk}"')

        response = self.client.get(url, {"q": "outubro"}, **HTMX)
        self.assertNotContains(response, f'data-pk="{self.payable_installment.pk}"')

        response = self.client.get(url, {"q": "inexistente"}, **HTMX)
        self.assertContains(response, "Nenhuma parcela pendente encontrada")

    def test_edit_form_shows_installment_label(self):
        self.post_payment("10")
        payment = Payment.objects.get()
        response = self.client.get(reverse("accounts:payment_edit", args=[payment.pk]))
        self.assertContains(response, 'value="Mensalidade outubro - 1ª parcela')
        self.assertContains(response, f'name="installment" id="id_installment_value" value="{self.installment.pk}"')

    def post_payable_payment(self, amount, **extra):
        data = {
            "installment": self.payable_installment.pk,
            "paid_at": timezone.localdate().isoformat(),
            "amount": amount,
            "penalty": "0",
            "interest": "0",
            "monetary_adjust": "0",
            "method": "TED",
            **extra,
        }
        return self.client.post(reverse("accounts:payable_payment_add"), data)

    def test_payable_payment_updates_installment_status(self):
        response = self.post_payable_payment("100")
        self.assertRedirects(response, reverse("accounts:payment_list") + "?direction=P")
        self.payable_installment.refresh_from_db()
        self.assertEqual(self.payable_installment.status, InstallmentStatus.PAID)

    def test_payable_form_rejects_receivable_installment(self):
        response = self.post_payable_payment("10", installment=self.installment.pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("installment"))
        self.assertFalse(Payment.objects.exists())

    def test_payable_add_prefills_from_installment_param(self):
        url = reverse("accounts:payable_payment_add")
        response = self.client.get(url, {"installment": self.payable_installment.pk})
        self.assertEqual(response.context["form"].initial["amount"], Decimal(100))
        response = self.client.get(url, {"installment": self.installment.pk})
        self.assertNotIn("installment", response.context["form"].initial)

    def test_edit_views_only_open_payments_of_their_direction(self):
        self.post_payment("10")
        self.post_payable_payment("10")
        receivable = Payment.objects.get(installment=self.installment)
        payable = Payment.objects.get(installment=self.payable_installment)
        edit = "accounts:payment_edit"
        payable_edit = "accounts:payable_payment_edit"
        self.assertEqual(self.client.get(reverse(edit, args=[receivable.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse(edit, args=[payable.pk])).status_code, 404)
        response = self.client.get(reverse(payable_edit, args=[payable.pk]))
        self.assertContains(response, 'value="Aluguel outubro - 1ª parcela')
        self.assertEqual(
            self.client.get(reverse(payable_edit, args=[receivable.pk])).status_code, 404
        )

    def test_payable_lookup_searches_supplier_installments(self):
        url = reverse("accounts:payable_installment_lookup")
        for q in ("imobiliária", "12345678"):
            response = self.client.get(url, {"q": q}, **HTMX)
            self.assertContains(response, f'data-pk="{self.payable_installment.pk}"')
            self.assertContains(response, "Imobiliária Centro")
        response = self.client.get(url, {"q": "outubro"}, **HTMX)
        self.assertNotContains(response, f'data-pk="{self.installment.pk}"')

    def test_list_filters_by_direction_and_method(self):
        self.post_payment("10")
        url = reverse("accounts:payment_list")
        response = self.client.get(url, {"direction": "R", "method": "PIX"}, **HTMX)
        self.assertTemplateUsed(response, "payments/partials/payment_table.html")
        self.assertContains(response, "Mensalidade outubro")
        response = self.client.get(url, {"direction": "P"}, **HTMX)
        self.assertNotContains(response, "Mensalidade outubro")
        response = self.client.get(url, {"method": "DIN"}, **HTMX)
        self.assertNotContains(response, "Mensalidade outubro")


class InstallmentViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        income = AccountType.objects.create(
            name="Mensalidade", direction=Direction.RECEIVABLE
        )
        expense = AccountType.objects.create(name="Aluguel", direction=Direction.PAYABLE)
        cls.receivable = AccountReceivable.objects.create(
            description="Mensalidade João", category=income, gross_value=Decimal(200)
        )
        cls.payable = AccountPayable.objects.create(
            description="Aluguel sede", category=expense, gross_value=Decimal(500)
        )
        today = timezone.localdate()
        cls.overdue = cls.receivable.installments.create(
            number=1, due_date=today - timedelta(days=5), amount=Decimal(100)
        )
        cls.future = cls.receivable.installments.create(
            number=2, due_date=today + timedelta(days=25), amount=Decimal(100)
        )
        cls.rent = cls.payable.installments.create(
            number=1, due_date=today + timedelta(days=3), amount=Decimal(500)
        )
        Payment.objects.create(
            installment=cls.rent,
            amount=Decimal(210),
            penalty=Decimal(10),
            method="PIX",
        )

    def test_create_assigns_next_number_when_blank(self):
        response = self.client.post(
            reverse("accounts:installment_add"),
            {
                "account": self.receivable.pk,
                "number": "",
                "due_date": timezone.localdate().isoformat(),
                "amount": "50.00",
            },
        )
        self.assertRedirects(response, reverse("accounts:installment_list"))
        self.assertTrue(self.receivable.installments.filter(number=3).exists())

    def test_create_rejects_duplicate_number(self):
        response = self.client.post(
            reverse("accounts:installment_add"),
            {
                "account": self.receivable.pk,
                "number": "1",
                "due_date": timezone.localdate().isoformat(),
                "amount": "50.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.receivable.installments.count(), 2)

    def test_add_prefills_from_account_param(self):
        response = self.client.get(
            reverse("accounts:installment_add"), {"account": self.payable.pk}
        )
        self.assertEqual(response.context["form"].initial["account"], self.payable)

    def test_list_annotates_outstanding_and_totals(self):
        response = self.client.get(reverse("accounts:installment_list"))
        rows = {i.pk: i for i in response.context["installments"]}
        self.assertEqual(rows[self.rent.pk].outstanding, Decimal(300))
        self.assertEqual(rows[self.rent.pk].outstanding, self.rent.balance())
        totals = response.context["totals"]
        self.assertEqual(totals["receivable_outstanding"], Decimal(200))
        self.assertEqual(totals["payable_outstanding"], Decimal(300))
        self.assertIsNone(totals["payable_paid"])

    def test_list_totals_paid_installments(self):
        Payment.objects.create(
            installment=self.overdue, amount=Decimal(100), method="PIX"
        )
        response = self.client.get(reverse("accounts:installment_list"))
        totals = response.context["totals"]
        self.assertEqual(totals["receivable_paid"], Decimal(100))
        self.assertIsNone(totals["payable_paid"])
        self.assertContains(response, "Recebido")

    def test_list_filters_and_search_return_partial(self):
        url = reverse("accounts:installment_list")
        response = self.client.get(url, {"status": "overdue"}, **HTMX)
        self.assertTemplateUsed(
            response, "installments/partials/installment_table.html"
        )
        self.assertEqual(list(response.context["installments"]), [self.overdue])
        response = self.client.get(url, {"direction": "P"}, **HTMX)
        self.assertEqual(list(response.context["installments"]), [self.rent])
        response = self.client.get(url, {"status": "P"}, **HTMX)
        self.assertEqual(list(response.context["installments"]), [self.rent])
        response = self.client.get(url, {"q": "joão"}, **HTMX)
        self.assertEqual(
            list(response.context["installments"]), [self.overdue, self.future]
        )


class SupplierViewsTests(LoggedInTestCase):
    def test_crud(self):
        response = self.client.post(
            reverse("accounts:supplier_add"),
            {"name": "Papelaria Central", "document": "12345678000190"},
        )
        self.assertRedirects(response, reverse("accounts:supplier_list"))
        supplier = Supplier.objects.get()

        response = self.client.post(
            reverse("accounts:supplier_edit", args=[supplier.pk]),
            {"name": "Papelaria Centro", "document": "12345678000190"},
        )
        self.assertRedirects(response, reverse("accounts:supplier_list"))
        supplier.refresh_from_db()
        self.assertEqual(supplier.name, "Papelaria Centro")

        response = self.client.get(
            reverse("accounts:supplier_list"), {"q": "centro"}, **HTMX
        )
        self.assertTemplateUsed(response, "suppliers/partials/supplier_table.html")
        self.assertContains(response, "Papelaria Centro")

        self.client.post(reverse("accounts:supplier_delete", args=[supplier.pk]))
        self.assertFalse(Supplier.objects.exists())

    def test_document_must_be_cpf_or_cnpj_digits(self):
        for document in ("12.345.678/0001-90", "123"):
            response = self.client.post(
                reverse("accounts:supplier_add"),
                {"name": "Papelaria", "document": document},
            )
            self.assertEqual(response.status_code, 200)
        self.assertFalse(Supplier.objects.exists())

    def test_delete_blocked_when_supplier_has_accounts(self):
        supplier = Supplier.objects.create(name="Imobiliária")
        AccountPayable.objects.create(
            description="Aluguel",
            category=AccountType.objects.create(
                name="Aluguel", direction=Direction.PAYABLE
            ),
            supplier=supplier,
            gross_value=Decimal(100),
        )
        response = self.client.post(
            reverse("accounts:supplier_delete", args=[supplier.pk])
        )
        self.assertRedirects(response, reverse("accounts:supplier_list"))
        self.assertTrue(Supplier.objects.filter(pk=supplier.pk).exists())


class AccountTypeViewsTests(LoggedInTestCase):
    def test_crud_and_filter(self):
        response = self.client.post(
            reverse("accounts:account_type_add"), {"name": "Material", "direction": "P"}
        )
        self.assertRedirects(response, reverse("accounts:account_type_list"))
        category = AccountType.objects.get()

        self.client.post(
            reverse("accounts:account_type_edit", args=[category.pk]),
            {"name": "Material escolar", "direction": "P"},
        )
        category.refresh_from_db()
        self.assertEqual(category.name, "Material escolar")

        url = reverse("accounts:account_type_list")
        self.assertContains(self.client.get(url, {"direction": "P"}, **HTMX), "Material")
        self.assertNotContains(
            self.client.get(url, {"direction": "R"}, **HTMX), "Material"
        )

        self.client.post(reverse("accounts:account_type_delete", args=[category.pk]))
        self.assertFalse(AccountType.objects.exists())

    def test_in_use_category_keeps_direction_and_is_protected(self):
        category = AccountType.objects.create(
            name="Mensalidade", direction=Direction.RECEIVABLE
        )
        AccountReceivable.objects.create(
            description="Mensalidade", category=category, gross_value=Decimal(100)
        )
        self.client.post(
            reverse("accounts:account_type_edit", args=[category.pk]),
            {"name": "Mensalidades", "direction": "P"},
        )
        category.refresh_from_db()
        self.assertEqual(category.name, "Mensalidades")
        self.assertEqual(category.direction, Direction.RECEIVABLE)

        self.client.post(reverse("accounts:account_type_delete", args=[category.pk]))
        self.assertTrue(AccountType.objects.filter(pk=category.pk).exists())
