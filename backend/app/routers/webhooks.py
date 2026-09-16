"""
Webhooks Router — Webhook configuration, management, and Alert subscription.

Subscription manager creates per-tenant NGSI-LD subscriptions for Alert
entities, forwarding notifications to the tenant's n8n workflow webhook.
"""

import hmac
import logging
import os
from typing import Optional

import httpx
import requests
import psycopg2
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import get_settings, Settings
from app.middleware import get_current_user, get_tenant_id, require_roles, TokenPayload
from app.common.tenant_config_service import get_tenant_config
from app.common.sanitize import sanitize_tenant_id
from app.common.fernet_crypto import decrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")

# ── Orion-LD configuration ────────────────────────────────────────────
ORION_URL = os.getenv("ORION_URL", "http://orion-ld-service:1026")
CONTEXT_URL = os.getenv(
    "CONTEXT_URL", "https://nekazari.robotika.cloud/ngsi-ld-context.json"
)
DATABASE_URL = os.getenv("DATABASE_URL", "")
SERVICE_HOST = os.getenv("SERVICE_HOST", "n8n-module-service")
SERVICE_PORT = os.getenv("SERVICE_PORT", "8000")
NOTIFICATION_URL = (
    f"http://{SERVICE_HOST}:{SERVICE_PORT}/api/n8n-nkz/webhooks/inbound"
)


# =============================================================================
# Models
# =============================================================================

class WebhookCreate(BaseModel):
    """Create a new webhook configuration."""
    name: str
    url: str
    secret: Optional[str] = None
    events: list[str]
    active: bool = True


class WebhookUpdate(BaseModel):
    """Update webhook configuration."""
    name: Optional[str] = None
    url: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[list[str]] = None
    active: Optional[bool] = None


# =============================================================================
# NGSI-LD subscription management for Alert entities
# =============================================================================

SUBSCRIPTION_DEF = {
    "description": "n8n Integration - Alert entities",
    "type": "Subscription",
    "entities": [{"type": "Alert"}],
    "watchedAttributes": ["status"],
    "notification": {
        "endpoint": {
            "uri": NOTIFICATION_URL,
            "accept": "application/json",
        },
        "format": "normalized",
        "attributes": [
            "id", "category", "alertType", "description",
            "severity", "refSourceSensor", "affectedVariables",
            "status", "observedAt",
        ],
    },
    "q": "status==\"active\"",
    "throttling": 5,
    "isActive": True,
}

INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "")
if INTERNAL_SERVICE_SECRET:
    SUBSCRIPTION_DEF["notification"]["endpoint"]["receiverInfo"] = [
        {"key": "X-Internal-Service-Secret", "value": INTERNAL_SERVICE_SECRET}
    ]


def _reject_unauthenticated_notify(x_internal_secret: str | None) -> HTTPException | None:
    """Flag-gated auth for the Orion notification receiver (two-phase rollout)."""
    require = os.getenv("NOTIFY_REQUIRE_INTERNAL_SECRET", "").lower() in (
        "1", "true", "yes", "on"
    )
    if not require:
        return None
    secret = os.getenv("INTERNAL_SERVICE_SECRET", "")
    if not secret or not hmac.compare_digest(x_internal_secret or "", secret):
        return HTTPException(status_code=401, detail="missing or invalid internal secret")
    return None


def _make_orion_headers(tenant_id: str) -> dict:
    """Build Orion-LD headers for a tenant."""
    return {
        "NGSILD-Tenant": tenant_id,
        "Fiware-Service": tenant_id,
        "Fiware-ServicePath": "/",
        "Content-Type": "application/json",
        "Link": f'<{CONTEXT_URL}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
    }


def _get_active_tenants() -> list:
    """Query PostgreSQL for all tenant IDs (from any table)."""
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set, cannot query tenants")
        return []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        try:
            cur = conn.cursor()
            # Prefer admin_platform.tenants, fallback to public.tenants
            cur.execute(
                "SELECT DISTINCT tenant_id FROM tenants WHERE tenant_id IS NOT NULL"
            )
            rows = cur.fetchall()
            cur.close()
            return [r[0] for r in rows]
        finally:
            conn.close()
    except Exception as e:
        logger.error("Error querying active tenants: %s", e)
        return []


def _ensure_alert_subscription(tenant_id: str):
    """Create Alert subscription for a tenant if it doesn't exist.

    Only creates if the tenant has n8n configured.
    """
    config = get_tenant_config(tenant_id)
    if not config or not config.get("n8n_url"):
        logger.debug("Tenant %s has no n8n, skipping Alert subscription", tenant_id)
        return

    headers = _make_orion_headers(tenant_id)
    try:
        # Check if subscription already exists
        resp = requests.get(
            f"{ORION_URL}/ngsi-ld/v1/subscriptions",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(
                "Failed to list subscriptions for %s: %s",
                tenant_id, resp.status_code,
            )
            return

        existing = resp.json() if isinstance(resp.json(), list) else []
        desc = SUBSCRIPTION_DEF["description"]
        if any(s.get("description") == desc for s in existing):
            logger.debug(
                "Alert subscription already exists for tenant %s", tenant_id
            )
            return

        # Create subscription
        logger.info("Creating Alert subscription for tenant %s", tenant_id)
        create_resp = requests.post(
            f"{ORION_URL}/ngsi-ld/v1/subscriptions",
            json=SUBSCRIPTION_DEF,
            headers=headers,
            timeout=10,
        )
        if create_resp.status_code not in (200, 201):
            logger.error(
                "Failed to create Alert subscription for %s: %s",
                tenant_id, create_resp.text,
            )
    except requests.RequestException as e:
        logger.error(
            "Error managing Alert subscription for %s: %s", tenant_id, e,
        )


def ensure_alert_subscriptions_for_all_tenants():
    """Create Alert subscriptions for all tenants that have n8n."""
    tenants = _get_active_tenants()
    logger.info("Checking Alert subscriptions for %d tenants", len(tenants))
    for tenant_id in tenants:
        _ensure_alert_subscription(tenant_id)


# =============================================================================
# Inbound Webhook — receives Orion-LD Alert notifications
# =============================================================================

@router.post("/inbound")
async def handle_inbound_webhook(
    request: Request,
    x_internal_secret: str | None = Header(None, alias="X-Internal-Service-Secret"),
):
    """Receive Orion-LD subscription notification for Alert entities.

    Extracts the Alert data and forwards to the tenant's n8n workflow
    webhook trigger. Returns 200 immediately.
    """
    reject = _reject_unauthenticated_notify(x_internal_secret)
    if reject:
        raise reject
    tenant_id = (
        request.headers.get("NGSILD-Tenant")
        or request.headers.get("Fiware-Service")
        or ""
    )
    if not tenant_id:
        logger.warning("Inbound webhook missing tenant context")
        return {"received": True, "status": "ignored"}

    try:
        body = await request.json()
    except Exception:
        logger.error("Invalid JSON in inbound webhook payload")
        return {"received": True, "status": "error"}, 400

    entities = body.get("data", []) if isinstance(body, dict) else []
    if not entities:
        return {"received": True, "status": "ok", "forwarded": 0}

    # Check if tenant has n8n configured
    config = get_tenant_config(tenant_id)
    if not config or not config.get("n8n_url"):
        logger.debug("Tenant %s has no n8n, skipping forward", tenant_id)
        return {"received": True, "status": "ignored", "forwarded": 0}

    # Decrypt n8n API key if available
    api_key = ""
    if config.get("n8n_api_key_encrypted"):
        try:
            api_key = decrypt_token(config["n8n_api_key_encrypted"])
        except Exception as e:
            logger.error("Failed to decrypt n8n API key: %s", e)

    # Forward each entity to the tenant's n8n workflow webhook
    # Use internal K8s service DNS to avoid hairpin NAT
    internal_url = (
        f"http://n8n-{sanitize_tenant_id(tenant_id)}-service:5678"
    )
    webhook_url = f"{internal_url}/webhook/alert-from-orion"

    forwarded = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        for entity in entities:
            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["X-N8N-API-KEY"] = api_key

                resp = await client.post(
                    webhook_url,
                    json={
                        "tenant_id": tenant_id,
                        "alert": entity,
                    },
                    headers=headers,
                )
                if resp.status_code < 400:
                    forwarded += 1
                else:
                    logger.warning(
                        "n8n webhook returned %s for tenant %s: %s",
                        resp.status_code, tenant_id, resp.text[:200],
                    )
            except httpx.RequestError as e:
                logger.error(
                    "Failed to forward alert to n8n for tenant %s: %s",
                    tenant_id, e,
                )

    logger.info(
        "Forwarded %d/%d alerts to n8n for tenant %s",
        forwarded, len(entities), tenant_id,
    )
    return {"received": True, "status": "ok", "forwarded": forwarded}


# =============================================================================
# CRUD webhook routes (existing — kept as-is for tenant configuration)
# =============================================================================

# In-memory storage for tenant-configured webhooks (not n8n workflows).
# These are separate from the Alert subscription flow.
_webhook_store: dict[str, dict] = {}


@router.get("")
async def list_webhooks(
    user: TokenPayload = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """List all webhook configurations for this tenant."""
    # In production, filter by tenant_id
    return {"webhooks": list(_webhook_store.values())}


@router.post("")
async def create_webhook(
    webhook: WebhookCreate,
    user: TokenPayload = Depends(require_roles("TenantAdmin", "PlatformAdmin")),
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a new webhook configuration."""
    import uuid
    webhook_id = f"wh-{str(uuid.uuid4())[:8]}"
    webhook_data = {
        "id": webhook_id,
        "name": webhook.name,
        "url": webhook.url,
        "secret": webhook.secret,
        "events": webhook.events,
        "active": webhook.active,
        "lastTriggered": None,
        "failureCount": 0,
        "tenant_id": tenant_id,
    }
    _webhook_store[webhook_id] = webhook_data
    return webhook_data


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    webhook: WebhookUpdate,
    user: TokenPayload = Depends(require_roles("TenantAdmin", "PlatformAdmin")),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update webhook configuration."""
    if webhook_id not in _webhook_store:
        raise HTTPException(status_code=404, detail="Webhook not found")
    existing = _webhook_store[webhook_id]
    if webhook.name is not None:
        existing["name"] = webhook.name
    if webhook.url is not None:
        existing["url"] = webhook.url
    if webhook.secret is not None:
        existing["secret"] = webhook.secret
    if webhook.events is not None:
        existing["events"] = webhook.events
    if webhook.active is not None:
        existing["active"] = webhook.active
    return existing


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user: TokenPayload = Depends(require_roles("TenantAdmin", "PlatformAdmin")),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete webhook configuration."""
    if webhook_id not in _webhook_store:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del _webhook_store[webhook_id]
    return {"message": f"Webhook {webhook_id} deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    user: TokenPayload = Depends(require_roles("TenantAdmin", "PlatformAdmin")),
    tenant_id: str = Depends(get_tenant_id),
):
    """Test webhook by sending a test payload."""
    if webhook_id not in _webhook_store:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook = _webhook_store[webhook_id]
    test_payload = {
        "event": "test",
        "timestamp": "2025-01-12T10:00:00Z",
        "data": {"message": "Test from n8n Integration Hub"},
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Content-Type": "application/json"}
            if webhook.get("secret"):
                headers["X-Webhook-Secret"] = webhook["secret"]
            response = await client.post(webhook["url"], json=test_payload, headers=headers)
            return {
                "success": response.status_code < 400,
                "statusCode": response.status_code,
                "response": response.text[:500] if response.text else None,
            }
    except httpx.RequestError as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Startup
# =============================================================================

def init_alert_subscriptions():
    """Bootstrap Alert subscriptions for all n8n-enabled tenants.

    Called at application startup.
    """
    try:
        ensure_alert_subscriptions_for_all_tenants()
    except Exception as e:
        logger.error(
            "Alert subscription bootstrap failed (non-fatal): %s", e,
        )
