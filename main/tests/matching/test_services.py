from django.test import TestCase
from django.utils import timezone

from main.models import Language, MatchHistory, User, UserRepository
from main.services.matching import (
    calculate_similarity,
    create_match,
    find_best_match,
    get_language_vector,
    get_talk_duration,
)


class TestGetLanguageVector(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            name="test_user",
            email="test@test.com",
            password="password",
        )
        self.python = Language.objects.create(name="Python")
        self.javascript = Language.objects.create(name="JavaScript")

    def test_empty_user(self):
        """ユーザーにリポジトリがない場合は空のベクトルを返す"""
        vector = get_language_vector(self.user)
        self.assertEqual(vector, {})

    def test_single_language(self):
        """1つの言語を持つ場合（pushed_atが今日なら重み≈1.0）"""
        now = timezone.now()
        UserRepository.objects.create(
            user=self.user,
            language=self.python,
            github_id=1,
            name="repo1",
            full_name="test/repo1",
            created_at=now,
            updated_at=now,
            pushed_at=now,
        )
        vector = get_language_vector(self.user)
        self.assertIn("Python", vector)
        self.assertAlmostEqual(vector["Python"], 1.0, places=1)

    def test_multiple_languages(self):
        """複数の言語を持つ場合（pushed_atが今日なら各≈1.0）"""
        now = timezone.now()
        UserRepository.objects.create(
            user=self.user,
            language=self.python,
            github_id=1,
            name="repo1",
            full_name="test/repo1",
            created_at=now,
            updated_at=now,
            pushed_at=now,
        )
        UserRepository.objects.create(
            user=self.user,
            language=self.python,
            github_id=2,
            name="repo2",
            full_name="test/repo2",
            created_at=now,
            updated_at=now,
            pushed_at=now,
        )
        UserRepository.objects.create(
            user=self.user,
            language=self.javascript,
            github_id=3,
            name="repo3",
            full_name="test/repo3",
            created_at=now,
            updated_at=now,
            pushed_at=now,
        )
        vector = get_language_vector(self.user)
        self.assertAlmostEqual(vector["Python"], 2.0, places=1)
        self.assertAlmostEqual(vector["JavaScript"], 1.0, places=1)


class TestSimilarity(TestCase):
    def test_identical_vectors(self):
        """同一ベクトルの類似度は1.0"""
        vec = {"Python": 3, "JavaScript": 2}
        similarity = calculate_similarity(vec, vec)
        self.assertAlmostEqual(similarity, 1.0, places=5)

    def test_orthogonal_vectors(self):
        """直交ベクトルの類似度は0.0（共通言語なし）"""
        vec1 = {"Python": 1}
        vec2 = {"JavaScript": 1}
        similarity = calculate_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 0.0, places=5)

    def test_partial_overlap(self):
        """部分的に重複するベクトル"""
        vec1 = {"Python": 2, "JavaScript": 1}
        vec2 = {"Python": 1, "TypeScript": 1}
        similarity = calculate_similarity(vec1, vec2)
        # 新しい計算式: sqrt(コサイン類似度 × ユークリッド距離の逆数)
        # コサイン類似度 ≈ 0.632
        # ユークリッド距離 = sqrt((2-1)² + (1-0)² + (0-1)²) = sqrt(3) ≈ 1.73
        # 逆数 = 1 / (1 + 1.73) ≈ 0.366
        # 最終 = sqrt(0.632 × 0.366) ≈ 0.48
        self.assertGreater(similarity, 0.3)
        self.assertLess(similarity, 0.7)

    def test_empty_vector(self):
        """空ベクトルの類似度は0.0"""
        vec1 = {}
        vec2 = {"Python": 1}
        self.assertEqual(calculate_similarity(vec1, vec2), 0.0)
        self.assertEqual(calculate_similarity(vec2, vec1), 0.0)
        self.assertEqual(calculate_similarity({}, {}), 0.0)


class TestGetTalkDuration(TestCase):
    def test_minimum_similarity(self):
        """類似度0.0の場合は最小時間（7分 = 420秒）"""
        duration = get_talk_duration(0.0)
        self.assertEqual(duration, 420)

    def test_maximum_similarity(self):
        """類似度1.0の場合は最大時間（15分 = 900秒）"""
        duration = get_talk_duration(1.0)
        self.assertEqual(duration, 900)

    def test_mid_similarity(self):
        """類似度0.5の場合は中間時間（11分 = 660秒）"""
        duration = get_talk_duration(0.5)
        self.assertEqual(duration, 660)


class TestFindBestMatch(TestCase):
    def setUp(self):
        self.python = Language.objects.create(name="Python")
        self.javascript = Language.objects.create(name="JavaScript")
        self.typescript = Language.objects.create(name="TypeScript")
        now = timezone.now()

        # Python専門のユーザー
        self.user_python = User.objects.create_user(
            name="Python Dev",
            email="python@test.com",
            password="password",
        )
        for i in range(3):
            UserRepository.objects.create(
                user=self.user_python,
                language=self.python,
                github_id=100 + i,
                name=f"py_repo{i}",
                full_name=f"python/py_repo{i}",
                created_at=now,
                updated_at=now,
            )

        # JavaScript専門のユーザー
        self.user_js = User.objects.create_user(
            name="JS Dev",
            email="js@test.com",
            password="password",
        )
        for i in range(3):
            UserRepository.objects.create(
                user=self.user_js,
                language=self.javascript,
                github_id=200 + i,
                name=f"js_repo{i}",
                full_name=f"js/js_repo{i}",
                created_at=now,
                updated_at=now,
            )

        # TypeScript専門のユーザー（JSに類似）
        self.user_ts = User.objects.create_user(
            name="TS Dev",
            email="ts@test.com",
            password="password",
        )
        for i in range(3):
            UserRepository.objects.create(
                user=self.user_ts,
                language=self.typescript,
                github_id=300 + i,
                name=f"ts_repo{i}",
                full_name=f"ts/ts_repo{i}",
                created_at=now,
                updated_at=now,
            )

        # Python + JSのフルスタックユーザー
        self.user_fullstack = User.objects.create_user(
            name="FullStack Dev",
            email="fullstack@test.com",
            password="password",
        )
        UserRepository.objects.create(
            user=self.user_fullstack,
            language=self.python,
            github_id=400,
            name="api",
            full_name="fullstack/api",
            created_at=now,
            updated_at=now,
        )
        UserRepository.objects.create(
            user=self.user_fullstack,
            language=self.javascript,
            github_id=401,
            name="frontend",
            full_name="fullstack/frontend",
            created_at=now,
            updated_at=now,
        )

    def test_find_best_match_for_python_user(self):
        """Pythonユーザーに最もマッチするのはフルスタックユーザー"""
        partner, similarity = find_best_match(self.user_python)
        self.assertEqual(partner, self.user_fullstack)
        self.assertGreater(similarity, 0)

    def test_find_best_match_for_js_user(self):
        """JSユーザーに最もマッチするのはフルスタックユーザー"""
        partner, similarity = find_best_match(self.user_js)
        self.assertEqual(partner, self.user_fullstack)
        self.assertGreater(similarity, 0)

    def test_no_match_when_all_busy(self):
        """全員がマッチ中の場合はマッチなし"""
        today = timezone.now().date()
        # 全員をマッチ中にする
        MatchHistory.objects.create(
            user1=self.user_js,
            user2=self.user_ts,
            similarity_score=0.5,
            talk_duration=600,
            event_date=today,
        )
        MatchHistory.objects.create(
            user1=self.user_fullstack,
            user2=User.objects.create_user(
                name="dummy", email="dummy@test.com", password="password"
            ),
            similarity_score=0.5,
            talk_duration=600,
            event_date=today,
        )
        partner, similarity = find_best_match(self.user_python)
        self.assertIsNone(partner)
        self.assertEqual(similarity, 0.0)

    def test_exclude_already_matched_today(self):
        """当日マッチ済みユーザーを除外"""
        today = timezone.now().date()
        # PythonとFullstackは既にマッチ済み（終了済み）
        MatchHistory.objects.create(
            user1=self.user_python,
            user2=self.user_fullstack,
            similarity_score=0.5,
            talk_duration=600,
            event_date=today,
            ended_at=timezone.now(),
        )
        partner, similarity = find_best_match(self.user_python)
        # フルスタックは除外されるのでJS or TSになる
        self.assertIn(partner, [self.user_js, self.user_ts])


class TestCreateMatch(TestCase):
    def setUp(self):
        self.python = Language.objects.create(name="Python")
        now = timezone.now()

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
        for i, user in enumerate([self.user1, self.user2]):
            UserRepository.objects.create(
                user=user,
                language=self.python,
                github_id=100 + i,
                name=f"repo{i}",
                full_name=f"user/repo{i}",
                created_at=now,
                updated_at=now,
            )

    def test_create_new_match(self):
        """新規マッチの作成"""
        match = create_match(self.user1)
        self.assertIsNotNone(match)
        self.assertEqual(match.user1, self.user1)
        self.assertEqual(match.user2, self.user2)
        self.assertIsNotNone(match.similarity_score)
        self.assertIsNotNone(match.talk_duration)

    def test_return_existing_active_match(self):
        """既存のアクティブマッチがある場合はそれを返す"""
        match1 = create_match(self.user1)
        match2 = create_match(self.user1)
        self.assertEqual(match1.id, match2.id)

    def test_no_match_when_alone(self):
        """他にユーザーがいない場合はNone"""
        self.user2.delete()
        match = create_match(self.user1)
        self.assertIsNone(match)
