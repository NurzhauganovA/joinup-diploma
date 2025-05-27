from django.core.mail import send_mail
from django.core.cache import cache
from random import randint

from diploma import settings


def _generate_random_code():
    return randint(1000, 9999)


def save_generated_code_to_cache(email, cache_key:str, code: int):
    cache.set(f'{cache_key}_{email}', code, timeout=300)


def send_email(email, subject, message):
    random_code = _generate_random_code()
    print(random_code)
    send_mail(
        subject=subject,
        message=f'{message}: {random_code}',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email]
    )

    save_generated_code_to_cache(email, 'activate_account', random_code)


def verify_account(email, code):
    cache_code = cache.get(f'activate_account_{email}')

    if cache_code is not None and int(cache_code) == int(code):
        return True

    return False