# Generated by Django 4.2.6 on 2024-12-29 07:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0039_alter_cert_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='OperationTypesAvailable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('position', models.IntegerField(default=1, null=True)),
                ('name', models.CharField(max_length=255)),
                ('enabled', models.BooleanField(default=True)),
                ('icon', models.CharField(blank=True, max_length=255)),
                ('color', models.CharField(blank=True, default=None, max_length=15, null=True)),
            ],
            options={
                'ordering': ['position'],
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='event',
            name='operation_type_fk',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='main.operationtypesavailable'),
        ),
        migrations.AddField(
            model_name='historicalevent',
            name='operation_type_fk',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.operationtypesavailable'),
        ),
    ]
