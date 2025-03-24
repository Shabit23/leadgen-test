from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('linkedin/', include('linkedin_auth.urls')),
    path('', include('leads.urls')),
]
