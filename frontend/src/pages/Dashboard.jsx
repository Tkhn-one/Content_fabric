import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function Dashboard() {
  const [topics, setTopics] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [log, setLog] = useState([]);

  const load = () => {
    api.get("/topics").then((r) => setTopics(r.data)).catch(() => {});
    api.get("/jobs").then((r) => setJobs(r.data)).catch(() => {});
    api.get("/publish/log").then((r) => setLog(r.data)).catch(() => {});
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 10000); // автополинг статусов
    return () => clearInterval(t);
  }, []);

  const active = topics.filter((t) => t.enabled).length;
  const done = jobs.filter((j) => j.status === "done").length;
  const published = log.filter((l) => l.status === "published").length;
  const inReview = jobs.filter((j) => j.status === "review").length;

  return (
    <div>
      <h1>Дашборд</h1>
      <div className="grid cards">
        <div className="card stat"><b>{topics.length}</b><span>Тем</span></div>
        <div className="card stat"><b>{active}</b><span>Расписаний активно</span></div>
        <div className="card stat"><b>{done}</b><span>Видео готово</span></div>
        <div className="card stat"><b>{published}</b><span>Публикаций</span></div>
        {inReview > 0 && (
          <div className="card stat warn"><b>{inReview}</b><span>Ждут модерации</span></div>
        )}
      </div>
      <div className="card">
        <h2>Последние задания</h2>
        <table>
          <thead><tr><th>ID</th><th>Тема</th><th>Статус</th><th>Шаг</th><th>Создано</th></tr></thead>
          <tbody>
            {jobs.slice(0, 8).map((j) => (
              <tr key={j.id}>
                <td>#{j.id}</td>
                <td>{j.topic_id ? `тема #${j.topic_id}` : "—"}</td>
                <td><StatusBadge status={j.status} /></td>
                <td>{j.step}</td>
                <td className="muted">{j.created_at?.slice(0, 19).replace("T", " ")}</td>
              </tr>
            ))}
            {jobs.length === 0 && <tr><td colSpan={5} className="muted">Пока нет заданий</td></tr>}
          </tbody>
        </table>
        <Link className="btn" to="/jobs">Все задания →</Link>
      </div>
    </div>
  );
}
