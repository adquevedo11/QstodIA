from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dojo', '0299_securityconcept'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExecutiveReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('classification', models.CharField(
                    choices=[
                        ('Confidencial', 'Confidencial'),
                        ('Interno', 'Interno'),
                        ('Público', 'Público'),
                    ],
                    default='Confidencial',
                    max_length=50,
                )),
                ('analyst_name', models.CharField(blank=True, max_length=300)),
                ('analyst_title', models.CharField(blank=True, max_length=300)),
                ('executive_summary', models.TextField(blank=True)),
                ('recommendations', models.TextField(blank=True)),
                ('next_steps', models.TextField(blank=True)),
                ('conclusion', models.TextField(blank=True)),
                ('sections', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='executive_reports',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('engagements', models.ManyToManyField(
                    blank=True,
                    related_name='executive_reports',
                    to='dojo.engagement',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='executive_reports',
                    to='dojo.product',
                )),
            ],
            options={
                'verbose_name': 'Informe Ejecutivo',
                'verbose_name_plural': 'Informes Ejecutivos',
                'ordering': ['-created_at'],
            },
        ),
    ]
