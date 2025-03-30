from django import forms

class LeadKeywordForm(forms.Form):
    keyword = forms.CharField(max_length=255)