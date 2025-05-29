from django.urls import path
from .views import (
    join_club, join_test_info, start_join_test, take_join_test, submit_test_answer,
    complete_join_test, join_test_results
)


urlpatterns = [
    # Страница с информацией о вступительном тесте
    path('', join_test_info, name='join_test_info'),

    # Начало вступительного теста
    path('start/', start_join_test, name='start_join_test'),

    # Принять участие в клубе
    path('join/<int:club_id>/', join_club, name='join_club'),

    # Прохождение вступительного теста
    path('take/<int:club_id>/', take_join_test, name='take_join_test'),

    # Отправка ответа на вопрос теста
    path('submit-answer/', submit_test_answer, name='submit_test_answer'),

    # Завершение вступительного теста
    path('complete/', complete_join_test, name='complete_join_test'),

    # Результаты вступительного теста
    path('results/<int:club_id>/', join_test_results, name='join_test_results'),
]