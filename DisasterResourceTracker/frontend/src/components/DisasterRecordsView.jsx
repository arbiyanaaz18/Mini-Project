import React, { useState, useEffect } from "react";
import { getDisasters, getStates } from "../services/api";

export default function DisasterRecordsView({ initialSearch = "" }) {
  const [disasters, setDisasters] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);

  const [search, setSearch] = useState(initialSearch);
  const [stateFilter, setStateFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [causeFilter, setCauseFilter] = useState("");

  const [statesList, setStatesList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedEvent, setSelectedEvent] = useState(null);

  // Fetch states for dropdown filter
  useEffect(() => {
    getStates()
      .then((data) => setStatesList(data.states || []))
      .catch(() => {});
  }, []);

  // Fetch disasters whenever pagination or filters change
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    getDisasters({
      page,
      limit,
      search: search.trim(),
      state: stateFilter.trim(),
      year: yearFilter.trim(),
      cause: causeFilter.trim(),
    })
      .then((data) => {
        if (!isMounted) return;
        setDisasters(data.disasters || []);
        setTotalRecords(data.total_records || 0);
        setTotalPages(data.total_pages || 1);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [page, limit, search, stateFilter, yearFilter, causeFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
  };

  const resetFilters = () => {
    setSearch("");
    setStateFilter("");
    setYearFilter("");
    setCauseFilter("");
    setPage(1);
  };

  return (
    <div className="panel" style={{ minHeight: "600px" }}>
      <div className="panel-heading" style={{ marginBottom: "15px" }}>
        <div>
          <h2>▤ Historical Disaster Records Explorer</h2>
          <p style={{ color: "#64748b", fontSize: "13px", marginTop: "4px" }}>
            Querying all 6,876 verified Indian flood records from the National Flood Inventory.
          </p>
        </div>
        <span className="badge badge-unverified" style={{ fontSize: "12px", padding: "6px 12px" }}>
          Total Matches: {totalRecords.toLocaleString()}
        </span>
      </div>

      {/* Filter Toolbar */}
      <form onSubmit={handleSearchSubmit} className="filter-bar">
        <div className="filter-group" style={{ flex: "1 1 200px" }}>
          <label>Search Keyword</label>
          <input
            type="text"
            className="filter-input"
            placeholder="Search district, cause, damage narrative..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="filter-group" style={{ flex: "0 1 180px" }}>
          <label>State / UT</label>
          <select
            className="filter-select"
            value={stateFilter}
            onChange={(e) => {
              setStateFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All States</option>
            {statesList.map((st) => (
              <option key={st.state_id} value={st.state_name}>
                {st.state_name}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group" style={{ flex: "0 1 110px" }}>
          <label>Year</label>
          <input
            type="text"
            className="filter-input"
            placeholder="e.g. 2010"
            value={yearFilter}
            onChange={(e) => {
              setYearFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="filter-group" style={{ flex: "0 1 140px" }}>
          <label>Cause</label>
          <input
            type="text"
            className="filter-input"
            placeholder="e.g. heavy rains"
            value={causeFilter}
            onChange={(e) => {
              setCauseFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="filter-group" style={{ flex: "0 1 100px" }}>
          <label>Per Page</label>
          <select
            className="filter-select"
            value={limit}
            onChange={(e) => {
              setLimit(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div className="filter-group" style={{ justifyContent: "flex-end", alignSelf: "flex-end" }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={resetFilters}
            style={{ padding: "8px 12px", height: "35px" }}
          >
            Reset
          </button>
        </div>
      </form>

      {/* Error State */}
      {error && (
        <div className="alert-banner alert-error">
          <div>
            <strong>Error Loading Records:</strong> {error}
          </div>
          <button className="alert-retry-btn" onClick={() => setPage(page)}>
            ↻ Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Querying verified disaster records from database...</p>
        </div>
      ) : disasters.length === 0 ? (
        <div className="empty-state">
          <p style={{ fontSize: "36px", marginBottom: "8px" }}>🔍</p>
          <h3>No Disaster Records Found</h3>
          <p>Try modifying your search keywords or state/year filters.</p>
          <button className="btn-secondary" onClick={resetFilters} style={{ marginTop: "12px" }}>
            Clear Filters
          </button>
        </div>
      ) : (
        <>
          {/* Disaster Data Table */}
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event Identifier</th>
                  <th>Dates (Start - End)</th>
                  <th>State & Districts</th>
                  <th>Primary Trigger</th>
                  <th>Duration</th>
                  <th>Fatalities</th>
                  <th>Injured</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {disasters.map((evt) => (
                  <tr key={evt.event_id}>
                    <td>
                      <code style={{ background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px" }}>
                        {evt.uei}
                      </code>
                    </td>
                    <td>
                      <div>{evt.start_date ? evt.start_date.split(" ")[0] : "—"}</div>
                      <small style={{ color: "#64748b" }}>
                        to {evt.end_date ? evt.end_date.split(" ")[0] : "—"}
                      </small>
                    </td>
                    <td>
                      <strong>{evt.state_name}</strong>
                      {evt.districts_mentioned && (
                        <div style={{ fontSize: "11px", color: "#64748b" }}>
                          {evt.districts_mentioned}
                        </div>
                      )}
                    </td>
                    <td>
                      <span style={{ textTransform: "capitalize" }}>{evt.main_cause || "Unspecified"}</span>
                    </td>
                    <td>
                      {evt.duration_days ? `${evt.duration_days} days` : "—"}
                    </td>
                    <td>
                      {evt.human_fatality > 0 ? (
                        <span className="badge badge-high">{evt.human_fatality} deaths</span>
                      ) : (
                        <span style={{ color: "#94a3b8" }}>0</span>
                      )}
                    </td>
                    <td>
                      {evt.human_injured > 0 ? (
                        <span className="badge badge-mod">{evt.human_injured} injured</span>
                      ) : (
                        <span style={{ color: "#94a3b8" }}>0</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        style={{ padding: "4px 8px", fontSize: "11px" }}
                        onClick={() => setSelectedEvent(evt)}
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="pagination">
            <div className="pagination-info">
              Showing {(page - 1) * limit + 1} to {Math.min(page * limit, totalRecords)} of{" "}
              {totalRecords.toLocaleString()} records (Page {page} of {totalPages})
            </div>

            <div className="pagination-buttons">
              <button
                className="page-btn"
                disabled={page <= 1}
                onClick={() => setPage(1)}
                title="First Page"
              >
                ««
              </button>
              <button
                className="page-btn"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
              >
                « Previous
              </button>

              <span className="page-btn active">Page {page}</span>

              <button
                className="page-btn"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
              >
                Next »
              </button>
              <button
                className="page-btn"
                disabled={page >= totalPages}
                onClick={() => setPage(totalPages)}
                title="Last Page"
              >
                »»
              </button>
            </div>
          </div>
        </>
      )}

      {/* Event Details Modal */}
      {selectedEvent && (
        <div className="modal-overlay" onClick={() => setSelectedEvent(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Flood Event: {selectedEvent.uei}</h3>
              <button className="modal-close-btn" onClick={() => setSelectedEvent(null)}>
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-item">
                  <strong>State</strong>
                  <span>{selectedEvent.state_name}</span>
                </div>
                <div className="detail-item">
                  <strong>Districts Mentioned</strong>
                  <span>{selectedEvent.districts_mentioned || "Not specified"}</span>
                </div>
                <div className="detail-item">
                  <strong>Start Date</strong>
                  <span>{selectedEvent.start_date || "—"}</span>
                </div>
                <div className="detail-item">
                  <strong>End Date</strong>
                  <span>{selectedEvent.end_date || "—"}</span>
                </div>
                <div className="detail-item">
                  <strong>Duration</strong>
                  <span>{selectedEvent.duration_days ? `${selectedEvent.duration_days} days` : "—"}</span>
                </div>
                <div className="detail-item">
                  <strong>Primary Trigger</strong>
                  <span>{selectedEvent.main_cause || "—"}</span>
                </div>
                <div className="detail-item">
                  <strong>Human Casualties</strong>
                  <span>
                    {selectedEvent.human_fatality} deaths, {selectedEvent.human_injured} injured
                  </span>
                </div>
                <div className="detail-item">
                  <strong>Data Source</strong>
                  <span>{selectedEvent.event_source || "IMD"}</span>
                </div>
              </div>

              {selectedEvent.description && (
                <div style={{ marginTop: "18px" }}>
                  <strong style={{ display: "block", fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>
                    Casualties & Incident Narrative
                  </strong>
                  <p style={{ background: "#f8fafc", padding: "12px", borderRadius: "6px", marginTop: "4px" }}>
                    {selectedEvent.description}
                  </p>
                </div>
              )}

              {selectedEvent.extent_of_damage && (
                <div style={{ marginTop: "14px" }}>
                  <strong style={{ display: "block", fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>
                    Infrastructure & Property Damage
                  </strong>
                  <p style={{ background: "#f8fafc", padding: "12px", borderRadius: "6px", marginTop: "4px" }}>
                    {selectedEvent.extent_of_damage}
                  </p>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedEvent(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
