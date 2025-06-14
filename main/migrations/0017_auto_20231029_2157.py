# Generated by Django 3.2.16 on 2023-10-30 04:57

from django.db import migrations, models
import django.db.models.deletion

def create_status(apps, schema_editor):
    TYPES = ( # current, available, pro, do, display
        ('TM', 'Technical Member', True, True, True, True, True, 1),
        ('FM', 'Field Member', True, True, True, True, True, 2),
        ('T', 'Trainee', True, True, True, True, True, 3),
        ('R', 'Reserve', True, False, False, False, True, 4),
        ('S', 'Support', True, True, True, True, True, 5),
        ('A', 'Associate', True, False, False, False, True, 6),
        ('G', 'Guest', False, False, False, False, True, 7),
        ('MA', 'Member Alum', False, False, False, False, True, 8),
        ('GA', 'Guest Alum', False, False, False, False, True, 9),
        ('MN', 'Member No-contact', False, False, False, False, False, 10),
        ('GN', 'Guest No-contact', False, False, False, False, False, 11),
        )
    MemberStatusType = apps.get_model('main', 'MemberStatusType')
    Member = apps.get_model('main', 'Member')
    HistoricalMember = apps.get_model('main', 'HistoricalMember')
    for t in TYPES:
        s,c = MemberStatusType.objects.get_or_create(
            short=t[0], long=t[1])
        s.is_current = t[2]
        s.is_available = t[3]
        s.is_pro_eligible = t[4]
        s.is_do_eligible = t[5]
        s.is_display = t[6]
        s.position = t[7]
        s.save()
    g = MemberStatusType.objects.get(short='G')
    g.is_default = True
    g.save()
    for m in Member.objects.all():
        m.status_fk = MemberStatusType.objects.get(short=m.status)
        m.save()
    for m in HistoricalMember.objects.all():
        m.status_fk = MemberStatusType.objects.get(short=m.status)
        m.save()

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_alter_inboundsms_body'),
    ]

    operations = [
        migrations.CreateModel(
            name='MemberStatusType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('position', models.IntegerField(default=1, null=True)),
                ('short', models.CharField(max_length=255)),
                ('long', models.CharField(max_length=255)),
                ('is_current', models.BooleanField(default=True)),
                ('is_available', models.BooleanField(default=True)),
                ('is_pro_eligible', models.BooleanField(default=True)),
                ('is_do_eligible', models.BooleanField(default=True)),
                ('is_display', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['position'],
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='historicalmember',
            name='status_fk',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.memberstatustype'),
        ),
        migrations.AddField(
            model_name='member',
            name='status_fk',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='main.memberstatustype'),
        ),
      migrations.RunPython(create_status),
    ]
