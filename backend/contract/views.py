import json
from datetime import datetime

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.http.request import HttpRequest

from school.services import GetSchoolPartData
from school.models import School
from contract.models import Contract, Transaction


def get_all_contracts(req: HttpRequest):
    school = School.objects.get(
        id=GetSchoolPartData(req.user.id).get_school_pk()
    )
    contracts = school.contracts.all()
    context = {
        "contracts": contracts
    }

    return render(req, "contract/contract.html", context)


def get_contract_info(request: HttpRequest, pk: int) -> JsonResponse:
    if request.method == "GET":
        contract = Contract.objects.get(id=pk)
        contract_info = {
            "id": contract.id,
            "name": contract.name,
            "student_full_name": contract.student.user.full_name if contract.student.user else "No data",
            "date": contract.date.strftime("%d.%m.%Y") if contract.date else "No data",
            "final_amount": int(contract.final_amount) if contract.final_amount else "No data",
            "status": contract.status if contract.status else "No data",
            "payment_type": contract.payment_type if contract.payment_type else "No data",
            "discounts": [discount.name for discount in contract.discount.all()],
        }

        return JsonResponse({'data': contract_info, 'status': 200})
    return JsonResponse({"error": "Not Allowed Method", "status": 405})


def change_contract_data(request: HttpRequest, contract_number: str):
    if request.method == "PUT":
        try:
            contract = Contract.objects.get(name=contract_number)
            data = request.body.decode('utf-8')
            data = json.loads(data)

            contract.name = data.get("contractNumber") if data.get("contractNumber") else contract.name
            contract.date = datetime.strptime(data.get("agreementDate"), "%d.%m.%Y").strftime("%Y-%m-%d") if data.get("agreementDate") else contract.date
            contract.final_amount = data.get("contractSum") if data.get("contractSum") else contract.final_amount
            contract.status = data.get("contractStatus") if data.get("contractStatus") else contract.status
            contract.payment_type = data.get("contractPaymentPeriod") if data.get("contractPaymentPeriod") else contract.payment_type
            contract.save()

            messages.success(request, "Contract data changed")
            return JsonResponse({'data': 'Contract data changed', 'status': 200})
        except Exception as e:
            messages.error(request, str(e))
            return JsonResponse({'error': str(e), 'status': 400})
    return JsonResponse({"error": "Not Allowed Method", "status": 405})


def get_contract_transactions(request: HttpRequest, pk: int) -> JsonResponse:
    if request.method == "GET":
        contract = Contract.objects.get(id=pk)
        transactions = Transaction.objects.filter(contract=contract)

        transactions_info = {
            "transactions": []
        }

        if transactions:
            for transaction in transactions:
                transactions_info["transactions"].append({
                    "id": transaction.id,
                    "date": transaction.datetime.strftime("%d.%m.%Y") if transaction.datetime else "No data",
                    "amount": transaction.amount if transaction.amount else "No data",
                    "description": transaction.description if transaction.description else "No data",
                    "payment_type": transaction.payment_type if hasattr(transaction, "payment_type") else "CASH",
                })

        return JsonResponse({'data': transactions_info, 'status': 200})

    return JsonResponse({"error": "Not Allowed Method", "status": 405})