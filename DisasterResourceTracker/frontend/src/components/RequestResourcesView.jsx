import React, { useState, useEffect } from "react";
import {
  getDistricts,
  getResources,
  getResourceRequests,
  submitResourceRequest,
  reviewResourceRequest,
} from "../services/api";

export default function RequestResourcesView() {
  const [districts, setDistricts] = useState([]);
  const [resources, setResources] = useState([]);
  const [requests, setRequests] = useState([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    district_id: "",
    resource_id: "",
    requester_name: "",
    requester_contact: "",
    quantity_requested: "",
    urgency_level: "High",
    reason_notes: "",
  });

  // Review Modal State
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [reviewerName, setReviewerName] = useState("Disaster Coordinator");
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      getDistricts(),
      getResources(),
      getResourceRequests(),
    ])
      .then(([distData, resData, reqData]) => {
        setDistricts(distData.districts || []);
        setResources(resData.resources || []);
        setRequests(reqData.requests || []);
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

    const qty = parseInt(formData.quantity_requested, 10);
    if (!formData.district_id || !formData.resource_id) {
      setError("Please select both an affected district and a required relief resource.");
      return;
    }
    if (isNaN(qty) || qty <= 0) {
      setError("Quantity requested must be a positive integer greater than 0.");
      return;
    }
    if (!formData.requester_name.trim() || !formData.requester_contact.trim()) {
      setError("Please provide requester name and contact number.");
      return;
    }

    setSubmitting(true);
    submitResourceRequest({
      district_id: parseInt(formData.district_id, 10),
      resource_id: parseInt(formData.resource_id, 10),
      requester_name: formData.requester_name.trim(),
      requester_contact: formData.requester_contact.trim(),
      quantity_requested: qty,
      urgency_level: formData.urgency_level,
      reason_notes: formData.reason_notes.trim() || undefined,
    })
      .then((data) => {
        setSubmitting(false);
        setSuccessMsg(
          `Request submitted successfully! Priority Dispatch Score: ${data.request?.calculated_priority_score} / 100.`
        );
        setFormData({
          district_id: "",
          resource_id: "",
          requester_name: "",
          requester_contact: "",
          quantity_requested: "",
          urgency_level: "High",
          reason_notes: "",
        });
        loadData();
        setTimeout(() => setSuccessMsg(null), 6000);
      })
      .catch((err) => {
        setSubmitting(false);
        setError(err.message);
      });
  };

  const handleDecision = (decision) => {
    if (!selectedRequest) return;
    setReviewError(null);
    setReviewing(true);

    reviewResourceRequest(selectedRequest.request_id, {
      status: decision,
      reviewed_by: reviewerName.trim() || "Relief Officer",
    })
      .then(() => {
        setReviewing(false);
        setSelectedRequest(null);
        setSuccessMsg(`Request #${selectedRequest.request_id} was successfully marked as ${decision}.`);
        loadData();
        setTimeout(() => setSuccessMsg(null), 5000);
      })
      .catch((err) => {
        setReviewing(false);
        setReviewError(err.message);
      });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Request Form Panel */}
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>🆘 Emergency Relief Supply Requisition</h2>
            <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
              Requests are dynamically evaluated by our heuristic dispatch prioritization algorithm.
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
                    {d.district_name} ({d.state_name}) — {d.risk_tier} Risk
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Relief Resource Needed *</label>
              <select
                className="form-control"
                value={formData.resource_id}
                onChange={(e) => setFormData({ ...formData, resource_id: e.target.value })}
                required
              >
                <option value="">Select Resource Supply</option>
                {resources.map((r) => (
                  <option key={r.resource_id} value={r.resource_id}>
                    {r.resource_name} ({r.category}) — Available: {r.available_quantity} {r.unit}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Quantity Needed *</label>
              <input
                type="number"
                min="1"
                className="form-control"
                placeholder="e.g. 200"
                value={formData.quantity_requested}
                onChange={(e) => setFormData({ ...formData, quantity_requested: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Urgency Level *</label>
              <select
                className="form-control"
                value={formData.urgency_level}
                onChange={(e) => setFormData({ ...formData, urgency_level: e.target.value })}
              >
                <option value="Critical">Critical (Immediate Evacuation / Life Threat)</option>
                <option value="High">High (Submerged Settlements / Isolated)</option>
                <option value="Medium">Medium (Displaced Communities / Camps)</option>
                <option value="Low">Low (Replenishment / Buffer Stock)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Requester / Field Officer Name *</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Captain Ramesh / DM Patna"
                value={formData.requester_name}
                onChange={(e) => setFormData({ ...formData, requester_name: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Requester Contact Phone *</label>
              <input
                type="text"
                className="form-control"
                placeholder="+91-9876543210"
                value={formData.requester_contact}
                onChange={(e) => setFormData({ ...formData, requester_contact: e.target.value })}
                required
              />
            </div>

            <div className="form-group form-full">
              <label className="form-label">Situation Justification / Remarks</label>
              <textarea
                className="form-control"
                placeholder="Describe local flooding situation, road access, and specific needs..."
                value={formData.reason_notes}
                onChange={(e) => setFormData({ ...formData, reason_notes: e.target.value })}
              />
            </div>
          </div>

          <div style={{ marginTop: "18px", display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="btn-submit" disabled={submitting}>
              {submitting ? "Calculating Priority & Submitting..." : "Submit Requisition Request →"}
            </button>
          </div>
        </form>
      </div>

      {/* Bottom Priority Queue & Decision Panel */}
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>📋 Coordinator Dispatch Triage Queue</h2>
            <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
              Sorted in real-time by Algorithmic Priority Score (combining Urgency, District Risk Tier, and Supply Feasibility).
            </p>
          </div>
          <span className="badge badge-unverified">
            Active Requests: {requests.length}
          </span>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading active relief requests...</p>
          </div>
        ) : requests.length === 0 ? (
          <div className="empty-state">
            <p style={{ fontSize: "32px" }}>📋</p>
            <h3>No Active Resource Requests</h3>
            <p>Use the form above to submit emergency relief requests for flood-impacted zones.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>District & State</th>
                  <th>Requested Resource</th>
                  <th>Quantity</th>
                  <th>Urgency</th>
                  <th>Requester</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => (
                  <tr key={req.request_id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span
                          style={{
                            fontSize: "14px",
                            fontWeight: "bold",
                            color: req.calculated_priority_score >= 70 ? "#dc2626" : "#2563eb",
                          }}
                        >
                          {req.calculated_priority_score}
                        </span>
                        <small style={{ color: "#64748b" }}>/100</small>
                      </div>
                    </td>
                    <td>
                      <strong>{req.district_name}</strong>
                      <div style={{ fontSize: "11px", color: "#64748b" }}>
                        {req.state_name} ({req.district_risk_tier} Risk)
                      </div>
                    </td>
                    <td>
                      <strong>{req.resource_name}</strong>
                      <div style={{ fontSize: "11px", color: "#64748b" }}>
                        In Stock: {req.current_resource_available} {req.resource_unit}
                      </div>
                    </td>
                    <td>
                      <strong>{req.quantity_requested} {req.resource_unit}</strong>
                    </td>
                    <td>
                      <span
                        className={
                          req.urgency_level === "Critical"
                            ? "badge badge-crit"
                            : req.urgency_level === "High"
                            ? "badge badge-high"
                            : req.urgency_level === "Medium"
                            ? "badge badge-mod"
                            : "badge badge-low"
                        }
                      >
                        {req.urgency_level}
                      </span>
                    </td>
                    <td>
                      <div>{req.requester_name}</div>
                      <small style={{ color: "#64748b" }}>{req.requester_contact}</small>
                    </td>
                    <td>
                      <span
                        className={
                          req.status === "Approved"
                            ? "badge badge-approved"
                            : req.status === "Rejected"
                            ? "badge badge-rejected"
                            : "badge badge-pending"
                        }
                      >
                        {req.status}
                      </span>
                    </td>
                    <td>
                      {req.status === "Pending" ? (
                        <button
                          className="btn-submit"
                          style={{ padding: "4px 10px", fontSize: "11px" }}
                          onClick={() => {
                            setSelectedRequest(req);
                            setReviewError(null);
                          }}
                        >
                          Review
                        </button>
                      ) : (
                        <span style={{ fontSize: "11px", color: "#64748b" }}>
                          {req.reviewed_by ? `by ${req.reviewed_by}` : "Reviewed"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Review & Decision Modal */}
      {selectedRequest && (
        <div className="modal-overlay" onClick={() => setSelectedRequest(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Review Relief Request #{selectedRequest.request_id}</h3>
              <button className="modal-close-btn" onClick={() => setSelectedRequest(null)}>
                ×
              </button>
            </div>

            <div className="modal-body">
              {reviewError && (
                <div className="alert-banner alert-error" style={{ marginBottom: "15px" }}>
                  {reviewError}
                </div>
              )}

              <div className="detail-grid">
                <div className="detail-item">
                  <strong>Affected District</strong>
                  <span>{selectedRequest.district_name}, {selectedRequest.state_name}</span>
                </div>
                <div className="detail-item">
                  <strong>District Vulnerability</strong>
                  <span>{selectedRequest.district_risk_tier} Tier</span>
                </div>
                <div className="detail-item">
                  <strong>Resource Requested</strong>
                  <span>{selectedRequest.resource_name}</span>
                </div>
                <div className="detail-item">
                  <strong>Quantity Demanded</strong>
                  <span>{selectedRequest.quantity_requested} {selectedRequest.resource_unit}</span>
                </div>
                <div className="detail-item">
                  <strong>Currently In Stock</strong>
                  <span>{selectedRequest.current_resource_available} {selectedRequest.resource_unit}</span>
                </div>
                <div className="detail-item">
                  <strong>Calculated Priority Score</strong>
                  <span><strong>{selectedRequest.calculated_priority_score} / 100</strong></span>
                </div>
              </div>

              {selectedRequest.reason_notes && (
                <div style={{ marginTop: "15px", background: "#f8fafc", padding: "12px", borderRadius: "8px" }}>
                  <strong style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>
                    Field Situation Notes
                  </strong>
                  <p style={{ marginTop: "4px", fontSize: "13px" }}>{selectedRequest.reason_notes}</p>
                </div>
              )}

              <div className="form-group" style={{ marginTop: "15px" }}>
                <label className="form-label">Reviewing Officer Name *</label>
                <input
                  type="text"
                  className="form-control"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  placeholder="e.g. NDRF Coordinator Sharma"
                />
              </div>

              {selectedRequest.current_resource_available < selectedRequest.quantity_requested && (
                <div className="alert-banner alert-error" style={{ marginTop: "12px" }}>
                  ⚠️ Warning: Available stock ({selectedRequest.current_resource_available}) is less than requested ({selectedRequest.quantity_requested}). Approval will be rejected by atomic inventory validation.
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="btn-action-sm btn-reject"
                disabled={reviewing}
                onClick={() => handleDecision("Rejected")}
              >
                Reject Request
              </button>
              <button
                className="btn-action-sm btn-approve"
                disabled={reviewing}
                onClick={() => handleDecision("Approved")}
              >
                {reviewing ? "Processing Transaction..." : "Approve & Allocate Inventory"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
