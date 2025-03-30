from django.contrib import admin
from .models import Lead, KeywordSlug, ValidationQuestion, ValidationResponse, ValidationCallLog

admin.site.register(Lead)
admin.site.register(KeywordSlug)
admin.site.register(ValidationQuestion)
admin.site.register(ValidationResponse)
admin.site.register(ValidationCallLog)