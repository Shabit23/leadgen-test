from django.shortcuts import render, redirect, get_object_or_404
from .forms import LeadKeywordForm
from .models import Lead, KeywordSlug
from .tasks import fetch_leads_task, call_and_validate_lead
from django.utils.text import slugify
from django.contrib import messages
from django.utils import timezone

def keyword_search_view(request):
    if request.method == "POST":
        form = LeadKeywordForm(request.POST)
        if form.is_valid():
            keyword = form.cleaned_data['keyword']
            slug = slugify(keyword)
            obj, created = KeywordSlug.objects.get_or_create(keyword=keyword, slug=slug)
            # obj, created = KeywordSlug.objects.get_or_create(slug=slug, defaults={"keyword": keyword})
            if created or not Lead.objects.filter(keyword=keyword).exists():
                fetch_leads_task(keyword)
            return redirect('keyword_leads', slug=slug) #changed for redirection
    else:
        form = LeadKeywordForm()
    return render(request, 'leads/keyword_form.html', {'form': form})

def keyword_leads_view(request, slug):
    keyword_obj = get_object_or_404(KeywordSlug, slug=slug)
    leads = Lead.objects.filter(keyword=keyword_obj.keyword)
    return render(request, 'leads/keyword_leads.html', {
        'keyword': keyword_obj.keyword,
        'leads': leads,
        'slug': slug,
    })

def keyword_list_view(request):
    from .models import KeywordSlug
    keywords = KeywordSlug.objects.all().order_by('-created_at')
    return render(request, 'leads/keyword_list.html', {'keywords': keywords})

# For Concurrent Calls
# def validate_leads(request, slug):
#     keyword_obj = get_object_or_404(KeywordSlug, slug=slug)
#     leads = Lead.objects.filter(keyword=keyword_obj.keyword, status__in=["Not Validated", "Pending"])
#     print(f"Validating {leads.count()} leads for keyword: {keyword_obj.keyword}")
#     for lead in leads:
#         call_and_validate_lead(lead.id)
#     messages.success(request, f"Initiated validation calls for {leads.count()} leads.")
#     return redirect('keyword_leads', slug=slug)

import time
from background_task.models import Task

def validate_leads(request, slug):
    from .models import KeywordSlug, Lead
    from .tasks import call_and_validate_lead
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    from datetime import timedelta
    

    keyword_obj = get_object_or_404(KeywordSlug, slug=slug)
    leads = Lead.objects.filter(keyword=keyword_obj.keyword, status__in=["Not Validated", "Pending"])
    print(f"Validating {leads.count()} leads for keyword: {keyword_obj.keyword}")
    delay_minutes = 0
    for lead in leads:
        # Schedule each call with increasing delay
        schedule_time = timezone.now() + timedelta(minutes=delay_minutes)
        call_and_validate_lead(lead.id, schedule=schedule_time)
        delay_minutes += 2  # each call 1 min apart

    messages.success(request, f"Validation scheduled sequentially for {leads.count()} leads.")
    return redirect('keyword_leads', slug=slug)

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Gather
from .models import Lead, ValidationQuestion, ValidationResponse, ValidationCallLog
import json

@csrf_exempt
def twilio_response(request):
    print("🚀 Twilio callback received")
    lead_id = request.GET.get("lead_id")
    question_index = int(request.GET.get("q", "0"))
    voice_result = request.POST.get("SpeechResult", "").lower() if request.method == "POST" else ""
    print(f"Received response for lead ID {lead_id}, question index {question_index}, answer: {voice_result}")
    response = VoiceResponse()

    lead = Lead.objects.filter(id=lead_id).first()
    if not lead:
        response.say("Invalid lead ID.")
        return HttpResponse(str(response), content_type="application/xml")

    # Initialize session for response tracking
    session_key = f"voice_q_{lead_id}"
    if not request.session.get(session_key):
        request.session[session_key] = []

    answers = request.session.get(session_key)
    print(f"Current answers: {answers}")

    questions = ValidationQuestion.objects.all().order_by("id")

    # Store last answer for previous question
    if voice_result and question_index > 0 and question_index - 1 < len(questions):
        question = questions[question_index - 1]
        ValidationResponse.objects.create(
            lead=lead,
            question=question,
            answer=voice_result
        )
        answers.append(voice_result)
        request.session[session_key] = answers
        print(f"Stored answer for question {question_index - 1}: {voice_result}")

        # from django.core.cache import cache

        # cache_key = f"voice_q_{lead_id}"
        # answers = cache.get(cache_key, [])

        # # Save
        # answers.append(voice_result)
        # cache.set(cache_key, answers, timeout=60*15)


    # Start of call (intro + disclaimer)
    if question_index == 0:
        response.say("Hello, this is an automated business call from BizConnect.")
        response.say("We help companies connect with reliable vendors and service providers.")
        response.say("This call is being recorded for quality and verification purposes.")

    # Ask next question
    if question_index < len(questions):
        next_q = questions[question_index].question
        gather = Gather(input="speech", action=f"{request.path}?lead_id={lead_id}&q={question_index+1}", timeout=5)
        gather.say(next_q)
        response.append(gather)
        response.say("Sorry, we did not get your response.")
        response.redirect(f"{request.path}?lead_id={lead_id}&q={question_index}")
        # response.redirect(f"{request.path}?lead_id={lead_id}&q={question_index}")
    else:
        # End of questions: analyze responses
        yes_keywords = ["yes", "interested", "sure", "okay", "fine", "of course", "yup", "definitely"]
        positive_count = sum(1 for a in answers if any(k in a for k in yes_keywords))

        if positive_count >= 3:
            lead.status = "Interested"
        elif positive_count == 0:
            lead.status = "Pending"
        else:
            lead.status = "Not interested"
        lead.save()

        # Save full transcript
        full_text = "\n".join(answers)
        ValidationCallLog.objects.update_or_create(
            lead=lead,
            defaults={"transcript": full_text}
        )
        request.session.pop(session_key, None)
        response.say("Thank you for your time. Your responses have been recorded. Goodbye.")

    return HttpResponse(str(response), content_type="application/xml")

@csrf_exempt
def twilio_status(request):
    print("📞 Status callback:", request.POST)
    return HttpResponse("OK")

def export_keyword_excel(request, slug):
    from .models import Lead, KeywordSlug
    import openpyxl
    from django.http import HttpResponse

    keyword_obj = KeywordSlug.objects.get(slug=slug)
    leads = Lead.objects.filter(keyword=keyword_obj.keyword)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{keyword_obj.keyword[:31]}"

    headers = ["Keyword", "Company", "Email", "Phone", "Website", "Location", "Status", "Created"]
    ws.append(headers)

    for lead in leads:
        ws.append([
            lead.keyword,
            lead.company_name,
            lead.email,
            lead.phone,
            lead.website,
            lead.location,
            lead.status,
            lead.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={slug}_leads.xlsx'
    wb.save(response)
    return response

from django.http import HttpResponseRedirect

@csrf_exempt
def call_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    # Simulate Twilio call triggering logic here
    print(f"[Calling Lead] {lead.company_name}, {lead.phone}")
    schedule_time = timezone.now()
    call_and_validate_lead(lead_id, schedule=schedule_time)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@csrf_exempt
def edit_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    if request.method == "POST":
        lead.company_name = request.POST.get("company_name")
        lead.email = request.POST.get("email")
        lead.phone = request.POST.get("phone")
        lead.website = request.POST.get("website")
        lead.location = request.POST.get("location")
        lead.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
