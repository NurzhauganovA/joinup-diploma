from django.db.models import QuerySet
from django.core.cache import cache
from typing import Any


# def cache_school_people(data: dict[str, QuerySet], pk: int):
#     """
#     Cache list of students, parents and employees of a school.
#     """

#     cache.set(f"school_{pk}", data, timeout=60*5)


# def cache_user_info(data: dict[str, Any], pk: int):
#     """Cache user's data."""

#     cache.set(f"user_{pk}", data, timeout=60*5)



class CacheData:
    """Class to cache and get data."""

    def __init__(self, key: str, pk: int):
        self.key = key
        self.pk = pk

    def cache_data(self, data: dict[str, Any]):
        cache.set(f"{self.key}_{self.pk}", data, timeout=60*5)

    def get_cached_data(self):
        return cache.get(f"{self.key}_{self.pk}")

