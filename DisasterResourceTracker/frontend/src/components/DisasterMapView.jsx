import React, { useState, useEffect } from "react";
import { getStates, getDistricts } from "../services/api";

export default function DisasterMapView({ initialSearch = "" }) {
  const [states, setStates] = useState([]);
  const [selectedStateId, setSelectedStateId] = useState("");
  const [selectedTier, setSelectedTier] = useState("");
  const [search, setSearch] = useState(initialSearch);

  const [districts, setDistricts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedDistrict, setSelectedDistrict] = useState(null);

  // Fetch states
  useEffect(() => {
    getStates()
      .then((data) => setStates(data.states || []))
      .catch((err) => setError(err.message));
  }, []);

  // Fetch districts with filters
  useEffect(() => {
    setLoading(true);
    setError(null);

    getDistricts({
      state_id: selectedStateId || undefined,
      risk_tier: selectedTier || undefined,
      search: search.trim() || undefined,
    })
      .then((data) => {
        setDistricts(data.districts || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedStateId, selectedTier, search]);

  const resetFilters = () => {
    setSelectedStateId("");
    setSelectedTier("");
    setSearch("");
  };

  return (
    <div className="panel" style={{ minHeight: "600px" }}>
      <div className="panel-heading">
        <div>
          <h2>📍 State & District Flood Vulnerability Analysis</h2>
          <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            Comprehensive risk profiling across all 732 districts and 37 Indian States / UTs.
          </p>
        </div>
        <span className="badge badge-unverified" style={{ fontSize: "12px", padding: "6px 12px" }}>
          Districts Listed: {districts.length}
        </span>
      </div>

      {/* Filter Toolbar */}
      <div className="filter-bar">
        <div className="filter-group" style={{ flex: "1 1 200px" }}>
          <label>Search District or State</label>
          <input
            type="text"
            className="filter-input"
            placeholder="e.g. Patna, Pune, Bihar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="filter-group" style={{ flex: "0 1 220px" }}>
          <label>Filter by State / UT</label>
          <select
            className="filter-select"
            value={selectedStateId}
            onChange={(e) => setSelectedStateId(e.target.value)}
          >
            <option value="">All 37 States & UTs</option>
            {states.map((st) => (
              <option key={st.state_id} value={st.state_id}>
                {st.state_name} ({st.district_count} districts)
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group" style={{ flex: "0 1 160px" }}>
          <label>Vulnerability Tier</label>
          <select
            className="filter-select"
            value={selectedTier}
            onChange={(e) => setSelectedTier(e.target.value)}
          >
            <option value="">All Risk Tiers</option>
            <option value="High">High Risk</option>
            <option value="Moderate">Moderate Risk</option>
            <option value="Low">Low Risk</option>
          </select>
        </div>

        <div className="filter-group" style={{ alignSelf: "flex-end" }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={resetFilters}
            style={{ padding: "8px 12px", height: "35px" }}
          >
            Reset
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="alert-banner alert-error">
          <div>
            <strong>Error Fetching Districts:</strong> {error}
          </div>
        </div>
      )}

      {/* Loading & Empty State */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Calculating risk metrics and loading districts...</p>
        </div>
      ) : districts.length === 0 ? (
        <div className="empty-state">
          <p style={{ fontSize: "36px", marginBottom: "8px" }}>🔍</p>
          <h3>No Districts Found</h3>
          <p>No districts match the selected state or risk tier criteria.</p>
          <button className="btn-secondary" onClick={resetFilters} style={{ marginTop: "12px" }}>
            Clear Filters
          </button>
        </div>
      ) : (
        /* Districts Table */
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>District & State</th>
                <th>Risk Tier</th>
                <th>Risk Score (0-100)</th>
                <th>DFSI Index</th>
                <th>Inundated Area (%)</th>
                <th>Population</th>
                <th>Historical Casualties</th>
                <th>Flood Duration</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {districts.map((d) => (
                <tr key={d.district_id}>
                  <td>
                    <strong>{d.district_name}</strong>
                    <div style={{ fontSize: "11px", color: "#64748b" }}>
                      State: {d.state_name}
                    </div>
                  </td>
                  <td>
                    {d.risk_tier === "High" && <span className="badge badge-high">High</span>}
                    {d.risk_tier === "Moderate" && <span className="badge badge-mod">Moderate</span>}
                    {d.risk_tier === "Low" && <span className="badge badge-low">Low</span>}
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <strong style={{ fontSize: "14px" }}>{d.risk_score}</strong>
                      <div
                        style={{
                          width: "50px",
                          height: "6px",
                          background: "#e2e8f0",
                          borderRadius: "3px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(d.risk_score, 100)}%`,
                            height: "100%",
                            background:
                              d.risk_tier === "High"
                                ? "#dc2626"
                                : d.risk_tier === "Moderate"
                                ? "#d97706"
                                : "#16a34a",
                          }}
                        />
                      </div>
                    </div>
                  </td>
                  <td>{d.dfsi_score?.toFixed(2) ?? "—"}</td>
                  <td>{d.corrected_flooded_area?.toFixed(2) ?? "0.00"}%</td>
                  <td>{d.population?.toLocaleString() ?? "0"}</td>
                  <td>
                    {d.human_fatality_total > 0 ? (
                      <span style={{ color: "#dc2626", fontWeight: "600" }}>
                        {d.human_fatality_total} deaths
                      </span>
                    ) : (
                      <span style={{ color: "#94a3b8" }}>0</span>
                    )}
                  </td>
                  <td>{d.mean_flood_duration_days?.toFixed(1) ?? "0.0"} days</td>
                  <td>
                    <button
                      className="btn-secondary"
                      style={{ padding: "4px 8px", fontSize: "11px" }}
                      onClick={() => setSelectedDistrict(d)}
                    >
                      Profile
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* District Detail Modal */}
      {selectedDistrict && (
        <div className="modal-overlay" onClick={() => setSelectedDistrict(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {selectedDistrict.district_name}, {selectedDistrict.state_name}
              </h3>
              <button className="modal-close-btn" onClick={() => setSelectedDistrict(null)}>
                ×
              </button>
            </div>

            <div className="modal-body">
              <div
                style={{
                  background:
                    selectedDistrict.risk_tier === "High"
                      ? "#fee2e2"
                      : selectedDistrict.risk_tier === "Moderate"
                      ? "#fef3c7"
                      : "#dcfce7",
                  padding: "16px",
                  borderRadius: "10px",
                  marginBottom: "18px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <span
                    className={
                      selectedDistrict.risk_tier === "High"
                        ? "badge badge-high"
                        : selectedDistrict.risk_tier === "Moderate"
                        ? "badge badge-mod"
                        : "badge badge-low"
                    }
                  >
                    {selectedDistrict.risk_tier} Vulnerability Tier
                  </span>
                  <h2 style={{ marginTop: "6px", fontSize: "22px" }}>
                    Risk Score: {selectedDistrict.risk_score} / 100
                  </h2>
                </div>
                <div style={{ textAlign: "right" }}>
                  <small style={{ color: "#64748b" }}>Population</small>
                  <p style={{ fontWeight: "bold", fontSize: "16px" }}>
                    {selectedDistrict.population?.toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="detail-grid">
                <div className="detail-item">
                  <strong>District Flood Susceptibility (DFSI)</strong>
                  <span>{selectedDistrict.dfsi_score?.toFixed(4) || "—"}</span>
                </div>
                <div className="detail-item">
                  <strong>Corrected Inundated Land Area</strong>
                  <span>{selectedDistrict.corrected_flooded_area?.toFixed(2)}%</span>
                </div>
                <div className="detail-item">
                  <strong>Gross Flooded Area</strong>
                  <span>{selectedDistrict.percent_flooded_area?.toFixed(2)}%</span>
                </div>
                <div className="detail-item">
                  <strong>Permanent Water Bodies</strong>
                  <span>{selectedDistrict.permanent_water_percent?.toFixed(2)}%</span>
                </div>
                <div className="detail-item">
                  <strong>Cumulative Human Casualties</strong>
                  <span>
                    {selectedDistrict.human_fatality_total} deaths, {selectedDistrict.human_injured_total} injured
                  </span>
                </div>
                <div className="detail-item">
                  <strong>Mean Disaster Persistence</strong>
                  <span>{selectedDistrict.mean_flood_duration_days?.toFixed(1)} days</span>
                </div>
              </div>

              <div style={{ marginTop: "18px", fontSize: "12px", color: "#64748b", background: "#f8fafc", padding: "12px", borderRadius: "8px" }}>
                <strong>Algorithm Methodology Note:</strong> District risk scores are calculated using a multi-criteria project heuristic combining DFSI (35%), Flooded Area (30%), Casualty Rate per 100k (20%), and Duration (15%).
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedDistrict(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
