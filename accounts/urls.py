from django.urls import path
from .views import LoginView, RegisterView, ForgotPasswordView, ResetPasswordView, LogoutView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('forgot_pwd/', ForgotPasswordView.as_view(), name='forgot_pwd'),
    path('pwd_reset/<uidb64>/<token>/', ResetPasswordView.as_view(), name='pwd_reset'),
    path('logout/', LogoutView.as_view(), name='logout')
]
