from django.db import models


class Regions(models.TextChoices):
    BATYS = "Batys", "Западно-Казахстанская область"
    AQTOBE = "Aqtobe", "Актюбинская область"
    ATYRAU = "Atyrau", "Атырауская область"
    MANGYSTAU = "Mangystau", "Мангистауская область"
    QOSTANAI = "Qostanay", "Костанайская область"
    SOLTUSTIK = "Soltustik", "Северо-Казахстанская область"
    PAVLODAR = "Pavlodar", "Павлодарская область"
    QARAGANDY = "Qaragandy", "Карагандинская область"
    ULYTAU = "Ulytau", "Улытауская область"
    QYZYLORDA = "Qyzylorda", "Кызылординская область"
    TURKISTAN = "Turkistan", "Туркестанская область"
    ZHAMBYL = "Zhambyl", "Жамбылская область"
    ALMATY = "Almaty", "Алматинская область"
    ZHETISU = "Zhetisu", "Жетысуская область"
    ABAY = "Abay", "Абайская область"
    SHYGYS = "Shygys", "Восточно-Казахстанская область"
    AQMOLA = "Aqmola", "Акмолинская область"

    @classmethod
    def get_choices(cls):
        return [region for region in cls.choices]


class SectionActionStatus(models.TextChoices):
    """ Статус посещения раздела """

    ATTENDED = 'Attended', 'Посещено'
    ABSENT = 'Absent', 'Отсутствие'
    PERMITTED = 'Permitted', 'Разрешено'
    LATE = 'Late', 'Опоздание'
    LEFT = 'Left', 'Покинул занятие'

    @classmethod
    def get_choices(cls):
        return [status for status in cls.choices]
