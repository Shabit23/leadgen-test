import os
import requests
from django.shortcuts import redirect
from django.http import HttpResponse
from .models import LinkedInToken

def linkedin_authorize(request):
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
    scope = "openid profile email"
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={requests.utils.quote(scope)}"
    )
    return redirect(auth_url)

def linkedin_callback(request):
    code = request.GET.get("code")
    if not code:
        return HttpResponse("Missing authorization code", status=400)

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        token_data = response.json()
        LinkedInToken.objects.all().delete()
        LinkedInToken.objects.create(
            access_token=token_data['access_token'],
            expires_in=token_data['expires_in']
        )
        return HttpResponse("✅ LinkedIn access token saved successfully!")
    else:
        return HttpResponse(f"Error fetching token: {response.text}", status=400)
