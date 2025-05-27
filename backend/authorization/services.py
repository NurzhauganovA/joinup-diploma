import random
from django.core.cache import cache


def save_generated_code_to_cache(email: str, code: int) -> None:
    cache.delete(email)
    cache.set(email, code, timeout=60*5)


def random_generated_code(email: str) -> int:
    code = random.randint(1000, 9999)
    save_generated_code_to_cache(email, code)

    return code
