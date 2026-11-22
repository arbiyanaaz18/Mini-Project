import React, { useState, useEffect } from "react";
import { getTrends } from "../services/api";

export default function StatisticsView() {
  const [trendsData, setTrendsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getTrends()
      .then((data) => {
        setTrendsData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="panel loading-state">
        <div className="spinner"></div>
        <p>Loading longitudinal disaster impact data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-banner alert-error">
        <div><strong>Error Loading Trends:</strong> {error}</div>
      </div>
    );
  }

  const { trends = [], summary = {} } = trendsData || {};

  return (
    <div className="panel" style={{ minHeight: "600px" }}>
      <div className="panel-heading">
        <div>
          <h2>▥ Longitudinal National Disaster Trends (12-Year Analysis)</h2>
          <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            Aggregated historical damage metrics across India from official dataset records.
          </p>
        </div>
        <span className="badge badge-unverified" style={{ fontSize: "12px", padding: "6px 12px" }}>
          Span: {trends.length} Financial Years
        </span>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", margin: "20px 0" }}>
        <div style={{ background: "#fee2e2", padding: "18px", borderRadius: "10px", border: "1px solid #fca5a5" }}>
          <span style={{ fontSize: "11px", color: "#991b1b", textTransform: "uppercase", fontWeight: "bold" }}>
            Cumulative Human Fatalities
          </span>
          <h2 style={{ fontSize: "24px", color: "#b91c1c", marginTop: "6px" }}>
            {summary.total_lives_lost?.toLocaleString() || "0"}
          </h2>
          <small style={{ color: "#7f1d1d" }}>Peak Year: {summary.peak_lives_lost_year}</small>
        </div>

        <div style={{ background: "#fef3c7", padding: "18px", borderRadius: "10px", border: "1px solid #fcd34d" }}>
          <span style={{ fontSize: "11px", color: "#92400e", textTransform: "uppercase", fontWeight: "bold" }}>
            Cumulative Cattle / Livestock Lost
          </span>
          <h2 style={{ fontSize: "24px", color: "#b45309", marginTop: "6px" }}>
            {summary.total_cattle_lost?.toLocaleString() || "0"}
          </h2>
          <small style={{ color: "#78350f" }}>Documented animal losses</small>
        </div>

        <div style={{ background: "#e0f2fe", padding: "18px", borderRadius: "10px", border: "1px solid #7dd3fc" }}>
          <span style={{ fontSize: "11px", color: "#075985", textTransform: "uppercase", fontWeight: "bold" }}>
            Total Housing Units Damaged
          </span>
          <h2 style={{ fontSize: "24px", color: "#0369a1", marginTop: "6px" }}>
            {summary.total_houses_damaged?.toLocaleString() || "0"}
          </h2>
          <small style={{ color: "#0c4a6e" }}>Peak Year: {summary.peak_houses_damaged_year}</small>
        </div>

        <div style={{ background: "#dcfce7", padding: "18px", borderRadius: "10px", border: "1px solid #86efac" }}>
          <span style={{ fontSize: "11px", color: "#166534", textTransform: "uppercase", fontWeight: "bold" }}>
            Cropped Area Inundated
          </span>
          <h2 style={{ fontSize: "24px", color: "#15803d", marginTop: "6px" }}>
            {summary.total_cropped_area_lakh_ha?.toLocaleString() || "0"}
          </h2>
          <small style={{ color: "#14532d" }}>Lakh Hectares</small>
        </div>
      </div>

      {/* 12-Year Longitudinal Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Financial Year</th>
              <th>Human Lives Lost</th>
              <th>Cattle / Livestock Lost</th>
              <th>Houses Damaged</th>
              <th>Cropped Area Damaged (Lakh Ha)</th>
            </tr>
          </thead>
          <tbody>
            {trends.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.year}</strong>
                </td>
                <td>
                  <span style={{ color: row.lives_lost > 2000 ? "#b91c1c" : "#1e293b", fontWeight: row.lives_lost > 2000 ? "bold" : "normal" }}>
                    {row.lives_lost.toLocaleString()}
                  </span>
                </td>
                <td>{row.cattle_lost.toLocaleString()}</td>
                <td>{row.houses_damaged.toLocaleString()}</td>
                <td>{row.cropped_area_affected_lakh_ha.toFixed(2)} lakh ha</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: "20px", background: "#f8fafc", padding: "15px", borderRadius: "8px", fontSize: "12px", color: "#64748b" }}>
        <strong>Source Dataset:</strong> Ingested from <code>cleaned_disaster_dataset_1.csv</code> covering national disaster assessments coordinated by the Government of India.
      </div>
    </div>
  );
}
