import { useEffect, useState } from "react";
import api from "../api.js";

const PLATFORMS = [
  { id: "youtube", label: "YouTube Shorts" },
  { id: "tiktok", label: "TikTok" },
  { id: "telegram", label: "Telegram" },
  { id: "vk", label: "VK Clips" },
  { id: "reels", label: "Reels (Pro+)" },
];

const TEMPLATES = [
  { id: "facts", label: "Факты" },
  { id: "top5", label: "Топ-5" },
  { id: "story", label: "История" },
  { id: "qa", label: "Вопрос-ответ" },
  { id: "myth", label: "Разрушение мифа" },
  { id: "chat", label: "💬 Фейк-чат (переписка)" },
];

const empty = {
  name: "", niche: "", language: "ru", tone: "casual", template: "facts",
  schedule_cron: "0 9,18 * * *", videos_per_day: 2, enabled: true,
  platforms: ["youtube"], auto_publish: false, auto_hashtags: true,
};

export default function Topics() {
  const [topics, setTopics] = useState([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = () => api.get("/topics").then((r) => setTopics(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const togglePlatform = (id) => {
    setForm((f) => ({
      ...f,
      platforms: f.platforms.includes(id) ? f.platforms.filter((p) => p !== id) : [...f.platforms, id],
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (editing) await api.patch(`/topics/${editing}`, form);
      else await api.post("/topics", form);
      setForm(empty); setEditing(null); load();
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка сохранения");
    }
  };

  const edit = (t) => { setForm({ ...t }); setEditing(t.id); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const remove = async (id) => { if (confirm("Удалить тему?")) { await api.delete(`/topics/${id}`); load(); } };

  return (
    <div>
      <h1>Темы и расписание</h1>

      <form className="card" onSubmit={submit}>
        <h2>{editing ? `Редактируем тему #${editing}` : "Новая тема"}</h2>
        <div className="form-grid">
          <label>Название
            <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Факты о космосе" required />
          </label>
          <label>Тема / ключевые слова
            <input value={form.niche} onChange={(e) => set("niche", e.target.value)} placeholder="космос, планеты, наука" required />
          </label>
          <label>Язык
            <select value={form.language} onChange={(e) => set("language", e.target.value)}>
              <option value="ru">Русский</option><option value="en">English</option>
              <option value="es">Español</option><option value="de">Deutsch</option><option value="fr">Français</option>
            </select>
          </label>
          <label>Тон
            <select value={form.tone} onChange={(e) => set("tone", e.target.value)}>
              <option value="casual">Разговорный</option><option value="dramatic">Эмоциональный</option>
              <option value="expert">Экспертный</option>
            </select>
          </label>
          <label>Шаблон сценария
            <select value={form.template} onChange={(e) => set("template", e.target.value)}>
              {TEMPLATES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
          </label>
          <label>Cron-расписание
            <input value={form.schedule_cron} onChange={(e) => set("schedule_cron", e.target.value)} placeholder="0 9,18 * * *" />
            <div className="cron-presets">
              {[
                ["09:00 ежедневно","0 9 * * *"],
                ["09:00 и 18:00","0 9,18 * * *"],
                ["каждые 6 часов","0 */6 * * *"],
                ["каждый час","0 * * * *"],
                ["пн-пт 10:00","0 10 * * 1-5"],
              ].map(([label,cron])=>(
                <button key={cron} type="button" onClick={()=>set("schedule_cron", cron)}>{label}</button>
              ))}
            </div>
          </label>
          <label>Видео в день
            <input type="number" min="1" max="50" value={form.videos_per_day} onChange={(e) => set("videos_per_day", +e.target.value)} />
          </label>
          <label>Голос (voice_id, Pro: ElevenLabs/HeyGen)
            <input value={form.voice_id || ""} onChange={(e) => set("voice_id", e.target.value || null)} placeholder="оставьте пустым — авто" />
          </label>
          <label>AI-аватар (avatar_id, Pro: HeyGen)
            <input value={form.avatar_id || ""} onChange={(e) => set("avatar_id", e.target.value || null)} placeholder="оставьте пустым — фейслесс" />
            <small className="muted">введите avatar_id из HeyGen для говорящего аватара</small>
          </label>
        </div>
        <div className="form-row">
          <label className="check"><input type="checkbox" checked={form.enabled} onChange={(e) => set("enabled", e.target.checked)} /> Расписание активно</label>
          <label className="check"><input type="checkbox" checked={form.auto_publish} onChange={(e) => set("auto_publish", e.target.checked)} /> Автопубликация без модерации</label>
          <label className="check"><input type="checkbox" checked={form.auto_hashtags} onChange={(e) => set("auto_hashtags", e.target.checked)} /> Авто-хештеги</label>
        </div>
        <div className="form-row">
          <span className="label">Публикация:</span>
          {PLATFORMS.map((p) => (
            <label key={p.id} className="chip-check">
              <input type="checkbox" checked={form.platforms.includes(p.id)} onChange={() => togglePlatform(p.id)} />
              {p.label}
            </label>
          ))}
        </div>
        {error && <div className="error">{error}</div>}
        <button type="submit" className="btn primary">{editing ? "Сохранить" : "Создать тему"}</button>
        {editing && <button type="button" className="btn" onClick={() => { setForm(empty); setEditing(null); }}>Отмена</button>}
      </form>

      <div className="card">
        <h2>Темы ({topics.length})</h2>
        <table>
          <thead><tr><th>Название</th><th>Расписание</th><th>Видео/день</th><th>Платформы</th><th>Режим</th><th></th></tr></thead>
          <tbody>
            {topics.map((t) => (
              <tr key={t.id}>
                <td><b>{t.name}</b><br /><small className="muted">{t.niche}</small></td>
                <td className="mono">{t.schedule_cron}</td>
                <td>{t.videos_per_day}</td>
                <td>{t.platforms.join(", ") || "—"}</td>
                <td>{t.auto_publish ? "авто" : "модерация"}</td>
                <td>
                  <button className="btn small" onClick={() => edit(t)}>Изменить</button>{" "}
                  <button className="btn small danger" onClick={() => remove(t.id)}>✕</button>
                </td>
              </tr>
            ))}
            {topics.length === 0 && <tr><td colSpan={6} className="muted">Тем пока нет — создайте первую</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
