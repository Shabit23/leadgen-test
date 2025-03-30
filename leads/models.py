from django.db import models
from django.utils.text import slugify

class Lead(models.Model):
    STATUS_CHOICES = [
        ("Not Validated", "Not Validated"),
        ("Pending", "Pending"),
        ("Interested", "Interested"),
        ("Not interested", "Not interested"),
    ]
    keyword = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    website = models.URLField()
    industry = models.CharField(max_length=255)
    revenue = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    procurement_history = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Not Validated")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class KeywordSlug(models.Model):
    keyword = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.keyword)
        super().save(*args, **kwargs)

class ValidationQuestion(models.Model):
    question = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question
    
class ValidationResponse(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(ValidationQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class ValidationCallLog(models.Model):
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE)
    transcript = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
