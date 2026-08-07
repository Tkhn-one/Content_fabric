import { useEffect, useState } from "react";
import api from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [topics, setTopics] = useState([]);
  const [selected, setSelected] = useState("");
  const [oneShot, setOneShot] = useState("");
  const [detail, setDetail] = useState(null);

  const load = () => {
    api.get("/jobs").then((r) => setJobs(r.data)).catch(() => {});
    api.get("/topics").then((r) => setTopics(r.data)).catch(() => {});
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const run = async () => {
    if (selected) await api.post("/jobs", { topic_id: +selected });
    else if (oneShot.trim()) await api.post("/jobs", { niche: oneShot.trim(), name: oneShot.trim(), platforms: ["youtube"] });
    else { alert("Выберите тему или введите разовую тему"); return; }
    load();
  };

  const approve = async (id) => { await api.post(`/jobs/${id}/approve`); load(); };
  const retry = async (id) => { await api.post(`/jobs/${id}/retry`); load(); };
  const open = async (id) => api.get(`/jobs/${id}`).then((r) => setDetail(r.data)).catch(() => {});

  return (
    <div>
      <h1>Задания</h1>
      <div className="card row">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">— по расписанию темы —</option>
          {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <input value={oneShot} onChange={(e) => setOneShot(e.target.value)} placeholder="или разовая тема (без сохранения)" />
        <button className="btn primary" onClick={run}>🎬 Сгенерировать сейчас</button>
      </div>

      <div className="card">
        <h2>История заданий</h2>
        <table>
          <thead><tr><th>ID</th><th>Тема</th><th>Статус</th><th>Ошибка</th><th></th></tr></thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>#{j.id}</td>
                <td>{topics.find((t) => t.id === j.topic_id)?.name || `тема #${j.topic_id}`}</td>
                <td><StatusBadge status={j.status} /></td>
                <td className="muted small">{j.error || ""}</td>
                <td>
                  <button className="btn small" onClick={() => open(j.id)}>Детали</button>{" "}
                  {j.status === "review" && <button className="btn small primary" onClick={() => approve(j.id)}>Опубликовать</button>}
                  {j.status === "failed" && <button className="btn small" onClick={() => retry(j.id)}>Повторить</button>}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && <tr><td colSpan={5} className="muted">Заданий нет</td></tr>}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="card">
          <h2>Задание #{detail.id} — {detail.status}</h2>
          {detail.error && <div className="error">{detail.error}</div>}
          <h3>Сценарий</h3>
          <pre className="script">{detail.payload?.script || "—"}</pre>
          {detail.payload?.video_path && (
            <p>🎞 <a href={`/media/${detail.payload.video_path.split("/").slice(-3).join("/")}`} target="_blank" rel="noreferrer">Смотреть ролик</a></p>
          )}
          <h3>Публикации</h3>
          <ul>
            {detail.publish_logs?.map((p, i) => (
              <li key={i}>{p.platform}: <b>{p.status}</b> {p.url && <a href={p.url} target="_blank" rel="noreferrer">{p.url}</a>}</li>
            ))}
            {!detail.publish_logs?.length && <li className="muted">нет публикаций</li>}
          </ul>
          <button className="btn" onClick={() => setDetail(null)}>Закрыть</button>
        </div>
      )}
    </div>
  );
}
