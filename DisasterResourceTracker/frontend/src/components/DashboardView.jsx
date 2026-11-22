import React from "react";

export default function DashboardView({ stats, loading, error, onRetry, onNavigate }) {
  if (loading && !stats) {
    return (
      <div className="panel loading-state">
        <div className="spinner"></div>
        <h3>Loading Real-Time Disaster Statistics...</h3>
        <p>Connecting to Flask SQLite backend at http://127.0.0.1:5000</p>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="alert-banner alert-error">
        <div>
          <strong>Backend Connection Error:</strong> {error}
        </div>
        {onRetry && (
          <button className="alert-retry-btn" onClick={onRetry}>
            ↻ Retry
          </button>
        )}
      </div>
    );
  }

  const kpis = [
    {
      icon: "⚠",
      title: "Total Flood Events",
      value: stats ? stats.total_disasters?.toLocaleString() : "—",
      sub: "Historical IMD records",
      color: "red",
    },
    {
      icon: "👥",
      title: "People Affected / Injured",
      value: stats ? stats.total_injured?.toLocaleString() : "—",
      sub: "Recorded injuries",
      color: "blue",
    },
    {
      icon: "✚",
      title: "Total Fatalities",
      value: stats ? stats.total_fatalities?.toLocaleString() : "—",
      sub: "Documented casualties",
      color: "green",
    },
    {
      icon: "📦",
      title: "Available Relief Supplies",
      value: stats && stats.resources ? stats.resources.available_quantity?.toLocaleString() : "—",
      sub: `${stats?.resources?.total_resource_types || 0} resource types tracked`,
      color: "orange",
    },
  ];

  return (
    <>
      {error && (
        <div className="alert-banner alert-error">
          <div>
            <strong>Warning:</strong> {error}
          </div>
          {onRetry && (
            <button className="alert-retry-btn" onClick={onRetry}>
              ↻ Retry
            </button>
          )}
        </div>
      )}

      {/* KPI Stats Grid */}
      <section className="stats-grid">
        {kpis.map((kpi) => (
          <div className="stat-card" key={kpi.title}>
            <div className={`stat-icon ${kpi.color}`}>{kpi.icon}</div>
            <div className="stat-info">
              <h2>{kpi.value}</h2>
              <p>{kpi.title}</p>
              <small>{kpi.sub}</small>
            </div>
          </div>
        ))}
      </section>

      {/* Middle Dashboard Grid */}
      <section className="dashboard-grid">
        {/* District Risk Distribution Panel */}
        <div className="panel map-panel">
          <div className="panel-heading">
            <h3>📍 District Vulnerability & Risk Tier Distribution</h3>
            <button onClick={() => onNavigate("Disaster Map")}>View All 732 Districts →</button>
          </div>

          <div style={{ padding: "15px 0" }}>
            <p style={{ color: "#64748b", fontSize: "13px", marginBottom: "16px" }}>
              Based on algorithmic multi-factor analysis (DFSI flood susceptibility, percent inundated area,
              population density, and flood duration).
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
              <div style={{ background: "#fee2e2", padding: "16px", borderRadius: "10px", textAlign: "center" }}>
                <span className="badge badge-high" style={{ marginBottom: "8px" }}>
                  High Risk
                </span>
                <h2 style={{ fontSize: "24px", color: "#b91c1c", marginTop: "6px" }}>
                  {stats?.risk_distribution?.High ?? 0}
                </h2>
                <small style={{ color: "#991b1b" }}>Critical Attention</small>
              </div>

              <div style={{ background: "#fef3c7", padding: "16px", borderRadius: "10px", textAlign: "center" }}>
                <span className="badge badge-mod" style={{ marginBottom: "8px" }}>
                  Moderate Risk
                </span>
                <h2 style={{ fontSize: "24px", color: "#b45309", marginTop: "6px" }}>
                  {stats?.risk_distribution?.Moderate ?? 0}
                </h2>
                <small style={{ color: "#92400e" }}>Active Monitoring</small>
              </div>

              <div style={{ background: "#dcfce7", padding: "16px", borderRadius: "10px", textAlign: "center" }}>
                <span className="badge badge-low" style={{ marginBottom: "8px" }}>
                  Low Risk
                </span>
                <h2 style={{ fontSize: "24px", color: "#15803d", marginTop: "6px" }}>
                  {stats?.risk_distribution?.Low ?? 0}
                </h2>
                <small style={{ color: "#166534" }}>Standard Readiness</small>
              </div>
            </div>

            <div style={{ marginTop: "18px", display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#64748b" }}>
              <span>Total Districts Profiled: <strong>{stats?.total_districts || 732}</strong></span>
              <span>Total States / UTs: <strong>{stats?.total_states || 37}</strong></span>
            </div>
          </div>
        </div>

        {/* Top Disaster Triggers Panel */}
        <div className="panel chart-panel">
          <div className="panel-heading">
            <h3>Top Meteorological Triggers</h3>
          </div>

          <div style={{ padding: "8px 0" }}>
            {stats?.top_causes && stats.top_causes.length > 0 ? (
              stats.top_causes.map((item, index) => (
                <div
                  key={index}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 0",
                    borderBottom: "1px solid #f1f5f9",
                    fontSize: "13px",
                  }}
                >
                  <span style={{ textTransform: "capitalize", fontWeight: "500" }}>{item.main_cause}</span>
                  <span className="badge badge-unverified">
                    {item.count.toLocaleString()} events
                  </span>
                </div>
              ))
            ) : (
              <p style={{ color: "#718198", fontSize: "13px" }}>No trigger statistics available</p>
            )}
          </div>
        </div>

        {/* Recent Flood Events Panel */}
        <div className="panel recent-panel">
          <div className="panel-heading">
            <h3>◷ Recent Flood Events</h3>
            <button onClick={() => onNavigate("Disaster Records")}>View All 6,876 Records →</button>
          </div>

          <div className="event-list">
            {stats?.recent_events && stats.recent_events.length > 0 ? (
              stats.recent_events.map((evt) => (
                <div className="event-row" key={evt.event_id}>
                  <div className="event-thumb">🌊</div>
                  <div className="event-info">
                    <strong>{evt.districts_mentioned ? `${evt.districts_mentioned}, ${evt.state_name}` : evt.state_name}</strong>
                    <span>
                      {evt.start_date || "Date unrecorded"} · Trigger: {evt.main_cause}
                    </span>
                  </div>
                  <span className="badge badge-unverified">
                    {evt.human_fatality ? `${evt.human_fatality} casualties` : "0 casualties"}
                  </span>
                </div>
              ))
            ) : (
              <p style={{ color: "#718198", fontSize: "13px" }}>No recent events recorded</p>
            )}
          </div>
        </div>
      </section>

      {/* Bottom Operational Grid */}
      <section className="bottom-grid">
        {/* Relief Resources Inventory Overview */}
        <div className="panel resources-panel">
          <div className="panel-heading">
            <h3>📦 Relief Supplies Stock Status</h3>
            <button onClick={() => onNavigate("Resources")}>Manage Inventory →</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "12px", marginTop: "10px" }}>
            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>Total Procured</span>
              <h3 style={{ fontSize: "18px", color: "#0f172a", marginTop: "4px" }}>
                {stats?.resources?.total_quantity?.toLocaleString() || "0"} units
              </h3>
            </div>

            <div style={{ background: "#f0fdf4", padding: "14px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
              <span style={{ fontSize: "11px", color: "#166534", textTransform: "uppercase" }}>Available to Dispatch</span>
              <h3 style={{ fontSize: "18px", color: "#15803d", marginTop: "4px" }}>
                {stats?.resources?.available_quantity?.toLocaleString() || "0"} units
              </h3>
            </div>
          </div>

          <div style={{ marginTop: "14px", fontSize: "12px", color: "#64748b" }}>
            <span>Pending Relief Requests: <strong>{stats?.pending_requests_count ?? 0}</strong></span>
            <span style={{ marginLeft: "15px" }}>Community Reports: <strong>{stats?.reported_incidents_count ?? 0}</strong></span>
          </div>
        </div>

        {/* Quick Submit Request Action */}
        <div className="panel request-panel">
          <h3>🆘 Need Emergency Supplies?</h3>
          <p>Field coordinators and relief officers can submit supply requests prioritized by algorithmic vulnerability scores.</p>
          <button onClick={() => onNavigate("Request Resources")}>
            Submit Relief Request →
          </button>
          <span className="request-art">💧 📦 ✚</span>
        </div>

        {/* Quick Report Disaster Action */}
        <div className="panel mission-panel">
          <h3>⚠ Report an Incident</h3>
          <p>
            Witnessing rising waters or infrastructure damage? Submit an incident report to assist emergency response coordination.
          </p>
          <button onClick={() => onNavigate("Report Disaster")}>
            Report Active Disaster →
          </button>
        </div>
      </section>
    </>
  );
}
