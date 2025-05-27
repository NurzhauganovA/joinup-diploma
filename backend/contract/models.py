from django.db import models
from django.utils import timezone

from contract import ContractStatus, ContractPaymentPeriodType
from school.models import School, Class
from authorization.models import Student


class Discount(models.Model):
    """ Модель скидок """

    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, db_column='school')
    name = models.CharField(max_length=255, null=True)
    percent = models.PositiveIntegerField(default=0)
    date = models.DateField(null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Скидка'
        verbose_name_plural = 'Скидки'
        db_table = 'discount'


class Contract(models.Model):
    """ Модель контрактов """

    student = models.ForeignKey(
        Student, 
        on_delete=models.SET_NULL, 
        null=True, 
        db_column='student',
        related_name="contracts"
    )
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, db_column='school', related_name="contracts")
    date = models.DateField()
    date_close = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=255, choices=ContractPaymentPeriodType.choices, default=ContractPaymentPeriodType.MONTHLY)
    status = models.CharField(max_length=255, choices=ContractStatus.choices, default=ContractStatus.FORMED)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    edu_year = models.CharField(max_length=255)
    classroom = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, db_column='classroom')
    discount = models.ManyToManyField(Discount, db_column='discount', related_name='discount')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Контракт'
        verbose_name_plural = 'Контракты'
        db_table = 'contract'


class ContractMonthPay(models.Model):
    """ Модель ежемесячных платежей по контрактам """

    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, db_column='contract')
    month = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.contract.name

    class Meta:
        verbose_name = 'Ежемесячный платеж'
        verbose_name_plural = 'Ежемесячные платежи'
        db_table = 'contract_month_pay'


class ContractDayPay(models.Model):
    """ Модель дневных платежей по контрактам """

    contract_month = models.ForeignKey(ContractMonthPay, on_delete=models.SET_NULL, null=True, db_column='contract_month')
    day = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.contract_month.contract.name

    class Meta:
        verbose_name = 'Дневной платеж'
        verbose_name_plural = 'Дневные платежи'
        db_table = 'contract_day_pay'


class Transaction(models.Model):
    """ Модель транзакций """

    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, db_column='contract', related_name="transactions")
    datetime = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    payment_type = models.CharField(max_length=255, default="Cash")

    def __str__(self):
        return f'{self.contract.name} - {self.amount}'

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        db_table = 'transaction'


class ContractFile(models.Model):
    """ Модель файлов контрактов """

    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, db_column='contract')
    file = models.FileField(upload_to='contract/files/')
    datetime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.contract.name

    class Meta:
        verbose_name = 'Файл контракта'
        verbose_name_plural = 'Файлы контрактов'
        db_table = 'contract_file'
