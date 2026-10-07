from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dojo', '0298_risk_acceptance_restore_verified_expired'),
    ]

    operations = [
        migrations.CreateModel(
            name='SecurityConcept',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(blank=True, max_length=100, verbose_name='Referencia')),
                ('title', models.CharField(max_length=500, verbose_name='Título')),
                ('client', models.CharField(blank=True, max_length=300, verbose_name='Cliente')),
                ('scope', models.CharField(blank=True, max_length=500, verbose_name='Alcance')),
                ('context_text', models.TextField(blank=True, verbose_name='Contexto')),
                ('analysis', models.TextField(blank=True, verbose_name='Análisis')),
                ('risk_level', models.CharField(
                    choices=[('Crítico', 'Crítico'), ('Alto', 'Alto'), ('Medio', 'Medio'), ('Bajo', 'Bajo'), ('Aceptable', 'Aceptable')],
                    default='Medio', max_length=50, verbose_name='Nivel de riesgo')),
                ('conclusion', models.TextField(blank=True, verbose_name='Conclusión')),
                ('analyst_name', models.CharField(blank=True, max_length=300, verbose_name='Analista')),
                ('analyst_title', models.CharField(blank=True, max_length=300, verbose_name='Cargo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='security_concepts',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('findings', models.ManyToManyField(
                    blank=True,
                    related_name='security_concepts',
                    to='dojo.finding',
                    verbose_name='Hallazgos',
                )),
            ],
            options={
                'verbose_name': 'Concepto de Seguridad',
                'verbose_name_plural': 'Conceptos de Seguridad',
                'ordering': ['-created_at'],
            },
        ),
    ]
