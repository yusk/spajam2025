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


class Language(models.Model):
    """Programming language with icon information."""
    name = models.CharField(max_length=100, unique=True)
    icon_url = models.URLField(blank=True)
    color = models.CharField(max_length=7, blank=True)  # GitHub linguist color

    class Meta:
        db_table = "main_language"
        ordering = ["name"]

    @classmethod
    def get_devicon_url(cls, language_name):
        """Generate devicon URL for a language."""
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
                "icon_url": cls.get_devicon_url(language_name),
            }
        )
        return language

    def __str__(self):
        return self.name
