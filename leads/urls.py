from django.urls import path
from . import views

urlpatterns = [
    path('', views.lead_form, name='lead_form'),
    path('leads/', views.lead_list, name='lead_list'),
]
