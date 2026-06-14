/**
 * GPS 定位 Hook —— watchPosition 持续追踪用户位置
 */
import { useState, useEffect, useRef } from 'react';

export interface GpsPosition {
  lat: number;
  lng: number;
  accuracy: number;
  timestamp: number;
}

interface UseGeolocationOptions {
  /** 轮询间隔 (毫秒)，默认5000 */
  interval?: number;
  /** 是否启用 */
  enabled?: boolean;
}

export function useGeolocation({ interval = 5000, enabled = true }: UseGeolocationOptions = {}) {
  const [position, setPosition] = useState<GpsPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [watching, setWatching] = useState(false);
  const watchIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      // 停止监听
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setWatching(false);
      return;
    }

    if (!navigator.geolocation) {
      setError('当前浏览器不支持GPS定位');
      return;
    }

    setWatching(true);

    // 使用 watchPosition 持续追踪
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          timestamp: pos.timestamp,
        });
        setError(null);
      },
      (err) => {
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError('GPS权限被拒绝，请在浏览器设置中允许访问位置信息');
            break;
          case err.POSITION_UNAVAILABLE:
            setError('无法获取位置信息，请检查GPS是否开启');
            break;
          case err.TIMEOUT:
            setError('获取位置超时');
            break;
          default:
            setError('定位失败');
        }
      },
      {
        enableHighAccuracy: true,
        maximumAge: interval,          // 缓存不超过轮询间隔
        timeout: 10000,
      }
    );

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [enabled, interval]);

  return { position, error, watching };
}
