from django.db import models
from .base import BaseModel


class AccessCode(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)  # Access code value (e.g. "4821#", "Keybox 2")
    notes = models.TextField(blank=True, null=True)
    last_verified_at = models.DateTimeField(blank=True, null=True)
    verified_good = models.BooleanField(default=True)
    keywords = models.TextField(blank=True, null=True)  # Optional search keywords

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} ({self.code})"


class AccessCodeLocation(models.Model):
    access_code = models.ForeignKey(
        AccessCode,
        related_name='locations',
        on_delete=models.CASCADE
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    label = models.CharField(max_length=255, blank=True, null=True)  # e.g., "North Gate"

    def __str__(self):
        return f"{self.access_code.name} - ({self.latitude}, {self.longitude})"
