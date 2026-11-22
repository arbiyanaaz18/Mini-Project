/**
 * Disaster Resource Tracker — Centralized API Client Service
 * Connects the React frontend to the Flask REST backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

/**
 * Generic request helper with error handling
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMessage = data?.error || `HTTP Error ${res.status}: ${res.statusText}`;
      const err = new Error(errorMessage);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error(
        'Backend server is unreachable. Please verify Flask is running on http://127.0.0.1:5000.'
      );
    }
    throw error;
  }
}

// ----------------------------------------------------------------------------
// Core Statistics & Health
// ----------------------------------------------------------------------------
export async function getHealth() {
  return request('/health');
}

export async function getStats() {
  return request('/stats');
}

// ----------------------------------------------------------------------------
// States & Districts
// ----------------------------------------------------------------------------
export async function getStates() {
  return request('/states');
}

export async function getDistricts(params = {}) {
  const query = new URLSearchParams();
  if (params.state_id) query.append('state_id', params.state_id);
  if (params.risk_tier) query.append('risk_tier', params.risk_tier);
  if (params.search) query.append('search', params.search);
  const qs = query.toString();
  return request(`/districts${qs ? `?${qs}` : ''}`);
}

export async function getDistrictById(districtId) {
  return request(`/districts/${districtId}`);
}

// ----------------------------------------------------------------------------
// Historical Flood Events
// ----------------------------------------------------------------------------
export async function getDisasters(params = {}) {
  const query = new URLSearchParams();
  query.append('page', params.page || 1);
  query.append('limit', params.limit || 25);
  if (params.state) query.append('state', params.state);
  if (params.year) query.append('year', params.year);
  if (params.cause) query.append('cause', params.cause);
  if (params.search) query.append('search', params.search);
  return request(`/disasters?${query.toString()}`);
}

export async function getDisasterById(eventId) {
  return request(`/disasters/${eventId}`);
}

// ----------------------------------------------------------------------------
// Annual Trends
// ----------------------------------------------------------------------------
export async function getTrends() {
  return request('/trends');
}

// ----------------------------------------------------------------------------
// Resources Inventory
// ----------------------------------------------------------------------------
export async function getResources(params = {}) {
  const query = new URLSearchParams();
  if (params.category) query.append('category', params.category);
  if (params.status) query.append('status', params.status);
  if (params.search) query.append('search', params.search);
  const qs = query.toString();
  return request(`/resources${qs ? `?${qs}` : ''}`);
}

export async function addResource(resourceData) {
  return request('/resources', {
    method: 'POST',
    body: JSON.stringify(resourceData),
  });
}

export async function updateResource(resourceId, resourceData) {
  return request(`/resources/${resourceId}`, {
    method: 'PUT',
    body: JSON.stringify(resourceData),
  });
}

export async function deleteResource(resourceId) {
  return request(`/resources/${resourceId}`, {
    method: 'DELETE',
  });
}

// ----------------------------------------------------------------------------
// Resource Requests & Approvals
// ----------------------------------------------------------------------------
export async function submitResourceRequest(requestData) {
  return request('/resources/request', {
    method: 'POST',
    body: JSON.stringify(requestData),
  });
}

export async function getResourceRequests(params = {}) {
  const query = new URLSearchParams();
  if (params.status) query.append('status', params.status);
  if (params.urgency) query.append('urgency', params.urgency);
  if (params.district_id) query.append('district_id', params.district_id);
  if (params.resource_id) query.append('resource_id', params.resource_id);
  const qs = query.toString();
  return request(`/resources/requests${qs ? `?${qs}` : ''}`);
}

export async function reviewResourceRequest(requestId, decisionData) {
  return request(`/resources/requests/${requestId}/status`, {
    method: 'PUT',
    body: JSON.stringify(decisionData),
  });
}

// ----------------------------------------------------------------------------
// Community Incidents
// ----------------------------------------------------------------------------
export async function reportIncident(incidentData) {
  return request('/incidents/report', {
    method: 'POST',
    body: JSON.stringify(incidentData),
  });
}

export async function getIncidents(params = {}) {
  const query = new URLSearchParams();
  if (params.severity_level) query.append('severity_level', params.severity_level);
  if (params.verification_status) query.append('verification_status', params.verification_status);
  if (params.district_id) query.append('district_id', params.district_id);
  if (params.disaster_type) query.append('disaster_type', params.disaster_type);
  const qs = query.toString();
  return request(`/incidents${qs ? `?${qs}` : ''}`);
}
