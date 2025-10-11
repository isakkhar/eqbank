# file: core/models.py

from django.db import models
from django.contrib.auth.models import User
from smart_selects.db_fields import ChainedForeignKey, ChainedManyToManyField


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

    # এখানে ChainedManyToManyField ব্যবহার করা হয়েছে
    subjects = ChainedManyToManyField(
        Subject,
        chained_field="class_level",  # এই ফিল্ডটি class_level-এর উপর নির্ভরশীল
        chained_model_field="class_name",  # Subject মডেলের class_name ফিল্ডের সাথে মিলবে
        horizontal=True,
    )
    # অধ্যায়ের জন্যও একই কাজ করা হয়েছে
    chapters = ChainedManyToManyField(
        Chapter,
        chained_field="subjects",  # এই ফিল্ডটি subjects-এর উপর নির্ভরশীল
        chained_model_field="subject",  # Chapter মডেলের subject ফিল্ডের সাথে মিলবে
        horizontal=True,
    )
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
    # ... আগের ফিল্ডগুলো ...
    text = models.TextField(verbose_name='প্রশ্ন')
    question_type = models.CharField(max_length=50, choices=[('mcq', 'বহু নির্বাচনি'), ('creative', 'সৃজনশীল'),
                                                             ('short', 'সংক্ষিপ্ত উত্তর')], default='mcq')

    class_name = models.ForeignKey(ClassName, on_delete=models.CASCADE, related_name='questions')

    # ForeignKey-এর পরিবর্তে ChainedForeignKey ব্যবহার করুন
    subject = ChainedForeignKey(
        Subject,
        chained_field="class_name",  # এই মডেলের কোন ফিল্ডের উপর নির্ভরশীল (class_name)
        chained_model_field="class_name",  # Subject মডেলের কোন ফিল্ডের সাথে মিলবে (class_name)
        show_all=False,  # শুধুমাত্র ফিল্টার করা ফলাফল দেখাবে
        auto_choose=True,  # যদি একটি মাত্র অপশন থাকে, তবে নিজে থেকেই সিলেক্ট হবে
        sort=True,  # অপশনগুলো সাজিয়ে দেখাবে
        on_delete=models.CASCADE,
        related_name='questions'
    )

    # অধ্যায়ের জন্যও একই কাজ করুন
    chapter = ChainedForeignKey(
        Chapter,
        chained_field="subject",  # এই মডেলের subject ফিল্ডের উপর নির্ভরশীল
        chained_model_field="subject",  # Chapter মডেলের subject ফিল্ডের সাথে মিলবে
        show_all=False,
        auto_choose=True,
        sort=True,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True, blank=True
    )

    # ... বাকি ফিল্ডগুলো ...
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
