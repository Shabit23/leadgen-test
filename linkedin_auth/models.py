from django.db import models

class LinkedInToken(models.Model):
    access_token = models.CharField(max_length=512)
    expires_in = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).seconds < self.expires_in
