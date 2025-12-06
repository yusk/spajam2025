import re

import requests
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import GithubToken
from main.serializers import (
    GitHubLanguagesResponseSerializer,
    GitHubCallbackErrorSerializer,
)


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
            return Response(
                {"error": "GitHub token not found or expired. Please re-authenticate with GitHub."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = github_token.access_token

        # Fetch all repositories with pagination
        repos, error = fetch_all_repos(access_token)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Aggregate language count from repo's primary language
        language_count = {}
        for repo in repos:
            language = repo.get("language")
            if language:
                language_count[language] = language_count.get(language, 0) + 1

        # Build response
        total_repos = sum(language_count.values())
        languages = []
        for lang, count in sorted(language_count.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_repos * 100) if total_repos > 0 else 0
            languages.append({
                "name": lang,
                "count": count,
                "percentage": round(percentage, 1),
            })

        return Response({
            "total_repos": len(repos),
            "languages": languages,
        })
