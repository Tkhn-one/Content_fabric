const COLORS = {
  queued: "#64748b",
  research: "#3b82f6",
  script: "#8b5cf6",
  review: "#f59e0b",
  voiceover: "#06b6d4",
  render: "#14b8a6",
  publish: "#22c55e",
  done: "#22c55e",
  failed: "#ef4444",
};

const LABELS = {
  queued: "В очереди",
  research: "Идеи и анализ",
  script: "Сценарий",
  review: "Модерация",
  voiceover: "Озвучка",
  render: "Монтаж",
  publish: "Публикация",
  done: "Готово",
  failed: "Ошибка",
};

export default function StatusBadge({ status }) {
  return (
    <span className="badge" style={{ background: COLORS[status] || "#64748b" }}>
      {LABELS[status] || status}
    </span>
  );
}
