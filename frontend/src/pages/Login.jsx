import { useState } from "react";
import api from "../api.js";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const url = mode === "login" ? "/auth/login" : "/auth/register";
      const { data } = await api.post(url, { username, password });
      localStorage.setItem("cf_token", data.access_token);
      location.href = "/";
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка входа");
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <h1>🎬 Content Factory</h1>
        <p className="muted">Автогенерация Shorts: идеи → сценарий → видео → публикация</p>
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Логин" required />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Пароль" type="password" required />
        {error && <div className="error">{error}</div>}
        <button type="submit" className="btn primary">{mode === "login" ? "Войти" : "Создать администратора"}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Нет аккаунта? Первый запуск — зарегистрируйтесь" : "Уже есть аккаунт? Войти"}
        </button>
      </form>
    </div>
  );
}
