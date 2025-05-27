from django.contrib import admin

from contract.models import Discount, Contract, ContractMonthPay, ContractDayPay, Transaction, ContractFile


admin.site.register(Discount)
admin.site.register(Contract)
admin.site.register(ContractMonthPay)
admin.site.register(ContractDayPay)
admin.site.register(Transaction)
admin.site.register(ContractFile)
