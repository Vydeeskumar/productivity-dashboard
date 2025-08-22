from django.shortcuts import render, reverse, redirect
from django.conf import settings
from django.http import HttpResponse
from google_auth_oauthlib.flow import Flow
import json
from django.contrib.auth import login, logout
from oauthlib.oauth2 import InvalidGrantError
from .models import User 
import requests
import os

CLIENT_SECRETS_CONFIG = {
    "web": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "project_id": "productivity-dashboard-469508",  
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
    }
}

def google_login(request):
    # Set these BEFORE creating the flow for local dev
    if settings.DEBUG:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    flow = Flow.from_client_config(
        client_config=CLIENT_SECRETS_CONFIG,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    
    # Ensure session exists and force save
    if not request.session.session_key:
        request.session.create()
    
    request.session['state'] = state
    request.session.modified = True  # Force Django to save session
    request.session.save()
    
    print(f"LOGIN - Session ID: {request.session.session_key}")
    print(f"LOGIN - Stored state: {state}")
    print(f"LOGIN - Session data: {dict(request.session)}")
    
    return redirect(authorization_url)



def google_callback(request):
    try:
        if settings.DEBUG:
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

        # Debug session information
        stored_state = request.session.get('state', '')
        received_state = request.GET.get('state', '')
        
        print(f"Session ID: {request.session.session_key}")
        print(f"Session data: {dict(request.session)}")
        print(f"CALLBACK - Stored: {stored_state}, Received: {received_state}")
        
        # Check for state mismatch (CSRF protection)
        if not stored_state or stored_state != received_state:
            print("STATE MISMATCH - Session may not be persisting")
            return HttpResponse(
                f'State mismatch. Please <a href="/">try again</a>.<br>'
                f'Debug: Stored: "{stored_state}" | Received: "{received_state}"', 
                status=403
            )

        # Clear the state from session since we verified it
        request.session.pop('state', '')

        # Create OAuth flow
        flow = Flow.from_client_config(
            client_config=CLIENT_SECRETS_CONFIG,
            scopes=settings.GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials
        
        # Get user information from Google
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )

        if not user_info_response.ok:
            return HttpResponse('Failed to fetch user info.', status=500)

        user_info = user_info_response.json()
        email = user_info.get('email')
        
        # Create or get user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=user_info.get('given_name') or '',
                last_name=user_info.get('family_name') or ''
            )

        # Update user with OAuth data
        user.google_id = user_info.get('sub')
        user.access_token = credentials.token
        user.refresh_token = credentials.refresh_token
        user.profile_picture = user_info.get('picture') or ''
        user.save()
        
        # Log the user in
        login(request, user)
        return redirect('/')
        
    except InvalidGrantError:
        # Handle expired/invalid authorization code gracefully
        print("InvalidGrantError: Authorization code expired or already used")
        return HttpResponse(
            "Login session expired or already used. Please <a href='/'>try again</a>.", 
            status=400
        )
    
    except Exception as e:
        # Handle any other errors
        print(f"Unexpected error in google_callback: {str(e)}")
        if settings.DEBUG:
            import traceback
            traceback.print_exc()
            return HttpResponse(f"Login failed: {str(e)}", status=500)
        else:
            return HttpResponse("Login failed. Please try again.", status=500)



def logout_view(request):
    logout(request)
    return redirect('/')
