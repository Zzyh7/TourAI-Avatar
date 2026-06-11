/**
 * 拍照识景 —— 上传照片，调用多模态大模型识别景点。
 */
import { useState, useRef } from 'react';
import { photoRecognize } from '../services/api';

interface PhotoRecognitionProps {
  disabled?: boolean;
  onResult?: (description: string) => void;
}

export default function PhotoRecognition({ disabled, onResult }: PhotoRecognitionProps) {
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 预览
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result as string);
    reader.readAsDataURL(file);

    // 压缩并转 base64
    const base64 = await compressImage(file);
    setLoading(true);

    try {
      const result = await photoRecognize(base64);
      if (result.description && onResult) {
        onResult(result.description);
      }
    } catch (err) {
      console.error('拍照识景失败:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFile}
        style={{ display: 'none' }}
      />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={disabled || loading}
        style={{
          ...styles.btn,
          opacity: disabled || loading ? 0.5 : 1,
        }}
        title="拍照识别景点"
      >
        {loading ? '⏳' : '📷'} 拍照识景
      </button>
      {preview && (
        <div style={styles.preview}>
          <img src={preview} alt="预览" style={{ maxWidth: 120, maxHeight: 80, borderRadius: 8 }} />
        </div>
      )}
    </div>
  );
}

/** 压缩图片到合理大小 */
function compressImage(file: File): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxW = 800;
        const scale = Math.min(1, maxW / img.width);
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;
        canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.8).split(',')[1]);
      };
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  });
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  btn: {
    padding: '8px 16px',
    borderRadius: 20,
    border: '1.5px solid #e0e0e0',
    background: '#fff',
    fontSize: 13,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  preview: {
    marginLeft: 8,
  },
};
