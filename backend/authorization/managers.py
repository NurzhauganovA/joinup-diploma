from typing import Any
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def _create_user(
            self,
            mobile_phone,
            password=None,
            is_staff=False,
            is_superuser=False,
            is_active=False
    ):
        user = self.model(
            mobile_phone=mobile_phone,
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_active=is_active
        )

        user.set_password(password)
        user.save()

        return user

    def create_user(self, mobile_phone, password, **extra_fields):
        return self._create_user(
            mobile_phone=mobile_phone,
            password=password,
            is_staff=extra_fields.get("is_staff", False),
            is_superuser=extra_fields.get("is_superuser", False),
            is_active=extra_fields.get("is_active", False)
        )

    def create_superuser(self, mobile_phone, password, **extra_fields):
        return self._create_user(
            mobile_phone=mobile_phone,
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

    def create(self, mobile_phone, password, **extra_fields):
        user = self.model(
            mobile_phone=mobile_phone,
            is_staff=False,
            is_superuser=False,
            is_active=True,
            full_name=extra_fields.get("full_name"),
            role=extra_fields.get("role")
        )

        user.set_password(password)
        user.save()

        return user
