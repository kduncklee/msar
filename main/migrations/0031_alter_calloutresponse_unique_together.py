# Generated by Django 3.2.16 on 2024-06-26 02:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0030_datafile_event'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='calloutresponse',
            unique_together={('period', 'member')},
        ),
    ]
