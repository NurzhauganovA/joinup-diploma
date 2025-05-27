import calendar
from datetime import timedelta
from sqlite3 import Date

from django.db.models import Sum, Q
from django.utils import timezone

from authorization.models import User, Student
from school.models import School
from .. import ContractPaymentPeriodType, ContractStatus
from ..models import Contract, Transaction, ContractMonthPay, ContractDayPay


class GetContractInfoService:
    def __init__(self, student_id):
        self.student_id = student_id
        self.student = Student.objects.get(id=self.student_id)

    def get_contracts(self):
        return Contract.objects.filter(student=self.student)


class GetContractDebtSumService:
    def __init__(self, student_id):
        self.student_id = student_id
        self.student = Student.objects.get(id=self.student_id)

    def get_transactions_sum(self):
        transaction_sum_obj = Transaction.objects.filter(contract__student=self.student).aggregate(Sum('amount'))
        return transaction_sum_obj['amount__sum']

    def get_accruals_sum(self):
        accruals_sum_obj = ContractMonthPay.objects.filter(contract__student=self.student).aggregate(Sum('amount'))
        return accruals_sum_obj['amount__sum']

    def get_debt_sum(self):
        transactions_sum = self.get_transactions_sum()
        accruals_sum = self.get_accruals_sum()

        return transactions_sum - accruals_sum


class CreateContractService:
    def __init__(self, student_id, school_id, created_date):
        self.student_id = student_id
        self.school_id = school_id
        self.created_date = created_date

        self.student = Student.objects.get(id=self.student_id)
        self.school = School.objects.get(id=self.school_id)

    def get_optimized_random_number(self, num: int):
        if num < 10:
            return f'000{num}'
        elif num < 100:
            return f'00{num}'
        elif num < 1000:
            return f'0{num}'

        return str(num)

    def get_contract_number(self):
        last_contract = Contract.objects.last()
        if not last_contract:
            return '0001'

        last_contract_num = int(last_contract.name.split('-')[-1])
        return self.get_optimized_random_number(last_contract_num + 1)

    def get_contract_name(self):
        current_year = timezone.now().year
        return f'{current_year}{self.school.short_name}-{self.get_contract_number()}'

    def get_edu_year(self):
        current_date = timezone.now()
        if current_date.month <= 12 and current_date.month >= 9:
            return f'{current_date.year}/{current_date.year + 1}'

        return f'{current_date.year - 1}/{current_date.year}'

    def create_contract_obj(self):
        contract = Contract.objects.create(
            student=self.student,
            school=self.school,
            date=self.created_date,
            name=self.get_contract_name(),
            amount=2000000,
            payment_type=ContractPaymentPeriodType.MONTHLY,
            status=ContractStatus.FORMED,
            final_amount=2000000,
            edu_year=self.get_edu_year(),
            classroom=self.student.stud_class
        )
        return contract

    @staticmethod
    def get_contract_year(contract_date):
        if 9 <= contract_date.month <= 12:
            return contract_date.year + 1

        return contract_date.year

    def create_month_pays(self, contract):
        contract_date = contract.date
        contract_start_date = contract_date
        contract_end_date = Date(self.get_contract_year(contract_date), 5, 25)

        edu_year_start_date = Date(contract_start_date.year - 1, 9, 1)
        if 9 <= contract_start_date.month <= 12:
            edu_year_start_date = Date(contract_start_date.year, 9, 1)

        total_month = 9
        monthly_cost = contract.final_amount / total_month

        while edu_year_start_date < contract_start_date:
            ContractMonthPay.objects.create(
                contract=contract,
                month=Date(year=edu_year_start_date.year,
                           month=edu_year_start_date.month,
                           day=edu_year_start_date.day),
                amount=0
            )
            if edu_year_start_date.month == 12:
                edu_year_start_date = Date(year=edu_year_start_date.year + 1, month=1, day=1)

            edu_year_start_date = Date(year=edu_year_start_date.year,
                                       month=edu_year_start_date.month + 1,
                                       day=edu_year_start_date.day)

        while contract_start_date < contract_end_date:
            # Определить последний день этого месяца или 25 мая
            if contract_start_date.month == 12:
                next_month_last_day = Date(year=contract_start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                next_month_last_day = Date(year=contract_start_date.year,
                                           month=contract_start_date.month + 1,
                                           day=1) - timedelta(days=1)

            ContractMonthPay.objects.create(
                contract=contract,
                month=Date(year=contract_start_date.year,
                           month=contract_start_date.month,
                           day=contract_start_date.day),
                amount=monthly_cost
            )

            # Переход к следующему месяцу
            contract_start_date = next_month_last_day + timedelta(days=1)

        return

    @staticmethod
    def get_sum_day_pays_per_month(date, month_sum):
        days_in_month = calendar.monthrange(date.year, date.month)[1]
        count_work_days = 0

        for day in range(1, days_in_month + 1):
            date = Date(date.year, date.month, day)
            if date.weekday() in (5, 6):
                continue
            else:
                count_work_days += 1

        return round(float(month_sum / count_work_days), 2)

    @staticmethod
    def calculate_month_sum_with_day_pays(contract_month_id):
        contract_month_pay = ContractMonthPay.objects.get(id=contract_month_id)
        contract_day_pays = ContractDayPay.objects.filter(contract_month=contract_month_pay).aggregate(Sum('amount'))[
            'amount__sum']

        contract_month_pay.amount = contract_day_pays
        contract_month_pay.save()

    def create_day_pays(self, contract):
        contract_date = contract.date
        contract_start_date = contract_date
        contract_end_date = Date(self.get_contract_year(contract_date), 5, 25)

        edu_year_start_date = Date(contract_start_date.year - 1, 9, 1)
        if 9 <= contract_start_date.month <= 12:
            edu_year_start_date = Date(contract_start_date.year, 9, 1)

        while edu_year_start_date < contract_start_date:
            ContractDayPay.objects.create(
                contract_month=ContractMonthPay.objects.filter(
                    Q(contract=contract) & Q(month__month=edu_year_start_date.month)).first() or None,
                day=edu_year_start_date,
                amount=0
            )
            edu_year_start_date += timedelta(days=1)

        while edu_year_start_date <= contract_start_date <= contract_end_date:
            get_contract_month = ContractMonthPay.objects.filter(
                Q(contract=contract) &
                Q(month__month=contract_start_date.month)).last()
            if ContractDayPay.objects.filter(
                    Q(contract_month=get_contract_month) &
                    Q(day=contract_start_date)).exists():
                contract_start_date += timedelta(days=1)
                continue
            else:
                if contract_start_date.weekday() in (5, 6):
                    ContractDayPay.objects.create(
                        contract_month=get_contract_month,
                        day=contract_start_date,
                        amount=0
                    )
                else:
                    ContractDayPay.objects.create(
                        contract_month=get_contract_month,
                        day=contract_start_date,
                        amount=self.get_sum_day_pays_per_month(contract_start_date, get_contract_month.amount)
                    )
                contract_start_date += timedelta(days=1)

        get_contract_date_month_object = ContractMonthPay.objects.filter(
            Q(contract=contract) & Q(month__month=contract_date.month)).last()
        self.calculate_month_sum_with_day_pays(get_contract_date_month_object.id)

        return

    def contract_auto_create(self):
        contract = self.create_contract_obj()
        self.create_month_pays(contract)
        self.create_day_pays(contract)

        return contract
