from django.db import models


class UserRoles(models.TextChoices):
    ADMIN = "Admin", "Администратор"
    EMPLOYEE = "Employee", "Сотрудник"
    HEADER = "Header", "Создатель"
    STUDENT = "Student", "Ученик"
