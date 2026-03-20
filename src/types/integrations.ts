/**
 * Type definitions for n8n Integration Hub
 */

type GeoPoint = {
  type: 'Point';
  coordinates: [number, number];
};

type GeoPolygon = {
  type: 'Polygon';
  coordinates: number[][][];
};

// ============================================================================
// n8n Types
// ============================================================================

export interface N8nWorkflow {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
  nodes: N8nNode[];
  connections: Record<string, any>;
  settings?: Record<string, any>;
  tags?: string[];
}

export interface N8nNode {
  id: string;
  name: string;
  type: string;
  position: [number, number];
  parameters?: Record<string, any>;
}

export interface N8nExecution {
  id: string;
  workflowId: string;
  finished: boolean;
  mode: 'manual' | 'trigger' | 'webhook';
  startedAt: string;
  stoppedAt?: string;
  status: 'success' | 'error' | 'running' | 'waiting';
  data?: any;
}

export interface N8nWebhook {
  id: string;
  workflowId: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  webhookPath: string;
  isForm: boolean;
  nodeId: string;
  nodeName: string;
}

// ============================================================================
// Sentinel/NDVI Types
// ============================================================================

export interface SentinelAnalysisRequest {
  parcelId: string;
  startDate: string;
  endDate: string;
  indices: VegetationIndex[];
  cloudCoverMax?: number;
}

export type VegetationIndex = 'NDVI' | 'NDWI' | 'EVI' | 'SAVI' | 'NDRE';

export interface SentinelAnalysisResult {
  parcelId: string;
  date: string;
  index: VegetationIndex;
  value: number;
  cloudCover: number;
  bounds: GeoPolygon;
  imageUrl?: string;
}

export interface NDVIAlert {
  id: string;
  parcelId: string;
  alertType: 'low_ndvi' | 'rapid_decline' | 'anomaly';
  severity: 'low' | 'medium' | 'high' | 'critical';
  currentValue: number;
  threshold: number;
  message: string;
  createdAt: string;
}

// ============================================================================
// Intelligence AI Types
// ============================================================================

export interface PredictionRequest {
  type: 'production' | 'pest' | 'disease' | 'irrigation';
  entityId: string;
  entityType: string;
  parameters?: Record<string, any>;
}

export interface PredictionResult {
  id: string;
  type: string;
  entityId: string;
  prediction: any;
  confidence: number;
  model: string;
  createdAt: string;
  validUntil: string;
}

export interface ProductionPrediction {
  entityId: string;
  cropType: string;
  estimatedYield: number;
  yieldUnit: string;
  harvestWindow: {
    start: string;
    end: string;
  };
  confidence: number;
  factors: PredictionFactor[];
}

export interface PestPrediction {
  entityId: string;
  pestType: string;
  probability: number;
  severity: 'low' | 'medium' | 'high';
  recommendedActions: string[];
  riskFactors: PredictionFactor[];
}

export interface PredictionFactor {
  name: string;
  impact: 'positive' | 'negative' | 'neutral';
  value: number;
  description: string;
}

// ============================================================================
// Notification Types
// ============================================================================

export interface NotificationRequest {
  channels: NotificationChannel[];
  recipients: string[];
  template: string;
  data: Record<string, any>;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  scheduledAt?: string;
}

export type NotificationChannel = 'email' | 'push' | 'sms' | 'telegram' | 'webhook';

export interface NotificationResult {
  id: string;
  channel: NotificationChannel;
  recipient: string;
  status: 'sent' | 'delivered' | 'failed' | 'pending';
  sentAt?: string;
  deliveredAt?: string;
  error?: string;
}

export interface NotificationTemplate {
  id: string;
  name: string;
  channel: NotificationChannel;
  subject?: string;
  body: string;
  variables: string[];
}

// ============================================================================
// Odoo ERP Types
// ============================================================================

export interface OdooParcel {
  id: number;
  name: string;
  area: number;
  areaUnit: string;
  cropType: string;
  status: string;
  location: GeoPoint;
}

export interface OdooHarvest {
  id: number;
  parcelId: number;
  cropType: string;
  quantity: number;
  quantityUnit: string;
  quality: string;
  harvestDate: string;
  workerId?: number;
}

export interface OdooInventoryItem {
  id: number;
  productId: number;
  productName: string;
  quantity: number;
  unit: string;
  location: string;
  lotNumber?: string;
  expirationDate?: string;
}

export interface OdooSyncStatus {
  lastSync: string;
  status: 'synced' | 'syncing' | 'error';
  entitiesSynced: number;
  errors?: string[];
}

// ============================================================================
// ROS2 Robotics Types
// ============================================================================

export interface ROS2Robot {
  id: string;
  name: string;
  type: 'tractor' | 'drone' | 'harvester' | 'sprayer' | 'seeder';
  status: 'idle' | 'working' | 'charging' | 'error' | 'maintenance';
  batteryLevel?: number;
  position?: GeoPoint;
  currentMission?: string;
  lastSeen: string;
}

export interface ROS2Mission {
  id: string;
  name: string;
  robotId: string;
  type: 'spray' | 'harvest' | 'seed' | 'survey' | 'transport';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  parcelIds: string[];
  parameters: Record<string, any>;
  progress: number;
  startedAt?: string;
  completedAt?: string;
}

export interface ROS2Command {
  robotId: string;
  command: 'start' | 'stop' | 'pause' | 'resume' | 'return_home' | 'emergency_stop';
  parameters?: Record<string, any>;
}

export interface ROS2Telemetry {
  robotId: string;
  timestamp: string;
  position: GeoPoint;
  heading: number;
  speed: number;
  batteryLevel: number;
  sensors: Record<string, any>;
}

// ============================================================================
// Integration Status Types
// ============================================================================

export interface IntegrationHealth {
  id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  lastCheck: string;
  latency?: number;
  message?: string;
  details?: Record<string, any>;
}

export interface WebhookConfig {
  id: string;
  name: string;
  url: string;
  secret?: string;
  events: string[];
  active: boolean;
  lastTriggered?: string;
  failureCount: number;
}
