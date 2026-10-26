"""
Registra ClientLicense en el estado de migraciones de license_manager.
La tabla dojo_clientlicense ya fue creada por dojo/0306_qustodia_v2;
aquí no se ejecutan operaciones de base de datos.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("dojo", "0306_qustodia_v2"),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ClientLicense",
                    fields=[
                        (
                            "id",
                            models.AutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "client_name",
                            models.CharField(
                                max_length=200, verbose_name="Nombre del cliente"
                            ),
                        ),
                        (
                            "product_type",
                            models.OneToOneField(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="license",
                                to="dojo.product_type",
                                verbose_name="Product Type asociado",
                            ),
                        ),
                        (
                            "is_active",
                            models.BooleanField(default=True, verbose_name="Activa"),
                        ),
                        (
                            "expires_at",
                            models.DateTimeField(verbose_name="Expira el"),
                        ),
                        (
                            "notes",
                            models.TextField(blank=True, verbose_name="Notas internas"),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "verbose_name": "Licencia de cliente",
                        "verbose_name_plural": "Licencias de clientes",
                        "db_table": "dojo_clientlicense",
                        "ordering": ["expires_at"],
                    },
                ),
            ],
            database_operations=[],  # tabla ya existe desde dojo 0306_qustodia_v2
        ),
    ]
