"""
Google OAuth 2.0 flow for salon onboarding.
Salon owners visit /oauth/connect to grant calendar access.
"""
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.config import settings
from app.integrations.db import save_salon_oauth_token

logger = logging.getLogger(__name__)
router = APIRouter()

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _make_flow() -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


@router.get("/connect", response_class=HTMLResponse)
async def oauth_connect(salon_id: str):
    """
    Start the Google OAuth flow for a salon.
    Salon owner visits: /oauth/connect?salon_id=abc123
    """
    flow = _make_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=salon_id,  # Pass salon_id through OAuth state param
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oauth_callback(request: Request, code: str, state: str):
    """
    Handle Google OAuth callback.
    Exchanges code for tokens and saves refresh token to Supabase.
    """
    salon_id = state
    if not salon_id:
        raise HTTPException(status_code=400, detail="Missing salon_id in state")

    try:
        flow = _make_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        await save_salon_oauth_token(salon_id=salon_id, refresh_token=creds.refresh_token)
        logger.info(f"OAuth token saved for salon: {salon_id}")
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save calendar access")

    return HTMLResponse(content="""
    <html>
      <body style="font-family:sans-serif;text-align:center;padding:60px;">
        <h2>✅ Calendar Connected!</h2>
        <p>Your Google Calendar has been successfully linked to HeyZenzai.</p>
        <p>Your AI booking assistant is now live. You can close this window.</p>
      </body>
    </html>
    """)
