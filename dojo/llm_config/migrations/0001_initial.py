from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LLMConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Nombre")),
                ("provider", models.CharField(
                    choices=[
                        ("openai", "OpenAI (GPT-4o, GPT-4, etc.)"),
                        ("azure_openai", "Azure OpenAI"),
                        ("anthropic", "Anthropic (Claude)"),
                        ("gemini", "Google Gemini"),
                        ("ollama", "Ollama (auto-hospedado)"),
                    ],
                    max_length=20,
                    verbose_name="Proveedor",
                )),
                ("api_key", models.CharField(blank=True, max_length=500, verbose_name="API Key")),
                ("model_name", models.CharField(max_length=200, verbose_name="Modelo")),
                ("base_url", models.CharField(blank=True, max_length=500, verbose_name="URL base / Endpoint")),
                ("api_version", models.CharField(blank=True, max_length=50, verbose_name="Versión API")),
                ("deployment_name", models.CharField(blank=True, max_length=200, verbose_name="Nombre de deployment")),
                ("is_active", models.BooleanField(default=False, verbose_name="Activo")),
                ("notes", models.TextField(blank=True, verbose_name="Notas internas")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración LLM",
                "verbose_name_plural": "Configuraciones LLM",
                "db_table": "dojo_llmconfig",
                "ordering": ["-is_active", "name"],
            },
        ),
    ]
