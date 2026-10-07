from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dojo', '0301_pentest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id',          models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',        models.CharField(max_length=100, unique=True, verbose_name='Actividad')),
                ('description', models.TextField(blank=True)),
                ('is_active',   models.BooleanField(default=True)),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Tipo de Actividad', 'verbose_name_plural': 'Tipos de Actividad'},
        ),
        migrations.CreateModel(
            name='HourPool',
            fields=[
                ('id',                  models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',                models.CharField(max_length=200, verbose_name='Nombre de la bolsa')),
                ('total_hours',         models.PositiveIntegerField(verbose_name='Horas totales')),
                ('alert_threshold_pct', models.PositiveIntegerField(default=20, verbose_name='Alerta al % restante')),
                ('valid_from',          models.DateField(verbose_name='Válida desde')),
                ('valid_until',         models.DateField(blank=True, null=True, verbose_name='Válida hasta')),
                ('status',              models.CharField(choices=[('active','Activa'),('depleted','Agotada'),('expired','Vencida'),('cancelled','Cancelada')], default='active', max_length=20, verbose_name='Estado')),
                ('notes',               models.TextField(blank=True, verbose_name='Notas')),
                ('created_at',          models.DateTimeField(auto_now_add=True)),
                ('created_by',          models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_hour_pools', to='dojo.Dojo_User')),
                ('product',             models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hour_pools', to='dojo.product')),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Bolsa de Horas', 'verbose_name_plural': 'Bolsas de Horas'},
        ),
        migrations.CreateModel(
            name='TimeEntry',
            fields=[
                ('id',              models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date',            models.DateField(verbose_name='Fecha')),
                ('hours',           models.PositiveIntegerField(verbose_name='Horas')),
                ('description',     models.TextField(blank=True, verbose_name='Descripción')),
                ('created_at',      models.DateTimeField(auto_now_add=True)),
                ('activity_type',   models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='dojo.activitytype', verbose_name='Actividad')),
                ('analyst',         models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='time_entries', to='dojo.Dojo_User')),
                ('pentest_project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='time_entries', to='dojo.pentestproject')),
                ('pool',            models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_entries', to='dojo.hourpool')),
            ],
            options={'ordering': ['-date', '-created_at'], 'verbose_name': 'Registro de Horas', 'verbose_name_plural': 'Registros de Horas'},
        ),
    ]
