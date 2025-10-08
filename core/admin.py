from django.contrib import admin

from core.models import Profile, ClassName, Subject, Chapter


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

admin.site.register(Profile, ProfileAdmin)
admin.site.register(ClassName, ClassNameAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.site_header = "স্বাগতম - ই-প্রশ্ন ব্যাংক"         # হেডার
admin.site.site_title = "ই-প্রশ্ন ব্যাংক | এডমিন প্যানেল"       # ব্রাউজার ট্যাব
admin.site.index_title = "ই-প্রশ্ন ব্যাংক"  # ড্যাশবোর্ড হোম
