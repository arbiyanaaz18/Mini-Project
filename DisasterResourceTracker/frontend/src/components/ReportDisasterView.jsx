import React, { useState, useEffect } from "react";
import { getDistricts, reportIncident, getIncidents } from "../services/api";

export default function ReportDisasterView() {
  const [districts, setDistricts] = useState([]);
  const [incidents, setIncidents] = useState([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [formData, setFormData] = useState({
    district_id: "",
    reporter_name: "",
    reporter_phone: "",
    disaster_type: "Flood",
    severity_level: "Severe",
    estimated_affected_people: "0",
    description: "",
  });

  const loadData = () => {
    setLoading(true);
    Promise.all([getDistricts(), getIncidents()])
      .then(([distData, incData]) => {
        setDistricts(distData.districts || []);
        setIncidents(incData.incidents || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.district_id) {
      setError("Please select the affected district.");
      return;
    }
    if (!formData.reporter_name.trim() || formData.reporter_name.trim().length < 2) {
      setError("Please provide a valid reporter name (at least 2 characters).");
      return;
    }
    if (!formData.reporter_phone.trim()) {
      setError("Please provide a contact phone number.");
      return;
    }
    if (!formData.description.trim()) {
      setError("Please describe the incident details.");
      return;
    }

    const affected = parseInt(formData.estimated_affected_people, 10);
    if (isNaN(affected) || affected < 0) {
      setError("Estimated affected people must be a non-negative number.");
      return;
    }

    setSubmitting(true);
    reportIncident({
      district_id: parseInt(formData.district_id, 10),
      reporter_name: formData.reporter_name.trim(),
      reporter_phone: formData.reporter_phone.trim(),
      disaster_type: formData.disaster_type,
      severity_level: formData.severity_level,
      estimated_affected_people: affected,
      description: formData.description.trim(),
    })
      .then(() => {
        setSubmitting(false);
        setSuccessMsg("Disaster incident logged successfully into response dispatch system.");
        setFormData({
          district_id: "",
          reporter_name: "",
          reporter_phone: "",
          disaster_type: "Flood",
          severity_level: "Severe",
          estimated_affected_people: "0",
          description: "",
        });
        loadData();
        setTimeout(() => setSuccessMsg(null), 5000);
      })
      .catch((err) => {
        setSubmitting(false);
        setError(err.message);
      });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Incident Intake Form Panel */}
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>⚠ Report Active Disaster Incident</h2>
            <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
              Citizen and volunteer observation intake. Validated data is flagged for emergency verification.
            </p>
          </div>
        </div>

        {successMsg && (
          <div className="alert-banner alert-success">
            <div>✓ {successMsg}</div>
          </div>
        )}

        {error && (
          <div className="alert-banner alert-error">
            <div><strong>Error:</strong> {error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ marginTop: "15px" }}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Affected District & State *</label>
              <select
                className="form-control"
                value={formData.district_id}
                onChange={(e) => setFormData({ ...formData, district_id: e.target.value })}
                required
              >
                <option value="">Select District</option>
                {districts.map((d) => (
                  <option key={d.district_id} value={d.district_id}>
                    {d.district_name} ({d.state_name})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Disaster Phenomenon *</label>
              <select
                className="form-control"
                value={formData.disaster_type}
                onChange={(e) => setFormData({ ...formData, disaster_type: e.target.value })}
              >
                <option value="Flood">Riverine Flood</option>
                <option value="Heavy Rains">Extreme Cloudburst / Heavy Rains</option>
                <option value="Inundation">Urban Waterlogging & Inundation</option>
                <option value="Embankment Breach">Embankment / Dam Breach</option>
                <option value="Landslide">Flood-Induced Landslide</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Severity Level *</label>
              <select
                className="form-control"
                value={formData.severity_level}
                onChange={(e) => setFormData({ ...formData, severity_level: e.target.value })}
              >
                <option value="Critical">Critical (Immediate life threat / water rising)</option>
                <option value="Severe">Severe (Major structural damage / cut off)</option>
                <option value="Moderate">Moderate (Partial submersion / disruption)</option>
                <option value="Minor">Minor (Localized pooling / precautionary)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Estimated People Stranded / Affected</label>
              <input
                type="number"
                min="0"
                className="form-control"
                placeholder="e.g. 50"
                value={formData.estimated_affected_people}
                onChange={(e) => setFormData({ ...formData, estimated_affected_people: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Your Name *</label>
              <input
                type="text"
                className="form-control"
                placeholder="Full Name"
                value={formData.reporter_name}
                onChange={(e) => setFormData({ ...formData, reporter_name: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Contact Phone Number *</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. +91 9876543210 (10-15 digits)"
                value={formData.reporter_phone}
                onChange={(e) => setFormData({ ...formData, reporter_phone: e.target.value })}
                required
              />
            </div>

            <div className="form-group form-full">
              <label className="form-label">Ground Situation Description *</label>
              <textarea
                className="form-control"
                placeholder="Specify precise location, landmark, water depth, road blockages, or emergency needs..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                required
              />
            </div>
          </div>

          <div style={{ marginTop: "18px", display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="btn-submit" disabled={submitting}>
              {submitting ? "Transmitting Incident..." : "Submit Incident Report →"}
            </button>
          </div>
        </form>
      </div>

      {/* Incident Log Table */}
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>📡 Community Incident Log & Field Reports</h2>
            <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
              Newest incoming reports listed first for field coordinator verification.
            </p>
          </div>
          <span className="badge badge-unverified">
            Total Logged: {incidents.length}
          </span>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading field incident reports...</p>
          </div>
        ) : incidents.length === 0 ? (
          <div className="empty-state">
            <p style={{ fontSize: "32px" }}>📡</p>
            <h3>No Community Incidents Reported</h3>
            <p>Use the form above to log field observations of active flooding or infrastructure hazards.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Location</th>
                  <th>Phenomenon</th>
                  <th>Severity</th>
                  <th>Affected</th>
                  <th>Reporter</th>
                  <th>Details</th>
                  <th>Verification</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <tr key={inc.incident_id}>
                    <td>
                      <small style={{ color: "#64748b" }}>{inc.reported_at}</small>
                    </td>
                    <td>
                      <strong>{inc.district_name || `District #${inc.district_id}`}</strong>
                      <div style={{ fontSize: "11px", color: "#64748b" }}>{inc.state_name}</div>
                    </td>
                    <td>{inc.disaster_type}</td>
                    <td>
                      <span
                        className={
                          inc.severity_level === "Critical"
                            ? "badge badge-crit"
                            : inc.severity_level === "Severe"
                            ? "badge badge-high"
                            : inc.severity_level === "Moderate"
                            ? "badge badge-mod"
                            : "badge badge-low"
                        }
                      >
                        {inc.severity_level}
                      </span>
                    </td>
                    <td>{inc.estimated_affected_people || 0} people</td>
                    <td>
                      <div>{inc.reporter_name}</div>
                      <small style={{ color: "#64748b" }}>{inc.reporter_phone}</small>
                    </td>
                    <td style={{ maxWidth: "250px" }}>
                      <span style={{ fontSize: "12px", color: "#334155" }}>{inc.description}</span>
                    </td>
                    <td>
                      <span className="badge badge-unverified">
                        {inc.verification_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
