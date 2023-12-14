import django.contrib.auth.forms
from main.models import Email, Member

class PasswordResetForm(django.contrib.auth.forms.PasswordResetForm):
    def get_users(self, email):
        emails = Email.objects.filter(address__iexact=email)
        users = set(Member.objects.filter(profile_email__iexact=email))
        users.update([e.member for e in emails])
        return [u for u in users if u.is_active and u.has_usable_password()]
