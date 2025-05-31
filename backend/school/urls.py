from django.urls import path
from . import views


urlpatterns = [
    # Главная страница клубов
    path('', views.clubs_list, name='clubs_list'),

    # Детальная страница клуба
    path('club/<slug:slug>/', views.club_detail, name='club_detail'),

    # Заявка на создание клуба
    path('create/', views.create_club_application, name='create_club'),
    path('get-application-form/', views.get_club_application_form, name='get_application_form'),

    # Регистрация на мероприятия
    path('events/<int:event_id>/register/', views.register_for_event, name='register_for_event'),

    # Мои клубы
    path('my-clubs/', views.my_clubs, name='my_clubs'),

    # Донаты
    path('club/<slug:slug>/donations/', views.club_donations, name='club_donations'),
    path('club/<slug:slug>/donate/', views.make_donation, name='make_donation'),

    # Управление клубом
    path('club/<slug:slug>/manage/', views.club_management, name='club_management'),
    path('club/<slug:slug>/application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('club/<slug:slug>/approve/<int:application_id>/', views.approve_application, name='approve_application'),
    path('club/<slug:slug>/reject/<int:application_id>/', views.reject_application, name='reject_application'),

    # Подписание контракта
    path('club/<slug:slug>/contract/sign/', views.contract_sign_page, name='contract_sign_page'),
    path('club/<slug:slug>/process-signature/', views.process_digital_signature, name='process_digital_signature'),
    path('club/<slug:slug>/sign-contract/', views.sign_contract, name='sign_contract'),
    path('club/<slug:slug>/contract/download/', views.download_contract_pdf, name='download_contract_pdf'),
]
