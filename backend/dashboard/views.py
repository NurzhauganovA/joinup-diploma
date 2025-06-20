from django.shortcuts import render, redirect

from authorization.models import User, Student
from dashboard.services import GetUserRegionsService, GetLastRegisteredUsersService, GetCountNewUsersThisMonthService, \
    GetOverallGoalUsersService, DailyUsersService, GetCurrentWeekDays, SchoolScheduleService
from school.models import School
from django.http import JsonResponse


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.role == 'Student':
        return student_dashboard(request)

    user_regions = GetUserRegionsService().get_user_regions()  # work
    last_registered_users = GetLastRegisteredUsersService().get_last_registered_users()  # work
    count_last_registered_users = GetCountNewUsersThisMonthService().get_count_new_users_current_month()  # work
    overall_users_analytics = GetOverallGoalUsersService().get_overall_users_analytics()  # work
    daily_users_analytics = DailyUsersService().get_daily_users()  # work

    context = {
        'user_regions': user_regions,
        'last_registered_users': last_registered_users,
        'count_last_registered_users': count_last_registered_users,
        'overall_users_analytics': overall_users_analytics,
        'daily_users_analytics': daily_users_analytics,
    }

    return render(request, 'dashboard/home.html', context)


def student_dashboard(request):
    school_schedule_context = SchoolScheduleService(request.user).get_school_schedule()
    # attendance_context = SchoolSectionAttendanceService(request.user).get_section_attendance()

    context = {
        'school_schedule': school_schedule_context,
    }

    return render(request, 'dashboard/student_dashboard.html', context)
