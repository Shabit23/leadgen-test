from django.urls import path
from . import views

urlpatterns = [
    path("authorize/", views.linkedin_authorize, name="linkedin_authorize"),
    path("callback/", views.linkedin_callback, name="linkedin_callback"),
]
