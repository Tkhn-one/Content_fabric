import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Jobs from "./pages/Jobs.jsx";
import Login from "./pages/Login.jsx";
import Log from "./pages/Log.jsx";
import Settings from "./pages/Settings.jsx";
import Topics from "./pages/Topics.jsx";

function RequireAuth({ children }) {
  return localStorage.getItem("cf_token") ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="topics" element={<Topics />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="log" element={<Log />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
