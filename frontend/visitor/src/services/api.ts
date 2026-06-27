/**
 * 后端 API 调用封装
 */
const BASE = 'http://10.40.0.157:8000/api';

export interface ChatEvent {
  type: 'token' | 'audio' | 'tool' | 'done' | 'error';
  data: any;
}

/**
 * SSE 流式聊天（文本 + TTS 音频）。
 * 传入 signal 可中断请求（AbortController）。
 */
export async function* streamChat(
  text: string,
  sessionId: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const resp = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, session_id: sessionId }),
    signal,
  });

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const eventMatch = line.match(/^event: (\w+)\ndata: (.+)$/s);
      if (eventMatch) {
        const type = eventMatch[1] as ChatEvent['type'];
        try {
          const data = JSON.parse(eventMatch[2]);
          yield { type, data };
        } catch {
          // skip parse errors
        }
      }
    }
  }
}

/** 创建新会话 */
export async function createSession(): Promise<string> {
  const resp = await fetch(`${BASE}/session/new`, { method: 'POST' });
  const data = await resp.json();
  return data.session_id;
}

/** 更新会话标签 */
export async function updateSessionTag(sessionId: string, tag: string) {
  await fetch(`${BASE}/session/${sessionId}/tag`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tag }),
  });
}

/** 拍照识景 */
export async function photoRecognize(imageBase64: string, lat?: number, lng?: number) {
  const resp = await fetch(`${BASE}/photo-recognize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64, lat, lng }),
  });
  return resp.json();
}

/** 个性化推荐 */
export async function getRecommendations(tags: string[], lat?: number, lng?: number) {
  const params = new URLSearchParams();
  params.set('tags', tags.join(','));
  if (lat) params.set('lat', String(lat));
  if (lng) params.set('lng', String(lng));

  const resp = await fetch(`${BASE}/recommend?${params}`);
  return resp.json();
}

/** GPS 附近景点 */
export async function getNearbySpots(lat: number, lng: number, radius = 500) {
  const resp = await fetch(`${BASE}/nearby-spots?lat=${lat}&lng=${lng}&radius=${radius}`);
  return resp.json();
}
