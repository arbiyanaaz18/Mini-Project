import { useState, useEffect } from "react";
import "./App.css";
import { getStats } from "./services/api";

import DashboardView from "./components/DashboardView";
import DisasterRecordsView from "./components/DisasterRecordsView";
import DisasterMapView from "./components/DisasterMapView";
import ResourcesView from "./components/ResourcesView";
import RequestResourcesView from "./components/RequestResourcesView";
import ReportDisasterView from "./components/ReportDisasterView";
import StatisticsView from "./components/StatisticsView";

const navigation = [
  ["⌂", "Dashboard"],
  ["📍", "Disaster Map"],
  ["▤", "Disaster Records"],
  ["📦", "Resources"],
  ["⚠", "Report Disaster"],
  ["♡", "Request Resources"],
  ["♧", "Volunteers"],
  ["▥", "Statistics"],
];

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [search, setSearch] = useState("");

  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(null);

  const fetchDashboardStats = () => {
    setStatsLoading(true);
    setStatsError(null);
    getStats()
      .then((data) => {
        setStats(data);
        setStatsLoading(false);
      })
      .catch((err) => {
        setStatsError(err.message);
        setStatsLoading(false);
      });
  };

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const handleGlobalSearch = (e) => {
    e.preventDefault();
    if (search.trim()) {
      setActivePage("Disaster Records");
    }
  };

  return (
    <div className="app">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">✚</div>
          <h2>Disaster<br />Resource Tracker</h2>
          <p>Be Prepared. Be Safe.</p>
        </div>

        <nav className="navigation">
          {navigation.map(([icon, name]) => (
            <button
              key={name}
              className={`nav-item ${activePage === name ? "active" : ""}`}
              onClick={() => setActivePage(name)}
            >
              <span className="nav-icon">{icon}</span>
              {name}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="india-symbol">🇮🇳</div>
          <p>Together for a<br />Safer India</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Top Header Bar */}
        <header className="topbar">
          <form onSubmit={handleGlobalSearch} className="search-box">
            <span>⌕</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search historical records, causes, states..."
            />
          </form>

          <div className="top-actions">
            <button
              className="notification"
              aria-label="Notifications"
              onClick={() => setActivePage("Request Resources")}
              title="Active Relief Requests"
            >
              {stats?.pending_requests_count ? (
                <span style={{ color: "#ef4444", fontWeight: "bold" }}>
                  ! {stats.pending_requests_count}
                </span>
              ) : (
                "♧"
              )}
            </button>
            <button className="profile">
              👤 <span>Admin Officer</span>
            </button>
          </div>
        </header>

        {/* Hero Section Banner */}
        <section className="hero">
          <div className="hero-content">
            <span className="hero-tag">INDIA EMERGENCY MANAGEMENT</span>
            <h1>Disaster Resource Tracker</h1>
            <h2>Real-Time Insights. Faster Relief.</h2>
            <p>
              Integrated multi-dataset monitoring, risk assessment heuristic scoring,
              and real-time relief inventory coordination across India.
            </p>

            <button
              className="hero-button"
              onClick={() => setActivePage("Report Disaster")}
            >
              + Report a Disaster <span>→</span>
            </button>
          </div>
        </section>

        {/* Dynamic Page Views */}
        {activePage === "Dashboard" && (
          <DashboardView
            stats={stats}
            loading={statsLoading}
            error={statsError}
            onRetry={fetchDashboardStats}
            onNavigate={(pageName) => setActivePage(pageName)}
          />
        )}

        {activePage === "Disaster Records" && (
          <DisasterRecordsView initialSearch={search} />
        )}

        {activePage === "Disaster Map" && (
          <DisasterMapView initialSearch={search} />
        )}

        {activePage === "Resources" && (
          <ResourcesView />
        )}

        {activePage === "Request Resources" && (
          <RequestResourcesView />
        )}

        {activePage === "Report Disaster" && (
          <ReportDisasterView />
        )}

        {activePage === "Statistics" && (
          <StatisticsView />
        )}

        {activePage === "Volunteers" && (
          <section className="panel" style={{ minHeight: "450px" }}>
            <div className="panel-heading">
              <div>
                <h2>♧ Community Volunteers & Response Network</h2>
                <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
                  Civil defense volunteers, disaster response coordinators, and grassroots helpers.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "16px", marginTop: "20px" }}>
              <div style={{ background: "#f8fafc", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "28px" }}>🦺</span>
                <h3 style={{ marginTop: "10px", fontSize: "16px" }}>First Responders Network</h3>
                <p style={{ fontSize: "13px", color: "#64748b", marginTop: "6px" }}>
                  Trained local volunteers available on short notice for swift-water rescue and evacuation assistance.
                </p>
                <div style={{ marginTop: "12px", fontWeight: "bold", color: "#2563eb", fontSize: "13px" }}>
                  732 Districts Covered
                </div>
              </div>

              <div style={{ background: "#f8fafc", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "28px" }}>🏥</span>
                <h3 style={{ marginTop: "10px", fontSize: "16px" }}>Medical Relief Brigades</h3>
                <p style={{ fontSize: "13px", color: "#64748b", marginTop: "6px" }}>
                  Volunteer physicians and paramedics trained in mass casualty triage, waterborne disease prevention, and emergency trauma care.
                </p>
                <div style={{ marginTop: "12px", fontWeight: "bold", color: "#16a34a", fontSize: "13px" }}>
                  8,000+ Registered First Aiders
                </div>
              </div>

              <div style={{ background: "#f8fafc", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "28px" }}>🚚</span>
                <h3 style={{ marginTop: "10px", fontSize: "16px" }}>Logistics & Supply Convoy</h3>
                <p style={{ fontSize: "13px", color: "#64748b", marginTop: "6px" }}>
                  Field transport coordinators managing truck dispatches and boat ferries from central storage depots to flood cut-off pockets.
                </p>
                <div style={{ marginTop: "12px", fontWeight: "bold", color: "#d97706", fontSize: "13px" }}>
                  24/7 Dispatch Readiness
                </div>
              </div>
            </div>

            <div style={{ marginTop: "30px", background: "#eff6ff", padding: "20px", borderRadius: "10px", border: "1px solid #bfdbfe", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h4 style={{ color: "#1e40af", fontSize: "15px" }}>Join the Disaster Response Network</h4>
                <p style={{ color: "#3b82f6", fontSize: "13px", marginTop: "4px" }}>
                  Register as a community volunteer to receive real-time relief mobilization alerts.
                </p>
              </div>
              <button
                className="btn-submit"
                onClick={() => setActivePage("Report Disaster")}
                style={{ fontSize: "13px" }}
              >
                Volunteer Signup →
              </button>
            </div>
          </section>
        )}

        {/* Footer */}
        <footer className="footer">
          Disaster Resource Tracker · India 🇮🇳
          <span>Connecting 732 districts, 6,876 historical flood events, and real-time relief allocation.</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
