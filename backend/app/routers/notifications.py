"""
Notifications Router - Multi-channel alert orchestration
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx

from app.config import get_settings, Settings
from app.middleware import get_current_user, get_tenant_id, require_roles, TokenPayload

router = APIRouter(prefix="/notifications")

# The platform email service exposes typed routes; notifications go to this one
# and must carry the shared internal secret.
EMAIL_NOTIFICATION_PATH = "/send/notification"


def email_payload(recipient: str, template: str, data: dict) -> dict:
    """Map a channel notification onto the email service's notification contract."""
    message = data.get("message") or data.get("body")
    if message is None:
        message = json.dumps({k: v for k, v in data.items() if k != "farmer_name"}) if data else ""
    return {
        "email": recipient,
        "farmer_name": str(data.get("farmer_name") or data.get("name") or recipient),
        "notification_type": template,
        "message": str(message),
    }


def email_headers(tenant_id: str, settings: Settings) -> dict:
    return {
        "fiware-service": tenant_id,
        "X-Internal-Service-Secret": settings.internal_service_secret,
    }


# =============================================================================
# Models
# =============================================================================

class NotificationRequest(BaseModel):
    """Request to send notification."""
    channels: List[str]  # email, push, sms, telegram, webhook
    recipients: List[str]
    template: str
    data: dict = {}
    priority: str = "normal"  # low, normal, high, urgent
    scheduledAt: Optional[str] = None


class TestNotificationRequest(BaseModel):
    """Request to test a notification channel."""
    channel: str
    recipient: str


# =============================================================================
# Routes
# =============================================================================

@router.post("/send")
async def send_notification(
    request: NotificationRequest,
    user: TokenPayload = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    settings: Settings = Depends(get_settings),
):
    """
    Send notification through specified channels.
    
    Channels:
    - email: Send email via email-service
    - push: Send push notification via FCM
    - sms: Send SMS via Twilio (if configured)
    - telegram: Send Telegram message (if configured)
    - webhook: POST to webhook URL
    """
    results = []
    
    for channel in request.channels:
        for recipient in request.recipients:
            try:
                if channel == "email":
                    # Send via email service
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{settings.email_service_url}{EMAIL_NOTIFICATION_PATH}",
                            json=email_payload(recipient, request.template, request.data),
                            headers=email_headers(tenant_id, settings),
                        )
                        response.raise_for_status()
                        results.append({
                            "channel": channel,
                            "recipient": recipient,
                            "status": "sent",
                        })
                else:
                    # Mock for other channels
                    results.append({
                        "channel": channel,
                        "recipient": recipient,
                        "status": "sent",
                    })
            except Exception as e:
                results.append({
                    "channel": channel,
                    "recipient": recipient,
                    "status": "failed",
                    "error": str(e),
                })
    
    return results


@router.get("/templates")
async def get_notification_templates(
    user: TokenPayload = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get available notification templates."""
    return {
        "templates": [
            {
                "id": "ndvi-alert",
                "name": "NDVI Alert",
                "channels": ["email", "push"],
                "subject": "Alerta de NDVI - {{parcelName}}",
                "variables": ["parcelName", "ndviValue", "threshold", "date"],
            },
            {
                "id": "pest-warning",
                "name": "Pest Warning",
                "channels": ["email", "push", "sms"],
                "subject": "Aviso de Plaga - {{pestType}}",
                "variables": ["parcelName", "pestType", "probability", "recommendations"],
            },
            {
                "id": "harvest-ready",
                "name": "Harvest Ready",
                "channels": ["email", "push"],
                "subject": "Cosecha Lista - {{parcelName}}",
                "variables": ["parcelName", "cropType", "estimatedYield", "harvestWindow"],
            },
            {
                "id": "robot-mission-complete",
                "name": "Robot Mission Complete",
                "channels": ["push", "webhook"],
                "subject": "Misión Completada - {{robotName}}",
                "variables": ["robotName", "missionType", "parcelName", "duration"],
            },
            {
                "id": "risk-notification",
                "name": "Risk Notification",
                "channels": ["email", "push"],
                "subject": "Alerta de Riesgo - {{riskName}}",
                "variables": ["riskName", "severity", "probability", "entityId"],
            },
        ]
    }


@router.post("/test")
async def test_notification_channel(
    request: TestNotificationRequest,
    user: TokenPayload = Depends(require_roles("TenantAdmin", "PlatformAdmin")),
    tenant_id: str = Depends(get_tenant_id),
    settings: Settings = Depends(get_settings),
):
    """
    Test a notification channel.
    Sends a test message to verify configuration.
    """
    try:
        if request.channel == "email":
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.email_service_url}{EMAIL_NOTIFICATION_PATH}",
                    json=email_payload(
                        request.recipient,
                        "test",
                        {"message": f"This is a test notification from n8n Integration Hub.\nTriggered by: {user.user_id}"},
                    ),
                    headers=email_headers(tenant_id, settings),
                )
                response.raise_for_status()
                return {
                    "channel": request.channel,
                    "recipient": request.recipient,
                    "status": "sent",
                    "message": "Test notification sent successfully"
                }
        else:
            return {
                "channel": request.channel,
                "recipient": request.recipient,
                "status": "sent",
                "message": f"Test {request.channel} notification sent (mock)"
            }
    except Exception as e:
        return {
            "channel": request.channel,
            "recipient": request.recipient,
            "status": "failed",
            "error": str(e)
        }
