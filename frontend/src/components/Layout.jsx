import { NavLink, Outlet } from "react-router-dom";
import api from "../api.js";
import { useEffect, useState } from "react";

export default function Layout() {
  const [user, setUser] = useState(null);
  const [license, setLicense] = useState(null);
  const [brand, setBrand] = useState(null);

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
    { to: "/", label: "Дашборд", end: true },
    { to: "/topics", label: "Темы и расписание" },
    { to: "/jobs", label: "Задания" },
    { to: "/log", label: "Журнал публикаций" },
    { to: "/analytics", label: "Аналитика" },
    { to: "/settings", label: "Подключения и API" },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          {brand?.logo_url ? <img src={brand.logo_url} alt="" style={{ height: "22px", verticalAlign: "middle", marginRight: "6px" }} /> : "🎬"}
          {" "}{brand?.app_name || "Content Factory"}
        </div>
        <nav>
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="license-badge">
            {license ? (
              license.demo ? (
                <span title="Демо-режим: водяной знак, до 3 роликов">ДЕМО-РЕЖИМ</span>
              ) : (
                <span title="Лицензия активна">
                  {license.tier.toUpperCase()} · {license.channels} кан.
                </span>
              )
            ) : null}
          </div>
          {user && <div className="user">{user.username} · <button className="link" onClick={logout}>выйти</button></div>}
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
