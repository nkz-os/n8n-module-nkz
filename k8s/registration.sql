-- =============================================================================
-- n8n Integration Hub Module Registration
-- =============================================================================
-- Register n8n Integration Hub module in the marketplace_modules table
-- =============================================================================

INSERT INTO marketplace_modules (
    id,
    name,
    display_name,
    description,
    remote_entry_url,
    scope,
    exposed_module,
    version,
    author,
    category,
    route_path,
    label,
    module_type,
    required_plan_type,
    pricing_tier,
    is_local,
    is_active,
    required_roles,
    metadata
) VALUES (
    'n8n-nkz',
    'n8n-nkz',
    'n8n Integration Hub',
    'Workflow Orchestration Hub - Integrates n8n with Nekazari platform services including Sentinel/NDVI analysis, AI predictions, notifications, Odoo ERP, and ROS2 robotics',
    'https://nekazari.robotika.cloud/modules/n8n-nkz/assets/remoteEntry.js',
    'n8n_nkz',
    './App',
    '1.0.0',
    'Nekazari Team',
    'integration',
    '/n8n-hub',
    'n8n Integration Hub',
    'ADDON_CORE',
    'premium',
    'INCLUDED',
    false,
    true,
    ARRAY['TenantAdmin', 'PlatformAdmin'],
    '{
        "icon": "🔄",
        "color": "#FF6D00",
        "features": [
            "Workflow Management Dashboard",
            "Sentinel/NDVI Index Analysis Triggers",
            "Production & Pest Prediction Pipelines",
            "Multi-channel Notification Orchestration",
            "Odoo ERP Synchronization",
            "ROS2 Robot Command & Telemetry"
        ],
        "slots": {
            "layer-toggle": ["IntegrationStatus"],
            "context-panel": ["WorkflowStatusPanel"],
            "bottom-panel": ["ExecutionMonitor"]
        }
    }'::jsonb
) ON CONFLICT (id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    remote_entry_url = EXCLUDED.remote_entry_url,
    scope = EXCLUDED.scope,
    exposed_module = EXCLUDED.exposed_module,
    version = EXCLUDED.version,
    metadata = EXCLUDED.metadata,
    is_active = true,
    updated_at = NOW();
