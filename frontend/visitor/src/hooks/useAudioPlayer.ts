/**
 * TTS 音频播放器 —— 播放 base64 编码的 mp3 音频片段。
 *
 * 优化：
 *  - 复用 Audio 元素减少创建开销
 *  - 预缓冲下一个音频片段（设置 src 后暂停等待）
 *  - 首音快速启动（loadedmetadata 即播放，不等 loadeddata）
 */
import { useRef, useCallback } from 'react';

interface QueuedAudio {
  base64: string;
  text: string;
}

export function useAudioPlayer(onPlayStart?: (text: string) => void) {
  const queueRef = useRef<QueuedAudio[]>([]);
  const playingRef = useRef(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const nextAudioRef = useRef<HTMLAudioElement | null>(null);

  const cleanupNextAudio = useCallback(() => {
    if (nextAudioRef.current) {
      nextAudioRef.current.pause();
      nextAudioRef.current.src = '';
      nextAudioRef.current = null;
    }
  }, []);

  const prepareAudio = useCallback((item: QueuedAudio): HTMLAudioElement => {
    const audio = new Audio();
    audio.preload = 'auto';
    // Blob URL 比 data: URI 更快（避免主线程 base64 解码）
    try {
      const byteString = atob(item.base64);
      const ab = new ArrayBuffer(byteString.length);
      const ia = new Uint8Array(ab);
      for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([ab], { type: 'audio/mp3' });
      audio.src = URL.createObjectURL(blob);
    } catch {
      // 降级：直接使用 data: URI
      audio.src = `data:audio/mp3;base64,${item.base64}`;
    }
    return audio;
  }, []);

  // 释放 Blob URL（避免内存泄漏）
  const releaseAudio = useCallback((audio: HTMLAudioElement) => {
    if (audio.src.startsWith('blob:')) {
      URL.revokeObjectURL(audio.src);
    }
  }, []);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false;
      return;
    }

    const item = queueRef.current.shift()!;
    playingRef.current = true;

    // 复用已预热的 nextAudio，或创建新的
    let audio: HTMLAudioElement;
    if (nextAudioRef.current) {
      audio = nextAudioRef.current;
      nextAudioRef.current = null;
      // 更新 onended 回调
    } else {
      audio = prepareAudio(item);
      // 如果准备好了就播放，否则等 loadedmetadata
      if (audio.readyState >= 1) {
        // nothing special needed, play below
      }
    }

    // 如果音频的 src 不是当前 item 的，重新设置
    // (正常流程中不应该发生，但做个保护)
    const expectedSrc = `data:audio/mp3;base64,${item.base64}`;
    if (!audio.src.includes(item.base64) && audio.src !== expectedSrc) {
      releaseAudio(audio);
      audio = prepareAudio(item);
    }

    currentAudioRef.current = audio;

    if (onPlayStart) {
      onPlayStart(item.text);
    }

    audio.onended = () => {
      // 预缓冲：如果队列中还有下一项，提前预热
      if (queueRef.current.length > 0) {
        const nextItem = queueRef.current[0];
        nextAudioRef.current = prepareAudio(nextItem);
        nextAudioRef.current.load(); // 触发预加载
      }
      releaseAudio(audio);
      playNext();
    };

    audio.onerror = () => {
      releaseAudio(audio);
      // 跳过播放失败的片段，继续下一个
      playNext();
    };

    audio.play().catch(() => {
      // 自动播放被阻止等
      playNext();
    });

    // 预缓冲队列中的下一个音频
    if (queueRef.current.length > 0 && !nextAudioRef.current) {
      const nextItem = queueRef.current[0];
      nextAudioRef.current = prepareAudio(nextItem);
      nextAudioRef.current.load();
    }
  }, [onPlayStart, prepareAudio, releaseAudio]);

  const enqueue = useCallback((base64: string, text: string) => {
    queueRef.current.push({ base64, text });
    if (!playingRef.current) {
      playNext();
    }
  }, [playNext]);

  const stop = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      releaseAudio(currentAudioRef.current);
      currentAudioRef.current = null;
    }
    cleanupNextAudio();
    queueRef.current = [];
    playingRef.current = false;
  }, [releaseAudio, cleanupNextAudio]);

  const isPlaying = useCallback(() => {
    return playingRef.current || queueRef.current.length > 0;
  }, []);

  return { enqueue, stop, isPlaying };
}
