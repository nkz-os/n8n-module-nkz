/**
 * Execution Monitor - Bottom Panel Slot
 * 
 * Timeline view of workflow executions with filtering and details.
 * Shows real-time execution status and history.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '@nekazari/sdk';
import { useUIKit } from '@/hooks/useUIKit';
import { useModuleApi } from '@/services/api';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw,
  AlertCircle,
  Filter,
  ChevronDown,
  ChevronUp,
  ExternalLink
} from 'lucide-react';

interface ExecutionMonitorProps {
  className?: string;
}

interface ExecutionItem {
  id: string;
  workflowId: string;
  workflowName: string;
  status: 'success' | 'error' | 'running' | 'waiting';
  startedAt: string;
  duration?: number;
  mode: string;
}

export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({ className }) => {
  const { Card } = useUIKit();
  const { isAuthenticated } = useAuth();
  const api = useModuleApi();

  const [executions, setExecutions] = useState<ExecutionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [expanded, setExpanded] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch executions
  const fetchExecutions = async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      await api.getExecutions({
        status: filter !== 'all' ? filter : undefined,
        limit: expanded ? 50 : 10
      });
      
      // Mock data for demo - would come from actual API
      const mockExecutions: ExecutionItem[] = [
        {
          id: '1',
          workflowId: 'wf-1',
          workflowName: 'NDVI Alert Pipeline',
          status: 'success',
          startedAt: new Date(Date.now() - 5*60*1000).toISOString(),
          duration: 3200,
          mode: 'trigger'
        },
        {
          id: '2',
          workflowId: 'wf-2',
          workflowName: 'Production Prediction',
          status: 'running',
          startedAt: new Date(Date.now() - 2*60*1000).toISOString(),
          mode: 'webhook'
        },
        {
          id: '3',
          workflowId: 'wf-3',
          workflowName: 'Pest Detection',
          status: 'success',
          startedAt: new Date(Date.now() - 15*60*1000).toISOString(),
          duration: 8500,
          mode: 'cron'
        },
        {
          id: '4',
          workflowId: 'wf-1',
          workflowName: 'NDVI Alert Pipeline',
          status: 'error',
          startedAt: new Date(Date.now() - 30*60*1000).toISOString(),
          duration: 1200,
          mode: 'trigger'
        },
        {
          id: '5',
          workflowId: 'wf-4',
          workflowName: 'Risk Notifications',
          status: 'success',
          startedAt: new Date(Date.now() - 60*60*1000).toISOString(),
          duration: 4500,
          mode: 'cron'
        },
      ];
      
      setExecutions(mockExecutions.filter(e => 
        filter === 'all' || e.status === filter
      ));
      setError(null);
    } catch (err: any) {
      console.error('[ExecutionMonitor] Error:', err);
      setError(err.message || 'Failed to load executions');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchExecutions();
    
    if (autoRefresh) {
      const interval = setInterval(fetchExecutions, 10000); // 10 seconds
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, filter, expanded, autoRefresh]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'running': return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'waiting': return <Clock className="w-4 h-4 text-yellow-500" />;
      default: return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-100';
      case 'error': return 'bg-red-100';
      case 'running': return 'bg-blue-100';
      case 'waiting': return 'bg-yellow-100';
      default: return 'bg-gray-100';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms/1000).toFixed(1)}s`;
    return `${(ms/60000).toFixed(1)}m`;
  };

  const formatTime = (iso: string) => {
    const date = new Date(iso);
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  if (!isAuthenticated) {
    return (
      <Card padding="sm" className={className}>
        <div className="flex items-center gap-2 text-amber-600">
          <AlertCircle className="w-4 h-4" />
          <span className="text-xs">Login required</span>
        </div>
      </Card>
    );
  }

  const runningCount = executions.filter(e => e.status === 'running').length;
  const errorCount = executions.filter(e => e.status === 'error').length;

  return (
    <Card padding="sm" className={`${className} overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-orange-500" />
            <span className="text-sm font-semibold text-slate-800">Executions</span>
          </div>
          
          {/* Status Summary */}
          <div className="flex items-center gap-2">
            {runningCount > 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
                <RefreshCw className="w-3 h-3 animate-spin" />
                {runningCount} running
              </span>
            )}
            {errorCount > 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">
                <XCircle className="w-3 h-3" />
                {errorCount} errors
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter */}
          <div className="flex items-center gap-1">
            <Filter className="w-3 h-3 text-slate-400" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-xs border-0 bg-transparent text-slate-600 focus:outline-none cursor-pointer"
            >
              <option value="all">All</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
              <option value="running">Running</option>
            </select>
          </div>

          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`p-1 rounded ${autoRefresh ? 'text-green-600' : 'text-slate-400'}`}
            title={autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          >
            <RefreshCw className={`w-3 h-3 ${autoRefresh ? 'animate-spin' : ''}`} />
          </button>

          {/* Expand/Collapse */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-slate-400 hover:text-slate-600"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          
          {/* Open n8n */}
          <a
            href="https://n8n.nekazari.artotxiki.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 text-orange-500 hover:text-orange-600"
            title="Open n8n"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded p-2 mb-2">
          <AlertCircle className="w-3 h-3" />
          <span className="text-xs">{error}</span>
        </div>
      )}

      {/* Executions Timeline */}
      <div className={`overflow-x-auto ${expanded ? 'max-h-64' : 'max-h-32'} overflow-y-auto`}>
        {loading && executions.length === 0 ? (
          <div className="flex items-center justify-center py-4">
            <RefreshCw className="w-4 h-4 text-orange-500 animate-spin" />
          </div>
        ) : executions.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-4">
            No executions found
          </div>
        ) : (
          <div className="flex gap-2 pb-2">
            {executions.map(execution => (
              <div
                key={execution.id}
                className={`flex-shrink-0 p-2 rounded-lg ${getStatusBg(execution.status)} min-w-[140px] cursor-pointer hover:opacity-80 transition-opacity`}
                title={`${execution.workflowName}\nStarted: ${new Date(execution.startedAt).toLocaleString()}\nDuration: ${formatDuration(execution.duration)}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {getStatusIcon(execution.status)}
                  <span className="text-xs text-slate-600">{formatTime(execution.startedAt)}</span>
                </div>
                <p className="text-xs font-medium text-slate-800 truncate">
                  {execution.workflowName}
                </p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-slate-500 uppercase">{execution.mode}</span>
                  <span className="text-[10px] text-slate-500">{formatDuration(execution.duration)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
};

export default ExecutionMonitor;
