export interface DocumentResponse {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  metadata: Record<string, string | number | boolean>;
}

export interface ChatRequest {
  question: string;
  conversation_id?: string;
  document_ids?: string[];
}

export interface SourceCitation {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content_preview: string;
  similarity_score: number;
}

export interface GuardrailResult {
  layer: 'input' | 'retrieval' | 'output';
  action: 'pass' | 'block' | 'warn';
  reason: string;
  confidence: number;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  confidence_score: number;
  guardrail_result: GuardrailResult;
  conversation_id: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceCitation[];
  confidence_score?: number;
  guardrail_result?: GuardrailResult;
  created_at: string;
}

export interface ConversationResponse {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface StreamingChatEvent {
  type: 'start' | 'token' | 'sources' | 'guardrail' | 'done' | 'error';
  data: unknown;
}

export interface StreamingTokenData {
  token: string;
}

export interface StreamingSourcesData {
  sources: SourceCitation[];
}

export interface StreamingGuardrailData {
  guardrail: GuardrailResult;
}

export interface StreamingDoneData {
  answer: string;
  confidence_score: number;
  conversation_id: string;
}

export interface StreamingErrorData {
  message: string;
  code: string;
}

export interface GuardrailStats {
  total_queries: number;
  blocked_queries: number;
  warned_queries: number;
  block_rate: number;
  warn_rate: number;
  layer_stats: {
    input: { total: number; blocked: number; warned: number };
    retrieval: { total: number; blocked: number; warned: number };
    output: { total: number; blocked: number; warned: number };
  };
  recent_scans: GuardrailScan[];
}

export interface GuardrailScan {
  id: string;
  text: string;
  result: GuardrailResult;
  timestamp: string;
}

export interface SystemStats {
  document_count: number;
  chunk_count: number;
  query_count: number;
  avg_confidence: number;
  block_rate: number;
  uptime_seconds: number;
  version: string;
}

export interface ApiError {
  detail: string;
  code?: string;
  status_code: number;
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy' | 'degraded';
  version: string;
  timestamp: string;
}
