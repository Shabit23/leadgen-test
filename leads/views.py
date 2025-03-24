from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Lead
from .tasks import fetch_leads_task

def lead_form(request):
    if request.method == 'POST':
        product = request.POST.get('product')
        if product:
            # Schedule the background task to fetch leads
            fetch_leads_task(product)
            messages.success(request, "Lead generation task has been scheduled. Please check back later for results.")
            return redirect('lead_list')
        else:
            messages.error(request, "Please enter a valid product or service.")
    return render(request, 'leads/lead_form.html')

def lead_list(request):
    leads = Lead.objects.all().order_by('-created_at')
    return render(request, 'leads/lead_list.html', {'leads': leads})
