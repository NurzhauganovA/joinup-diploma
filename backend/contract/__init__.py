from django.db import models


class ContractPaymentPeriodType(models.TextChoices):
    """ Типы периодов оплаты контрактов """

    MONTHLY = 'Monthly', 'Ежемесячно'
    QUARTERLY = 'Quarterly', 'Ежеквартально'
    ANNUAL = 'Annual', 'Ежегодно'


class ContractStatus(models.TextChoices):
    """ Статусы контрактов """

    FORMED = 'Formed', 'Сформирован'
    CONSIDERATION = 'Consideration', 'На рассмотрении'
    SIGNED = 'Signed', 'Подписан'
    FINISHED = 'Finished', 'Завершен'
    CANCELED = 'Canceled', 'Отменен'
    DISSOLVED = 'Dissolved', 'Расторгнут'
