/**
 * 系统配置页 —— 数字人形象 / 音色 / 语速设置
 */
import { useState, useEffect } from 'react';
import {
  getDigitalHumanConfig,
  updateDigitalHumanConfig,
  type DigitalHumanConfig,
} from '../services/api';

// 豆包 TTS (Seed-TTS-2.0 WebSocket) — 已实测可用
const VOICE_OPTIONS = [
  { value: 'zh_male_tiancaitongsheng_mars_bigtts', label: '天才童声（男，默认）' },
  { value: 'zh_male_shaonianzixin_uranus_bigtts', label: '少年自信（男）' },
  { value: 'zh_female_vv_uranus_bigtts', label: 'Vivi 2.0（女，温暖对话）' },
  { value: 'zh_female_xiaohe_uranus_bigtts', label: 'Mindy（女，甜美）' },
  { value: 'zh_male_m191_uranus_bigtts', label: 'Kian（男，清爽）' },
  { value: 'zh_male_taocheng_uranus_bigtts', label: 'Cedric（男，沉稳）' },
  { value: 'zh_female_shuangkuaisisi_moon_bigtts', label: '新闻播报（女，干脆）' },
  { value: 'zh_male_yuanboxiaoshu_moon_bigtts', label: '温暖男主播（男，叙事）' },
];

const LIVE2D_OPTIONS = [
  { value: 'default', label: '默认形象' },
  { value: 'haru', label: 'Haru（女）' },
  { value: 'hibiki', label: 'Hibiki（男）' },
  { value: 'shizuku', label: 'Shizuku（女）' },
  { value: 'epsilon', label: 'Epsilon（女）' },
];

export default function Config() {
  const [config, setConfig] = useState<DigitalHumanConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  // 表单
  const [live2dModel, setLive2dModel] = useState('default');
  const [voiceName, setVoiceName] = useState('zh_male_shaonianzixin_uranus_bigtts');
  const [voiceSpeed, setVoiceSpeed] = useState(1.0);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await getDigitalHumanConfig();
      setConfig(data);
      setLive2dModel(data.live2d_model);
      setVoiceName(data.voice_name);
      setVoiceSpeed(data.voice_speed);
    } catch (e) {
      console.error('加载配置失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg('');
    try {
      const result = await updateDigitalHumanConfig({
        live2d_model: live2dModel,
        voice_name: voiceName,
        voice_speed: voiceSpeed,
      });
      if (result.error) {
        setMsg(`❌ ${result.error}`);
      } else {
        setMsg('✅ 配置已保存');
        setConfig(prev => prev ? { ...prev, live2d_model: live2dModel, voice_name: voiceName, voice_speed: voiceSpeed } : prev);
      }
    } catch (e: any) {
      console.error('保存配置失败:', e);
      setMsg(`❌ 保存失败: ${e.message || '网络错误，请确认后端服务已启动'}`);
    } finally {
      setSaving(false);
      setTimeout(() => setMsg(''), 5000);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>加载中...</div>;
  }

  return (
    <div>
      <h1 style={styles.title}>⚙️ 系统配置</h1>
      <p style={styles.subtitle}>配置数字人形象、TTS 音色和语速等参数</p>

      <div style={styles.card}>
        <h3 style={styles.sectionTitle}>🤖 数字人形象</h3>
        <div style={styles.formGroup}>
          <label style={styles.label}>Live2D 模型</label>
          <select
            value={live2dModel}
            onChange={e => setLive2dModel(e.target.value)}
            style={styles.select}
          >
            {LIVE2D_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <span style={styles.hint}>选择前端展示的数字人模型形象</span>
        </div>

        <h3 style={{ ...styles.sectionTitle, marginTop: 28 }}>🔊 语音合成 (TTS)</h3>
        <div style={styles.formGroup}>
          <label style={styles.label}>Edge-TTS 音色</label>
          <select
            value={voiceName}
            onChange={e => setVoiceName(e.target.value)}
            style={styles.select}
          >
            {VOICE_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <span style={styles.hint}>选择 TTS 语音合成的发音人（微软 Edge 免费引擎）</span>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>语速: {voiceSpeed.toFixed(1)}x</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: '#999' }}>0.5x</span>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={voiceSpeed}
              onChange={e => setVoiceSpeed(Number(e.target.value))}
              style={styles.range}
            />
            <span style={{ fontSize: 12, color: '#999' }}>2.0x</span>
          </div>
          <span style={styles.hint}>调整语音播放速度，1.0 为正常速度</span>
        </div>

        <div style={styles.actions}>
          <button onClick={handleSave} disabled={saving} style={styles.primaryBtn}>
            {saving ? '保存中...' : '💾 保存配置'}
          </button>
          {msg && (
            <span style={{
              fontSize: 14,
              color: msg.startsWith('✅') ? '#4CAF50' : '#f44336',
              fontWeight: 500,
            }}>
              {msg}
            </span>
          )}
        </div>
      </div>

      {/* 当前配置状态 */}
      {config && (
        <div style={{ ...styles.card, marginTop: 16 }}>
          <h3 style={styles.sectionTitle}>📋 当前生效配置</h3>
          <div style={styles.configGrid}>
            <div style={styles.configItem}>
              <div style={styles.configLabel}>Live2D 模型</div>
              <div style={styles.configValue}>{config.live2d_model}</div>
            </div>
            <div style={styles.configItem}>
              <div style={styles.configLabel}>TTS 音色</div>
              <div style={styles.configValue}>{config.voice_name}</div>
            </div>
            <div style={styles.configItem}>
              <div style={styles.configLabel}>语速</div>
              <div style={styles.configValue}>{config.voice_speed}x</div>
            </div>
            <div style={styles.configItem}>
              <div style={styles.configLabel}>最后更新</div>
              <div style={styles.configValue}>
                {config.updated_at ? new Date(config.updated_at).toLocaleString('zh-CN') : '-'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  title: {
    fontSize: 22,
    fontWeight: 600,
    marginBottom: 4,
    color: '#1a1a2e',
  },
  subtitle: {
    fontSize: 13,
    color: '#999',
    marginBottom: 20,
  },
  card: {
    background: '#fff',
    borderRadius: 10,
    padding: 24,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    maxWidth: 680,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 16,
    color: '#333',
  },
  formGroup: {
    marginBottom: 18,
  },
  label: {
    display: 'block',
    fontSize: 14,
    color: '#444',
    marginBottom: 6,
    fontWeight: 500,
  },
  select: {
    width: '100%',
    maxWidth: 400,
    padding: '9px 14px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 14,
    outline: 'none',
    background: '#fff',
    marginBottom: 6,
  },
  hint: {
    display: 'block',
    fontSize: 12,
    color: '#aaa',
  },
  range: {
    flex: 1,
    maxWidth: 300,
    accentColor: '#1976D2',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    marginTop: 24,
    paddingTop: 20,
    borderTop: '1px solid #f0f0f0',
  },
  primaryBtn: {
    padding: '10px 24px',
    borderRadius: 6,
    border: 'none',
    background: '#1976D2',
    color: '#fff',
    fontSize: 14,
    cursor: 'pointer',
    fontWeight: 500,
  },
  configGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 16,
  },
  configItem: {
    padding: '12px 16px',
    borderRadius: 8,
    background: '#f9fafb',
  },
  configLabel: {
    fontSize: 12,
    color: '#999',
    marginBottom: 4,
  },
  configValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: 500,
    fontFamily: 'monospace',
  },
};
