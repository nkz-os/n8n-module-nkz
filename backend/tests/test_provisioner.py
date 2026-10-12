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
