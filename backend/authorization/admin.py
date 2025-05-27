from django.contrib import admin

from .models import User, UserInfo, Student


class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'mobile_phone', 'role', 'date_joined')
    search_fields = ('full_name', 'email', 'mobile_phone')
    list_filter = ('role', 'date_joined')
    ordering = ('-date_joined',)


admin.site.register(User, UserAdmin)
admin.site.register(UserInfo)
admin.site.register(Student)
