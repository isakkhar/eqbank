# file: core/models.py

from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    division = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    thana = models.CharField(max_length=100) # নতুন ফিল্ড যোগ করা হয়েছে

    def __str__(self):
        return f'{self.user.username} Profile'