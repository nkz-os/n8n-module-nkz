# n8n Integration Hub - Nekazari Module

> **Workflow Orchestration Hub** - External module that connects n8n with Nekazari platform services for agricultural automation.

## Overview

The n8n Integration Hub is an external module for the Nekazari Platform that provides a centralized interface for:

- **n8n Workflow Management** - Monitor, execute, and control automation workflows
- **Sentinel/NDVI Analysis** - Trigger satellite imagery analysis and vegetation index calculations
- **Intelligence AI** - ML predictions for production, pest detection, and disease risk
- **Multi-channel Notifications** - Email, push, SMS, Telegram, and webhook alerts
- **Odoo ERP Integration** - Synchronize farm management data with Odoo
- **ROS2 Robotics** - Control and monitor agricultural robots

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      n8n Integration Hub                            │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (React + Module Federation)                               │
│  ├── Workflow Dashboard                                             │
│  ├── Execution Monitor (Bottom Panel Slot)                          │
│  ├── Workflow Status Panel (Context Panel Slot)                     │
│  └── Integration Status (Layer Toggle Slot)                         │
├─────────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI)                                                  │
│  ├── /n8n        - Workflow & execution management                  │
│  ├── /sentinel   - NDVI analysis triggers                           │
│  ├── /intelligence - AI prediction requests                         │
│  ├── /notifications - Alert orchestration                           │
│  ├── /odoo       - ERP synchronization                              │
│  ├── /ros2       - Robot control & telemetry                        │
│  └── /webhooks   - Inbound/outbound webhook config                  │
├─────────────────────────────────────────────────────────────────────┤
│  Integrations                                                       │
│  ├── n8n (n8n-service:5678)                                         │
│  ├── Intelligence Module (intelligence-api-service:8000)            │
│  ├── NDVI Worker (ndvi-worker-service:8000)                         │
│  ├── Email Service (email-service:8000)                             │
│  ├── ROS2 Bridge (ros2-fiware-bridge-service:8000)                  │
│  ├── Odoo ERP (external)                                            │
│  └── Orion-LD (orion-ld-service:1026)                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose (for containerized development)

### Local Development

```bash
# Clone the repository
git clone https://github.com/nkz-os/n8n-module-nkz.git
cd n8n-module-nkz

# Install frontend dependencies
npm install

# Start frontend dev server
npm run dev  # http://localhost:5003

# In another terminal, start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Docker Development

```bash
docker-compose up
# Frontend: http://localhost:5003
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/api/n8n-nkz/docs
```

## Project Structure

```
n8n-module-nkz/
├── src/                          # Frontend React application
│   ├── App.tsx                   # Main standalone app
│   ├── components/slots/         # Unified Viewer slot components
│   │   ├── WorkflowStatusPanel.tsx
│   │   ├── ExecutionMonitor.tsx
│   │   └── IntegrationStatus.tsx
│   ├── services/api.ts           # SDK-based API client
│   ├── hooks/useUIKit.tsx        # UI Kit access hook
│   ├── slots/index.ts            # Slot registration
│   └── types/                    # TypeScript definitions
├── backend/                      # Python FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Environment configuration
│   │   ├── middleware/          # JWT auth middleware
│   │   └── routers/             # API routes
│   │       ├── health.py        # Health checks
│   │       ├── n8n.py           # n8n workflow management
│   │       ├── sentinel.py      # NDVI analysis
│   │       ├── intelligence.py  # AI predictions
│   │       ├── notifications.py # Alert orchestration
│   │       ├── odoo.py          # ERP integration
│   │       ├── ros2.py          # Robotics control
│   │       └── webhooks.py      # Webhook management
│   ├── tests/                   # Pytest tests
│   ├── Dockerfile               # Backend container
│   └── requirements.txt         # Python dependencies
├── frontend/                    # Frontend Docker config
│   ├── Dockerfile
│   └── nginx.conf
├── k8s/                         # Kubernetes manifests
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   └── registration.sql
├── .github/workflows/           # CI/CD
│   └── build-push.yml
├── manifest.json                # Module metadata
├── docker-compose.yml           # Local development
├── vite.config.ts              # Module Federation config
└── env.example                  # Environment template
```

## API Endpoints

### n8n Workflows
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/n8n/workflows` | GET | List all workflows |
| `/n8n/workflows/{id}` | GET | Get workflow details |
| `/n8n/workflows/{id}/active` | PUT | Toggle workflow active state |
| `/n8n/workflows/{id}/execute` | POST | Execute workflow manually |
| `/n8n/executions` | GET | List executions |
| `/n8n/webhooks` | GET | List registered webhooks |

### Sentinel/NDVI
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sentinel/analyze` | POST | Request satellite analysis |
| `/sentinel/parcels/{id}/results` | GET | Get analysis results |
| `/sentinel/alerts` | GET | Get active NDVI alerts |
| `/sentinel/parcels/{id}/thresholds` | PUT | Set alert thresholds |

### Intelligence AI
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/intelligence/predict` | POST | Request AI prediction |
| `/intelligence/predictions/{id}` | GET | Get prediction result |
| `/intelligence/entities/{id}/predictions` | GET | List entity predictions |
| `/intelligence/webhook` | POST | Trigger via webhook |
| `/intelligence/plugins` | GET | List available models |

### Notifications
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/send` | POST | Send notification |
| `/notifications/templates` | GET | Get templates |
| `/notifications/test` | POST | Test channel |

### Odoo ERP
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/odoo/status` | GET | Get sync status |
| `/odoo/sync` | POST | Trigger sync |
| `/odoo/parcels` | GET | Get synced parcels |
| `/odoo/harvests` | GET | Get harvest records |
| `/odoo/push/{model}` | POST | Push data to Odoo |

### ROS2 Robotics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ros2/robots` | GET | List connected robots |
| `/ros2/robots/{id}` | GET | Get robot details |
| `/ros2/commands` | POST | Send robot command |
| `/ros2/missions` | GET | List missions |
| `/ros2/missions` | POST | Create mission |

### Webhooks
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks` | GET | List webhook configs |
| `/webhooks` | POST | Create webhook |
| `/webhooks/{id}` | PUT | Update webhook |
| `/webhooks/{id}` | DELETE | Delete webhook |
| `/webhooks/{id}/test` | POST | Test webhook |
| `/webhooks/inbound` | POST | Receive webhook (no auth) |

## Viewer Slots

The module integrates into the Nekazari Unified Viewer via three slots:

### 1. Integration Status (Layer Toggle)
Quick status overview of all connected services with health indicators.

### 2. Workflow Status Panel (Context Panel)
Shows relevant workflows and quick actions when an entity is selected.

### 3. Execution Monitor (Bottom Panel)
Real-time timeline of workflow executions with filtering and status.

## Deployment

### 1. Build Docker Images

```bash
# Build via CI/CD (recommended)
git tag v1.0.0
git push origin v1.0.0

# Or build manually
docker build -f frontend/Dockerfile -t n8n-nkz-frontend:v1.0.0 .
docker build -f backend/Dockerfile -t n8n-nkz-backend:v1.0.0 ./backend
```

### 2. Deploy to Kubernetes

```bash
# Apply deployments
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Register module in database
kubectl exec -it <postgres-pod> -n nekazari -- psql -U nekazari -d nekazari -f /path/to/k8s/registration.sql
```

### 3. Update Ingress

Add to `nekazari-public/k8s/core/networking/ingress.yaml`:

```yaml
# API route
- path: /api/n8n-nkz
  pathType: Prefix
  backend:
    service:
      name: n8n-nkz-api-service
      port:
        number: 8000

# Frontend route (MUST come before /modules)
- path: /modules/n8n-nkz
  pathType: Prefix
  backend:
    service:
      name: n8n-nkz-frontend-service
      port:
        number: 80
```

### 4. n8n Service Configuration

**Important**: The n8n service **must** be configured to use a **subdomain** (e.g., `n8n.example.com`), **not** a subdirectory path (e.g., `example.com/n8n`).

This is a requirement because:
- n8n requires proper hostname configuration for webhooks and external integrations
- Subdirectory routing causes issues with n8n's internal routing and asset loading
- n8n's authentication and session management work correctly only with subdomain configuration

**Deployment Steps**:

1. **Configure DNS**: Create a DNS record for the n8n subdomain pointing to your server IP address.

2. **Update n8n Deployment**: In the n8n deployment configuration (`nekazari-public/k8s/addons/iot/n8n-deployment.yaml`), ensure the following environment variables are set:
   ```yaml
   - name: N8N_HOST
     value: "n8n.yourdomain.com"  # Use your actual subdomain
   - name: N8N_PROTOCOL
     value: "https"
   - name: WEBHOOK_URL
     value: "https://n8n.yourdomain.com/"
   ```

3. **Create n8n Ingress**: Configure a dedicated Ingress resource for n8n with the subdomain:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: n8n-ingress
     namespace: nekazari
     annotations:
       cert-manager.io/cluster-issuer: "letsencrypt-prod"
   spec:
     ingressClassName: nginx
     tls:
     - hosts:
       - n8n.yourdomain.com  # Use your actual subdomain
       secretName: n8n-tls
     rules:
     - host: n8n.yourdomain.com  # Use your actual subdomain
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: n8n-service
               port:
                 number: 5678
   ```

4. **Update Module Configuration**: Ensure the module's environment variables (in `k8s/backend-deployment.yaml` and `env.example`) point to the correct n8n subdomain URL for external access (e.g., `https://n8n.yourdomain.com`), while internal service-to-service communication uses the Kubernetes service name (`http://n8n-service:5678`).

**Note**: When deploying to a different server or domain, update all references to the n8n subdomain in both the n8n deployment configuration and this module's configuration files.

### 5. Authentication Configuration

**Current Setup**: n8n is configured with basic authentication (username/password).

**Recommended**: Integrate n8n with Keycloak for Single Sign-On (SSO) to provide a unified authentication experience across the platform.

**Options for Keycloak Integration**:

1. **OAuth2 Proxy** (Recommended for Community Edition):
   - Deploy OAuth2 Proxy as a sidecar or middleware that validates Keycloak JWT tokens
   - Users authenticate via Keycloak, and OAuth2 Proxy forwards validated requests to n8n
   - Requires additional deployment but works with n8n Community Edition
   - Configuration example:
     ```yaml
     # OAuth2 Proxy configuration
     - name: OAUTH2_PROXY_PROVIDER
       value: "keycloak-oidc"
     - name: OAUTH2_PROXY_OIDC_ISSUER_URL
       value: "https://yourdomain.com/auth/realms/nekazari"
     - name: OAUTH2_PROXY_CLIENT_ID
       value: "n8n-client"
     - name: OAUTH2_PROXY_CLIENT_SECRET
       valueFrom:
         secretKeyRef:
           name: keycloak-secret
           key: n8n-client-secret
     ```

2. **n8n Enterprise with SAML 2.0**:
   - n8n Enterprise edition supports SAML 2.0 SSO
   - Configure Keycloak as SAML Identity Provider
   - Provides native SSO integration
   - Requires n8n Enterprise license

3. **Basic Auth (Current/Temporary)**:
   - Simple username/password authentication
   - Users need separate credentials for n8n
   - Not recommended for production with Keycloak-enabled platform

**Keycloak Client Configuration**:

If using OAuth2 Proxy or SAML, create a Keycloak client for n8n:

```json
{
  "clientId": "n8n-client",
  "name": "n8n Workflow Automation",
  "enabled": true,
  "publicClient": false,
  "redirectUris": [
    "https://n8n.yourdomain.com/oauth2/callback"
  ],
  "webOrigins": [
    "https://n8n.yourdomain.com"
  ],
  "protocol": "openid-connect"
}
```

**Note**: The current deployment uses basic authentication. To enable Keycloak SSO, you'll need to either:
- Deploy OAuth2 Proxy and configure it to validate Keycloak tokens
- Upgrade to n8n Enterprise and configure SAML 2.0
- Keep basic auth as a temporary solution until SSO is implemented

## Environment Variables

See `env.example` for all available configuration options.

Key variables:
- `N8N_URL` - n8n service URL
- `N8N_API_KEY` - n8n API key (optional)
- `INTELLIGENCE_URL` - Intelligence module URL
- `ODOO_URL` - Odoo ERP URL (if using)
- `ROS2_BRIDGE_URL` - ROS2 bridge service URL

## Use Cases

### 1. NDVI Monitoring Pipeline
```
Sentinel-2 → NDVI Worker → Orion-LD → n8n Workflow → Alert
```

### 2. Production Prediction
```
User Request → n8n Hub → Intelligence Module → Prediction → Notification
```

### 3. Robot Mission Automation
```
NDVI Alert → n8n Workflow → Create Mission → ROS2 Bridge → Robot
```

### 4. ERP Sync
```
Harvest Data → n8n Workflow → n8n Hub → Odoo Push → ERP Updated
```

## License

AGPL-3.0 - Same as Nekazari Platform

## Support

- GitHub Issues: https://github.com/nkz-os/n8n-module-nkz
- Email: nekazari@artotxiki.com
