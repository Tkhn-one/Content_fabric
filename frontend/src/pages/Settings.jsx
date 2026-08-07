import { useEffect, useState } from "react";
import api from "../api.js";

export default function Settings() {
  const [catalog, setCatalog] = useState([]);
  const [providers, setProviders] = useState([]);
  const [license, setLicense] = useState(null);
  const [licenseKey, setLicenseKey] = useState("");
  const [form, setForm] = useState({ provider_type: "llm", provider_name: "", label: "", payload: {}, is_default: false });
  const [msg, setMsg] = useState("");
  const [brand, setBrand] = useState({ app_name: "", logo_url: "" });

  const load = () => {
    api.get("/settings/providers/catalog").then((r) => setCatalog(r.data)).catch(() => {});
    api.get("/settings/providers").then((r) => setProviders(r.data)).catch(() => {});
    api.get("/settings/license").then((r) => setLicense(r.data)).catch(() => {});
    api.get("/settings/branding").then((r) => setBrand(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const types = [...new Set(catalog.map((c) => c.type))];
  const byType = (t) => catalog.filter((c) => c.type === t);

  const save = async (e) => {
    e.preventDefault();
    setMsg("");
    try {
      await api.post("/settings/providers", form);
      setMsg("Сохранено ✓");
      load();
    } catch (err) {
      setMsg(err.response?.data?.detail || "Ошибка");
    }
  };

  const activateLicense = async () => {
    try {
      const { data } = await api.post("/settings/license", { key: licenseKey });
      setMsg(`Лицензия активирована: ${data.tier}`);
      load();
    } catch (err) {
      setMsg(err.response?.data?.detail || "Ключ не подошёл");
    }
  };

  const saveBranding = async () => {
    try {
      await api.put("/settings/branding", brand);
      setMsg("Брендинг сохранён ✓");
    } catch (err) {
      setMsg(err.response?.data?.detail || "Ошибка");
    }
  };

  const fieldValue = (f) => form.payload[f] || "";
  const setField = (f, v) => setForm((s) => ({ ...s, payload: { ...s.payload, [f]: v } }));

  return (
    <div>
      <h1>Подключения и API</h1>

      <div className="card">
        <h2>Лицензия</h2>
        {license && (
          <p>
            Статус: <b>{license.demo ? "ДЕМО-РЕЖИМ (водяной знак)" : `${license.tier.toUpperCase()}, каналов: ${license.channels}`}</b>
            {license.customer && <> · {license.customer}</>}
            {license.support_until && <> · поддержка до {license.support_until}</>}
          </p>
        )}
        <div className="row">
          <input value={licenseKey} onChange={(e) => setLicenseKey(e.target.value)} placeholder="Вставить лицензионный ключ" className="grow" />
          <button className="btn" onClick={activateLicense}>Активировать</button>
        </div>
        <p className="muted small">Ключ выдаётся после покупки. Без ключа система работает в демо-режиме.</p>
      </div>

      <div className="card">
        <h2>Мастер подключения API</h2>
        <p className="muted">Все ключи хранятся зашифрованными на вашем сервере. Никаких скрытых подписок — вы подключаете свои ключи.</p>
        <form className="form-grid" onSubmit={save}>
          <label>Тип
            <select value={form.provider_type} onChange={(e) => setForm({ ...form, provider_type: e.target.value, provider_name: "" })}>
              {types.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label>Провайдер
            <select value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} required>
              <option value="">— выберите —</option>
              {byType(form.provider_type).map((c) => (
                <option key={c.name} value={c.name}>{c.name} {c.free ? "(бесплатно)" : "(платно)"}</option>
              ))}
            </select>
          </label>
          {byType(form.provider_type).find((c) => c.name === form.provider_name) && (
            <>
              {byType(form.provider_type).find((c) => c.name === form.provider_name).fields.map((f) => (
                <label key={f}>{f}
                  <input value={fieldValue(f)} onChange={(e) => setField(f, e.target.value)} placeholder={`Введите ${f}`} />
                </label>
              ))}
            </>
          )}
          <label>Комментарий (необязательно)
            <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} placeholder="например: канал для фактов" />
          </label>
          <label className="check"><input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /> Использовать по умолчанию</label>
          {msg && <div className="error">{msg}</div>}
          <div><button type="submit" className="btn primary">Сохранить подключение</button></div>
        </form>
      </div>

      <div className="card">
        <h2>Брендинг (white-label, Unlimited)</h2>
        <div className="form-grid">
          <label>Название системы
            <input value={brand.app_name} onChange={(e) => setBrand({ ...brand, app_name: e.target.value })} placeholder="Content Factory" />
          </label>
          <label>Логотип (URL)
            <input value={brand.logo_url} onChange={(e) => setBrand({ ...brand, logo_url: e.target.value })} placeholder="https://.../logo.png" />
          </label>
        </div>
        <button className="btn" onClick={saveBranding}>Сохранить брендинг</button>
      </div>

      <div className="card">
        <h2>Справочник провайдеров</h2>
        <table>
          <thead><tr><th>Тип</th><th>Провайдер</th><th>Описание</th><th>Стоимость</th></tr></thead>
          <tbody>
            {catalog.map((c, i) => (
              <tr key={i}>
                <td>{c.type}</td>
                <td><b>{c.name}</b></td>
                <td className="small">{c.description}</td>
                <td>{c.free ? "бесплатно" : "по тарифу провайдера"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
