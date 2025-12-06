from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import Language, User, UserRepository


# テストユーザー設定（異なる言語傾向を持つユーザー）
SEED_USERS = [
    {
        "name": "Alice (Frontend)",
        "email": "alice@example.com",
        "repos": [
            {"name": "react-app", "language": "TypeScript"},
            {"name": "vue-project", "language": "Vue"},
            {"name": "next-blog", "language": "TypeScript"},
            {"name": "css-library", "language": "CSS"},
            {"name": "html-template", "language": "HTML"},
            {"name": "js-utils", "language": "JavaScript"},
        ],
    },
    {
        "name": "Bob (Backend Python)",
        "email": "bob@example.com",
        "repos": [
            {"name": "django-api", "language": "Python"},
            {"name": "flask-app", "language": "Python"},
            {"name": "fastapi-service", "language": "Python"},
            {"name": "ml-project", "language": "Python"},
            {"name": "data-analysis", "language": "Jupyter Notebook"},
        ],
    },
    {
        "name": "Charlie (Full Stack)",
        "email": "charlie@example.com",
        "repos": [
            {"name": "nextjs-app", "language": "TypeScript"},
            {"name": "django-backend", "language": "Python"},
            {"name": "react-components", "language": "JavaScript"},
            {"name": "api-server", "language": "Python"},
        ],
    },
    {
        "name": "Diana (Mobile)",
        "email": "diana@example.com",
        "repos": [
            {"name": "ios-app", "language": "Swift"},
            {"name": "android-app", "language": "Kotlin"},
            {"name": "flutter-app", "language": "Dart"},
            {"name": "react-native-app", "language": "TypeScript"},
        ],
    },
    {
        "name": "Eve (Systems)",
        "email": "eve@example.com",
        "repos": [
            {"name": "rust-cli", "language": "Rust"},
            {"name": "go-service", "language": "Go"},
            {"name": "c-library", "language": "C"},
            {"name": "cpp-engine", "language": "C++"},
        ],
    },
    {
        "name": "Frank (DevOps)",
        "email": "frank@example.com",
        "repos": [
            {"name": "terraform-infra", "language": "HCL"},
            {"name": "k8s-configs", "language": "Shell"},
            {"name": "ansible-playbooks", "language": "Shell"},
            {"name": "docker-images", "language": "Dockerfile"},
            {"name": "python-scripts", "language": "Python"},
        ],
    },
    {
        "name": "Grace (TypeScript)",
        "email": "grace@example.com",
        "repos": [
            {"name": "ts-monorepo", "language": "TypeScript"},
            {"name": "node-api", "language": "TypeScript"},
            {"name": "deno-app", "language": "TypeScript"},
            {"name": "nestjs-backend", "language": "TypeScript"},
            {"name": "angular-frontend", "language": "TypeScript"},
        ],
    },
    {
        "name": "Henry (Python)",
        "email": "henry@example.com",
        "repos": [
            {"name": "web-scraper", "language": "Python"},
            {"name": "automation-scripts", "language": "Python"},
            {"name": "django-cms", "language": "Python"},
            {"name": "pytest-plugins", "language": "Python"},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed test users and repositories for matching feature"

    def handle(self, *args, **options):
        now = timezone.now()
        created_users = []

        for user_data in SEED_USERS:
            # Create or get user
            user, created = User.objects.get_or_create(
                email=user_data["email"],
                defaults={
                    "name": user_data["name"],
                    "email_confirmed": True,
                },
            )
            if created:
                user.set_unusable_password()
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {user.name}"))
            else:
                self.stdout.write(f"User already exists: {user.name}")

            # Create repositories
            for i, repo_data in enumerate(user_data["repos"]):
                language = Language.get_or_create_from_github(repo_data["language"])

                repo, repo_created = UserRepository.objects.get_or_create(
                    user=user,
                    github_id=hash(f"{user.email}_{repo_data['name']}") % (10**9),
                    defaults={
                        "name": repo_data["name"],
                        "full_name": f"{user_data['name'].split()[0].lower()}/{repo_data['name']}",
                        "language": language,
                        "created_at": now,
                        "updated_at": now,
                        "pushed_at": now,
                        "stargazers_count": (i + 1) * 10,
                        "forks_count": i,
                        "is_fork": False,
                    },
                )
                if repo_created:
                    self.stdout.write(f"  - Created repo: {repo.name} ({language.name})")

            created_users.append(user)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Seed completed! {len(created_users)} users ready for matching."))
        self.stdout.write("")
        self.stdout.write("Expected similarity (high to low):")
        self.stdout.write("  - Alice <-> Grace: High (TypeScript)")
        self.stdout.write("  - Bob <-> Henry: High (Python)")
        self.stdout.write("  - Charlie <-> Alice/Grace: Medium (TypeScript + Python)")
        self.stdout.write("  - Diana <-> others: Low (Mobile specific)")
        self.stdout.write("  - Eve <-> others: Low (Systems specific)")
