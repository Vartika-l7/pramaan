export type SourceType = 'whatsapp' | 'bank_pdf' | 'bank_csv' | 'calllog' | 'image' | 'unknown';
export type Tier = 'VERIFIED BY CODE' | 'LEAD' | 'APPROVED';
export type Severity = 'HIGH' | 'MEDIUM' | 'LOW';

export interface Evidence {
  id: string;
  exhibit_id: string;
  filename: string;
  sha256: string;
  size_bytes: number;
  source_type: SourceType;
  received_at_utc: string;
  stored_path: string;
  parser?: string;
  parse_status: string;
  parse_notes?: string;
}

export interface CustodyEvent {
  seq: number;
  ts_utc: string;
  actor: string;
  action: string;
  evidence_id?: string;
  details?: Record<string, any>;
  prev_hash: string;
  entry_hash: string;
}

export interface ForensicEvent {
  id: string;
  evidence_id: string;
  exhibit_id?: string;
  filename?: string;
  source_type: SourceType;
  ts_utc: string;
  ts_original: string;
  tz_assumed: string;
  actor?: string;
  counterparty?: string;
  kind: string;
  text?: string;
  amount?: number;
  currency?: string;
  location_id?: string;
  ref: Record<string, any>;
}

export interface Entity {
  id: string;
  type: string;
  value_norm: string;
  display: string;
  first_event_id?: string;
  mention_count?: number;
}

export interface Mention {
  id: string;
  entity_id: string;
  event_id: string;
  char_start: number;
  char_end: number;
  extractor: string;
  tier: Tier;
  text?: string;
  ts_utc?: string;
  source_type?: string;
  exhibit_id?: string;
  filename?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  edge_type: string;
  basis: string;
  reason_text: string;
  strength: number;
  tier: Tier;
  status: string;
  event_ids: string[];
}

export interface Anomaly {
  id: string;
  kind: string;
  severity: Severity;
  evidence_id: string;
  exhibit_id?: string;
  filename?: string;
  event_ids: string[];
  description: string;
  detail: Record<string, any>;
  status: string;
}

export interface Claim {
  id: string;
  text: string;
  kind: string;
  tier: Tier;
  status: 'PROPOSED' | 'VERIFIED' | 'REMOVED' | 'APPROVED' | 'REJECTED';
  source_refs: string[];
  quotes: Array<{ event_id: string; text: string }>;
  generated_by: string;
  verifier_notes?: string;
}

export interface IntegrityStatus {
  intact: boolean;
  total_exhibits: number;
  merkle_root: string;
  chain_intact: boolean;
  chain_error?: string;
  failed_exhibit?: string;
  exhibits: Array<{
    exhibit_id: string;
    filename: string;
    sha256: string;
    status: 'PASS' | 'FAIL';
    reason: string;
  }>;
  verified_at_utc: string;
}

export interface SystemCapabilities {
  ollama: { available: boolean; models: string[]; host: string };
  tesseract: { available: boolean; languages: string[]; error?: string };
  pdf_engine: { engine: string; available: boolean; notes: string };
  indic_ner: { enabled: boolean; notes: string };
  network_use?: {
    outbound_connections: number;
    blocked_attempts: Array<{ host: string; port?: number; ts_utc: string }>;
    guard_active: boolean;
    offline_mode: boolean;
  };
}

