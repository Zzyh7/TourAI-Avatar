/**
 * 个性化推荐标签栏 —— 游客选择兴趣偏好。
 */
interface RecommendationBarProps {
  onSelect: (tag: string) => void;
  selected: string;
}

const TAGS = [
  { key: '家庭游', label: '👨‍👩‍👧 家庭游', desc: '亲子友好路线' },
  { key: '情侣游', label: '💑 情侣游', desc: '浪漫打卡路线' },
  { key: '文化深度游', label: '📚 文化深度游', desc: '历史文化路线' },
  { key: '休闲游', label: '🌿 休闲游', desc: '轻松惬意路线' },
];

export default function RecommendationBar({ onSelect, selected }: RecommendationBarProps) {
  return (
    <div style={styles.container}>
      <span style={styles.label}>选择您的游览偏好：</span>
      <div style={styles.tags}>
        {TAGS.map(tag => (
          <button
            key={tag.key}
            onClick={() => onSelect(tag.key)}
            style={{
              ...styles.tag,
              background: selected === tag.key ? '#1976D2' : '#fff',
              color: selected === tag.key ? '#fff' : '#555',
              borderColor: selected === tag.key ? '#1976D2' : '#e0e0e0',
            }}
            title={tag.desc}
          >
            {tag.label}
          </button>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 0',
    flexWrap: 'wrap',
  },
  label: {
    fontSize: 13,
    color: '#888',
    whiteSpace: 'nowrap',
  },
  tags: {
    display: 'flex',
    gap: 8,
    flexWrap: 'wrap',
  },
  tag: {
    padding: '6px 16px',
    borderRadius: 20,
    border: '1.5px solid #e0e0e0',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
  },
};
