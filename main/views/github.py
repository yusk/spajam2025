import re
from datetime import timedelta

import requests
from django.http import JsonResponse
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from main.models import GithubToken, Language, UserRepository

from main.serializers import (
    GitHubLanguagesResponseSerializer,
    GitHubCallbackErrorSerializer,
)

# Cache duration for repository sync
REPO_SYNC_CACHE_HOURS = 24


def fetch_all_repos(access_token):
    """Fetch all repositories with pagination support."""
    repos = []
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {
        "per_page": 100,
        "sort": "updated",
    }

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            return None, "Failed to fetch repositories from GitHub"

        repos.extend(response.json())

        # Parse Link header for next page
        url = None
        params = None  # params are included in the next URL
        link_header = response.headers.get("Link", "")
        for link in link_header.split(","):
            if 'rel="next"' in link:
                match = re.search(r"<([^>]+)>", link)
                if match:
                    url = match.group(1)
                break

    return repos, None


class UserGitHubLanguagesView(APIView):
    @swagger_auto_schema(
        operation_description="GitHubリポジトリの言語統計を取得します。",
        responses={
            200: GitHubLanguagesResponseSerializer,
            400: GitHubCallbackErrorSerializer,
        },
    )
    def get(self, request):
        user = request.user

        # Get valid GitHub token
        github_token = GithubToken.objects.get_valid_token(user)
        if not github_token:
            return JsonResponse(
                {"error": "GitHub token not found or expired. Please re-authenticate with GitHub."},
                status=400,
            )

        access_token = github_token.access_token

        # Check if we need to sync (cache for 24 hours)
        last_synced = user.repositories.order_by("-synced_at").values_list("synced_at", flat=True).first()
        needs_sync = (
            last_synced is None
            or last_synced < timezone.now() - timedelta(hours=REPO_SYNC_CACHE_HOURS)
        )

        if needs_sync:
            # Fetch all repositories with pagination
            repos, error = fetch_all_repos(access_token)
            if error:
                return JsonResponse({"error": error}, status=400)

            # Sync repositories to database
            UserRepository.sync_from_github(user, repos, Language)

        # Aggregate language count from saved repositories
        language_count = {}
        for repo in user.repositories.select_related("language").all():
            if repo.language:
                lang_name = repo.language.name
                language_count[lang_name] = language_count.get(lang_name, 0) + 1

        # Build response
        total_repos = sum(language_count.values())
        languages = []
        for lang_name, count in sorted(language_count.items(), key=lambda x: x[1], reverse=True):
            language = Language.objects.get(name=lang_name)
            percentage = (count / total_repos * 100) if total_repos > 0 else 0
            languages.append({
                "name": language.name,
                "icon_url": language.icon_url,
                "count": count,
                "percentage": round(percentage, 1),
            })

        return JsonResponse({
            "total_repos": user.repositories.count(),
            "languages": languages,
        })
