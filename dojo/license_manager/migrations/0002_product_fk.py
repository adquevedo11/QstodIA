"""
Cambia la FK de ClientLicense de Product_Type a Product.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("license_manager", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="clientlicense",
            name="product",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="license",
                to="dojo.product",
                verbose_name="Producto (activo) asociado",
            ),
        ),
        migrations.RemoveField(
            model_name="clientlicense",
            name="product_type",
        ),
    ]
