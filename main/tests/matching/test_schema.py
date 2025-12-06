"""
Tests to verify that API responses match the Swagger schema definitions.
"""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from main.models import Language, MatchHistory, User, UserRepository


class SchemaValidationTestBase(TestCase):
    """Base class for schema validation tests."""

    def setUp(self):
        self.client = APIClient()
        self.python = Language.objects.create(name="Python")
        self.javascript = Language.objects.create(name="JavaScript")
        now = timezone.now()

        # User 1 - Python developer
        self.user1 = User.objects.create_user(
            name="User1",
            email="user1@test.com",
            password="password",
        )
        self.user1.github_icon_url = "https://avatars.githubusercontent.com/u/1"
        self.user1.save()
        UserRepository.objects.create(
            user=self.user1,
            language=self.python,
            github_id=100,
            name="repo1",
            full_name="user1/repo1",
            created_at=now,
            updated_at=now,
        )

        # User 2 - Python developer
        self.user2 = User.objects.create_user(
            name="User2",
            email="user2@test.com",
            password="password",
        )
        self.user2.github_icon_url = "https://avatars.githubusercontent.com/u/2"
        self.user2.save()
        UserRepository.objects.create(
            user=self.user2,
            language=self.python,
            github_id=200,
            name="repo2",
            full_name="user2/repo2",
            created_at=now,
            updated_at=now,
        )

    def assertHasKeys(self, data, keys, msg=None):
        """Assert that data has all specified keys."""
        for key in keys:
            self.assertIn(key, data, msg or f"Missing key: {key}")

    def assertFieldType(self, value, expected_type, field_name):
        """Assert that a field has the expected type."""
        if expected_type == "string":
            self.assertIsInstance(value, str, f"{field_name} should be string")
        elif expected_type == "integer":
            self.assertIsInstance(value, int, f"{field_name} should be integer")
        elif expected_type == "number":
            self.assertIsInstance(value, (int, float), f"{field_name} should be number")
        elif expected_type == "boolean":
            self.assertIsInstance(value, bool, f"{field_name} should be boolean")
        elif expected_type == "array":
            self.assertIsInstance(value, list, f"{field_name} should be array")
        elif expected_type == "object":
            self.assertIsInstance(value, dict, f"{field_name} should be object")
        elif expected_type == "null":
            self.assertIsNone(value, f"{field_name} should be null")
        elif expected_type == "string_or_null":
            self.assertTrue(
                value is None or isinstance(value, str),
                f"{field_name} should be string or null"
            )


class TestMatchingStatusSchema(SchemaValidationTestBase):
    """Test /api/matching/status/ response matches schema."""

    def test_status_free_schema(self):
        """MatchStatusSerializer schema when status is free."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # MatchStatusSerializer fields
        self.assertHasKeys(data, ["status", "match"])
        self.assertFieldType(data["status"], "string", "status")
        self.assertIn(data["status"], ["free", "talking"])
        self.assertIsNone(data["match"])

    def test_status_talking_schema(self):
        """MatchStatusSerializer schema when status is talking."""
        today = timezone.now().date()
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.85,
            talk_duration=600,
            event_date=today,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # MatchStatusSerializer fields
        self.assertHasKeys(data, ["status", "match"])
        self.assertEqual(data["status"], "talking")

        # MatchResultSerializer fields
        match = data["match"]
        self.assertHasKeys(match, [
            "id", "partner", "similarity_score", "talk_duration",
            "matched_at", "remaining_seconds", "matched_languages"
        ])
        self.assertFieldType(match["id"], "integer", "match.id")
        self.assertFieldType(match["similarity_score"], "number", "match.similarity_score")
        self.assertFieldType(match["talk_duration"], "integer", "match.talk_duration")
        self.assertFieldType(match["matched_at"], "string", "match.matched_at")
        self.assertFieldType(match["remaining_seconds"], "integer", "match.remaining_seconds")
        self.assertFieldType(match["matched_languages"], "array", "match.matched_languages")

        # MatchPartnerSerializer fields
        partner = match["partner"]
        self.assertHasKeys(partner, ["id", "name", "icon", "github_icon_url"])
        self.assertFieldType(partner["id"], "string", "partner.id")
        self.assertFieldType(partner["name"], "string", "partner.name")
        self.assertFieldType(partner["github_icon_url"], "string_or_null", "partner.github_icon_url")

        # MatchedLanguageSerializer fields (if any)
        for lang in match["matched_languages"]:
            self.assertHasKeys(lang, ["name", "icon_url"])
            self.assertFieldType(lang["name"], "string", "matched_languages[].name")
            self.assertFieldType(lang["icon_url"], "string", "matched_languages[].icon_url")


class TestMatchingCreateSchema(SchemaValidationTestBase):
    """Test POST /api/matching/ response matches schema."""

    def test_create_match_schema(self):
        """MatchResultSerializer schema on successful match creation."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # MatchResultSerializer fields
        self.assertHasKeys(data, [
            "id", "partner", "similarity_score", "talk_duration",
            "matched_at", "remaining_seconds", "matched_languages"
        ])
        self.assertFieldType(data["id"], "integer", "id")
        self.assertFieldType(data["similarity_score"], "number", "similarity_score")
        self.assertFieldType(data["talk_duration"], "integer", "talk_duration")
        self.assertFieldType(data["matched_at"], "string", "matched_at")
        self.assertFieldType(data["remaining_seconds"], "integer", "remaining_seconds")
        self.assertFieldType(data["matched_languages"], "array", "matched_languages")

        # MatchPartnerSerializer fields
        partner = data["partner"]
        self.assertHasKeys(partner, ["id", "name", "icon", "github_icon_url"])
        self.assertFieldType(partner["id"], "string", "partner.id")
        self.assertFieldType(partner["name"], "string", "partner.name")

        # MatchedLanguageSerializer fields
        for lang in data["matched_languages"]:
            self.assertHasKeys(lang, ["name", "icon_url"])
            self.assertFieldType(lang["name"], "string", "matched_languages[].name")
            self.assertFieldType(lang["icon_url"], "string", "matched_languages[].icon_url")

    def test_create_match_error_schema(self):
        """MatchErrorSerializer schema when no match available."""
        self.user2.delete()
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/")
        self.assertEqual(response.status_code, 404)
        data = response.json()

        # MatchErrorSerializer fields
        self.assertHasKeys(data, ["error"])
        self.assertFieldType(data["error"], "string", "error")


class TestMatchingEndSchema(SchemaValidationTestBase):
    """Test POST /api/matching/end/ response matches schema."""

    def test_end_match_schema(self):
        """MatchEndResponseSerializer schema on successful end."""
        today = timezone.now().date()
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.85,
            talk_duration=600,
            event_date=today,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/end/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # MatchEndResponseSerializer fields
        self.assertHasKeys(data, ["message"])
        self.assertFieldType(data["message"], "string", "message")

    def test_end_match_error_schema(self):
        """MatchErrorSerializer schema when no active match."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/end/")
        self.assertEqual(response.status_code, 404)
        data = response.json()

        # MatchErrorSerializer fields
        self.assertHasKeys(data, ["error"])
        self.assertFieldType(data["error"], "string", "error")


class TestMatchingHistorySchema(SchemaValidationTestBase):
    """Test GET /api/matching/history/ response matches schema."""

    def test_history_empty_schema(self):
        """MatchHistoryResponseSerializer schema when empty."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/history/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # MatchHistoryResponseSerializer fields
        self.assertHasKeys(data, ["history"])
        self.assertFieldType(data["history"], "array", "history")
        self.assertEqual(len(data["history"]), 0)

    def test_history_with_matches_schema(self):
        """MatchHistoryResponseSerializer schema with matches."""
        today = timezone.now().date()
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.85,
            talk_duration=600,
            event_date=today,
            ended_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/history/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # MatchHistoryResponseSerializer fields
        self.assertHasKeys(data, ["history"])
        self.assertFieldType(data["history"], "array", "history")
        self.assertGreater(len(data["history"]), 0)

        # MatchHistorySerializer fields
        match = data["history"][0]
        self.assertHasKeys(match, [
            "id", "partner", "similarity_score", "talk_duration",
            "matched_at", "ended_at"
        ])
        self.assertFieldType(match["id"], "integer", "history[].id")
        self.assertFieldType(match["similarity_score"], "number", "history[].similarity_score")
        self.assertFieldType(match["talk_duration"], "integer", "history[].talk_duration")
        self.assertFieldType(match["matched_at"], "string", "history[].matched_at")
        self.assertFieldType(match["ended_at"], "string_or_null", "history[].ended_at")

        # MatchPartnerSerializer fields
        partner = match["partner"]
        self.assertHasKeys(partner, ["id", "name", "icon", "github_icon_url"])
        self.assertFieldType(partner["id"], "string", "history[].partner.id")
        self.assertFieldType(partner["name"], "string", "history[].partner.name")


class TestUserGitHubSchema(SchemaValidationTestBase):
    """Test GET /api/users/{id}/github/ response matches schema."""

    def test_user_github_schema(self):
        """UserGitHubResponseSerializer schema."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/users/{self.user1.id}/github/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # UserGitHubResponseSerializer fields
        self.assertHasKeys(data, [
            "user_id", "user_name", "github_username",
            "github_icon_url", "total_repos", "languages"
        ])
        self.assertFieldType(data["user_id"], "string", "user_id")
        self.assertFieldType(data["user_name"], "string", "user_name")
        self.assertFieldType(data["github_username"], "string_or_null", "github_username")
        self.assertFieldType(data["github_icon_url"], "string_or_null", "github_icon_url")
        self.assertFieldType(data["total_repos"], "integer", "total_repos")
        self.assertFieldType(data["languages"], "array", "languages")

        # GitHubLanguageSerializer fields
        for lang in data["languages"]:
            self.assertHasKeys(lang, ["name", "icon_url", "count", "percentage"])
            self.assertFieldType(lang["name"], "string", "languages[].name")
            self.assertFieldType(lang["icon_url"], "string", "languages[].icon_url")
            self.assertFieldType(lang["count"], "integer", "languages[].count")
            self.assertFieldType(lang["percentage"], "number", "languages[].percentage")
