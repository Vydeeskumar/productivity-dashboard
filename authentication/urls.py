from django.urls import path
from .views import google_login, google_callback, logout_view

app_name = "authentication"

urlpatterns = [
    path('login/', google_login, name='google_login'),
    path('callback/', google_callback, name='google_callback'),
    path('logout/', logout_view, name='logout'),
]
