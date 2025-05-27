from django.urls import path
from . import views


urlpatterns = [
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    path('profile', views.profile, name='profile'),
    path('edit-profile', views.edit_profile, name='edit_profile'),
    path('my-contracts', views.my_contracts, name='my_contracts'),

    path('enter-email/', views.enter_email, name='enter-email'),
    path('verify-email/', views.verify_email, name='verify-email'),
    path('reset/', views.forgot_password, name='forgot_password'),
    path("verify-by-code", views.verify_by_code, name="verify-by-code"),
    path('set-password/', views.set_new_password, name='set_new_password'),
]
