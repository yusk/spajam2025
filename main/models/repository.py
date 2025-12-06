from django.db import models


class UserRepository(models.Model):
    """ユーザーのGitHubリポジトリ"""
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="repositories")
    language = models.ForeignKey("Language", on_delete=models.SET_NULL, null=True, blank=True)

    # GitHub リポジトリ情報
    github_id = models.BigIntegerField()
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)  # owner/repo

    # 時系列用
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    pushed_at = models.DateTimeField(null=True, blank=True)

    # メタ情報（将来の重み付け用）
    stargazers_count = models.IntegerField(default=0)
    forks_count = models.IntegerField(default=0)
    is_fork = models.BooleanField(default=False)

    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "main_user_repository"
        unique_together = ["user", "github_id"]
        ordering = ["-pushed_at"]

    def __str__(self):
        return f"{self.full_name} ({self.language})"

    @classmethod
    def sync_from_github(cls, user, repos, Language):
        """GitHubから取得したリポジトリ情報を同期"""
        from django.utils.dateparse import parse_datetime

        synced_ids = []
        for repo in repos:
            github_id = repo.get("id")
            language_name = repo.get("language")
            language = None
            if language_name:
                language = Language.get_or_create_from_github(language_name)

            defaults = {
                "name": repo.get("name", ""),
                "full_name": repo.get("full_name", ""),
                "language": language,
                "created_at": parse_datetime(repo.get("created_at")),
                "updated_at": parse_datetime(repo.get("updated_at")),
                "pushed_at": parse_datetime(repo.get("pushed_at")) if repo.get("pushed_at") else None,
                "stargazers_count": repo.get("stargazers_count", 0),
                "forks_count": repo.get("forks_count", 0),
                "is_fork": repo.get("fork", False),
            }

            # Avoid update_or_create to prevent SAVEPOINT issues with MySQL
            try:
                obj = cls.objects.get(user=user, github_id=github_id)
                for key, value in defaults.items():
                    setattr(obj, key, value)
                obj.save()
            except cls.DoesNotExist:
                cls.objects.create(user=user, github_id=github_id, **defaults)

            synced_ids.append(github_id)

        # 削除されたリポジトリを削除
        cls.objects.filter(user=user).exclude(github_id__in=synced_ids).delete()

        return synced_ids
