import re


def sanitize_tenant_id(tenant_id: str) -> str:
    """Sanitize tenant ID for K8s resource names."""
    sanitized = tenant_id.lower()
    sanitized = re.sub(r"[^a-z0-9-]", "-", sanitized)
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    sanitized = sanitized.strip("-")
    return sanitized[:63]


def n8n_resource_name(tenant_id: str, suffix: str = "") -> str:
    """Generate K8s resource name for n8n tenant instance."""
    base = f"n8n-{sanitize_tenant_id(tenant_id)}"
    if suffix:
        return f"{base}-{suffix}"
    return base


def n8n_db_name(tenant_id: str) -> str:
    """Generate PostgreSQL database name for tenant n8n instance."""
    safe = sanitize_tenant_id(tenant_id).replace("-", "_")
    return f"n8n_{safe}"


def n8n_db_role(tenant_id: str) -> str:
    """PostgreSQL role that owns the tenant's n8n database (same name as the database)."""
    return n8n_db_name(tenant_id)


def n8n_host(tenant_id: str) -> str:
    """Generate the n8n URL for a tenant (subdomain-based: <tenant>.n8n.robotika.cloud)."""
    safe = sanitize_tenant_id(tenant_id)
    return f"{safe}.n8n.robotika.cloud"
