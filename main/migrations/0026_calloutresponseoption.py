# Generated by Django 3.2.16 on 2023-11-07 05:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_patrol'),
    ]

    operations = [
        migrations.CreateModel(
            name='CalloutResponseOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('response', models.CharField(max_length=255)),
                ('is_attending', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
