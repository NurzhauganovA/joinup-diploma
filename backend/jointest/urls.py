from django.urls import path
from .views import (
    join_club, join_test_info, start_join_test, take_join_test, submit_test_answer,
    complete_join_test, join_test_results
)


urlpatterns = [
    # Присоединение к клубу (AJAX запрос)
    path('join/<int:club_id>/', join_club, name='join_club'),

    # Страница с информацией о тесте
    path('info/<int:membership_id>/', join_test_info, name='join_test_info'),

    # Начало прохождения теста
    path('start/<int:membership_id>/', start_join_test, name='start_join_test'),

    # Страница прохождения теста
    path('take/<int:attempt_id>/', take_join_test, name='take_join_test'),

    # Отправка ответа на вопрос
    path('submit-answer/<int:attempt_id>/', submit_test_answer, name='submit_test_answer'),

    # Завершение теста
    path('complete/<int:attempt_id>/', complete_join_test, name='complete_join_test'),

    # Результаты теста
    path('results/<int:attempt_id>/', join_test_results, name='join_test_results'),
]