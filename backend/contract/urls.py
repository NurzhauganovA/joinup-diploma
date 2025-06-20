from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    # Главная страница контрактов
    path('', views.contracts_dashboard, name='dashboard'),

    # Список контрактов
    path('list/', views.contracts_list, name='list'),

    # Детальная страница контракта
    path('<int:contract_id>/', views.contract_detail, name='detail'),

    # Скачивание контракта
    path('<int:contract_id>/download/', views.download_signed_contract, name='download'),

    # Проверка контракта
    path('<int:contract_id>/verify/', views.contract_verification, name='verify'),
]