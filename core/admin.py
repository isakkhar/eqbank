from django.contrib import admin

from django import forms
from django.shortcuts import redirect
from django.urls import path
from django.contrib import messages

from core.models import Profile, ClassName, Subject, Chapter, Question


# Register your models here.
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'division', 'district', 'thana')
    list_filter = ('division', 'district', 'thana')
    search_fields = ('user__username', 'user__email')

class ClassNameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    lit_filter = ('name',)
    search_fields = ('name',)

class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_name',)
    list_filter = ('class_name',)
    search_fields = ('name',)

class ChapterAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject')
    list_filter = ('name', 'subject')
    search_fields = ('name',)


class QuestionUploadForm(forms.Form):
    csv_file = forms.FileField()


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_text', 'question_type', 'class_name', 'subject', 'chapter')
    list_filter = ('class_name', 'subject', 'chapter', 'question_type')
    search_fields = ('text',)

    def short_text(self, obj):
        return str(obj)[:80]
    short_text.short_description = 'প্রশ্ন'

    change_list_template = 'admin/questions_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv), name='questions_upload_csv'),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if request.method == 'POST':
            form = QuestionUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data['csv_file']
                import csv, io
                decoded = f.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                created = 0
                errors = 0
                for row in reader:
                    try:
                        class_obj = ClassName.objects.get(name=row.get('class_name') or row.get('class'))
                        subject_obj = Subject.objects.get(name=row.get('subject'), class_name=class_obj)
                        chapter_obj = None
                        chap_name = row.get('chapter')
                        if chap_name:
                            chapter_obj, _ = Chapter.objects.get_or_create(name=chap_name, subject=subject_obj)

                        q = Question.objects.create(
                            text=row.get('text') or row.get('question') or '',
                            question_type=row.get('question_type') or 'mcq',
                            class_name=class_obj,
                            subject=subject_obj,
                            chapter=chapter_obj,
                            option_a=row.get('option_a'),
                            option_b=row.get('option_b'),
                            option_c=row.get('option_c'),
                            option_d=row.get('option_d'),
                            correct_option=row.get('correct_option')
                        )
                        created += 1
                    except Exception as e:
                        errors += 1
                messages.success(request, f'Created {created} questions. {errors} rows failed.')
                return redirect('..')
        else:
            form = QuestionUploadForm()
        context = dict(
            self.admin_site.each_context(request),
            form=form,
        )
        from django.template.response import TemplateResponse
        return TemplateResponse(request, 'admin/questions_upload.html', context)

admin.site.register(Profile, ProfileAdmin)
admin.site.register(ClassName, ClassNameAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.site_header = "স্বাগতম - ই-প্রশ্ন ব্যাংক"         # হেডার
admin.site.site_title = "ই-প্রশ্ন ব্যাংক | এডমিন প্যানেল"       # ব্রাউজার ট্যাব
admin.site.index_title = "ই-প্রশ্ন ব্যাংক"  # ড্যাশবোর্ড হোম
