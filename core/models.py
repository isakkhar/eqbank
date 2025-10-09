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


class QuestionPaper(models.Model):
    program_name = models.CharField(max_length=255)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    class_level = models.ForeignKey(ClassName, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subject)
    chapters = models.ManyToManyField(Chapter)
    # store selected questions for the paper
    questions = models.ManyToManyField('Question', blank=True)

    QUESTION_TYPES = [
        ('mcq', 'বহু নির্বাচনি'),
        ('creative', 'সৃজনশীল'),
        ('combined', 'সমন্বিত প্রশ্ন'),
    ]
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES)
    number_of_questions = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.program_name


class Question(models.Model):
    """Represents a single question in the bank. Designed to be simple and
    extensible for MCQ and descriptive types. Bulk uploads (CSV) will map
    to these fields.
    """
    QUESTION_TYPES = [
        ('mcq', 'বহু নির্বাচনি'),
        ('creative', 'সৃজনশীল'),
        ('short', 'সংক্ষিপ্ত উত্তর'),
    ]

    text = models.TextField(verbose_name='প্রশ্ন')
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPES, default='mcq')
    class_name = models.ForeignKey(ClassName, on_delete=models.CASCADE, related_name='questions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)

    # optional fields for MCQ
    option_a = models.CharField(max_length=1000, null=True, blank=True)
    option_b = models.CharField(max_length=1000, null=True, blank=True)
    option_c = models.CharField(max_length=1000, null=True, blank=True)
    option_d = models.CharField(max_length=1000, null=True, blank=True)
    correct_option = models.CharField(max_length=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        short = self.text[:75].replace('\n', ' ')
        return f"Q({self.id}) [{self.subject.name}] {short}"

    class Meta:
        verbose_name = 'প্রশ্ন'
        verbose_name_plural = 'প্রশ্ন সমূহ'
