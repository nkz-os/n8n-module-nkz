"""The Alert subscription registrar must recreate stale subscriptions."""

from app.routers import webhooks as wh


def _sub(uri=None, status="active", secret=None, with_receiver=True):
    endpoint = {"uri": uri if uri is not None else wh.NOTIFICATION_URL, "accept": "application/json"}
    if with_receiver:
        endpoint["receiverInfo"] = [{"key": "X-Internal-Service-Secret", "value": secret}]
    return {
        "id": "urn:ngsi-ld:subscription:test",
        "description": wh.SUBSCRIPTION_DEF["description"],
        "status": status,
        "notification": {"endpoint": endpoint},
    }


def test_notification_url_targets_the_module_service(monkeypatch):
    monkeypatch.delenv("SERVICE_HOST", raising=False)
    assert wh.NOTIFICATION_URL == "http://n8n-nkz-api-service:8000/api/n8n-nkz/webhooks/inbound"


def test_current_subscription_is_kept(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "s3cret")
    assert wh._subscription_diverges(_sub(secret="s3cret")) is None


def test_dead_endpoint_is_recreated(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "s3cret")
    reason = wh._subscription_diverges(_sub(uri="http://n8n-module-service:8000/api/n8n-nkz/webhooks/inbound", secret="s3cret"))
    assert reason and "endpoint" in reason


def test_paused_subscription_is_recreated(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "s3cret")
    reason = wh._subscription_diverges(_sub(status="paused", secret="s3cret"))
    assert reason and "paused" in reason


def test_rotated_secret_is_recreated(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "new")
    assert wh._subscription_diverges(_sub(secret="old")) == "stale internal secret"
    assert wh._subscription_diverges(_sub(with_receiver=False)) == "missing internal secret"


def test_secret_not_checked_when_unset(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "")
    assert wh._subscription_diverges(_sub(with_receiver=False)) is None
