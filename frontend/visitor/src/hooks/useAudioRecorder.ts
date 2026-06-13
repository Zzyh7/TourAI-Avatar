/**
 * 音频录制 Hook —— 使用 AudioContext + ScriptProcessorNode 录制为 WAV。
 *
 * 产物：16kHz 单声道 16-bit PCM WAV，通过 DashScope Paraformer 做语音识别。
 * 不依赖 Google SpeechRecognition，在国内可用。
 */

import { useRef, useCallback, useState } from 'react';

export function useAudioRecorder(onResult: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  const inputSampleRateRef = useRef(16000);
  const listeningRef = useRef(false);  // 避免闭包陷阱

  const start = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    try {
      // 1. 获取麦克风
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      // 2. 创建 AudioContext（目标采样率 16kHz）
      const ctx = new AudioContext({ sampleRate: 16000 });
      ctxRef.current = ctx;
      inputSampleRateRef.current = ctx.sampleRate;

      const source = ctx.createMediaStreamSource(stream);

      // 3. ScriptProcessorNode 捕获原始 PCM
      const bufferSize = 4096;
      const processor = ctx.createScriptProcessor(bufferSize, 1, 1);

      processor.onaudioprocess = (e) => {
        if (!listeningRef.current) return;
        const inputData = e.inputBuffer.getChannelData(0);
        chunksRef.current.push(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(ctx.destination);

      listeningRef.current = true;
      setIsListening(true);
    } catch (e: any) {
      if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
        setError('麦克风权限被拒绝，请在浏览器设置中允许访问麦克风');
      } else {
        setError(`麦克风启动失败: ${e.message}`);
      }
    }
  }, []);

  const stop = useCallback(async () => {
    listeningRef.current = false;
    setIsListening(false);

    // 停止麦克风
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }

    // 关闭 AudioContext（先关闭再组装 WAV）
    if (ctxRef.current) {
      try { ctxRef.current.close(); } catch { /* ignore */ }
      ctxRef.current = null;
    }

    const allChunks = chunksRef.current;
    if (allChunks.length === 0) {
      setError('未录制到音频');
      return;
    }

    try {
      // 4. 合并所有 Float32 chunk，转为 16-bit PCM
      const totalLength = allChunks.reduce((sum, c) => sum + c.length, 0);
      const combined = new Float32Array(totalLength);
      let offset = 0;
      for (const c of allChunks) {
        combined.set(c, offset);
        offset += c.length;
      }

      const int16 = float32ToInt16(combined);
      const sampleRate = inputSampleRateRef.current;

      // 5. 构建 WAV 文件
      const wavBlob = buildWav(int16, sampleRate);

      // 6. 发送到后端 STT
      const resp = await speechToText(wavBlob);
      if (resp.text) {
        onResult(resp.text);
        setError(null);
      } else {
        setError(resp.error || '未识别到语音内容，请靠近麦克风再说一次');
      }
    } catch (e: any) {
      setError(`语音识别失败: ${e.message}`);
    }
  }, [onResult]);

  return { isListening, error, start, stop };
}

// ============================================================
// 工具函数
// ============================================================

function float32ToInt16(float32: Float32Array): Int16Array {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return int16;
}

function buildWav(pcm: Int16Array, sampleRate: number): Blob {
  const byteLength = pcm.length * 2;
  const buffer = new ArrayBuffer(44 + byteLength);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + byteLength, true);
  writeString(view, 8, 'WAVE');

  // fmt chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);        // chunk size
  view.setUint16(20, 1, true);          // PCM
  view.setUint16(22, 1, true);          // mono
  view.setUint32(24, sampleRate, true); // sample rate
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);          // block align
  view.setUint16(34, 16, true);         // bits per sample

  // data chunk
  writeString(view, 36, 'data');
  view.setUint32(40, byteLength, true);

  // PCM samples
  const pcmView = new DataView(buffer, 44);
  for (let i = 0; i < pcm.length; i++) {
    pcmView.setInt16(i * 2, pcm[i], true);
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

async function speechToText(audioBlob: Blob): Promise<{ text: string; error?: string }> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');
  formData.append('mime_type', 'audio/wav');

  const resp = await fetch('/api/stt', {
    method: 'POST',
    body: formData,
  });

  const data = await resp.json().catch(() => ({ text: '', success: false, error: `HTTP ${resp.status}` }));

  if (!resp.ok) {
    return { text: '', error: data.error || `HTTP ${resp.status}` };
  }

  return { text: data.text || '', error: data.error || undefined };
}
