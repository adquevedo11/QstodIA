from django.db import migrations


class Migration(migrations.Migration):
    # Merge migration: reconciles the old QustodIA migration chain (0249-0254)
    # with the renumbered chain (0299-0304). Both leaf nodes refer to the same
    # schema changes applied at different positions due to a renumbering.
    dependencies = [
        ('dojo', '0254_alter_activitytype_id_and_more'),
        ('dojo', '0304_alter_activitytype_id_and_more'),
    ]
    operations = []
