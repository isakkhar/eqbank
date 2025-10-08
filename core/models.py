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
    class Meta:
        verbose_name = "প্রোফাইল"
        verbose_name_plural = "প্রোফাইল সমূহ"

class ClassName(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="ক্লাসের নাম")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "ক্লাস"
        verbose_name_plural = "ক্লাস সমূহ"

# বিষয় (যেমন: পদার্থবিজ্ঞান, গণিত)
class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="বিষয়ের নাম")
    class_name = models.ForeignKey(ClassName, on_delete=models.CASCADE, related_name='subjects', verbose_name="ক্লাস")

    def __str__(self):
        return f"{self.name} - {self.class_name.name}"

    class Meta:
        verbose_name = "বিষয়"
        verbose_name_plural = "বিষয়সমূহ"

# অধ্যায়
class Chapter(models.Model):
    name = models.CharField(max_length=200, verbose_name="অধ্যায়ের নাম")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters', verbose_name="বিষয়")

    def __str__(self):
        return f"{self.name} ({self.subject.name})"

    class Meta:
        verbose_name = "অধ্যায়"
        verbose_name_plural = "অধ্যায়সমূহ"