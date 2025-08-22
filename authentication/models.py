from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    google_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    profile_picture = models.URLField(null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email or self.username
    
    