from django.db import models

class Lead(models.Model):
    keyword = models.CharField(max_length=1024)  # NEW FIELD: stores the search keyword
    company_name = models.CharField(max_length=2048)
    email = models.EmailField()
    phone = models.CharField(max_length=1024)
    website = models.URLField()
    industry = models.CharField(max_length=1024)
    revenue = models.CharField(max_length=1024)
    location = models.CharField(max_length=1024)
    procurement_history = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name
