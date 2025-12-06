import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.settings import api_settings

from main.env import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRETS
from main.models import User
from main.serializers import (
    GitHubCallbackErrorSerializer,
    GitHubCallbackResponseSerializer,
)

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


def _fetch_detailed_languages(access_token):
    """Backup: Fetch detailed language stats per repo (uses more API calls)."""
    repos_response = requests.get(
        "https://api.github.com/user/repos",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        },
        params={
            "per_page": 100,
            "sort": "updated",
        },
        timeout=30,
    )
    if repos_response.status_code == 200:
        repos = repos_response.json()
        print("=" * 60)
        print("Repositories and Languages (detailed)")
        print("=" * 60)

        total_language_bytes = {}

        for repo in repos:
            repo_name = repo.get("name")
            owner = repo.get("owner", {}).get("login")

            languages_response = requests.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/languages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30,
            )

            if languages_response.status_code == 200:
                languages = languages_response.json()
                print(f"\n[{repo_name}]")
                if languages:
                    for lang, bytes_count in languages.items():
                        print(f"  {lang}: {bytes_count:,} bytes")
                        total_language_bytes[lang] = total_language_bytes.get(lang, 0) + bytes_count
                else:
                    print("  (no languages detected)")

        print("\n" + "=" * 60)
        print("Total Language Statistics (bytes)")
        print("=" * 60)
        sorted_languages = sorted(total_language_bytes.items(), key=lambda x: x[1], reverse=True)
        total_bytes = sum(total_language_bytes.values())
        for lang, bytes_count in sorted_languages:
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            print(f"  {lang}: {bytes_count:,} bytes ({percentage:.1f}%)")
        print("=" * 60)


class GitHubCallbackView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description="GitHub OAuthコールバック。認証コードをJWTトークンに交換します。",
        manual_parameters=[
            openapi.Parameter(
                "code",
                openapi.IN_QUERY,
                description="GitHubから受け取った認証コード",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: GitHubCallbackResponseSerializer,
            400: GitHubCallbackErrorSerializer,
        },
    )
    def get(self, request):
        code = request.query_params.get("code")
        if not code:
            return Response(
                {"error": "Authorization code not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Exchange code for access token
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRETS,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )

        if token_response.status_code != 200:
            return Response(
                {"error": "Failed to obtain access token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            error = token_data.get("error_description", "Failed to obtain access token")
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Get user info from GitHub
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30,
        )

        if user_response.status_code != 200:
            return Response(
                {"error": "Failed to fetch user info from GitHub"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        github_user = user_response.json()
        github_id = github_user.get("id")
        github_login = github_user.get("login")
        github_email = github_user.get("email")

        # If email is not public, fetch from emails endpoint
        if not github_email:
            emails_response = requests.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30,
            )
            if emails_response.status_code == 200:
                emails = emails_response.json()
                primary_email = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                github_email = primary_email or (emails[0]["email"] if emails else None)

        if not github_email:
            return Response(
                {"error": "Could not retrieve email from GitHub"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch all repositories and aggregate languages
        repos_response = requests.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            params={
                "per_page": 100,
                "sort": "updated",
            },
            timeout=30,
        )
        if repos_response.status_code == 200:
            repos = repos_response.json()
            print("=" * 60)
            print("Repositories and Languages")
            print("=" * 60)

            # Aggregate language count from repo's primary language
            language_count = {}

            for repo in repos:
                repo_name = repo.get("name")
                language = repo.get("language")
                print(f"  {repo_name}: {language}")
                if language:
                    language_count[language] = language_count.get(language, 0) + 1

            # Print aggregated stats
            print("\n" + "=" * 60)
            print("Language Statistics (by repo count)")
            print("=" * 60)
            sorted_languages = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
            total_repos = sum(language_count.values())
            for lang, count in sorted_languages:
                percentage = (count / total_repos * 100) if total_repos > 0 else 0
                print(f"  {lang}: {count} repos ({percentage:.1f}%)")
            print("=" * 60)

        # Find or create user
        user = User.objects.filter(email=github_email).first()

        if not user:
            user = User.objects.create_user(
                email=github_email,
                password=None,
                name=github_login or f"github_{github_id}",
            )
            user.email_confirmed = True
            user.save()

        # Generate JWT token
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        return Response(
            {
                "token": token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                },
            }
        )
