from django.contrib import admin

from core.models import Profile


# Register your models here.
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'division', 'district', 'thana')
    list_filter = ('division', 'district', 'thana')
    search_fields = ('user__username', 'user__email')



admin.site.register(Profile, ProfileAdmin)

admin.site.site_header = "স্বাগতম - ই-প্রশ্ন ব্যাংক"         # হেডার
admin.site.site_title = "ই-প্রশ্ন ব্যাংক | এডমিন প্যানেল"       # ব্রাউজার ট্যাব
admin.site.index_title = "ই-প্রশ্ন ব্যাংক"  # ড্যাশবোর্ড হোম
