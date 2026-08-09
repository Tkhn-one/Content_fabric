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

  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const showToast = (m) => { setToast(m); setTimeout(()=>setToast(""), 2800); };
  const [filter, setFilter] = useState("all");

  const run = async () => {
    if (!selected && !oneShot.trim()) { showToast("Выберите тему или введите разовую тему"); return; }
    setBusy(true);
    try{
      if (selected) await api.post("/jobs", { topic_id: +selected });
      else await api.post("/jobs", { niche: oneShot.trim(), name: oneShot.trim(), platforms: ["youtube"] });
      setOneShot(""); showToast("Задание запущено ✓");
    }catch(e){ showToast(e.response?.data?.detail || "Ошибка запуска"); }
    setBusy(false); load();
  };

  const approve = async (id) => { await api.post(`/jobs/${id}/approve`); load(); };
  const retry = async (id) => { await api.post(`/jobs/${id}/retry`); load(); };
  const open = async (id) => api.get(`/jobs/${id}`).then((r) => setDetail(r.data)).catch(() => {});

  // путь к видео может быть с / или \ (Windows) — нормализуем в URL под /media/...
  const mediaHref = (path) => {
    const norm = String(path).replaceAll("\\", "/");
    const idx = norm.indexOf("media/");
    return idx >= 0 ? `/media/${norm.slice(idx + 6)}` : `/media/${norm.split("/").filter(Boolean).slice(-3).join("/")}`;
  };

  const filtered = filter==="all" ? jobs : jobs.filter(j=>j.status===filter);

  return (
    <div>
      <h1>Задания</h1>
      <div className="card row">
        <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{flex:"1 1 200px"}}>
          <option value="">— тема из списка —</option>
          {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <input value={oneShot} onChange={(e) => setOneShot(e.target.value)} placeholder="или разовая тема (без сохранения)" style={{flex:"2 1 260px"}} />
        <button className="btn primary" onClick={run} disabled={busy}>{busy ? "Запуск…" : "🎬 Сгенерировать сейчас"}</button>
      </div>
      {toast && <div className="success" style={{marginTop:"-.6rem"}}>{toast}</div>}

      <div className="card">
        <div className="row" style={{justifyContent:"space-between", marginBottom:".7rem"}}>
          <h2 style={{margin:0}}>История заданий · {jobs.length}</h2>
          <div className="row">
            <select value={filter} onChange={(e)=>setFilter(e.target.value)} style={{width:"auto"}}>
              <option value="all">все</option>
              <option value="review">на модерации</option>
              <option value="done">готово</option>
              <option value="failed">ошибки</option>
              <option value="queued">в очереди</option>
            </select>
            <button className="btn small" onClick={load}>Обновить</button>
          </div>
        </div>
        <div className="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>Тема</th><th>Статус</th><th>Ошибка</th><th></th></tr></thead>
          <tbody>
            {filtered.map((j) => (
              <tr key={j.id}>
                <td>#{j.id}</td>
                <td>{topics.find((t) => t.id === j.topic_id)?.name || `тема #${j.topic_id}`}</td>
                <td><StatusBadge status={j.status} /></td>
                <td className="muted small" style={{maxWidth:"280px", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"}} title={j.error || ""}>{j.error || "—"}</td>
                <td>
                  <button className="btn small" onClick={() => open(j.id)}>Детали</button>{" "}
                  {j.status === "review" && <button className="btn small primary" onClick={() => approve(j.id)}>Опубликовать</button>}
                  {j.status === "failed" && <button className="btn small" onClick={() => retry(j.id)}>Повторить</button>}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={5} className="empty">Ничего не найдено — смените фильтр или создайте задание</td></tr>}
          </tbody>
        </table>
        </div>
      </div>

      {detail && (
        <div className="card">
          <h2>Задание #{detail.id} — {detail.status}</h2>
          {detail.error && <div className="error">{detail.error}</div>}
          <p className="muted small">
            {detail.payload?.voice_note && <>🎙 {detail.payload.voice_note}<br /></>}
            {detail.payload?.video_note && <>🎞 {detail.payload.video_note}</>}
          </p>
          <h3>Сценарий</h3>
          <pre className="script">{detail.payload?.script || "—"}</pre>
          {detail.payload?.video_path && (
            <p>🎬 <a href={mediaHref(detail.payload.video_path)} target="_blank" rel="noreferrer">Смотреть ролик</a> ({detail.payload.video_duration} сек)</p>
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
