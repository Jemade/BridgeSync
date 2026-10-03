import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  FileText,
  LayoutDashboard,
  Link2,
  LogOut,
  Menu,
  Settings,
  Upload,
  Check,
} from "lucide-react";
import { api, type User } from "./api";
import { Logo } from "./ui";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Orders from "./pages/Orders";
import Payments from "./pages/Payments";
import Integrations from "./pages/Integrations";
import ActivityPage from "./pages/ActivityPage";
import SettingsPage from "./pages/SettingsPage";

const nav = [
  ["overview", "Overview", LayoutDashboard],
  ["orders", "Orders", FileText],
  ["payments", "Payments", Upload],
  ["integrations", "Integrations", Link2],
  ["activity", "Activity", Activity],
  ["settings", "Settings", Settings],
] as const;
export type Tab = (typeof nav)[number][0];

export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<Tab>(() =>
    nav.some((n) => n[0] === location.hash.slice(1))
      ? (location.hash.slice(1) as Tab)
      : "overview",
  );
  const [mobile, setMobile] = useState(false),
    [revision, setRevision] = useState(0),
    [toast, setToast] = useState("");
  useEffect(() => {
    const expired = () => setUser(null);
    addEventListener("bridgesync:session-expired", expired);
    return () => removeEventListener("bridgesync:session-expired", expired);
  }, []);
  useEffect(() => {
    api<User>("/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    const f = () => {
      const t = location.hash.slice(1);
      if (nav.some((n) => n[0] === t)) setTab(t as Tab);
    };
    addEventListener("hashchange", f);
    return () => removeEventListener("hashchange", f);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 6000);
    return () => clearTimeout(t);
  }, [toast]);
  const refresh = () => setRevision((r) => r + 1);
  function go(t: Tab) {
    setTab(t);
    location.hash = t;
    setMobile(false);
  }
  if (checking)
    return <main className="loading-page">Loading your workspace...</main>;
  if (!user) return <Login onLogin={(u) => setUser(u)} />;
  const write = user.role !== "viewer";
  return (
    <div className="shell">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <Logo />
        <div className="workspace-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav
            .filter((n) => n[0] !== "settings" || user.role === "admin")
            .map(([id, label, Icon]) => (
              <button
                key={id}
                className={tab === id ? "nav-item selected" : "nav-item"}
                onClick={() => go(id)}
                aria-current={tab === id ? "page" : undefined}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="connection-dot" /> Connected to your workspace
          <p>Order delivery &amp; reconciliation</p>
        </div>
      </aside>
      {mobile && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobile(!mobile)}
          >
            <Menu size={20} />
          </button>
          <span className="org-name">{user.organisation}</span>
          <div className="user">
            <span className="avatar">
              {user.name
                .split(" ")
                .map((s) => s[0])
                .slice(0, 2)
                .join("")}
            </span>
            <div>
              <strong>{user.name}</strong>
              <small>{user.role}</small>
            </div>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={async () => {
                await api("/auth/logout", { method: "POST" });
                setUser(null);
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="content">
          <div className="breadcrumb">
            Workspace <span>/</span> {nav.find((n) => n[0] === tab)?.[1]}
          </div>
          {tab === "overview" && <Overview revision={revision} go={go} />}
          {tab === "orders" && (
            <Orders
              revision={revision}
              refresh={refresh}
              write={write}
              notify={setToast}
            />
          )}
          {tab === "payments" && (
            <Payments
              revision={revision}
              refresh={refresh}
              write={write}
              notify={setToast}
            />
          )}
          {tab === "integrations" && (
            <Integrations admin={user.role === "admin"} notify={setToast} />
          )}
          {tab === "activity" && <ActivityPage revision={revision} />}
          {tab === "settings" && user.role === "admin" && (
            <SettingsPage user={user} notify={setToast} />
          )}
          <footer className="footer">
            BridgeSync <span>Reliable work. Clear records.</span>
            <a href="/docs" target="_blank" rel="noreferrer">
              API reference <ArrowRight size={12} />
            </a>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Check size={17} />
          {toast}
        </div>
      )}
    </div>
  );
}
