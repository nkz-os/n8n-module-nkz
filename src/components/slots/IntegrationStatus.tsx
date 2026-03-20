/**
 * Integration Status - Layer Toggle Slot
 * 
 * Quick status overview of all integrations in the layer panel.
 * Provides at-a-glance health status of connected services.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '@nekazari/sdk';
import { useUIKit } from '@/hooks/useUIKit';
import { useModuleApi } from '@/services/api';
import { 
  Workflow, 
  Satellite, 
  Brain, 
  Bell, 
  Database, 
  Bot,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  ExternalLink
} from 'lucide-react';

interface IntegrationStatusProps {
  className?: string;
}

interface Integration {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  latency?: number;
}

export const IntegrationStatus: React.FC<IntegrationStatusProps> = ({ className }) => {
  const { Card } = useUIKit();
  const { isAuthenticated } = useAuth();
  const api = useModuleApi();

  const [integrations, setIntegrations] = useState<Integration[]>([
    { id: 'n8n', name: 'n8n', icon: <Workflow className="w-3 h-3" />, status: 'unknown' },
    { id: 'sentinel', name: 'NDVI', icon: <Satellite className="w-3 h-3" />, status: 'unknown' },
    { id: 'intelligence', name: 'AI', icon: <Brain className="w-3 h-3" />, status: 'unknown' },
    { id: 'notifications', name: 'Alerts', icon: <Bell className="w-3 h-3" />, status: 'unknown' },
    { id: 'odoo', name: 'ERP', icon: <Database className="w-3 h-3" />, status: 'unknown' },
    { id: 'ros2', name: 'Robots', icon: <Bot className="w-3 h-3" />, status: 'unknown' },
  ]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const checkHealth = async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      const healthData = await api.getIntegrationsHealth();
      
      setIntegrations(prev => prev.map(integration => {
        const health = healthData.find(h => h.id === integration.id);
        return {
          ...integration,
          status: health?.status || 'unknown',
          latency: health?.latency,
        };
      }));
    } catch (err) {
      console.error('[IntegrationStatus] Error checking health:', err);
      // Set all to unknown on error
      setIntegrations(prev => prev.map(i => ({ ...i, status: 'unknown' as const })));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Check health every 60 seconds
    const interval = setInterval(checkHealth, 60000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'unhealthy': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle2 className="w-3 h-3 text-green-500" />;
      case 'degraded': return <AlertCircle className="w-3 h-3 text-yellow-500" />;
      case 'unhealthy': return <AlertCircle className="w-3 h-3 text-red-500" />;
      default: return <Clock className="w-3 h-3 text-gray-400" />;
    }
  };

  const healthyCount = integrations.filter(i => i.status === 'healthy').length;
  const totalCount = integrations.length;

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Card padding="sm" className={className}>
      {/* Compact Header */}
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-orange-100">
            <Workflow className="w-3 h-3 text-orange-600" />
          </div>
          <span className="text-xs font-medium text-slate-700">n8n Hub</span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Quick Status Dots */}
          <div className="flex items-center gap-0.5">
            {integrations.slice(0, 6).map(integration => (
              <div
                key={integration.id}
                className={`w-1.5 h-1.5 rounded-full ${getStatusColor(integration.status)}`}
                title={`${integration.name}: ${integration.status}`}
              />
            ))}
          </div>
          
          <span className="text-[10px] text-slate-500">
            {healthyCount}/{totalCount}
          </span>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              checkHealth();
            }}
            className="p-0.5 text-slate-400 hover:text-slate-600"
            disabled={loading}
            title="Refresh status"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <a
            href="https://n8n.nekazari.artotxiki.com"
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-0.5 text-orange-500 hover:text-orange-600"
            title="Open n8n"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-2 pt-2 border-t border-slate-100 space-y-1">
          {integrations.map(integration => (
            <div
              key={integration.id}
              className="flex items-center justify-between py-1"
            >
              <div className="flex items-center gap-2">
                <span className="text-slate-400">{integration.icon}</span>
                <span className="text-xs text-slate-600">{integration.name}</span>
              </div>
              <div className="flex items-center gap-1">
                {integration.latency && (
                  <span className="text-[10px] text-slate-400">{integration.latency}ms</span>
                )}
                {getStatusIcon(integration.status)}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

export default IntegrationStatus;
