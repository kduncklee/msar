# Generated by Django 3.2.16 on 2023-10-10 03:43

from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_auto_20231009_1915'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventNotificationsAvailable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('position', models.IntegerField(default=1, null=True)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['position'],
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='event',
            name='handling_unit',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalevent',
            name='handling_unit',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.CreateModel(
            name='HistoricalEvent_notifications_made',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('m2m_history_id', models.AutoField(primary_key=True, serialize=False)),
                ('event', models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.event')),
                ('eventnotificationsavailable', models.ForeignKey(blank=True, db_constraint=False, db_tablespace='', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.eventnotificationsavailable')),
                ('history', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, to='main.historicalevent')),
            ],
            options={
                'verbose_name': 'HistoricalEvent_notifications_made',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name='event',
            name='notifications_made',
            field=models.ManyToManyField(to='main.EventNotificationsAvailable'),
        ),
    ]
