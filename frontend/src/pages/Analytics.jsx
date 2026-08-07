import { useEffect, useState } from "react";
import api from "../api.js";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

export default function Analytics() {
  const [overview, setOverview] = useState(null);
  const [videos, setVideos] = useState([]);
  const [hours, setHours] = useState([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.get("/stats/overview").then((r) => setOverview(r.data)).catch(() => {});
    api.get("/stats/videos").then((r) => setVideos(r.data)).catch(() => {});
    api.get("/stats/best-hours").then((r) => setHours(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const sync = async () => {
    setBusy(true);
    setMsg("Синхронизация со статистикой YouTube…");
    try {
      const { data } = await api.post("/stats/sync");
      setMsg(data.ok ? `Обновлено: ${data.synced} видео` : data.error);
      load();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Ошибка синхронизации");
    }
    setBusy(false);
  };

  const platformRows = overview
    ? Object.entries(overview.by_platform || {}).map(([p, d]) => ({ platform: p, ...d }))
    : [];

  return (
    <div>
      <h1>Аналитика</h1>
      <div className="row">
        <button className="btn primary" onClick={sync} disabled={busy}>
          {busy ? "Синхронизация…" : "🔄 Синхронизировать с YouTube"}
        </button>
        {msg && <span className="muted">{msg}</span>}
      </div>
      <p className="muted small">Статистика подтягивается из YouTube Data API по опубликованным видео. Нужен подключённый YouTube (Шаг 3 в SETUP_GUIDE).</p>

      <div className="grid cards">
        <div className="card stat"><b>{overview?.total_published ?? "—"}</b><span>Публикаций</span></div>
        <div className="card stat"><b>{overview?.total_views ?? "—"}</b><span>Просмотров</span></div>
        <div className="card stat"><b>{overview?.total_likes ?? "—"}</b><span>Лайков</span></div>
        <div className="card stat"><b>{overview?.total_comments ?? "—"}</b><span>Комментариев</span></div>
      </div>

      {platformRows.length > 0 && (
        <div className="card">
          <h2>По платформам</h2>
          <table>
            <thead><tr><th>Платформа</th><th>Видео</th><th>Просмотры</th><th>Лайки</th><th>Комментарии</th></tr></thead>
            <tbody>
              {platformRows.map((r) => (
                <tr key={r.platform}>
                  <td><b>{r.platform}</b></td>
                  <td>{r.count}</td><td>{r.views}</td><td>{r.likes}</td><td>{r.comments}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h2>Просмотры по последним видео</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={videos.slice(0, 20)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="topic" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94a3b8" }} />
            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }} />
            <Bar dataKey="views" fill="#6366f1" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {hours.length > 0 && (
        <div className="card">
          <h2>Просмотры по часу публикации (UTC)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={hours}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="hour" tick={{ fill: "#94a3b8" }} />
              <YAxis tick={{ fill: "#94a3b8" }} />
              <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }} />
              <Line type="monotone" dataKey="views" stroke="#8b5cf6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
          <p className="muted small">Показывает, в какие часы публикации видео собирают больше просмотров — подсказка для расписания.</p>
        </div>
      )}
    </div>
  );
}
