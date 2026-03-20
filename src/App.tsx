/**
 * n8n Integration Hub - Main App Component
 * 
 * This module provides workflow orchestration capabilities connecting n8n
 * with Nekazari platform services including:
 * - Sentinel/NDVI satellite analysis
 * - AI predictions (production, pests)
 * - Multi-channel notifications
 * - Odoo ERP synchronization
 * - ROS2 agricultural robotics
 */

import React, { useState } from 'react';
import { 
  Workflow, 
  Satellite, 
  Brain, 
  Bell, 
  Database, 
  Bot, 
  Play, 
  Pause,
  RefreshCw,
  Settings,
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  Info
} from 'lucide-react';
import './index.css';

// Export viewerSlots for host integration
export { viewerSlots } from './slots/index';

// Integration status type
interface IntegrationStatus {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: 'connected' | 'disconnected' | 'error' | 'pending';
  lastSync?: string;
  description: string;
}

// Workflow type
interface WorkflowItem {
  id: string;
  name: string;
  active: boolean;
  lastExecution?: string;
  status: 'success' | 'error' | 'running' | 'idle';
  executions: number;
}

const ModuleApp: React.FC = () => {
  const [integrations] = useState<IntegrationStatus[]>([
    {
      id: 'n8n',
      name: 'n8n Core',
      icon: <Workflow className="w-5 h-5" />,
      status: 'connected',
      lastSync: new Date().toISOString(),
      description: 'Workflow automation engine'
    },
    {
      id: 'sentinel',
      name: 'Sentinel/NDVI',
      icon: <Satellite className="w-5 h-5" />,
      status: 'connected',
      lastSync: new Date().toISOString(),
      description: 'Satellite imagery and vegetation indices'
    },
    {
      id: 'intelligence',
      name: 'Intelligence AI',
      icon: <Brain className="w-5 h-5" />,
      status: 'connected',
      lastSync: new Date().toISOString(),
      description: 'ML predictions and analysis'
    },
    {
      id: 'notifications',
      name: 'Notifications',
      icon: <Bell className="w-5 h-5" />,
      status: 'connected',
      lastSync: new Date().toISOString(),
      description: 'Multi-channel alerts (email, push, SMS)'
    },
    {
      id: 'odoo',
      name: 'Odoo ERP',
      icon: <Database className="w-5 h-5" />,
      status: 'pending',
      description: 'Farm management and inventory'
    },
    {
      id: 'ros2',
      name: 'ROS2 Robotics',
      icon: <Bot className="w-5 h-5" />,
      status: 'pending',
      description: 'Agricultural robot control'
    },
  ]);

  const [workflows, setWorkflows] = useState<WorkflowItem[]>([
    {
      id: '1',
      name: 'NDVI Alert Pipeline',
      active: true,
      lastExecution: new Date().toISOString(),
      status: 'success',
      executions: 156
    },
    {
      id: '2',
      name: 'Production Prediction',
      active: true,
      lastExecution: new Date().toISOString(),
      status: 'running',
      executions: 89
    },
    {
      id: '3',
      name: 'Pest Detection Alerts',
      active: true,
      lastExecution: new Date().toISOString(),
      status: 'success',
      executions: 234
    },
    {
      id: '4',
      name: 'Odoo Sync - Harvests',
      active: false,
      status: 'idle',
      executions: 0
    },
    {
      id: '5',
      name: 'Robot Mission Scheduler',
      active: false,
      status: 'idle',
      executions: 0
    },
  ]);

  const [loading, setLoading] = useState(false);

  const getStatusColor = (status: IntegrationStatus['status']) => {
    switch (status) {
      case 'connected': return 'text-green-500 bg-green-100';
      case 'disconnected': return 'text-gray-500 bg-gray-100';
      case 'error': return 'text-red-500 bg-red-100';
      case 'pending': return 'text-yellow-500 bg-yellow-100';
    }
  };

  const getStatusIcon = (status: IntegrationStatus['status']) => {
    switch (status) {
      case 'connected': return <CheckCircle2 className="w-4 h-4" />;
      case 'disconnected': return <AlertCircle className="w-4 h-4" />;
      case 'error': return <AlertCircle className="w-4 h-4" />;
      case 'pending': return <Clock className="w-4 h-4" />;
    }
  };

  const getWorkflowStatusColor = (status: WorkflowItem['status']) => {
    switch (status) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'running': return 'bg-blue-500 animate-pulse';
      case 'idle': return 'bg-gray-400';
    }
  };

  const toggleWorkflow = (id: string) => {
    setWorkflows(prev => prev.map(w => 
      w.id === id ? { ...w, active: !w.active } : w
    ));
  };

  const refreshStatus = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
  };

  return (
    <div className="w-full bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg n8n-gradient">
                <Workflow className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">n8n Integration Hub</h1>
                <p className="text-xs text-gray-500">Workflow Orchestration for Nekazari</p>
              </div>
              <div className="flex items-center gap-2 px-3 py-1 bg-orange-50 border border-orange-200 rounded-full ml-4">
                <Info className="w-4 h-4 text-orange-600" />
                <span className="text-xs text-orange-700">Standalone Mode</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={refreshStatus}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <a 
                href="https://n8n.nekazari.artotxiki.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors"
              >
                <Settings className="w-4 h-4" />
                Open n8n
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100">
                <Activity className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {integrations.filter(i => i.status === 'connected').length}
                </p>
                <p className="text-sm text-gray-500">Active Integrations</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Workflow className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {workflows.filter(w => w.active).length}
                </p>
                <p className="text-sm text-gray-500">Active Workflows</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100">
                <Play className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {workflows.reduce((acc, w) => acc + w.executions, 0)}
                </p>
                <p className="text-sm text-gray-500">Total Executions</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-100">
                <CheckCircle2 className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {workflows.filter(w => w.status === 'success').length}
                </p>
                <p className="text-sm text-gray-500">Successful Today</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Integrations Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Service Integrations</h2>
              <p className="text-sm text-gray-500">Connected platform services</p>
            </div>
            <div className="p-6 space-y-3">
              {integrations.map(integration => (
                <div 
                  key={integration.id}
                  className={`integration-card ${
                    integration.status === 'connected' ? 'integration-card-active' : 
                    integration.status === 'error' ? 'integration-card-error' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${getStatusColor(integration.status)}`}>
                        {integration.icon}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{integration.name}</p>
                        <p className="text-xs text-gray-500">{integration.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${getStatusColor(integration.status)}`}>
                        {getStatusIcon(integration.status)}
                        {integration.status}
                      </span>
                    </div>
                  </div>
                  {integration.lastSync && (
                    <p className="text-xs text-gray-400 mt-2">
                      Last sync: {new Date(integration.lastSync).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Workflows Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Active Workflows</h2>
              <p className="text-sm text-gray-500">Automated pipelines and triggers</p>
            </div>
            <div className="p-6 space-y-3">
              {workflows.map(workflow => (
                <div 
                  key={workflow.id}
                  className="p-4 rounded-lg border border-gray-200 bg-white hover:border-orange-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${getWorkflowStatusColor(workflow.status)}`} />
                      <div>
                        <p className="font-medium text-gray-900">{workflow.name}</p>
                        <p className="text-xs text-gray-500">
                          {workflow.executions} executions
                          {workflow.lastExecution && ` · Last: ${new Date(workflow.lastExecution).toLocaleString()}`}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => toggleWorkflow(workflow.id)}
                      className={`p-2 rounded-lg transition-colors ${
                        workflow.active 
                          ? 'bg-green-100 text-green-600 hover:bg-green-200' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {workflow.active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Info Banner */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> This standalone view is for development and monitoring. 
                In production, the module integrates into the Unified Viewer via slots for 
                real-time workflow status and execution monitoring.
              </p>
              <p className="text-xs text-blue-600 mt-2">
                Access the full n8n interface at{' '}
                <a href="https://n8n.nekazari.artotxiki.com" className="underline" target="_blank" rel="noopener">
                  n8n.nekazari.artotxiki.com
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// CRITICAL: Export as default - required for Module Federation
export default ModuleApp;
