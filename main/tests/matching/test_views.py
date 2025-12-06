from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from main.models import Language, MatchHistory, User, UserRepository


class MatchingAPITestBase(TestCase):
    """Base class for matching API tests."""

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
        UserRepository.objects.create(
            user=self.user1,
            language=self.python,
            github_id=100,
            name="repo1",
            full_name="user1/repo1",
            created_at=now,
            updated_at=now,
        )

        # User 2 - Python developer (similar to user1)
        self.user2 = User.objects.create_user(
            name="User2",
            email="user2@test.com",
            password="password",
        )
        UserRepository.objects.create(
            user=self.user2,
            language=self.python,
            github_id=200,
            name="repo2",
            full_name="user2/repo2",
            created_at=now,
            updated_at=now,
        )

        # User 3 - JavaScript developer
        self.user3 = User.objects.create_user(
            name="User3",
            email="user3@test.com",
            password="password",
        )
        UserRepository.objects.create(
            user=self.user3,
            language=self.javascript,
            github_id=300,
            name="repo3",
            full_name="user3/repo3",
            created_at=now,
            updated_at=now,
        )


class TestMatchingStatusView(MatchingAPITestBase):
    def test_status_free_when_no_match(self):
        """マッチがない場合はfreeステータス"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "free")
        self.assertIsNone(data["match"])

    def test_status_talking_when_active_match(self):
        """アクティブマッチがある場合はtalkingステータス"""
        today = timezone.now().date()
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=1.0,
            talk_duration=600,
            event_date=today,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "talking")
        self.assertIsNotNone(data["match"])
        self.assertEqual(data["match"]["id"], match.id)
        self.assertEqual(data["match"]["partner"]["name"], "User2")

    def test_status_free_when_match_ended(self):
        """終了済みマッチの場合はfreeステータス"""
        today = timezone.now().date()
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=1.0,
            talk_duration=600,
            event_date=today,
            ended_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "free")

    def test_unauthenticated_returns_401(self):
        """未認証の場合は401"""
        response = self.client.get("/api/matching/status/")
        self.assertEqual(response.status_code, 401)


class TestMatchingCreateView(MatchingAPITestBase):
    def test_create_new_match(self):
        """新規マッチを作成"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("partner", data)
        self.assertIn("similarity_score", data)
        self.assertIn("talk_duration", data)

    def test_return_existing_match(self):
        """既存のアクティブマッチがある場合はそれを返す"""
        today = timezone.now().date()
        existing_match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=1.0,
            talk_duration=600,
            event_date=today,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], existing_match.id)

    def test_no_match_available(self):
        """マッチ相手がいない場合は404"""
        # Delete other users
        self.user2.delete()
        self.user3.delete()
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("error", data)

    def test_unauthenticated_returns_401(self):
        """未認証の場合は401"""
        response = self.client.post("/api/matching/")
        self.assertEqual(response.status_code, 401)


class TestMatchingEndView(MatchingAPITestBase):
    def test_end_active_match(self):
        """アクティブマッチを終了"""
        today = timezone.now().date()
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=1.0,
            talk_duration=600,
            event_date=today,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/end/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Match ended successfully")

        # Verify match is ended
        match.refresh_from_db()
        self.assertIsNotNone(match.ended_at)

    def test_no_active_match_returns_404(self):
        """アクティブマッチがない場合は404"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/matching/end/")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("error", data)

    def test_unauthenticated_returns_401(self):
        """未認証の場合は401"""
        response = self.client.post("/api/matching/end/")
        self.assertEqual(response.status_code, 401)


class TestMatchingHistoryView(MatchingAPITestBase):
    def test_empty_history(self):
        """履歴がない場合は空リスト"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/history/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["history"], [])

    def test_history_with_matches(self):
        """履歴がある場合はリストで返す"""
        today = timezone.now().date()
        match1 = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=1.0,
            talk_duration=600,
            event_date=today,
            ended_at=timezone.now(),
        )
        match2 = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user3,
            similarity_score=0.5,
            talk_duration=500,
            event_date=today,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/history/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["history"]), 2)

    def test_history_excludes_other_days(self):
        """他の日のマッチは含まない"""
        from datetime import timedelta

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Today's match
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=1.0,
            talk_duration=600,
            event_date=today,
        )
        # Yesterday's match
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user3,
            similarity_score=0.5,
            talk_duration=500,
            event_date=yesterday,
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/history/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["history"]), 1)

    def test_unauthenticated_returns_401(self):
        """未認証の場合は401"""
        response = self.client.get("/api/matching/history/")
        self.assertEqual(response.status_code, 401)


class TestMatchingDebugSimilarityView(MatchingAPITestBase):
    def setUp(self):
        super().setUp()
        # Check if debug endpoint is available by trying to resolve it
        from django.urls import resolve
        from django.urls.exceptions import Resolver404
        try:
            resolve("/api/matching/debug/similarity/")
            self.debug_available = True
        except Resolver404:
            self.debug_available = False

    def test_debug_similarity_response(self):
        """デバッグ類似度APIのレスポンス"""
        if not self.debug_available:
            self.skipTest("Debug endpoint not available")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/debug/similarity/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check current user info
        self.assertIn("current_user", data)
        self.assertEqual(data["current_user"]["name"], "User1")
        self.assertIn("languages", data["current_user"])

        # Check similarities
        self.assertIn("similarities", data)
        self.assertEqual(len(data["similarities"]), 2)  # user2 and user3

        # Each similarity should have required fields
        for sim in data["similarities"]:
            self.assertIn("user_id", sim)
            self.assertIn("user_name", sim)
            self.assertIn("similarity_score", sim)
            self.assertIn("similarity_percent", sim)
            self.assertIn("talk_duration_seconds", sim)
            self.assertIn("talk_duration_minutes", sim)
            self.assertIn("languages", sim)

    def test_similarity_sorted_descending(self):
        """類似度は降順でソート"""
        if not self.debug_available:
            self.skipTest("Debug endpoint not available")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/matching/debug/similarity/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        similarities = data["similarities"]
        scores = [s["similarity_score"] for s in similarities]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_unauthenticated_returns_401(self):
        """未認証の場合は401"""
        if not self.debug_available:
            self.skipTest("Debug endpoint not available")
        response = self.client.get("/api/matching/debug/similarity/")
        self.assertEqual(response.status_code, 401)
