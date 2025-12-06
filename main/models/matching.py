from django.db import models
from django.db.models import Q
from django.utils import timezone


class MatchHistoryManager(models.Manager):
    def get_active_match(self, user):
        """Get user's current active match (not ended)."""
        today = timezone.now().date()
        return self.filter(
            Q(user1=user) | Q(user2=user),
            event_date=today,
            ended_at__isnull=True,
        ).first()

    def get_today_matched_users(self, user):
        """Get list of users that have been matched with today."""
        today = timezone.now().date()
        matches = self.filter(
            Q(user1=user) | Q(user2=user),
            event_date=today,
        )
        matched_user_ids = set()
        for match in matches:
            if match.user1_id == user.id:
                matched_user_ids.add(match.user2_id)
            else:
                matched_user_ids.add(match.user1_id)
        return matched_user_ids

    def get_free_users(self, exclude_user=None):
        """Get users who are not currently in an active match."""
        today = timezone.now().date()
        # Users with active matches (ended_at is null)
        active_matches = self.filter(
            event_date=today,
            ended_at__isnull=True,
        )
        busy_user_ids = set()
        for match in active_matches:
            busy_user_ids.add(match.user1_id)
            busy_user_ids.add(match.user2_id)

        from main.models import User
        queryset = User.objects.exclude(id__in=busy_user_ids)
        if exclude_user:
            queryset = queryset.exclude(id=exclude_user.id)
        return queryset


class MatchHistory(models.Model):
    """マッチング履歴"""
    user1 = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="matches_as_user1",
    )
    user2 = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="matches_as_user2",
    )
    similarity_score = models.FloatField()  # シンクロ度 (0.0 - 1.0)
    talk_duration = models.IntegerField()   # 話す時間（秒）
    matched_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    event_date = models.DateField()  # その日のイベント識別用

    objects = MatchHistoryManager()

    class Meta:
        db_table = "main_match_history"
        ordering = ["-matched_at"]

    def __str__(self):
        return f"Match: {self.user1} <-> {self.user2} ({self.similarity_score:.1%})"

    def get_partner(self, user):
        """Get the other user in this match."""
        if self.user1_id == user.id:
            return self.user2
        return self.user1

    def end_match(self):
        """End the match."""
        self.ended_at = timezone.now()
        self.save()

    @property
    def is_active(self):
        return self.ended_at is None
