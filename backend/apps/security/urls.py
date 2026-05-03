"""
Security app URL patterns — included under /api/auth/ in the main router.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Registration
    path("register/", views.send_registration_otp, name="register-send-otp"),
    path("register/complete/", views.complete_registration, name="register-complete"),

    # Login
    path("otp/send/", views.send_login_otp, name="login-send-otp"),
    path("first-login/otp/send/", views.send_first_login_otp, name="first-login-send-otp"),
    path("first-login/complete/", views.complete_first_login, name="first-login-complete"),
    path("login/", views.login_view, name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Password reset
    path("reset-password/", views.send_password_reset_otp, name="reset-password-send-otp"),
    path("reset-password/confirm/", views.confirm_password_reset, name="reset-password-confirm"),

    # PIN reset
    path("reset-pin/", views.send_pin_reset_otp, name="reset-pin-send-otp"),
    path("reset-pin/confirm/", views.confirm_pin_reset, name="reset-pin-confirm"),
]
