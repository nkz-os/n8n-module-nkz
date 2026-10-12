"""Email notifications must follow the platform email service's contract."""

from app.config import Settings
from app.routers.notifications import EMAIL_NOTIFICATION_PATH, email_headers, email_payload


def test_route_is_the_typed_notification_endpoint():
    assert EMAIL_NOTIFICATION_PATH == "/send/notification"


def test_payload_has_every_required_field():
    payload = email_payload("farmer@example.org", "alert", {"farmer_name": "Ane", "message": "Frost tonight"})
    assert payload == {
        "email": "farmer@example.org",
        "farmer_name": "Ane",
        "notification_type": "alert",
        "message": "Frost tonight",
    }


def test_payload_falls_back_when_data_is_free_form():
    payload = email_payload("farmer@example.org", "alert", {"severity": "high"})
    assert payload["farmer_name"] == "farmer@example.org"
    assert "high" in payload["message"]
    assert email_payload("x@y.z", "t", {})["message"] == ""


def test_headers_carry_tenant_and_internal_secret():
    settings = Settings(internal_service_secret="s3cret")
    assert email_headers("acme", settings) == {"fiware-service": "acme", "X-Internal-Service-Secret": "s3cret"}


def test_email_service_default_port_matches_the_service():
    assert Settings().email_service_url == "http://email-service:5000"
