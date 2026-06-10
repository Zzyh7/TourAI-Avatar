/**
 * TTS 音频播放器 —— 播放 base64 编码的 mp3 音频片段
 */
import { useRef, useCallback } from 'react';

interface QueuedAudio {
  base64: string;
  text: string;
}

export function useAudioPlayer(onPlayStart?: (text: string) => void) {
  const queueRef = useRef<QueuedAudio[]>([]);
  const playingRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false;
      return;
    }

    const item = queueRef.current.shift()!;
    playingRef.current = true;

    const audio = new Audio(`data:audio/mp3;base64,${item.base64}`);
    audioRef.current = audio;

    if (onPlayStart) {
      onPlayStart(item.text);
    }

    audio.onended = () => {
      playNext();
    };

    audio.onerror = () => {
      // 跳过播放失败的片段，继续下一个
      playNext();
    };

    audio.play().catch(() => {
      playNext();
    });
  }, [onPlayStart]);

  const enqueue = useCallback((base64: string, text: string) => {
    queueRef.current.push({ base64, text });
    if (!playingRef.current) {
      playNext();
    }
  }, [playNext]);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    queueRef.current = [];
    playingRef.current = false;
  }, []);

  const isPlaying = () => playingRef.current || queueRef.current.length > 0;

  return { enqueue, stop, isPlaying };
}
