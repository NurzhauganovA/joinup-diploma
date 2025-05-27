from django.utils import timezone
import datetime
from decimal import Decimal

from authorization.models import User, Student
from school.models import School


class GetUserRegionsService:
    @staticmethod
    def get_user_regions():
        users = User.objects.all()
        regions = []
        for user in users:
            region = user.user_info.region
            if region not in [reg['name'] for reg in regions]:
                regions.append({
                    'name': region,
                    'count': 1,
                    'users': [user.mobile_phone]
                })
            else:
                for reg in regions:
                    if reg['name'] == region:
                        reg['count'] += 1
                        reg['users'].append(user.mobile_phone)
                        break

        return regions


class GetLastRegisteredUsersService:
    @classmethod
    def set_response_data(cls, response_data):
        data = []
        for user in response_data:
            data.append({
                'photo_avatar': user.get_photo()
            })

        return data

    def get_last_registered_users(self):
        users = User.objects.all().order_by('-date_joined')[:5]
        return self.set_response_data(users)


class GetCountNewUsersThisMonthService:
    @staticmethod
    def get_count_new_users_current_month():
        current_month = timezone.now().month
        users = User.objects.filter(date_joined__month=current_month)

        return users.count()


class GetOverallGoalUsersService:
    @classmethod
    def set_response_data(cls, overall, goal, difference):
        return {
            'overall_users': overall,
            'goal_users': goal,
            'percent': int(Decimal(overall / goal * 100).quantize(Decimal(".01"))),
            'difference': goal - overall if goal - overall > 0 else 'Выполнено',
            'difference_with_before_month': abs(difference),
            'is_upper': True if difference < 0 else False
        }

    @staticmethod
    def get_overall_users_analytics():
        overall, goal = User.objects.all().count(), 10

        date = timezone.now() - datetime.timedelta(days=30)
        last_month = User.objects.filter(date_joined__month=date.month).count()
        current_month = User.objects.filter(date_joined__month=timezone.now().month).count()

        difference = last_month - current_month

        return GetOverallGoalUsersService.set_response_data(overall, goal, difference)


class WeekLoginCount:
    
    def __init__(self, user_count: list[int], week_days: list[str]):
        self.user_count = user_count
        self.week_days = week_days


class DailyUsersService:

    week = {
        1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI", 6: "SAT", 7: "SUN",
    }

    def get_daily_users(self) -> WeekLoginCount:
        today = timezone.now().date()
        result = {}

        for day in range(6, -1, -1):
            date = today - datetime.timedelta(days=day)
            result[self.week[date.isoweekday()]] = (
                User.objects.filter(login_days__icontains=date.strftime("%d.%m.%Y")).count()
            )

        return WeekLoginCount(
            user_count=[value for value in result.values()],
            week_days=[key for key in result.keys()],
        )


class GetCurrentWeekDays:
    @staticmethod
    def current_week():
        today = datetime.datetime.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=4)
        return start_of_week, end_of_week


class SchoolScheduleService:
    def __init__(self, user):
        self.user = user

    @staticmethod
    def _format_time_range(start_time, duration_hours):
        end_time = start_time + datetime.timedelta(hours=duration_hours)
        return f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"

    @staticmethod
    def week_day_breaks(schedule):
        breaks = []
        for i in range(len(schedule) - 1):
            current_section = schedule[i][0]
            next_section = schedule[i + 1][0]
            break_duration = (next_section.datetime - (current_section.datetime + datetime.timedelta(
                hours=current_section.duration))).total_seconds() // 60
            breaks.append(int(break_duration))

        return breaks

    def week_day_schedule(self, week_day, this_week_sections, start_of_week):
        schedule = []
        for section in this_week_sections.filter(datetime__week_day=start_of_week.weekday() + week_day):
            formatted_time = self._format_time_range(section.datetime, section.duration)
            schedule.append((section, formatted_time))

        return schedule

    def get_school_schedule(self):
        this_week = GetCurrentWeekDays().current_week()
        start_of_week, end_of_week = this_week
        this_week_sections = School.objects.filter(
            datetime__range=this_week,
            subject__classroom=Student.objects.get(user=self.user).stud_class
        )
        this_week_sections_count = this_week_sections.count()

        monday_schedule = self.week_day_schedule(1, this_week_sections, start_of_week)
        monday_breaks = self.week_day_breaks(monday_schedule)

        tuesday_schedule = self.week_day_schedule(2, this_week_sections, start_of_week)
        tuesday_breaks = self.week_day_breaks(tuesday_schedule)

        wednesday_schedule = self.week_day_schedule(3, this_week_sections, start_of_week)
        wednesday_breaks = self.week_day_breaks(wednesday_schedule)

        thursday_schedule = self.week_day_schedule(4, this_week_sections, start_of_week)
        thursday_breaks = self.week_day_breaks(thursday_schedule)

        friday_schedule = self.week_day_schedule(5, this_week_sections, start_of_week)
        friday_breaks = self.week_day_breaks(friday_schedule)

        context = {
            'monday_schedule': monday_schedule,
            'monday_breaks': monday_breaks,

            'tuesday_schedule': tuesday_schedule,
            'tuesday_breaks': tuesday_breaks,

            'wednesday_schedule': wednesday_schedule,
            'wednesday_breaks': wednesday_breaks,

            'thursday_schedule': thursday_schedule,
            'thursday_breaks': thursday_breaks,

            'friday_schedule': friday_schedule,
            'friday_breaks': friday_breaks,

            'this_week_sections_count': this_week_sections_count,
            'today_day': datetime.datetime.today().strftime('%A'),
        }

        return context


# class SchoolSectionAttendanceService:
#     def __init__(self, user):
#         self.user = user
#
#     def get_section_attendance(self):
#         attendance_dict = {}
#         attendance_difference = []
#         student_attendance = SectionAction.objects.filter(student=Student.objects.get(user=self.user))
#
#         for status in SectionActionStatus.get_choices():
#             attendance_dict[status[1]] = student_attendance.filter(status=status[0]).count()
#
#         for status in attendance_dict:
#             attendance_difference.append(attendance_dict[status])
#
#         attended_status_count = SectionAction.objects.filter(student=Student.objects.get(user=self.user),
#                                                              status=SectionActionStatus.ATTENDED).count()
#         attended_status_percent = int((attended_status_count / len(student_attendance)) * 100)
#
#         attendance_context = {
#             'attended_status_count': attended_status_count,
#             'attended_status_percent': attended_status_percent,
#             'attendance_difference': attendance_difference,
#             'total_attendance_status': sum(attendance_difference),
#         }
#
#         return attendance_context
