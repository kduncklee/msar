# Generated by Django 3.2.16 on 2024-06-22 04:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0029_radio'),
    ]

    operations = [
        migrations.AddField(
            model_name='datafile',
            name='event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.event'),
        ),
    ]
