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

    # Вступление в клуб
    path('club/<int:club_id>/join/', views.join_club, name='join_club'),

    # Тест для подбора клуба
    path('quiz/', views.start_club_quiz, name='quiz_start'),
    path('quiz/submit-answer/', views.submit_quiz_answer, name='quiz_submit_answer'),
    path('quiz-results/', views.quiz_results, name='quiz_results'),

    # Регистрация на мероприятия
    path('events/<int:event_id>/register/', views.register_for_event, name='register_for_event'),

    # Мои клубы
    path('my-clubs/', views.my_clubs, name='my_clubs'),

    path('club/<slug:slug>/donations/', views.club_donations, name='club_donations'),
    path('club/<slug:slug>/donate/', views.make_donation, name='make_donation'),
]
