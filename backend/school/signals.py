from django.db.models.signals import post_save
from django.dispatch import receiver


# @receiver(post_save, sender=SectionHomeworkGrade)
# def notify_student_on_grade(sender, instance, created, **kwargs):
#     if created:
#         print('notify_student_on_grade')
#         teacher = instance.homework.section.subject.teacher
#         student = instance.student.user
#         subject = instance.homework.section.subject.name
#         grade = instance.grade
#
#         body = f"Вам выставлена оценка по предмету {subject}"
#         text = f"""
#         Вам выставлена оценка по предмету {subject}.
#         Оценка: {grade}.
#         Ответственный учитель: {teacher.mobile_phone}.
#         """
#         send_notification(teacher, student, body, text)
