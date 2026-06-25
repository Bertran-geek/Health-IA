export interface QueryRequest {
  question: string;
  language?: string;
  include_chart?: boolean;
}

export interface ChartSpec {
  type: string;
  title: string;
  x: string[];
  series: { name: string; data: number[] }[];
  image_base64?: string;
}

export interface QueryResponse {
  answer: string;
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  chart: ChartSpec | null;
  trend: string | null;
  language: string;
  cached: boolean;
  elapsed_ms: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  llm: string;
  cache: string;
  version: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}
