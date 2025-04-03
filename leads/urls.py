from django.urls import path
from . import views

urlpatterns = [
    path('', views.keyword_search_view, name='keyword_form'),
    path('generated_leads/', views.keyword_list_view, name='keyword_list'),
    path('results/<slug:slug>/', views.keyword_leads_view, name='keyword_leads'),
    path('validate/<slug:slug>/', views.validate_leads, name='validate_leads'),
    path('twilio-response/', views.twilio_response, name='twilio_response'),
    path('export/<slug:slug>/', views.export_keyword_excel, name='export_keyword_excel'),
    path('lead/<int:lead_id>/call/', views.call_lead, name='call_lead'),
    path('lead/<int:lead_id>/edit/', views.edit_lead, name='edit_lead'),
]