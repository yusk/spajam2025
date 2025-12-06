from django.db import models


# Mapping for languages that need special handling for devicon
DEVICON_NAME_MAP = {
    "C++": "cplusplus",
    "C#": "csharp",
    "Objective-C": "objectivec",
    "Objective-C++": "objectivec",
    "Vim Script": "vim",
    "Vim script": "vim",
    "VimL": "vim",
    "Shell": "bash",
    "Dockerfile": "docker",
    "Makefile": "cmake",
    "SCSS": "sass",
    "F#": "fsharp",
    "Visual Basic .NET": "visualbasic",
    "Jupyter Notebook": "jupyter",
    "PLpgSQL": "postgresql",
    "TSQL": "microsoftsqlserver",
    "HCL": "terraform",
    "Nix": "nixos",
}

# Languages that use Simple Icons instead of devicon (due to size issues)
SIMPLE_ICONS_LANGUAGES = {
    "CSS": "css3",
    "HTML": "html5",
}


class Language(models.Model):
    """Programming language with icon information."""
    name = models.CharField(max_length=100, unique=True)
    icon_url = models.URLField(blank=True)
    color = models.CharField(max_length=7, blank=True)  # GitHub linguist color

    class Meta:
        db_table = "main_language"
        ordering = ["name"]

    @classmethod
    def get_icon_url(cls, language_name):
        """Generate icon URL for a language."""
        # Use Simple Icons for problematic languages
        if language_name in SIMPLE_ICONS_LANGUAGES:
            slug = SIMPLE_ICONS_LANGUAGES[language_name]
            return f"https://cdn.simpleicons.org/{slug}"

        # Use devicon for everything else
        slug = DEVICON_NAME_MAP.get(language_name)
        if not slug:
            slug = language_name.lower().replace(" ", "").replace("#", "sharp")
        return f"https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{slug}/{slug}-original.svg"

    @classmethod
    def get_or_create_from_github(cls, language_name):
        """Get or create a Language from GitHub language name."""
        language, created = cls.objects.get_or_create(
            name=language_name,
            defaults={
                "icon_url": cls.get_icon_url(language_name),
            }
        )
        return language

    def __str__(self):
        return self.name
