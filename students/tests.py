from django.db import IntegrityError
from django.urls import reverse

from base.testing import LoggedInTestCase
from students.models import Guardian, GuardianAssociation, Relationship, Student


class FinancialGuardianTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )
        cls.mother = Guardian.objects.create(
            name="Maria Souza", cpf="00275010198", rg="7654321", issuing_authority="SSP"
        )
        cls.father = Guardian.objects.create(
            name="João Souza", cpf="11122233344", rg="7654322", issuing_authority="SSP"
        )

    def post_data(self, *financial, self_financial=False):
        data = {
            "name": self.student.name,
            "cpf": self.student.cpf,
            "rg": self.student.rg,
            "issuing_authority": self.student.issuing_authority,
            "guardians-TOTAL_FORMS": "2",
            "guardians-INITIAL_FORMS": "0",
        }
        if self_financial:
            data["is_self_financial"] = "on"
        for i, guardian in enumerate((self.mother, self.father)):
            data[f"guardians-{i}-guardian"] = guardian.pk
            data[f"guardians-{i}-relationship"] = Relationship.MOTHER
            if guardian in financial:
                data[f"guardians-{i}-is_financial"] = "on"
        return data

    def post(self, data):
        return self.client.post(
            reverse("students:student_edit", args=[self.student.pk]), data
        )

    def test_rejects_two_financial_guardians(self):
        response = self.post(self.post_data(self.mother, self.father))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apenas um responsável pode ser")
        self.assertFalse(GuardianAssociation.objects.exists())

    def test_rejects_financial_guardian_when_student_is_self_financial(self):
        response = self.post(self.post_data(self.mother, self_financial=True))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "próprio responsável financeiro")

    def test_requires_a_financial_payer(self):
        response = self.post(self.post_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marque um responsável financeiro")

    def test_saves_self_financial_student_without_financial_guardian(self):
        response = self.post(self.post_data(self_financial=True))
        self.assertRedirects(
            response, reverse("students:student_edit", args=[self.student.pk])
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.financial_payer, self.student)

    def test_saves_one_financial_guardian(self):
        response = self.post(self.post_data(self.mother))
        self.assertRedirects(
            response, reverse("students:student_edit", args=[self.student.pk])
        )
        self.assertEqual(self.student.financial_payer, self.mother)

    def test_database_allows_only_one_financial_guardian(self):
        GuardianAssociation.objects.create(
            student=self.student,
            guardian=self.mother,
            relationship=Relationship.MOTHER,
            is_financial=True,
        )
        with self.assertRaises(IntegrityError):
            GuardianAssociation.objects.create(
                student=self.student,
                guardian=self.father,
                relationship=Relationship.FATHER,
                is_financial=True,
            )


class WhatsAppLinkTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = Student.objects.create(
            name="Ana Souza",
            cpf="12345678901",
            rg="1234567",
            issuing_authority="SSP",
            mobile="61912345678",
        )
        cls.mother = Guardian.objects.create(
            name="Maria Souza",
            cpf="00275010198",
            rg="7654321",
            issuing_authority="SSP",
            mobile="62987654321",
        )
        cls.father = Guardian.objects.create(
            name="João Souza", cpf="11122233344", rg="7654322", issuing_authority="SSP"
        )
        for guardian in (cls.mother, cls.father):
            GuardianAssociation.objects.create(
                student=cls.student,
                guardian=guardian,
                relationship=Relationship.MOTHER,
            )

    def test_filter(self):
        from base.templatetags.ui import whatsapp

        self.assertEqual(whatsapp("(61) 91234-5678"), "5561912345678")
        self.assertEqual(whatsapp("(61) 3234-5678"), "556132345678")
        self.assertEqual(whatsapp("+55 61 91234-5678"), "5561912345678")
        self.assertEqual(whatsapp("91234-5678"), "")
        self.assertEqual(whatsapp(""), "")
        self.assertEqual(whatsapp(None), "")

    def test_edit_page_links_student_and_guardians_with_mobile(self):
        response = self.client.get(
            reverse("students:student_edit", args=[self.student.pk])
        )
        self.assertContains(response, "WhatsApp ((61) 91234-5678)")
        self.assertContains(response, "WhatsApp ((62) 98765-4321)")
        self.assertContains(
            response, 'href="https://web.whatsapp.com/send?phone=5561912345678"'
        )
        self.assertContains(
            response, 'href="https://web.whatsapp.com/send?phone=5562987654321"'
        )
        # the father has no mobile, so only two buttons
        self.assertContains(response, "web.whatsapp.com/send", count=2)

    def test_add_page_has_no_links(self):
        response = self.client.get(reverse("students:student_add"))
        self.assertNotContains(response, "web.whatsapp.com")


class PhoneDigitsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.guardian = Guardian.objects.create(
            name="Maria Souza", cpf="00275010198", rg="7654321", issuing_authority="SSP"
        )

    def post(self, **phones):
        data = {
            "name": self.guardian.name,
            "cpf": self.guardian.cpf,
            "rg": self.guardian.rg,
            "issuing_authority": self.guardian.issuing_authority,
            **phones,
        }
        return self.client.post(
            reverse("students:guardian_edit", args=[self.guardian.pk]), data
        )

    def test_filter(self):
        from base.templatetags.ui import phone

        self.assertEqual(phone("61998544554"), "(61) 99854-4554")
        self.assertEqual(phone("6132345678"), "(61) 3234-5678")
        self.assertEqual(phone("(61) 9985"), "(61) 9985")
        self.assertEqual(phone(None), "")

    def test_saves_masked_input_as_digits(self):
        self.post(phone="(61) 3234-5678", mobile="(61) 99854-4554")
        self.guardian.refresh_from_db()
        self.assertEqual(self.guardian.phone, "6132345678")
        self.assertEqual(self.guardian.mobile, "61998544554")

    def test_rejects_number_without_ddd(self):
        response = self.post(mobile="99854-4554")
        self.assertContains(response, "Informe DDD + número")
        self.guardian.refresh_from_db()
        self.assertEqual(self.guardian.mobile, "")
