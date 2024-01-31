from django.urls import path
from .views import PhotoCheckAPI

urlpatterns = [
    path('check-photo/', PhotoCheckAPI.as_view(), name='check_photo'),
]
