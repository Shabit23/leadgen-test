import os
import re
import time
import requests
import logging
from bs4 import BeautifulSoup
from background_task import background
from .models import Lead

# CHANGE #L2: import token model
from linkedin_auth.models import LinkedInToken

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# CHANGE #1: Email extraction improved
def extract_email(text):
    pattern = re.compile(r'(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9])')
    emails = pattern.findall(text)
    valid_emails = []
    for email in emails:
        email_lower = email.lower()
        if any(x in email_lower for x in ['noreply', 'donotreply']):
            continue
        valid_emails.append(email)
    return valid_emails[0] if valid_emails else "N/A"

# CHANGE #2: Custom phone number regex
def extract_phone(text):
    pattern = re.compile(r'\+?\d[\d\-\.\(\) ]{6,}\d')
    candidates = pattern.findall(text)
    valid_numbers = []
    for candidate in candidates:
        digits = re.sub(r'\D', '', candidate)
        if 7 <= len(digits) <= 15:
            valid_numbers.append(candidate.strip())
    return ', '.join(valid_numbers) if valid_numbers else "N/A"

def extract_field(text, field_name):
    pattern = re.compile(rf"{field_name}\s*:\s*(.+)", re.IGNORECASE)
    match = pattern.search(text)
    return match.group(1).split('\n')[0].strip() if match else "N/A"

def extract_company_name(soup):
    return soup.title.string.strip() if soup.title and soup.title.string else "N/A"

def is_commercial_page(soup, url):
    if any(x in url.lower() for x in ['article', 'blog', 'archive', 'news', 'history', 'forum']):
        return False
    text = soup.get_text().lower()
    return any(x in text for x in ['contact us', 'services', 'products', 'buy now', 'solutions'])

# CHANGE #3: fetch page with headers
def fetch_page(url):
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/98.0.4758.102 Safari/537.36")
    }
    return requests.get(url, headers=headers, timeout=10)

# CHANGE #4: Google search logic
def search_google(product):
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not cx:
        logger.error("Google API credentials missing.")
        return []

    results = {}
    query = (f'{product} (supplier OR manufacturer OR distributor OR "company") '
             '(buy OR purchase OR "need service") '
             '-inurl:forum -inurl:answers -inurl:discussion -inurl:qa')
    start = 1
    while True:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": api_key, "cx": cx, "q": query, "start": start, "num": 10}
        r = requests.get(url, params=params)
        if r.status_code != 200:
            logger.error("Google search error: %s", r.text)
            break
        items = r.json().get("items", [])
        for item in items:
            link = item.get("link")
            if link and link not in results:
                # results[link] = item
                results[link] = {**item, "source": "google"}
        if len(items) < 10:
            break
        start += 10
    return list(results.values())

# CHANGE #5: LinkedIn search using token from DB
def search_linkedin(product):
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not cx:
        logger.error("Google API key or search engine ID is missing.")
        return []

    query = f'site:linkedin.com/company/ "{product}" (buy OR purchase OR need OR service)'
    start = 1
    all_results = {}

    logger.info(f"🔍 [LinkedIn via Google] Searching for: {query}")

    while True:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "start": start,
            "num": 10
        }

        response = requests.get(url, params=params)
        logger.debug(f"🌐 Google CSE Request URL: {response.url}")

        if response.status_code != 200:
            logger.error(f"❌ Google CSE failed (LinkedIn): {response.status_code} - {response.text}")
            break

        items = response.json().get("items", [])
        if not items:
            break

        for item in items:
            link = item.get("link")
            if link and "linkedin.com/company/" in link.lower() and link not in all_results:
                all_results[link] = {**item, "source": "linkedin-google"}

        logger.info(f"✅ Retrieved {len(items)} items from Google CSE (LinkedIn pages)")
        if len(items) < 10:
            break
        start += 10

    logger.info(f"🎯 Total LinkedIn company links found: {len(all_results)}")
    return list(all_results.values())


# CHANGE #6: background task
@background(schedule=0)
def fetch_leads_task(product):
    logger.info("Fetching leads for: %s", product)
    results = search_google(product) + search_linkedin(product)
    seen = set()
    total = 0
    valid = 0

    for item in results:
        link = item.get("link")
        source = item.get("source", "unknown")
        if not link or link in seen:
            continue
        seen.add(link)
        print(f"🟢 Processing lead from {source.upper()}: {link}")
        total += 1
        try:
            response = fetch_page(link)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error("Fetch error %s: %s", link, e)
            continue

        if not is_commercial_page(soup, link):
            continue

        text = soup.get_text()
        email = extract_email(text)
        phone = extract_phone(text)
        if phone == "N/A":
            continue

        lead = Lead.objects.create(
            keyword=product,
            company_name=extract_company_name(soup),
            email=email,
            phone=phone,
            website=link,
            industry=extract_field(text, "Industry"),
            revenue=extract_field(text, "Revenue"),
            location=extract_field(text, "Location"),
            procurement_history=extract_field(text, "Procurement History")
        )
        valid += 1
        logger.info("Lead added: %s", lead.company_name)

    logger.info("Finished: %d scanned, %d leads created", total, valid)


from twilio.rest import Client
from django.conf import settings
from django.urls import reverse

@background(schedule=0)
def call_and_validate_lead(lead_id):
    from .models import Lead
    from django.conf import settings
    from django.urls import reverse

    try:
        print(f"[CALL SCHEDULED] Triggering call for lead ID {lead_id}")
        lead = Lead.objects.get(id=lead_id)
        callback_url = f"{settings.CALLBACK_BASE_URL}{reverse('twilio_response')}?lead_id={lead.id}&q=0"

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            # to="+8801716573924",
            to=lead.phone,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=callback_url,
            timeout=20
        )
        lead.status = "Pending"
        lead.save()
        
    except Exception as e:
        print("Call failed:", e)


from datetime import timedelta
from django.utils import timezone

@background(schedule=3600)  # 1 hour later
def retry_pending_leads():
    leads = Lead.objects.filter(status="Pending", created_at__lte=timezone.now() - timedelta(minutes=60))
    for lead in leads:
        call_and_validate_lead(lead.id)
