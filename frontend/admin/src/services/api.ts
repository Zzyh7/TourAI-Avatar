/**
 * 管理后台 API 调用封装
 */
const BASE = '/api/admin';

// ==================== 通用类型 ====================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

// ==================== 统计 ====================

export interface StatsOverview {
  total_sessions: number;
  total_conversations: number;
  sentiment_rate: number;
  avg_latency_ms: number;
}

export interface HotQA {
  question: string;
  count: number;
}

export interface SentimentTrend {
  date: string;
  [key: string]: any;
}

export interface DailyStats {
  date: string;
  count: number;
}

export async function getStatsOverview(): Promise<StatsOverview> {
  const resp = await fetch(`${BASE}/stats/overview`);
  return resp.json();
}

export async function getHotQA(limit = 10): Promise<HotQA[]> {
  const resp = await fetch(`${BASE}/stats/qa-hot?limit=${limit}`);
  return resp.json();
}

export async function getSentimentTrend(days = 7): Promise<SentimentTrend[]> {
  const resp = await fetch(`${BASE}/stats/sentiment?days=${days}`);
  return resp.json();
}

export async function getDailyStats(days = 7): Promise<DailyStats[]> {
  const resp = await fetch(`${BASE}/stats/daily?days=${days}`);
  return resp.json();
}

// ==================== 常用对话 ====================

export interface CommonDialogue {
  id: number;
  question: string;
  answer: string;
  keywords: string;
  category: string;
  priority: number;
  enabled: number;
  created_at: string;
  updated_at: string;
}

export interface CommonDialogueCreate {
  question: string;
  answer: string;
  keywords?: string;
  variants?: string;
  category?: string;
  priority?: number;
  enabled?: number;
}

export async function getCommonDialogues(params?: {
  category?: string;
  enabled?: number;
  search?: string;
}): Promise<CommonDialogue[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.enabled !== undefined) searchParams.set('enabled', String(params.enabled));
  if (params?.search) searchParams.set('search', params.search);
  const qs = searchParams.toString();
  const resp = await fetch(`${BASE}/common-dialogues${qs ? '?' + qs : ''}`);
  return resp.json();
}

export async function getCommonDialogueCategories(): Promise<string[]> {
  const resp = await fetch(`${BASE}/common-dialogues/categories`);
  const data = await resp.json();
  return data.categories || [];
}

export async function createCommonDialogue(data: CommonDialogueCreate): Promise<CommonDialogue> {
  const resp = await fetch(`${BASE}/common-dialogues`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return resp.json();
}

export async function updateCommonDialogue(id: number, data: Partial<CommonDialogueCreate>): Promise<CommonDialogue> {
  const resp = await fetch(`${BASE}/common-dialogues/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return resp.json();
}

export async function deleteCommonDialogue(id: number): Promise<void> {
  await fetch(`${BASE}/common-dialogues/${id}`, { method: 'DELETE' });
}

export async function batchImportCommonDialogues(items: CommonDialogueCreate[]): Promise<{ imported: number }> {
  const resp = await fetch(`${BASE}/common-dialogues/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
  return resp.json();
}

export async function exportCommonDialogues(): Promise<CommonDialogue[]> {
  const resp = await fetch(`${BASE}/common-dialogues/export/all`);
  return resp.json();
}

// ==================== 景点管理 ====================

export interface ScenicSpot {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  trigger_radius: number;
  description: string;
  audio_intro_path: string;
  category: string;
  visit_duration: number;
  created_at: string;
}

export async function getScenicSpots(params?: {
  category?: string;
  search?: string;
}): Promise<ScenicSpot[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.search) searchParams.set('search', params.search);
  const qs = searchParams.toString();
  const resp = await fetch(`${BASE}/scenic-spots${qs ? '?' + qs : ''}`);
  return resp.json();
}

export async function getScenicSpotCategories(): Promise<string[]> {
  const resp = await fetch(`${BASE}/scenic-spots/categories`);
  const data = await resp.json();
  return data.categories || [];
}

export async function createScenicSpot(data: Partial<ScenicSpot>): Promise<ScenicSpot> {
  const resp = await fetch(`${BASE}/scenic-spots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return resp.json();
}

export async function updateScenicSpot(id: number, data: Partial<ScenicSpot>): Promise<ScenicSpot> {
  const resp = await fetch(`${BASE}/scenic-spots/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return resp.json();
}

export async function deleteScenicSpot(id: number): Promise<void> {
  await fetch(`${BASE}/scenic-spots/${id}`, { method: 'DELETE' });
}

// ==================== 会话 & 对话 ====================

export interface SessionItem {
  id: string;
  visitor_tag: string;
  created_at: string;
  conversation_count: number;
}

export interface ConversationItem {
  id: number;
  session_id: string;
  role: string;
  content: string;
  sentiment: string;
  latency_ms: number;
  created_at: string;
}

export interface SessionDetail extends SessionItem {
  conversations: ConversationItem[];
}

export async function getSessions(params?: {
  search?: string;
  tag?: string;
  page?: number;
  page_size?: number;
}): Promise<SessionItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set('search', params.search);
  if (params?.tag) searchParams.set('tag', params.tag);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  const resp = await fetch(`${BASE}/data/sessions${qs ? '?' + qs : ''}`);
  return resp.json();
}

export async function getSessionCount(): Promise<number> {
  const resp = await fetch(`${BASE}/data/sessions/count`);
  const data = await resp.json();
  return data.total;
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  const resp = await fetch(`${BASE}/data/sessions/${sessionId}`);
  return resp.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/data/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getConversations(params?: {
  session_id?: string;
  role?: string;
  sentiment?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<ConversationItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.session_id) searchParams.set('session_id', params.session_id);
  if (params?.role) searchParams.set('role', params.role);
  if (params?.sentiment) searchParams.set('sentiment', params.sentiment);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  const resp = await fetch(`${BASE}/data/conversations${qs ? '?' + qs : ''}`);
  return resp.json();
}

export async function deleteConversation(convId: number): Promise<void> {
  await fetch(`${BASE}/data/conversations/${convId}`, { method: 'DELETE' });
}

// ==================== 知识库文档 ====================

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  chunk_count: number;
  size_bytes: number;
  uploaded_at: string;
}

// 改用 RAG API
const RAG_BASE = '/api/rag/admin';

export async function getDocuments(): Promise<DocumentItem[]> {
  const resp = await fetch(`${RAG_BASE}/documents`);
  const data = await resp.json();
  return data.documents || [];
}

export async function uploadDocument(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`${RAG_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });
  return resp.json();
}

export async function deleteDocument(docId: number): Promise<void> {
  await fetch(`${RAG_BASE}/documents/${docId}`, { method: 'DELETE' });
}

export async function getRAGHealth(): Promise<{ faq_count: number; status: string }> {
  const resp = await fetch('/api/rag/health');
  return resp.json();
}

export async function importFAQ(items: { question: string; answer: string }[]): Promise<any> {
  const resp = await fetch(`${RAG_BASE}/faq/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
  return resp.json();
}

export async function importDialoguesToKnowledge(
  items: { question: string; answer: string }[],
): Promise<any> {
  const resp = await fetch(`${RAG_BASE}/import-dialogues`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
  return resp.json();
}

// ==================== 数字人配置 ====================

export interface DigitalHumanConfig {
  live2d_model: string;
  voice_name: string;
  voice_speed: number;
  updated_at: string | null;
}

export async function getDigitalHumanConfig(): Promise<DigitalHumanConfig> {
  const resp = await fetch(`${BASE}/config/digital-human`);
  return resp.json();
}

export async function updateDigitalHumanConfig(data: {
  live2d_model?: string;
  voice_name?: string;
  voice_speed?: number;
}): Promise<any> {
  const resp = await fetch(`${BASE}/config/digital-human`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return resp.json();
}

// ==================== 数据分析 (Analytics) ====================

const ANALYTICS_BASE = '/api/admin/analytics';

export interface FullDashboard {
  interaction: {
    today: { sessions: number; conversations: number };
    yesterday: { sessions: number; conversations: number };
    week: { sessions: number; conversations: number };
    month: { sessions: number; conversations: number };
    hourly_distribution: { hour: number; count: number }[];
    avg_conversations_per_session: number;
    avg_daily_conversations: number;
    repeat_visitors_week: number;
  };
  spot_popularity: {
    ranking: { name: string; count: number }[];
    top5: { name: string; count: number }[];
    cold_spots: { name: string; count: number }[];
  };
  qa_quality: {
    total_answers: number;
    unable_to_answer: number;
    unable_rate: number;
    sentiment: { positive: number; neutral: number; negative: number };
    satisfaction_rate: number;
  };
  time_comparison: {
    today: { conversations: number; positive: number; sessions: number; rate: number };
    yesterday: { conversations: number; positive: number; sessions: number; rate: number };
    week_daily: { conversations: number; positive: number; sessions: number; rate: number }[];
    this_week_total: number;
    last_week_total: number;
    week_change: number;
  };
  question_analysis: {
    categories: { name: string; count: number }[];
    top_questions: { question: string; count: number }[];
    unable_questions: { question: string; count: number }[];
  };
  visitor_segmentation: VisitorProfileRes;
}

export async function fetchFullDashboard(): Promise<FullDashboard> {
  const resp = await fetch(`${ANALYTICS_BASE}/full-dashboard`);
  return resp.json();
}

export interface SpotPopularityRes {
  ranking: { name: string; count: number }[];
  top5: { name: string; count: number }[];
  cold_spots: { name: string; count: number }[];
  total_queries: number;
}

export async function fetchSpotPopularity(): Promise<SpotPopularityRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/spot-popularity`);
  return resp.json();
}

export interface TimeComparisonRes {
  today: { conversations: number; positive: number; sessions: number; rate: number };
  yesterday: { conversations: number; positive: number; sessions: number; rate: number };
  week_daily: { conversations: number; positive: number; sessions: number; rate: number }[];
  this_week_total: number;
  last_week_total: number;
  week_change: number;
}

export async function fetchTimeComparison(): Promise<TimeComparisonRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/time-comparison`);
  return resp.json();
}

export interface QAQualityRes {
  total_answers: number;
  unable_to_answer: number;
  unable_rate: number;
  sentiment: { positive: number; neutral: number; negative: number };
  satisfaction_rate: number;
}

export async function fetchQAQuality(): Promise<QAQualityRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/qa-quality`);
  return resp.json();
}

export interface QuestionAnalysisRes {
  categories: { name: string; count: number }[];
  top_questions: { question: string; count: number }[];
  unable_questions: { question: string; count: number }[];
}

export async function fetchQuestionAnalysis(): Promise<QuestionAnalysisRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/question-analysis`);
  return resp.json();
}

export interface VisitorSegmentationRes {
  segments: { label: string; count: number }[];
  tag_distribution: { name: string; value: number }[];
  preference_distribution?: { name: string; value: number }[];
}

export async function fetchVisitorSegmentation(): Promise<VisitorSegmentationRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/visitor-segmentation`);
  return resp.json();
}

/* ========== 游客画像 (新版) ========== */

export interface RouteRecommendation {
  label: string;
  spots: string[];
  description: string;
}

export interface PreferenceStat {
  name: string;
  value: number;
  recommended_routes: RouteRecommendation[];
}

export interface OriginAnalysis {
  data_available: boolean;
  method: string;
  distribution: { name: string; value: number }[];
  note: string;
}

export interface Feasibility {
  score: string;
  analysis: string;
  recommendation: string;
}

export interface StratSegment {
  label: string;
  count: number;
  confidence: string;
}

export interface Stratification {
  feasibility: Feasibility;
  segments: StratSegment[];
}

export interface VisitorProfileRes {
  total_visitors: number;
  attribute_tags: { name: string; value: number }[];
  preference_stats: PreferenceStat[];
  origin_analysis: OriginAnalysis;
  stratification: Stratification;
}

export async function fetchVisitorProfile(): Promise<VisitorProfileRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/visitor-profile`);
  return resp.json();
}

export interface NegativeAnalysisRes {
  total_negative: number;
  categories: { category: string; count: number }[];
  unclassified: number;
  samples: string[];
  ai_suggestion: string;
}

export async function fetchNegativeAnalysis(): Promise<NegativeAnalysisRes> {
  const resp = await fetch(`${ANALYTICS_BASE}/negative-analysis`);
  return resp.json();
}
