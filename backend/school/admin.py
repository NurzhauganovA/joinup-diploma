from django.contrib import admin

from school.models import *

admin.site.register(School)
admin.site.register(SchoolRequisites)
admin.site.register(Class)
admin.site.register(Faculty)
admin.site.register(ClubCategory)
admin.site.register(Club)
admin.site.register(ClubMember)
admin.site.register(ClubEvent)
admin.site.register(EventRegistration)
admin.site.register(ClubApplication)
admin.site.register(ClubResource)
admin.site.register(ClubNews)
admin.site.register(Donation)