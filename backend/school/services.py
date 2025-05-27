from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet, Prefetch
from django.core.cache import cache

from authorization import UserRoles
from authorization.models import User, Student
from school.models import School, Class


class GetSchoolPartData:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_school_pk(self) -> int:
        school_cache = cache.get(f'school_{self.user_id}')
        if not school_cache:
            try:
                school_pk = User.objects.get(id=self.user_id).school.first().id
            except AttributeError:
                school_pk = School.objects.first().id

            return school_pk

        school_pk = int(school_cache.split("_")[-1])
        return school_pk

    def get_school_part(self) -> dict:
        school_pk = self.get_school_pk()

        students: QuerySet = User.objects.filter(school__id=school_pk, role=UserRoles.STUDENT)
        parents: QuerySet = User.objects.filter(school__id=school_pk, role=UserRoles.PARENT)
        teachers: QuerySet = User.objects.filter(school__id=school_pk, role=UserRoles.TEACHER)

        return {
            "students": students,
            "parents": parents,
            "teachers": teachers,
        }

    def get_school_distribution_statements(self) -> dict:
        school_pk = self.get_school_pk()
        statements = Student.objects.filter(user__school__id=school_pk, is_studying=False, stud_class=None)

        classes = Class.objects.filter(school_id=school_pk).prefetch_related(
            Prefetch('student_class', queryset=Student.objects.filter(is_studying=False))
        )

        class_data = [
            {
                "id": class_obj.id,
                "class_name": f'{class_obj.class_num}{class_obj.class_liter}',
                "teacher": class_obj.mentor.full_name if class_obj.mentor else None,
                "students": [
                    {
                        "id": student.id,
                        "full_name": student.user.full_name,
                        # "contract_number": student.contracts.last().contract_number if student.contracts.exists() else None,
                    }
                    for student in class_obj.student_class.all()
                ]
            }
            for class_obj in classes
        ]

        teachers = User.objects.filter(school__id=school_pk, role=UserRoles.TEACHER)
        parents = User.objects.filter(school__id=school_pk, role=UserRoles.PARENT)

        return {
            "statements": statements,
            "classes": class_data,
            "teachers": teachers,
            "parents": parents
        }
