from django.test import TestCase
from django.utils import timezone

from main.models import MatchHistory, User


class TestMatchHistory(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            name="User1",
            email="user1@test.com",
            password="password",
        )
        self.user2 = User.objects.create_user(
            name="User2",
            email="user2@test.com",
            password="password",
        )
        self.user3 = User.objects.create_user(
            name="User3",
            email="user3@test.com",
            password="password",
        )
        self.today = timezone.now().date()

    def test_str_representation(self):
        """__str__メソッドのテスト"""
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.75,
            talk_duration=600,
            event_date=self.today,
        )
        # User.__str__ returns email
        self.assertIn("user1@test.com", str(match))
        self.assertIn("user2@test.com", str(match))
        self.assertIn("75.0%", str(match))

    def test_get_partner_from_user1(self):
        """user1からpartnerを取得"""
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        partner = match.get_partner(self.user1)
        self.assertEqual(partner, self.user2)

    def test_get_partner_from_user2(self):
        """user2からpartnerを取得"""
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        partner = match.get_partner(self.user2)
        self.assertEqual(partner, self.user1)

    def test_end_match(self):
        """マッチを終了"""
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        self.assertIsNone(match.ended_at)
        self.assertTrue(match.is_active)

        match.end_match()

        self.assertIsNotNone(match.ended_at)
        self.assertFalse(match.is_active)

    def test_is_active_property(self):
        """is_activeプロパティ"""
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        self.assertTrue(match.is_active)

        match.ended_at = timezone.now()
        match.save()
        self.assertFalse(match.is_active)


class TestMatchHistoryManager(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            name="User1",
            email="user1@test.com",
            password="password",
        )
        self.user2 = User.objects.create_user(
            name="User2",
            email="user2@test.com",
            password="password",
        )
        self.user3 = User.objects.create_user(
            name="User3",
            email="user3@test.com",
            password="password",
        )
        self.user4 = User.objects.create_user(
            name="User4",
            email="user4@test.com",
            password="password",
        )
        self.today = timezone.now().date()

    def test_get_active_match_returns_match(self):
        """アクティブマッチを返す"""
        match = MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        result = MatchHistory.objects.get_active_match(self.user1)
        self.assertEqual(result, match)

        result = MatchHistory.objects.get_active_match(self.user2)
        self.assertEqual(result, match)

    def test_get_active_match_returns_none_when_ended(self):
        """終了済みマッチは返さない"""
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
            ended_at=timezone.now(),
        )
        result = MatchHistory.objects.get_active_match(self.user1)
        self.assertIsNone(result)

    def test_get_active_match_returns_none_when_no_match(self):
        """マッチがない場合はNone"""
        result = MatchHistory.objects.get_active_match(self.user1)
        self.assertIsNone(result)

    def test_get_today_matched_users(self):
        """今日マッチしたユーザーIDを取得"""
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user3,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
            ended_at=timezone.now(),
        )
        matched_ids = MatchHistory.objects.get_today_matched_users(self.user1)
        self.assertEqual(len(matched_ids), 2)
        self.assertIn(self.user2.id, matched_ids)
        self.assertIn(self.user3.id, matched_ids)
        self.assertNotIn(self.user4.id, matched_ids)

    def test_get_today_matched_users_excludes_other_days(self):
        """他の日のマッチは含まない"""
        from datetime import timedelta

        yesterday = self.today - timedelta(days=1)
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=yesterday,
        )
        matched_ids = MatchHistory.objects.get_today_matched_users(self.user1)
        self.assertEqual(len(matched_ids), 0)

    def test_get_free_users(self):
        """フリーユーザーを取得"""
        # user1とuser2がアクティブマッチ中
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
        )
        free_users = MatchHistory.objects.get_free_users()
        free_user_ids = set(free_users.values_list("id", flat=True))

        self.assertNotIn(self.user1.id, free_user_ids)
        self.assertNotIn(self.user2.id, free_user_ids)
        self.assertIn(self.user3.id, free_user_ids)
        self.assertIn(self.user4.id, free_user_ids)

    def test_get_free_users_with_exclude(self):
        """特定ユーザーを除外してフリーユーザーを取得"""
        free_users = MatchHistory.objects.get_free_users(exclude_user=self.user1)
        free_user_ids = set(free_users.values_list("id", flat=True))

        self.assertNotIn(self.user1.id, free_user_ids)
        self.assertIn(self.user2.id, free_user_ids)
        self.assertIn(self.user3.id, free_user_ids)
        self.assertIn(self.user4.id, free_user_ids)

    def test_get_free_users_includes_ended_match_users(self):
        """終了済みマッチのユーザーはフリー"""
        MatchHistory.objects.create(
            user1=self.user1,
            user2=self.user2,
            similarity_score=0.5,
            talk_duration=600,
            event_date=self.today,
            ended_at=timezone.now(),
        )
        free_users = MatchHistory.objects.get_free_users()
        free_user_ids = set(free_users.values_list("id", flat=True))

        self.assertIn(self.user1.id, free_user_ids)
        self.assertIn(self.user2.id, free_user_ids)
