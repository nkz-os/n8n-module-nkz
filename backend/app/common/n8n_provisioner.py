"""K8s provisioning engine for per-tenant n8n instances."""

import base64
import logging
import re
import secrets
from datetime import datetime, timezone
from kubernetes import client, config
from app.common.sanitize import n8n_resource_name, n8n_db_name, n8n_db_role, n8n_host, sanitize_tenant_id
from app.common.fernet_crypto import encrypt_token
from app.common.tenant_config_service import get_tenant_config, upsert_tenant_config
from app.common.db import get_db_connection_safe
from app.config import get_settings

logger = logging.getLogger(__name__)

NAMESPACE = "nekazari"
N8N_PORT = 5678


def _load_k8s_config():
    """Load in-cluster config, fallback to kubeconfig for local dev."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _k8s_apps_v1():
    return client.AppsV1Api()


def _k8s_core_v1():
    return client.CoreV1Api()


def _k8s_networking_v1():
    return client.NetworkingV1Api()


def _k8s_autoscaling_v1():
    return client.AutoscalingV1Api()


def generate_credentials() -> dict:
    """Generate random credentials for a tenant n8n instance."""
    return {
        "username": f"admin_{secrets.token_hex(4)}",
        "password": secrets.token_urlsafe(16),
        "api_key": secrets.token_urlsafe(24),
        "db_password": secrets.token_urlsafe(24),
    }


_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def _ident(name: str) -> str:
    """Quote a database identifier that the sanitizer already constrained."""
    if not _IDENT.match(name):
        raise ValueError(f"unsafe identifier: {name!r}")
    return f'"{name}"'


def tenant_db_sql(db_name: str, role: str, password: str, db_exists: bool = False) -> list:
    """Statements giving a tenant n8n its own role and database; re-runnable.

    The role owns only its database and PUBLIC loses CONNECT on it, so a Code
    node inside that n8n cannot reach any other database. The password is a
    bound parameter: it never appears in SQL text or in logs. Re-provisioning
    rotates the password to the one held in the tenant Secret.
    """
    db, r = _ident(db_name), _ident(role)
    stmts = [
        (
            "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '" + role + "') THEN "
            f"CREATE ROLE {r} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT; "
            "END IF; END $$",
            None,
        ),
        (f"ALTER ROLE {r} PASSWORD %s", (password,)),
        (f"GRANT {r} TO CURRENT_USER", None),
    ]
    if not db_exists:
        stmts.append((f"CREATE DATABASE {db} OWNER {r}", None))
    stmts += [
        (f"ALTER DATABASE {db} OWNER TO {r}", None),
        (f"REVOKE CONNECT ON DATABASE {db} FROM PUBLIC", None),
        (f"GRANT CONNECT ON DATABASE {db} TO {r}", None),
    ]
    return stmts


def create_n8n_tenant_db(tenant_id: str, db_password: str) -> bool:
    """Create (or converge) the tenant's n8n database and its owning role."""
    conn = get_db_connection_safe()
    if not conn:
        return False
    try:
        conn.autocommit = True
        cur = conn.cursor()
        db_name = n8n_db_name(tenant_id)
        role = n8n_db_role(tenant_id)

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone() is not None
        for stmt, params in tenant_db_sql(db_name, role, db_password, db_exists=exists):
            cur.execute(stmt, params)
        logger.info("n8n tenant database ready: db=%s role=%s existed=%s", db_name, role, exists)

        cur.close()
        return True
    except Exception as e:
        logger.error(f"Failed to prepare DB for tenant {tenant_id}: {type(e).__name__}")
        return False
    finally:
        conn.close()


def _ensure_db_credentials(core_v1, name: str, role: str, fallback_password: str) -> str:
    """Password of the tenant's database role, taken from its Secret.

    Secrets created before the per-tenant role lack the db keys: add them
    (with the freshly generated password) so the Deployment can reference them.
    """
    existing = core_v1.read_namespaced_secret(f"{name}-secret", NAMESPACE)
    data = existing.data or {}
    if "db-password" in data:
        return base64.b64decode(data["db-password"]).decode()
    core_v1.patch_namespaced_secret(
        f"{name}-secret", NAMESPACE, {"stringData": {"db-user": role, "db-password": fallback_password}}
    )
    return fallback_password


def drop_n8n_tenant_db(tenant_id: str) -> bool:
    """Drop the tenant's n8n PostgreSQL database."""
    conn = get_db_connection_safe()
    if not conn:
        return False
    try:
        conn.autocommit = True
        cur = conn.cursor()
        db_name = n8n_db_name(tenant_id)

        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.execute(f"DROP ROLE IF EXISTS {_ident(n8n_db_role(tenant_id))}")

        cur.close()
        return True
    except Exception as e:
        logger.error(f"Failed to drop DB for tenant {tenant_id}: {e}")
        return False
    finally:
        conn.close()


def tenant_pod_labels(name: str, tenant_id: str) -> dict:
    """Pod template labels for a tenant n8n instance.

    The egress-restricted label opts the pod into the tenant-workload egress
    NetworkPolicy; the Deployment selector stays {"app": name}.
    """
    return {
        "app": name,
        "module": "n8n-nkz",
        "tenant": tenant_id,
        "nkz-os.org/egress-restricted": "true",
    }


def tenant_env(name: str, db_name: str, path_prefix: str, host: str) -> list:
    """Container env for a tenant n8n instance.

    N8N_BLOCK_ENV_ACCESS_IN_NODE stops Code nodes reading process.env, which
    holds the shared database password.
    """
    return [
        client.V1EnvVar(name="N8N_HOST", value="n8n.robotika.cloud"),
        client.V1EnvVar(name="N8N_PROTOCOL", value="https"),
        client.V1EnvVar(name="N8N_PATH_PREFIX", value=path_prefix),
        client.V1EnvVar(name="WEBHOOK_URL", value=f"https://{host}/"),
        client.V1EnvVar(name="N8N_BASIC_AUTH_ACTIVE", value="true"),
        client.V1EnvVar(
            name="N8N_BASIC_AUTH_USER",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name=f"{name}-secret", key="username"
                )
            ),
        ),
        client.V1EnvVar(
            name="N8N_BASIC_AUTH_PASSWORD",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name=f"{name}-secret", key="password"
                )
            ),
        ),
        client.V1EnvVar(name="DB_TYPE", value="postgresdb"),
        client.V1EnvVar(name="DB_POSTGRESDB_HOST", value="postgresql-service"),
        client.V1EnvVar(name="DB_POSTGRESDB_PORT", value="5432"),
        client.V1EnvVar(name="DB_POSTGRESDB_DATABASE", value=db_name),
        client.V1EnvVar(
            name="DB_POSTGRESDB_USER",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name=f"{name}-secret", key="db-user"
                )
            ),
        ),
        client.V1EnvVar(
            name="DB_POSTGRESDB_PASSWORD",
            value_from=client.V1EnvVarSource(
                secret_key_ref=client.V1SecretKeySelector(
                    name=f"{name}-secret", key="db-password"
                )
            ),
        ),
        client.V1EnvVar(name="GENERIC_TIMEZONE", value="Europe/Madrid"),
        client.V1EnvVar(name="N8N_METRICS", value="true"),
        client.V1EnvVar(name="N8N_BLOCK_ENV_ACCESS_IN_NODE", value="true"),
        client.V1EnvVar(name="EXECUTIONS_DATA_PRUNE", value="true"),
        client.V1EnvVar(name="EXECUTIONS_DATA_MAX_AGE", value="168"),
    ]


def tenant_pvc(name: str) -> "client.V1PersistentVolumeClaim":
    """Workflow storage for a tenant instance.

    PVC resources use V1VolumeResourceRequirements: with kubernetes>=30 the
    PVC spec rejects V1ResourceRequirements (pydantic model_type error), which
    broke every provision and re-provision until the class was corrected.
    """
    return client.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=client.V1ObjectMeta(name=f"{name}-workflows", namespace="nekazari"),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1VolumeResourceRequirements(
                requests={"storage": "10Gi"}
            ),
        ),
    )


def provision_n8n_tenant(tenant_id: str) -> dict:
    """Provision all K8s resources for a tenant's n8n instance.
    Returns dict with URL, credentials, and resource names.
    """
    _load_k8s_config()
    apps_v1 = _k8s_apps_v1()
    core_v1 = _k8s_core_v1()
    net_v1 = _k8s_networking_v1()
    auto_v1 = _k8s_autoscaling_v1()

    name = n8n_resource_name(tenant_id)
    db_name = n8n_db_name(tenant_id)
    host = n8n_host(tenant_id)
    path_prefix = f"/{sanitize_tenant_id(tenant_id)}"
    creds = generate_credentials()

    # 1. Create Secret (idempotent — skip if already exists from partial provision)
    try:
        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=f"{name}-secret", namespace="nekazari"),
            string_data={
                "username": creds["username"],
                "password": creds["password"],
                "api-key": creds["api_key"],
                "db-user": n8n_db_role(tenant_id),
                "db-password": creds["db_password"],
            },
        )
        core_v1.create_namespaced_secret("nekazari", secret)
    except client.ApiException as e:
        if e.status != 409:
            raise
        logger.info(f"Secret {name}-secret already exists, reusing")
        creds["db_password"] = _ensure_db_credentials(core_v1, name, n8n_db_role(tenant_id), creds["db_password"])

    # 2. Create PVC (idempotent)
    try:
        pvc = tenant_pvc(name)
        core_v1.create_namespaced_persistent_volume_claim("nekazari", pvc)
    except client.ApiException as e:
        if e.status == 409:
            logger.info(f"PVC {name}-workflows already exists, reusing")
        else:
            raise

    # 3. Create Deployment
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=name, namespace="nekazari"),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": name}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels=tenant_pod_labels(name, tenant_id)
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="n8n",
                            image=get_settings().n8n_instance_image,
                            ports=[client.V1ContainerPort(container_port=5678)],
                            env=tenant_env(name, db_name, path_prefix, host),
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "256Mi", "cpu": "100m"},
                                limits={"memory": "1Gi", "cpu": "500m"},
                            ),
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="workflows",
                                    mount_path="/home/node/.n8n",
                                )
                            ],
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="workflows",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=f"{name}-workflows"
                            ),
                        )
                    ],
                ),
            ),
        ),
    )
    try:
        apps_v1.create_namespaced_deployment("nekazari", deployment)
    except client.ApiException as e:
        if e.status == 409:
            logger.info(f"Deployment {name} already exists, updating")
            apps_v1.patch_namespaced_deployment(name, "nekazari", deployment)
        else:
            raise

    # 4. Create Service (idempotent)
    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=f"{name}-service", namespace="nekazari"),
        spec=client.V1ServiceSpec(
            selector={"app": name},
            ports=[client.V1ServicePort(port=5678, target_port=5678)],
        ),
    )
    try:
        core_v1.create_namespaced_service("nekazari", service)
    except client.ApiException as e:
        if e.status == 409:
            logger.info(f"Service {name}-service already exists, reusing")
        else:
            raise

    # 5. NO per-tenant Ingress — routed via api-gateway path proxy (n8n.robotika.cloud/<tenant>)

    # 6. Create HPA (idempotent)
    hpa = client.V1HorizontalPodAutoscaler(
        api_version="autoscaling/v1",
        kind="HorizontalPodAutoscaler",
        metadata=client.V1ObjectMeta(name=f"{name}-hpa", namespace="nekazari"),
        spec=client.V1HorizontalPodAutoscalerSpec(
            scale_target_ref=client.V1CrossVersionObjectReference(
                api_version="apps/v1",
                kind="Deployment",
                name=name,
            ),
            min_replicas=1,
            max_replicas=3,
            target_cpu_utilization_percentage=70,
        ),
    )
    try:
        auto_v1.create_namespaced_horizontal_pod_autoscaler("nekazari", hpa)
    except client.ApiException as e:
        if e.status == 409:
            logger.info(f"HPA {name}-hpa already exists, reusing")
        else:
            raise

    # 7. Create database and its owning role (password = the tenant Secret's)
    create_n8n_tenant_db(tenant_id, creds["db_password"])

    # 8. Save config
    url = f"https://{host}"
    config_data = {
        "n8n_url": url,
        "n8n_api_key_encrypted": encrypt_token(creds["api_key"]),
        "provisioning_status": "active",
        "provisioned_at": None,
        "suspended_at": None,
        "stripe_subscription_id": None,
        "n8n_admin_username": creds["username"],
        "n8n_admin_password_encrypted": encrypt_token(creds["password"]),
        "n8n_db_name": db_name,
    }
    upsert_tenant_config(tenant_id, config_data)

    return {
        "url": url,
        "username": creds["username"],
        "password": creds["password"],
        "api_key": creds["api_key"],
        "db_name": db_name,
    }


def suspend_n8n_tenant(tenant_id: str) -> bool:
    """Scale the tenant's n8n deployment to 0 replicas."""
    _load_k8s_config()
    apps_v1 = _k8s_apps_v1()
    name = n8n_resource_name(tenant_id)

    try:
        apps_v1.patch_namespaced_deployment(
            name=name,
            namespace=NAMESPACE,
            body={"spec": {"replicas": 0}},
        )

        config = get_tenant_config(tenant_id) or {}
        config["provisioning_status"] = "suspended"
        config["suspended_at"] = datetime.now(timezone.utc).isoformat()
        upsert_tenant_config(tenant_id, config)
        return True
    except Exception as e:
        logger.error(f"Failed to suspend n8n for tenant {tenant_id}: {e}")
        return False


def reactivate_n8n_tenant(tenant_id: str) -> bool:
    """Scale the tenant's n8n deployment back to 1 replica."""
    _load_k8s_config()
    apps_v1 = _k8s_apps_v1()
    name = n8n_resource_name(tenant_id)

    try:
        apps_v1.patch_namespaced_deployment(
            name=name,
            namespace=NAMESPACE,
            body={"spec": {"replicas": 1}},
        )

        config = get_tenant_config(tenant_id) or {}
        config["provisioning_status"] = "active"
        config["suspended_at"] = None
        upsert_tenant_config(tenant_id, config)
        return True
    except Exception as e:
        logger.error(f"Failed to reactivate n8n for tenant {tenant_id}: {e}")
        return False


def start_grace_period_n8n_tenant(tenant_id: str) -> bool:
    """Suspend the deployment and mark as grace_period."""
    _load_k8s_config()
    apps_v1 = _k8s_apps_v1()
    name = n8n_resource_name(tenant_id)

    try:
        apps_v1.patch_namespaced_deployment(
            name=name,
            namespace=NAMESPACE,
            body={"spec": {"replicas": 0}},
        )

        config = get_tenant_config(tenant_id) or {}
        config["provisioning_status"] = "grace_period"
        config["suspended_at"] = datetime.now(timezone.utc).isoformat()
        upsert_tenant_config(tenant_id, config)
        return True
    except Exception as e:
        logger.error(f"Failed to start grace period for tenant {tenant_id}: {e}")
        return False


def purge_n8n_tenant(tenant_id: str) -> bool:
    """Delete ALL K8s resources and DB for a tenant's n8n instance."""
    _load_k8s_config()
    apps_v1 = _k8s_apps_v1()
    core_v1 = _k8s_core_v1()
    net_v1 = _k8s_networking_v1()
    auto_v1 = _k8s_autoscaling_v1()
    name = n8n_resource_name(tenant_id)

    errors = []

    resources = [
        ("HPA", lambda: auto_v1.delete_namespaced_horizontal_pod_autoscaler(
            f"{name}-hpa", NAMESPACE)),
        ("Ingress", lambda: net_v1.delete_namespaced_ingress(
            f"{name}-ingress", NAMESPACE)),
        ("Deployment", lambda: apps_v1.delete_namespaced_deployment(
            name, NAMESPACE)),
        ("Service", lambda: core_v1.delete_namespaced_service(
            f"{name}-service", NAMESPACE)),
        ("PVC", lambda: core_v1.delete_namespaced_persistent_volume_claim(
            f"{name}-workflows", NAMESPACE)),
        ("Secret", lambda: core_v1.delete_namespaced_secret(
            f"{name}-secret", NAMESPACE)),
    ]

    for resource_name, delete_fn in resources:
        try:
            delete_fn()
        except client.ApiException as e:
            if e.status == 404:
                continue
            errors.append(f"{resource_name}: {e}")

    if not drop_n8n_tenant_db(tenant_id):
        errors.append("DB drop failed")

    if errors:
        logger.error(f"Purge errors for tenant {tenant_id}: {errors}")
        return False

    config = get_tenant_config(tenant_id) or {}
    config["provisioning_status"] = "none"
    config["n8n_url"] = None
    config["n8n_api_key_encrypted"] = None
    config["suspended_at"] = None
    config["stripe_subscription_id"] = None
    upsert_tenant_config(tenant_id, config)

    return True
