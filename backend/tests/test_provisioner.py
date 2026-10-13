"""Unit tests for n8n provisioner (non-K8s parts)."""

from app.common.n8n_provisioner import generate_credentials
from app.common.n8n_provisioner import tenant_pod_labels, tenant_env


def test_generate_credentials_returns_dict():
    creds = generate_credentials()
    assert "username" in creds
    assert "password" in creds
    assert "api_key" in creds


def test_generate_credentials_unique():
    creds1 = generate_credentials()
    creds2 = generate_credentials()
    assert creds1["username"] != creds2["username"]
    assert creds1["password"] != creds2["password"]
    assert creds1["api_key"] != creds2["api_key"]


def test_generate_credentials_lengths():
    creds = generate_credentials()
    assert len(creds["username"]) > 6
    assert len(creds["password"]) >= 16
    assert len(creds["api_key"]) >= 24


def test_tenant_pod_labels_mark_egress_restricted():
    labels = tenant_pod_labels("n8n-acme", "acme")
    assert labels["app"] == "n8n-acme"
    assert labels["module"] == "n8n-nkz"
    assert labels["tenant"] == "acme"
    assert labels["nkz-os.org/egress-restricted"] == "true"


def test_tenant_env_blocks_process_env_in_code_nodes():
    env = {e.name: e.value for e in tenant_env("n8n-acme", "n8n_acme", "/acme", "n8n.example")}
    assert env["N8N_BLOCK_ENV_ACCESS_IN_NODE"] == "true"
    assert env["DB_TYPE"] == "postgresdb"
    assert env["DB_POSTGRESDB_HOST"] == "postgresql-service"


def test_tenant_pvc_uses_volume_resource_requirements():
    from kubernetes import client
    from app.common.n8n_provisioner import tenant_pvc

    pvc = tenant_pvc("n8n-acme")
    assert isinstance(pvc.spec.resources, client.V1VolumeResourceRequirements)
    assert pvc.spec.resources.requests == {"storage": "10Gi"}
    assert pvc.metadata.name == "n8n-acme-workflows"


def test_tenant_image_is_digest_pinned():
    from app.config import get_settings

    assert get_settings().n8n_instance_image.startswith("n8nio/n8n@sha256:")


# --- per-tenant database role (sprint 2 / sub 4) -----------------------------
from app.common.n8n_provisioner import tenant_db_sql  # noqa: E402


def _statements(db_name="n8n_acme", role="n8n_acme", password="pw"):
    return [sql.as_string(None) if hasattr(sql, "as_string") else str(sql) for sql, _ in tenant_db_sql(db_name, role, password)]


def test_role_sql_is_idempotent():
    joined = "\n".join(_statements())
    assert "DO $$" in joined and "IF NOT EXISTS (SELECT 1 FROM pg_roles" in joined
    assert "ALTER ROLE" in joined and "PASSWORD" in joined  # rotation on re-provision
    assert "OWNER TO" in joined
    assert "REVOKE CONNECT ON DATABASE" in joined and "FROM PUBLIC" in joined
    assert "GRANT CONNECT ON DATABASE" in joined


def test_password_travels_as_a_parameter_never_inline():
    for sql, params in tenant_db_sql("n8n_acme", "n8n_acme", "s3cret-value"):
        text = sql.as_string(None) if hasattr(sql, "as_string") else str(sql)
        assert "s3cret-value" not in text
    assert any("s3cret-value" in (params or ()) for _, params in tenant_db_sql("n8n_acme", "n8n_acme", "s3cret-value"))


def test_tenant_env_uses_tenant_db_role():
    env = {e.name: e for e in tenant_env("n8n-acme", "n8n_acme", "/acme", "n8n.example")}
    assert env["DB_POSTGRESDB_USER"].value_from.secret_key_ref.name == "n8n-acme-secret"
    assert env["DB_POSTGRESDB_USER"].value_from.secret_key_ref.key == "db-user"
    assert env["DB_POSTGRESDB_PASSWORD"].value_from.secret_key_ref.name == "n8n-acme-secret"
    assert env["DB_POSTGRESDB_PASSWORD"].value_from.secret_key_ref.key == "db-password"


def test_existing_secret_without_db_keys_gets_them(monkeypatch):
    import base64
    from app.common import n8n_provisioner as prov

    class FakeCore:
        def __init__(self, data):
            self.data = data
            self.patched = None

        def read_namespaced_secret(self, name, ns):
            return type("S", (), {"data": self.data})()

        def patch_namespaced_secret(self, name, ns, body):
            self.patched = (name, body)

    old = FakeCore({"username": base64.b64encode(b"u").decode()})
    assert prov._ensure_db_credentials(old, "n8n-acme", "n8n_acme", "fresh") == "fresh"
    assert old.patched[0] == "n8n-acme-secret"
    assert old.patched[1]["stringData"] == {"db-user": "n8n_acme", "db-password": "fresh"}

    new = FakeCore({"db-password": base64.b64encode(b"kept").decode()})
    assert prov._ensure_db_credentials(new, "n8n-acme", "n8n_acme", "fresh") == "kept"
    assert new.patched is None
