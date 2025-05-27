from django.urls import path
from . import views

urlpatterns = [
    path('', views.clubs_list, name='clubs_list'),

    # Club application
    path('create/', views.create_club_application, name='create_club'),
    path('get-application-form/', views.get_club_application_form, name='get_application_form'),

    # Club interest quiz
    path('quiz/', views.start_club_quiz, name='quiz_start'),
    path('quiz/submit-answer/', views.submit_quiz_answer, name='quiz_submit_answer'),
    path('quiz-results/', views.quiz_results, name='quiz_results'),
]
