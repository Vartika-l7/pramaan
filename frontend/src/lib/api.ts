import {
  Evidence,
  ForensicEvent,
  Entity,
  IntegrityStatus,
  Anomaly,
  Claim,
  SystemCapabilities,
} from '../types';

const BASE_URL = '/api';

export async function fetchIntegrityStatus(): Promise<IntegrityStatus> {
  const res = await fetch(`${BASE_URL}/integrity/status`);
  if (!res.ok) throw new Error('Failed to fetch integrity status');
  return res.json();
}

export async function verifyIntegrity(): Promise<IntegrityStatus> {
  const res = await fetch(`${BASE_URL}/integrity/verify`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run integrity verification');
  return res.json();
}

export async function fetchEvidenceList(): Promise<Evidence[]> {
  const res = await fetch(`${BASE_URL}/evidence`);
  if (!res.ok) throw new Error('Failed to fetch evidence list');
  return res.json();
}

export async function fetchEvidenceDetail(evidenceId: string): Promise<Evidence & { custody_events: any[] }> {
  const res = await fetch(`${BASE_URL}/evidence/${evidenceId}`);
  if (!res.ok) throw new Error('Failed to fetch evidence detail');
  return res.json();
}

export async function uploadEvidenceFile(file: File, sourceType?: string): Promise<Evidence> {
  const formData = new FormData();
  formData.append('file', file);
  if (sourceType) formData.append('source_type', sourceType);

  const res = await fetch(`${BASE_URL}/evidence`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload evidence');
  return res.json();
}

export async function fetchEvents(params?: {
  from?: string;
  to?: string;
  source?: string;
  actor?: string;
  kind?: string;
  limit?: number;
}): Promise<ForensicEvent[]> {
  const query = new URLSearchParams();
  if (params?.from) query.set('from', params.from);
  if (params?.to) query.set('to', params.to);
  if (params?.source) query.set('source', params.source);
  if (params?.actor) query.set('actor', params.actor);
  if (params?.kind) query.set('kind', params.kind);
  if (params?.limit) query.set('limit', params.limit.toString());

  const res = await fetch(`${BASE_URL}/events?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

export async function fetchEventSource(eventId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/events/${eventId}/source`);
  if (!res.ok) throw new Error('Failed to fetch event source context');
  return res.json();
}

export async function fetchEntities(type?: string, q?: string): Promise<Entity[]> {
  const query = new URLSearchParams();
  if (type) query.set('type', type);
  if (q) query.set('q', q);

  const res = await fetch(`${BASE_URL}/entities?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch entities');
  return res.json();
}

export async function fetchEntityDetail(entityId: string): Promise<Entity & { mentions: any[] }> {
  const res = await fetch(`${BASE_URL}/entities/${entityId}`);
  if (!res.ok) throw new Error('Failed to fetch entity detail');
  return res.json();
}

export async function fetchGraph(params?: {
  type?: string;
  tier?: string;
  min_strength?: number;
}): Promise<{ nodes: any[]; edges: any[]; total_nodes: number; total_edges: number }> {
  const query = new URLSearchParams();
  if (params?.type) query.set('type', params.type);
  if (params?.tier) query.set('tier', params.tier);
  if (params?.min_strength !== undefined) query.set('min_strength', params.min_strength.toString());

  const res = await fetch(`${BASE_URL}/graph?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch graph data');
  return res.json();
}

export async function fetchEdgeDetail(edgeId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/graph/edges/${edgeId}`);
  if (!res.ok) throw new Error('Failed to fetch edge explanation');
  return res.json();
}

export async function reviewEdge(edgeId: string, decision: 'APPROVED' | 'REJECTED' | 'LEAD', note?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/graph/edges/${edgeId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, note }),
  });
  if (!res.ok) throw new Error('Failed to submit edge review');
  return res.json();
}

export async function fetchAnomalies(params?: { severity?: string; kind?: string }): Promise<Anomaly[]> {
  const query = new URLSearchParams();
  if (params?.severity) query.set('severity', params.severity);
  if (params?.kind) query.set('kind', params.kind);

  const res = await fetch(`${BASE_URL}/anomalies?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch anomalies');
  return res.json();
}

export async function fetchImageAuthenticity(evidenceId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/authenticity/image/${evidenceId}`);
  if (!res.ok) throw new Error('Failed to fetch image authenticity');
  return res.json();
}

export async function fetchStatementCheck(evidenceId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/authenticity/statement/${evidenceId}`);
  if (!res.ok) throw new Error('Failed to fetch statement arithmetic breakdown');
  return res.json();
}

export async function triggerFullAnalysis(): Promise<any> {
  const res = await fetch(`${BASE_URL}/analyze`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to execute analysis pipeline');
  return res.json();
}

export async function fetchSystemCapabilities(): Promise<SystemCapabilities> {
  const res = await fetch(`${BASE_URL}/system/capabilities`);
  if (!res.ok) throw new Error('Failed to fetch system capabilities');
  return res.json();
}

export async function fetchSequence(): Promise<{ episode_count: number; episodes: any[] }> {
  const res = await fetch(`${BASE_URL}/sequence`);
  if (!res.ok) throw new Error('Failed to fetch event sequence');
  return res.json();
}

export async function generateSequence(): Promise<{ status: string; episode_count: number; episodes: any[] }> {
  const res = await fetch(`${BASE_URL}/sequence/generate`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to generate event sequence');
  return res.json();
}

export async function fetchScene(episodeId?: string): Promise<any> {
  const q = episodeId ? `?episode_id=${encodeURIComponent(episodeId)}` : '';
  const res = await fetch(`${BASE_URL}/scene${q}`);
  if (!res.ok) throw new Error('Failed to fetch crime scene reconstruction');
  return res.json();
}

export async function fetchSceneReplay(episodeId?: string): Promise<any> {
  const q = episodeId ? `?episode_id=${encodeURIComponent(episodeId)}` : '';
  const res = await fetch(`${BASE_URL}/scene/replay${q}`);
  if (!res.ok) throw new Error('Failed to fetch scene replay');
  return res.json();
}

/**
 * Re-hash a file directly inside the browser using standard Web Crypto API.
 */
export async function computeBrowserSha256(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

