import React, { useState, useEffect } from "react";
import { getResources, addResource } from "../services/api";

export default function ResourcesView() {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const [newResource, setNewResource] = useState({
    resource_name: "",
    category: "Food & Water",
    unit: "Kits",
    total_quantity: "",
    warehouse_location: "",
  });

  const loadResources = () => {
    setLoading(true);
    setError(null);
    getResources({
      category: categoryFilter || undefined,
      status: statusFilter || undefined,
      search: search.trim() || undefined,
    })
      .then((data) => {
        setResources(data.resources || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadResources();
  }, [categoryFilter, statusFilter, search]);

  const handleCreateResource = (e) => {
    e.preventDefault();
    setFormError(null);

    if (!newResource.resource_name.trim() || !newResource.warehouse_location.trim()) {
      setFormError("Please fill out all required fields.");
      return;
    }

    const qty = parseInt(newResource.total_quantity, 10);
    if (isNaN(qty) || qty < 0) {
      setFormError("Total quantity must be a non-negative integer.");
      return;
    }

    setSubmitting(true);
    addResource({
      resource_name: newResource.resource_name.trim(),
      category: newResource.category.trim(),
      unit: newResource.unit.trim(),
      total_quantity: qty,
      warehouse_location: newResource.warehouse_location.trim(),
    })
      .then(() => {
        setSubmitting(false);
        setShowAddModal(false);
        setSuccessMsg("New relief resource item registered successfully.");
        setNewResource({
          resource_name: "",
          category: "Food & Water",
          unit: "Kits",
          total_quantity: "",
          warehouse_location: "",
        });
        loadResources();
        setTimeout(() => setSuccessMsg(null), 4000);
      })
      .catch((err) => {
        setSubmitting(false);
        setFormError(err.message);
      });
  };

  const categories = Array.from(new Set(resources.map((r) => r.category)));

  return (
    <div className="panel" style={{ minHeight: "600px" }}>
      <div className="panel-heading">
        <div>
          <h2>📦 Disaster Relief Supply Inventory</h2>
          <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            Track verified relief stock levels, warehouse hubs, and dispatch readiness across India.
          </p>
        </div>
        <button
          className="btn-submit"
          onClick={() => setShowAddModal(true)}
          style={{ fontSize: "13px" }}
        >
          + Add New Relief Item
        </button>
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

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="filter-group" style={{ flex: "1 1 200px" }}>
          <label>Search Supplies</label>
          <input
            type="text"
            className="filter-input"
            placeholder="Search item name or warehouse..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="filter-group" style={{ flex: "0 1 180px" }}>
          <label>Category</label>
          <select
            className="filter-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group" style={{ flex: "0 1 150px" }}>
          <label>Stock Status</label>
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="Available">Available (&gt;25%)</option>
            <option value="Low Stock">Low Stock (10-25%)</option>
            <option value="Critical">Critical (&lt;10%)</option>
          </select>
        </div>
      </div>

      {/* Inventory Cards Grid */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Querying real-time relief inventory...</p>
        </div>
      ) : resources.length === 0 ? (
        <div className="empty-state">
          <p style={{ fontSize: "36px" }}>📦</p>
          <h3>No Relief Resources Found</h3>
          <p>No resources match the selected category or status criteria.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px", marginTop: "15px" }}>
          {resources.map((res) => {
            const ratio = res.total_quantity > 0 ? (res.available_quantity / res.total_quantity) * 100 : 0;
            return (
              <div
                key={res.resource_id}
                style={{
                  background: "#ffffff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "10px",
                  padding: "18px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <span style={{ fontSize: "11px", fontWeight: "bold", color: "#64748b", textTransform: "uppercase" }}>
                      {res.category}
                    </span>
                    <span
                      className={
                        res.status === "Available"
                          ? "badge badge-avail"
                          : res.status === "Low Stock"
                          ? "badge badge-mod"
                          : "badge badge-crit"
                      }
                    >
                      {res.status}
                    </span>
                  </div>

                  <h3 style={{ fontSize: "16px", color: "#0f172a", marginBottom: "4px" }}>
                    {res.resource_name}
                  </h3>
                  <small style={{ color: "#64748b" }}>📍 {res.warehouse_location}</small>

                  {/* Stock Progress Bar */}
                  <div style={{ marginTop: "14px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                      <span>Available: <strong>{res.available_quantity.toLocaleString()} {res.unit}</strong></span>
                      <span style={{ color: "#64748b" }}>Total: {res.total_quantity.toLocaleString()}</span>
                    </div>
                    <div style={{ width: "100%", height: "8px", background: "#f1f5f9", borderRadius: "4px", overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${Math.min(ratio, 100)}%`,
                          height: "100%",
                          background: ratio > 25 ? "#16a34a" : ratio >= 10 ? "#d97706" : "#dc2626",
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: "14px", paddingTop: "10px", borderTop: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b" }}>
                  <span>Dispatched: <strong>{res.allocated_quantity.toLocaleString()} {res.unit}</strong></span>
                  <span>{res.is_demo_data ? "(Demo Baseline)" : "(Operational)"}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Resource Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Register New Disaster Relief Supply</h3>
              <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>
                ×
              </button>
            </div>

            <form onSubmit={handleCreateResource}>
              <div className="modal-body">
                {formError && (
                  <div className="alert-banner alert-error" style={{ marginBottom: "15px" }}>
                    {formError}
                  </div>
                )}

                <div className="form-grid">
                  <div className="form-group form-full">
                    <label className="form-label">Supply Item Name *</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Life Jackets (Adult)"
                      value={newResource.resource_name}
                      onChange={(e) => setNewResource({ ...newResource, resource_name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Category *</label>
                    <select
                      className="form-control"
                      value={newResource.category}
                      onChange={(e) => setNewResource({ ...newResource, category: e.target.value })}
                    >
                      <option value="Food & Water">Food & Water</option>
                      <option value="Medical Supplies">Medical Supplies</option>
                      <option value="Rescue Equipment">Rescue Equipment</option>
                      <option value="Shelter & Bedding">Shelter & Bedding</option>
                      <option value="Power & Utility">Power & Utility</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Measurement Unit *</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Kits, Cans, Units, Pieces"
                      value={newResource.unit}
                      onChange={(e) => setNewResource({ ...newResource, unit: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Initial Quantity *</label>
                    <input
                      type="number"
                      min="0"
                      className="form-control"
                      placeholder="e.g. 500"
                      value={newResource.total_quantity}
                      onChange={(e) => setNewResource({ ...newResource, total_quantity: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Warehouse Depot / Hub *</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. State Relief Hub Patna"
                      value={newResource.warehouse_location}
                      onChange={(e) => setNewResource({ ...newResource, warehouse_location: e.target.value })}
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowAddModal(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={submitting}>
                  {submitting ? "Saving to Database..." : "Save Relief Item"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
