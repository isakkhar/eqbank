from django.contrib import admin

from django import forms
from django.shortcuts import redirect
from django.urls import path
from django.contrib import messages
from django.db import transaction
from django.template.response import TemplateResponse

from core.models import Profile, ClassName, Subject, Chapter, Question


# Register your models here.
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'division', 'district', 'thana')
    list_filter = ('division', 'district', 'thana')
    search_fields = ('user__username', 'user__email')

class ClassNameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('name',)
    search_fields = ('name',)

class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_name',)
    list_filter = ('class_name',)
    search_fields = ('name',)

class ChapterAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject')
    list_filter = ('name', 'subject')
    search_fields = ('name',)


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'class_name', 'subject', 'chapter')
    list_filter = ('class_name', 'subject', 'chapter', 'question_type')
    search_fields = ('text',)
    change_list_template = 'admin/questions_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv), name='questions_upload_csv'),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        class QuestionUploadForm(forms.Form):
            csv_file = forms.FileField()

        if request.method == 'POST':
            form = QuestionUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data['csv_file']
                import csv, io
                decoded = f.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                created = 0
                errors = []
                notes = []
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Try common column names for class
                        class_name = (row.get('class_name') or row.get('class') or row.get('class_id') or '').strip()
                        subject_name = (row.get('subject') or '').strip()

                        # If class_name not provided, try to infer from an existing Subject record
                        class_obj = None
                        subject_obj = None
                        if class_name:
                            class_obj, _ = ClassName.objects.get_or_create(name=class_name)

                        if not subject_name:
                            raise ValueError('missing subject')

                        # If class wasn't provided but a matching subject exists in DB, infer class from it
                        if not class_obj:
                            subj_match = Subject.objects.filter(name__iexact=subject_name).select_related('class_name').first()
                            if subj_match:
                                subject_obj = subj_match
                                class_obj = subj_match.class_name
                            else:
                                # Fallback: create/use an 'Unspecified' class so rows without class_name are still imported.
                                class_obj, _ = ClassName.objects.get_or_create(name='Unspecified')
                                notes.append(f"Row {row_num}: class_name missing; assigned fallback class 'Unspecified' for subject '{subject_name}'")

                        # If subject_obj wasn't inferred above, create/get it using the determined class_obj
                        if not subject_obj:
                            subject_obj, _ = Subject.objects.get_or_create(name=subject_name, class_name=class_obj)

                        chap_name = (row.get('chapter') or '').strip()
                        if chap_name:
                            chapter_obj, _ = Chapter.objects.get_or_create(name=chap_name, subject=subject_obj)
                        else:
                            chapter_obj = None

                        text = (row.get('text') or row.get('question') or '').strip()
                        if not text:
                            raise ValueError('missing question text')

                        question_type = (row.get('question_type') or 'mcq').strip()

                        with transaction.atomic():
                            Question.objects.create(
                                text=text,
                                question_type=question_type,
                                class_name=class_obj,
                                subject=subject_obj,
                                chapter=chapter_obj,
                                option_a=row.get('option_a') or None,
                                option_b=row.get('option_b') or None,
                                option_c=row.get('option_c') or None,
                                option_d=row.get('option_d') or None,
                                correct_option=(row.get('correct_option') or '').strip() or None
                            )
                        created += 1
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')

                messages.success(request, f'Created {created} questions. {len(errors)} rows failed.')
                if errors:
                    max_show = 10
                    show = errors[:max_show]
                    more = len(errors) - len(show)
                    err_text = '; '.join(show)
                    if more > 0:
                        err_text += f'; and {more} more...'
                    messages.warning(request, err_text)
                return redirect('..')
        else:
            form = QuestionUploadForm()
        context = dict(
            self.admin_site.each_context(request),
            form=form,
        )
        return TemplateResponse(request, 'admin/questions_upload.html', context)

admin.site.register(Profile, ProfileAdmin)
admin.site.register(ClassName, ClassNameAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.site_header = "স্বাগতম - ই-প্রশ্ন ব্যাংক"         # হেডার
admin.site.site_title = "ই-প্রশ্ন ব্যাংক | এডমিন প্যানেল"       # ব্রাউজার ট্যাব
admin.site.index_title = "ই-প্রশ্ন ব্যাংক"  # ড্যাশবোর্ড হোম
