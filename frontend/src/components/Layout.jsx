import { NavLink, Outlet } from "react-router-dom";
import api from "../api.js";
import { useEffect, useState } from "react";

export default function Layout() {
  const [user, setUser] = useState(null);
  const [license, setLicense] = useState(null);
  const [brand, setBrand] = useState(null);
  const [menuOpen, setMenuOpen] = useState(true);

  useEffect(() => {
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {});
    api.get("/settings/license").then((r) => setLicense(r.data)).catch(() => {});
    api.get("/settings/branding").then((r) => setBrand(r.data)).catch(() => {});
  }, []);

  const logout = () => {
    localStorage.removeItem("cf_token");
    location.href = "/login";
  };

  const nav = [
    { to: "/", label: "Дашборд", end: true, icon: "📊" },
    { to: "/topics", label: "Темы и расписание", icon: "🎯" },
    { to: "/jobs", label: "Задания", icon: "🎬" },
    { to: "/log", label: "Журнал", icon: "📜" },
    { to: "/analytics", label: "Аналитика", icon: "📈" },
    { to: "/settings", label: "Подключения", icon: "🔌" },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">🎬</div>
          <span>{brand?.app_name || "Content Factory"}</span>
          <button className="burger" onClick={() => setMenuOpen(!menuOpen)} style={{ marginLeft: "auto" }}>{menuOpen ? "✕" : "☰"}</button>
        </div>
        {(menuOpen || window.innerWidth > 860) && (
          <nav>
            {nav.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
                <span>{n.icon}</span> {n.label}
              </NavLink>
            ))}
          </nav>
        )}
        <div className="sidebar-bottom">
          <div className="license-badge">
            {license ? (
              license.demo ? <span title="Демо: до 3 роликов с водяным знаком">ДЕМО · 3/∞</span>
                : <span>{license.tier.toUpperCase()} · {license.channels} кан.</span>
            ) : null}
          </div>
          {user && <div className="user"><span>👤 {user.username}</span><button className="link" onClick={logout}>выйти</button></div>}
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
