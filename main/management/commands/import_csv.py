from django.core.management.base import BaseCommand, CommandError

from main.lib.phone import format_e164
from main.models import Member, MemberStatusType

import csv
import sys


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--it-is-during-the-database-import', action='store_true')

    def handle(self, *args, **options):
        if not options['it_is_during_the_database_import']:
            print("This should only be run once, when importing the database.")
            sys.exit(1)

        with open('in.csv', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                #print(', '.join(row))
                r=row[0]
                if r.isnumeric():
                    if int(r) < 10:
                        r = 'R0' + r
                    else:
                        r = 'R' + r
                last=row[1]
                first=row[2]
                address=row[4]
                home=row[5]
                work=row[6]
                cell=row[7]
                email=row[8]
                emp=row[9]
                status=row[11]
                print('{} {} {}'.format(first, last, status))
                s,cs = MemberStatusType.objects.get_or_create(
                    short=status,
                    defaults={'long':status})
                member_defaults = {
                    'first_name':first,
                    'last_name':last,
                    'profile_email':'{}@example.com'.format(r.lower()),
                    'status':s,
                    'v9':emp,
                }
                m,cm = Member.objects.get_or_create(
                    username=r,
                    defaults=member_defaults)
                m.profile_email = '{}@example.com'.format(r.lower())
                m.save()
                if not cm:
                    for attr, value in member_defaults.items(): 
                        setattr(m, attr, value)
                    m.save()
                # if address:
                #     m.address_set.get_or_create(
                #         type='Home',
                #         address1=address,
                #         city='',state='',zip='')
                m.email_set.get_or_create(
                    type='Home',
                    address=email,
                    defaults={'pagable':False})
                if home:
                    m.phone_set.get_or_create(
                        type='Home',
                        number=format_e164(home),
                        defaults={'pagable':False})
                if work:
                    m.phone_set.get_or_create(
                        type='Work',
                        number=format_e164(work),
                        defaults={'pagable':False})
                if cell:
                    m.phone_set.get_or_create(
                        type='Mobile',
                        number=format_e164(cell),
                        defaults={'pagable':False})
