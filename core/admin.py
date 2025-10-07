from django.contrib import admin

from core.models import Profile


# Register your models here.
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'division', 'district', 'thana')
    list_filter = ('division', 'district', 'thana')
    search_fields = ('user__username', 'user__email')



admin.site.register(Profile, ProfileAdmin)
