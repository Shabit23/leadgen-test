from django.db import models

class Lead(models.Model):
    keyword = models.CharField(max_length=255)  # NEW FIELD: stores the search keyword
    company_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    website = models.URLField()
    industry = models.CharField(max_length=255)
    revenue = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    procurement_history = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name
