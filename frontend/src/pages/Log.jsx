import { useEffect, useState } from "react";
import api from "../api.js";

export default function Log() {
  const [log, setLog] = useState([]);
  useEffect(() => {
    api.get("/publish/log").then((r) => setLog(r.data)).catch(() => {});
  }, []);

  return (
    <div>
      <h1>Журнал публикаций</h1>
      <div className="card">
        <p className="muted">Синхронизация в Google Sheets и архив в Google Drive — этап 2.</p>
        <table>
          <thead><tr><th>ID</th><th>Задание</th><th>Платформа</th><th>Статус</th><th>Ссылка</th><th>Опубликовано</th></tr></thead>
          <tbody>
            {log.map((r) => (
              <tr key={r.id}>
                <td>#{r.id}</td>
                <td>#{r.job_id}</td>
                <td>{r.platform}</td>
                <td>
                  <b>{r.status}</b>
                  {r.stats?.note && <div className="muted small">{r.stats.note}</div>}
                </td>
                <td className="small">{r.url || "—"}</td>
                <td className="muted">{r.published_at?.slice(0, 19).replace("T", " ") || "—"}</td>
              </tr>
            ))}
            {log.length === 0 && <tr><td colSpan={6} className="muted">Публикаций пока нет</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
