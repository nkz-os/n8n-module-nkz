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


class _Resp:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body if body is not None else []
        self.text = ""

    def json(self):
        return self._body


def test_ensure_recreates_stale_and_dedupes_current(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "s3cret")
    monkeypatch.setattr(wh, "get_tenant_config", lambda t: {"n8n_url": "http://n8n"})
    stale = dict(_sub(uri="http://n8n-module-service:8000/x", secret="old"), id="urn:stale")
    keep = dict(_sub(secret="s3cret"), id="urn:keep")
    dup = dict(_sub(secret="s3cret"), id="urn:dup")
    calls = []
    monkeypatch.setattr(wh.requests, "get", lambda url, **kw: _Resp(200, [stale, keep, dup]))
    monkeypatch.setattr(wh.requests, "delete", lambda url, **kw: calls.append(("delete", url.rsplit("/", 1)[-1])) or _Resp(204))
    monkeypatch.setattr(wh.requests, "post", lambda url, **kw: calls.append(("post", "")) or _Resp(201))
    wh._ensure_alert_subscription("acme")
    assert ("delete", "urn:stale") in calls
    assert ("delete", "urn:dup") in calls
    assert ("delete", "urn:keep") not in calls
    assert ("post", "") not in calls


def test_ensure_creates_when_none_is_current(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "s3cret")
    monkeypatch.setattr(wh, "get_tenant_config", lambda t: {"n8n_url": "http://n8n"})
    stale = dict(_sub(status="paused", secret="s3cret"), id="urn:stale")
    calls = []
    monkeypatch.setattr(wh.requests, "get", lambda url, **kw: _Resp(200, [stale]))
    monkeypatch.setattr(wh.requests, "delete", lambda url, **kw: calls.append("delete") or _Resp(204))
    monkeypatch.setattr(wh.requests, "post", lambda url, **kw: calls.append("post") or _Resp(201))
    wh._ensure_alert_subscription("acme")
    assert calls == ["delete", "post"]


def test_listing_asks_for_every_subscription(monkeypatch):
    monkeypatch.setattr(wh, "INTERNAL_SERVICE_SECRET", "s3cret")
    monkeypatch.setattr(wh, "get_tenant_config", lambda t: {"n8n_url": "http://n8n"})
    seen = {}
    monkeypatch.setattr(wh.requests, "get", lambda url, **kw: seen.update(kw) or _Resp(200, []))
    monkeypatch.setattr(wh.requests, "post", lambda url, **kw: _Resp(201))
    wh._ensure_alert_subscription("acme")
    assert seen["params"]["limit"] >= 1000
