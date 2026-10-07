"""
Smoke tests for QustodIA custom models and their API endpoints.
Covers: SecurityConcept, ExecutiveReport, PentestProject/Finding/Evidence,
        HourPool/TimeEntry/ActivityType.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from dojo.models import (
    ActivityType,
    Dojo_User,
    Engagement,
    ExecutiveReport,
    HourPool,
    PentestFinding,
    PentestProject,
    PentestType,
    Product,
    Product_Type,
    SecurityConcept,
    TimeEntry,
)

PASSWORD = "testTEST1234!@#$"


class QustodIAModelTestCase(TestCase):
    """Base setup: product tree + staff user."""

    @classmethod
    def setUpTestData(cls):
        cls.product_type = Product_Type.objects.create(name="QA_pt_qustodia")
        cls.product = Product.objects.create(
            name="QA_product_qustodia", description="test", prod_type=cls.product_type,
        )
        cls.user = Dojo_User.objects.create_user(
            username="qustodia_test_user", password=PASSWORD, is_staff=True,
        )
        cls.engagement = Engagement.objects.create(
            name="QA_eng_qustodia",
            product=cls.product,
            target_start=date.today(),
            target_end=date.today(),
        )


class SecurityConceptModelTest(QustodIAModelTestCase):

    def test_create_security_concept(self):
        sc = SecurityConcept.objects.create(
            reference="SC-001",
            title="Test Concept",
            client="ACME Corp",
            risk_level="High",
            created_by=self.user,
        )
        self.assertEqual(str(sc.reference), "SC-001")
        self.assertEqual(sc.risk_level, "High")

    def test_security_concept_url_reverse(self):
        url = reverse("security_concept")
        self.assertTrue(url.startswith("/"))

    def test_security_concept_list_url(self):
        url = reverse("security_concept_list")
        self.assertTrue(url.startswith("/"))


class ExecutiveReportModelTest(QustodIAModelTestCase):

    def test_create_executive_report(self):
        er = ExecutiveReport.objects.create(
            title="Q3 2026 Report",
            product=self.product,
            classification="confidential",
            period_start=date.today(),
            period_end=date.today(),
            created_by=self.user,
        )
        self.assertEqual(er.title, "Q3 2026 Report")
        self.assertEqual(er.product, self.product)

    def test_executive_report_list_url(self):
        url = reverse("executive_report_list")
        self.assertTrue(url.startswith("/"))


class PentestModelTest(QustodIAModelTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pentest_type = PentestType.objects.create(name="Web Application")
        cls.project = PentestProject.objects.create(
            engagement=cls.engagement,
            title="QA Pentest Project",
            pentest_type=cls.pentest_type,
            start_date=date.today(),
            end_date=date.today(),
            status="in_progress",
        )

    def test_create_pentest_project(self):
        self.assertEqual(self.project.title, "QA Pentest Project")
        self.assertEqual(self.project.pentest_type.name, "Web Application")

    def test_create_pentest_finding(self):
        finding = PentestFinding.objects.create(
            project=self.project,
            title="XSS in login form",
            cvss_score=7.5,
            status="open",
        )
        self.assertEqual(finding.project, self.project)
        self.assertEqual(finding.cvss_score, 7.5)

    def test_pentest_list_url(self):
        url = reverse("pentest_list")
        self.assertTrue(url.startswith("/"))

    def test_pentest_detail_url(self):
        url = reverse("pentest_detail", kwargs={"pk": self.project.pk})
        self.assertTrue(url.startswith("/"))


class HourPoolModelTest(QustodIAModelTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity = ActivityType.objects.create(name="QA Assessment")
        cls.pool = HourPool.objects.create(
            product=cls.product,
            name="Q3 2026 Pool",
            total_hours=100,
            valid_from=date.today(),
            created_by=cls.user,
        )

    def test_create_hour_pool(self):
        self.assertEqual(self.pool.total_hours, 100)
        self.assertEqual(self.pool.product, self.product)

    def test_create_time_entry(self):
        entry = TimeEntry.objects.create(
            pool=self.pool,
            date=date.today(),
            hours=8,
            analyst=self.user,
            activity_type=self.activity,
        )
        self.assertEqual(entry.pool, self.pool)
        self.assertEqual(entry.hours, 8)

    def test_hour_pool_list_url(self):
        url = reverse("hour_pool_list")
        self.assertTrue(url.startswith("/"))


class PentestAPITest(QustodIAModelTestCase):
    """Basic API smoke tests for PentestProject endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pentest_type = PentestType.objects.create(name="API Test Type")
        cls.project = PentestProject.objects.create(
            engagement=cls.engagement,
            title="API Test Project",
            pentest_type=cls.pentest_type,
            start_date=date.today(),
            end_date=date.today(),
            status="in_progress",
        )
        cls.token = Token.objects.get_or_create(user=cls.user)[0]

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_pentest_project_list(self):
        response = self.client.get("/api/v2/pentests/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_pentest_project_detail(self):
        response = self.client.get(f"/api/v2/pentests/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "API Test Project")

    def test_pentest_type_list(self):
        response = self.client.get("/api/v2/pentests/types/")
        self.assertEqual(response.status_code, 200)

    def test_pentest_finding_list(self):
        response = self.client.get("/api/v2/pentests/findings/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_rejected(self):
        anon_client = APIClient()
        response = anon_client.get("/api/v2/pentests/projects/")
        self.assertIn(response.status_code, [401, 403])


class HourPoolAPITest(QustodIAModelTestCase):
    """Basic API smoke tests for HourPool endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.pool = HourPool.objects.create(
            product=cls.product,
            name="API Pool",
            total_hours=50,
            valid_from=date.today(),
            created_by=cls.user,
        )
        cls.token = Token.objects.get_or_create(user=cls.user)[0]

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_hour_pool_list(self):
        response = self.client.get("/api/v2/hour-pools/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_hour_pool_detail_has_usage(self):
        response = self.client.get(f"/api/v2/hour-pools/{self.pool.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("used_hours", response.data)
        self.assertIn("remaining_hours", response.data)
        self.assertIn("usage_pct", response.data)

    def test_unauthenticated_rejected(self):
        anon_client = APIClient()
        response = anon_client.get("/api/v2/hour-pools/")
        self.assertIn(response.status_code, [401, 403])
