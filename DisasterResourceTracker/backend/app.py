"""
Flask REST API for Disaster Resource Tracker.
Provides core REST endpoints for dashboard analytics, states, districts,
historical flood records, and annual disaster trends.
"""

import math
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import DB_PATH, get_db_connection
from algorithms import calculate_request_priority_score
from kv_store import KeyValueStore

app = Flask(__name__)
# Persistent Key-Value Store Cache
cache = KeyValueStore(
    capacity=100,
    eviction_policy="LRU"
)
def invalidate_resource_cache():
    """Remove cached resource-list results after inventory changes."""
    for key in cache.keys():
        if key.startswith("resources:"):
            cache.delete(key)
# Enable Cross-Origin Resource Sharing so the React frontend can query the API
CORS(app, resources={r"/api/*": {"origins": "*"}})

def get_db():
    """Returns database connection, respecting app.config['DATABASE'] if set for test isolation."""
    custom_path = app.config.get("DATABASE")
    return get_db_connection(custom_path)



# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(error):
    """Handle standard 404 Not Found errors with JSON."""
    return jsonify({
        "error": "The requested endpoint or resource was not found.",
        "status_code": 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Errors gracefully."""
    return jsonify({
        "error": "An internal server error occurred.",
        "status_code": 500
    }), 500


# -----------------------------------------------------------------------------
# 0. Health Check Endpoint
# -----------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify backend server and SQLite database connection."""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS ok;")
        row = cursor.fetchone()
        return jsonify({
            "status": "healthy",
            "message": "Disaster Resource Tracker Backend API is online.",
            "database": "connected" if row and row["ok"] == 1 else "error"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 1. Overview Statistics Endpoint: GET /api/stats
# -----------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    Returns high-level summary statistics aggregated from actual database records:
    - Total disasters, fatalities, injured
    - Total districts and states
    - District risk tier breakdown
    - Resource supply metrics
    - Pending requests and reported incident counts
    - Top disaster triggers and recent events
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Aggregate historical flood events metrics
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_disasters,
                COALESCE(SUM(human_fatality), 0) AS total_fatalities,
                COALESCE(SUM(human_injured), 0) AS total_injured
            FROM flood_events;
        """)
        event_stats = dict(cursor.fetchone())

        # Districts and states count
        cursor.execute("SELECT COUNT(*) AS total_districts FROM districts;")
        total_districts = cursor.fetchone()["total_districts"]

        cursor.execute("SELECT COUNT(*) AS total_states FROM states;")
        total_states = cursor.fetchone()["total_states"]

        # Risk tier distribution
        cursor.execute("""
            SELECT risk_tier, COUNT(*) AS count
            FROM districts
            GROUP BY risk_tier;
        """)
        risk_dist = {"High": 0, "Moderate": 0, "Low": 0}
        for row in cursor.fetchall():
            risk_dist[row["risk_tier"]] = row["count"]

        # Resources metrics
        cursor.execute("""
            SELECT 
                COALESCE(SUM(total_quantity), 0) AS total_quantity,
                COALESCE(SUM(available_quantity), 0) AS available_quantity,
                COALESCE(SUM(allocated_quantity), 0) AS allocated_quantity,
                COUNT(*) AS total_resource_types
            FROM resources;
        """)
        res_stats = dict(cursor.fetchone())

        # Operational queues
        cursor.execute("SELECT COUNT(*) AS pending FROM resource_requests WHERE status = 'Pending';")
        pending_requests = cursor.fetchone()["pending"]

        cursor.execute("SELECT COUNT(*) AS incidents FROM reported_incidents;")
        reported_incidents = cursor.fetchone()["incidents"]

        # Top causes of floods
        cursor.execute("""
            SELECT main_cause, COUNT(*) AS count
            FROM flood_events
            WHERE main_cause IS NOT NULL AND main_cause != 'Unspecified'
            GROUP BY main_cause
            ORDER BY count DESC
            LIMIT 5;
        """)
        top_causes = [dict(row) for row in cursor.fetchall()]

        # Recent disaster events sample
        cursor.execute("""
            SELECT event_id, uei, start_date, end_date, state_name, districts_mentioned, main_cause, human_fatality
            FROM flood_events
            ORDER BY event_id DESC
            LIMIT 5;
        """)
        recent_events = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "total_disasters": event_stats["total_disasters"],
            "total_fatalities": event_stats["total_fatalities"],
            "total_injured": event_stats["total_injured"],
            "total_districts": total_districts,
            "total_states": total_states,
            "risk_distribution": risk_dist,
            "resources": res_stats,
            "pending_requests_count": pending_requests,
            "reported_incidents_count": reported_incidents,
            "top_causes": top_causes,
            "recent_events": recent_events
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to calculate statistics: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 2. States List Endpoint: GET /api/states
# -----------------------------------------------------------------------------
@app.route("/api/states", methods=["GET"])
def get_states():
    """
    Returns a list of all 37 States and Union Territories with district counts,
    ordered alphabetically.
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                s.state_id,
                s.state_name,
                COUNT(d.district_id) AS district_count
            FROM states s
            LEFT JOIN districts d ON s.state_id = d.state_id
            GROUP BY s.state_id, s.state_name
            ORDER BY s.state_name ASC;
        """)
        states_list = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            "states": states_list,
            "total": len(states_list)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch states: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 3. Districts List Endpoint: GET /api/districts
# -----------------------------------------------------------------------------
@app.route("/api/districts", methods=["GET"])
def get_districts():
    """
    Returns districts with support for multi-criteria filtering:
    - state_id: integer filter by state
    - risk_tier: 'High', 'Moderate', 'Low'
    - search: substring search matching district name or state name
    """
    conn = None
    try:
        state_id_param = request.args.get("state_id")
        risk_tier_param = request.args.get("risk_tier")
        search_param = request.args.get("search")

        # Validation: state_id must be integer if provided
        state_id = None
        if state_id_param:
            try:
                state_id = int(state_id_param)
            except ValueError:
                return jsonify({"error": "Invalid state_id parameter. Must be an integer."}), 400

        # Validation: risk_tier must be High, Moderate, or Low if provided
        risk_tier = None
        if risk_tier_param:
            valid_tiers = {"high": "High", "moderate": "Moderate", "low": "Low"}
            normalized_tier = valid_tiers.get(risk_tier_param.strip().lower())
            if not normalized_tier:
                return jsonify({
                    "error": "Invalid risk_tier parameter. Allowed values: High, Moderate, Low."
                }), 400
            risk_tier = normalized_tier

        # Build parameterized query
        query = """
            SELECT 
                d.district_id,
                d.district_name,
                d.state_id,
                s.state_name,
                d.dfsi_score,
                d.population,
                d.human_fatality_total,
                d.human_injured_total,
                d.mean_flood_duration_days,
                d.percent_flooded_area,
                d.permanent_water_percent,
                d.corrected_flooded_area,
                d.risk_score,
                d.risk_tier
            FROM districts d
            JOIN states s ON d.state_id = s.state_id
            WHERE 1=1
        """
        params = []

        if state_id is not None:
            query += " AND d.state_id = ?"
            params.append(state_id)

        if risk_tier is not None:
            query += " AND d.risk_tier = ?"
            params.append(risk_tier)

        if search_param and search_param.strip():
            search_term = f"%{search_param.strip()}%"
            query += " AND (d.district_name LIKE ? OR s.state_name LIKE ?)"
            params.extend([search_term, search_term])

        query += " ORDER BY d.risk_score DESC, d.district_name ASC;"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        districts_list = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "districts": districts_list,
            "count": len(districts_list)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch districts: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 4. District Profile Endpoint: GET /api/districts/<int:district_id>
# -----------------------------------------------------------------------------
@app.route("/api/districts/<int:district_id>", methods=["GET"])
def get_district_by_id(district_id):
    """
    Returns full vulnerability and impact details for a specific district.
    Returns 404 if the district does not exist.
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.district_id,
                d.district_name,
                d.state_id,
                s.state_name,
                d.dfsi_score,
                d.population,
                d.human_fatality_total,
                d.human_injured_total,
                d.mean_flood_duration_days,
                d.percent_flooded_area,
                d.permanent_water_percent,
                d.corrected_flooded_area,
                d.risk_score,
                d.risk_tier
            FROM districts d
JOIN states s ON d.state_id = s.state_id
WHERE d.district_id = %s;
""", (district_id,))
         row = cursor.fetchone()

        if not row:
            return jsonify({
                "error": f"District with ID {district_id} was not found."
            }), 404

        return jsonify(dict(row)), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch district profile: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 5. Historical Flood Disasters (Paginated): GET /api/disasters
# -----------------------------------------------------------------------------
@app.route("/api/disasters", methods=["GET"])
def get_disasters():
    """
    Returns historical flood event records with pagination and multi-criteria filtering:
    - page: default 1 (>= 1)
    - limit: default 25 (1 - 100)
    - state: filter by state_name (substring search)
    - year: filter by year in start_date or UEI (e.g. '2010')
    - cause: filter by main_cause (substring search)
    - search: general search across districts_mentioned, description, cause, or state
    """
    conn = None
    try:
        # 1. Parse and validate pagination
        page_param = request.args.get("page", 1)
        limit_param = request.args.get("limit", 25)

        try:
            page = int(page_param)
            if page < 1:
                return jsonify({"error": "Page parameter must be an integer >= 1."}), 400
        except ValueError:
            return jsonify({"error": "Invalid page parameter. Must be an integer."}), 400

        try:
            limit = int(limit_param)
            if limit < 1 or limit > 100:
                return jsonify({"error": "Limit parameter must be an integer between 1 and 100."}), 400
        except ValueError:
            return jsonify({"error": "Invalid limit parameter. Must be an integer."}), 400

        offset = (page - 1) * limit

        # 2. Parse filter arguments
        state_filter = request.args.get("state")
        year_filter = request.args.get("year")
        cause_filter = request.args.get("cause")
        search_filter = request.args.get("search")

        # 3. Build WHERE clause with parameters
        where_clauses = ["1=1"]
        params = []

        if state_filter and state_filter.strip():
            where_clauses.append("state_name LIKE ?")
            params.append(f"%{state_filter.strip()}%")

        if year_filter and year_filter.strip():
            where_clauses.append("(start_date LIKE ? OR uei LIKE ?)")
            year_val = f"%{year_filter.strip()}%"
            params.extend([year_val, year_val])

        if cause_filter and cause_filter.strip():
            where_clauses.append("main_cause LIKE ?")
            params.append(f"%{cause_filter.strip()}%")

        if search_filter and search_filter.strip():
            search_term = f"%{search_filter.strip()}%"
            where_clauses.append(
                "(state_name LIKE ? OR districts_mentioned LIKE ? OR main_cause LIKE ? OR description LIKE ? OR uei LIKE ?)"
            )
            params.extend([search_term, search_term, search_term, search_term, search_term])

        where_sql = " AND ".join(where_clauses)

        conn = get_db()
        cursor = conn.cursor()

        # Count total matching records
        count_sql = f"SELECT COUNT(*) AS total FROM flood_events WHERE {where_sql};"
        cursor.execute(count_sql, params)
        total_records = cursor.fetchone()["total"]

        total_pages = math.ceil(total_records / limit) if total_records > 0 else 1

        # Fetch paginated slice
        data_sql = f"""
            SELECT 
                event_id,
                uei,
                start_date,
                end_date,
                duration_days,
                main_cause,
                state_name,
                districts_mentioned,
                human_fatality,
                human_injured,
                human_displaced,
                animal_fatality,
                description,
                extent_of_damage,
                event_source
            FROM flood_events
            WHERE {where_sql}
            ORDER BY event_id ASC
            LIMIT ? OFFSET ?;
        """
        cursor.execute(data_sql, params + [limit, offset])
        disasters = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
            "disasters": disasters
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch disaster records: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 6. Disaster Event Detail Endpoint: GET /api/disasters/<int:event_id>
# -----------------------------------------------------------------------------
@app.route("/api/disasters/<int:event_id>", methods=["GET"])
def get_disaster_by_id(event_id):
    """
    Returns full details for a single historical flood event by its primary key.
    Returns 404 if event is not found.
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                event_id,
                uei,
                start_date,
                end_date,
                duration_days,
                main_cause,
                state_name,
                districts_mentioned,
                human_fatality,
                human_injured,
                human_displaced,
                animal_fatality,
                description,
                extent_of_damage,
                event_source,
                district_lgd_codes,
                state_codes
            FROM flood_events
            WHERE event_id = ?;
        """, (event_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({
                "error": f"Flood disaster record with ID {event_id} was not found."
            }), 404

        return jsonify(dict(row)), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch disaster detail: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 7. Annual Longitudinal Trends Endpoint: GET /api/trends
# -----------------------------------------------------------------------------
@app.route("/api/trends", methods=["GET"])
def get_trends():
    """
    Returns annual national impact records across all 12 recorded financial years
    from annual_impact (lives lost, cattle lost, houses damaged, cropped area affected),
    along with cumulative summary metrics.
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id,
                year,
                lives_lost,
                cattle_lost,
                houses_damaged,
                cropped_area_affected_lakh_ha
            FROM annual_impact
            ORDER BY id ASC;
        """)
        trends_list = [dict(row) for row in cursor.fetchall()]

        # Compute summary metrics across all recorded years
        total_lives_lost = sum(t["lives_lost"] for t in trends_list)
        total_cattle_lost = sum(t["cattle_lost"] for t in trends_list)
        total_houses_damaged = sum(t["houses_damaged"] for t in trends_list)
        total_crop_area_lakh_ha = round(sum(t["cropped_area_affected_lakh_ha"] for t in trends_list), 2)

        # Identify peak damage years
        max_lives_year = max(trends_list, key=lambda x: x["lives_lost"]) if trends_list else None
        max_houses_year = max(trends_list, key=lambda x: x["houses_damaged"]) if trends_list else None

        return jsonify({
            "trends": trends_list,
            "total_years": len(trends_list),
            "summary": {
                "total_lives_lost": total_lives_lost,
                "total_cattle_lost": total_cattle_lost,
                "total_houses_damaged": total_houses_damaged,
                "total_cropped_area_lakh_ha": total_crop_area_lakh_ha,
                "peak_lives_lost_year": max_lives_year["year"] if max_lives_year else None,
                "peak_houses_damaged_year": max_houses_year["year"] if max_houses_year else None
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch annual trends: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# Helper: Automatic Stock Status Calculation
# -----------------------------------------------------------------------------
def compute_stock_status(available_qty, total_qty):
    """
    Computes stock status based on documented thresholds:
    - 'Critical': When available stock is 0 or less than 10% of total quantity.
    - 'Low Stock': When available stock is between 10% and 25% (inclusive) of total quantity.
    - 'Available': When available stock is strictly greater than 25% of total quantity.
    """
    if total_qty <= 0 or available_qty <= 0:
        return "Critical"
    ratio = available_qty / total_qty
    if ratio < 0.10:
        return "Critical"
    elif ratio <= 0.25:
        return "Low Stock"
    else:
        return "Available"


# -----------------------------------------------------------------------------
# 8. Resources List Endpoint: GET /api/resources
# -----------------------------------------------------------------------------

@app.route("/api/resources", methods=["GET"])
def get_resources():
    """
    Returns relief resources with caching.

    Supports:
    - Category filtering
    - Status filtering
    - Search filtering

    Uses persistent Key-Value Store caching
    with LRU eviction.
    """

    conn = None

    try:
        # Read filter parameters
        category_param = request.args.get("category", "").strip()
        status_param = request.args.get("status", "").strip()
        search_param = request.args.get("search", "").strip()

        # Validate status
        valid_statuses = {
            "available": "Available",
            "low stock": "Low Stock",
            "critical": "Critical"
        }

        norm_status = None

        if status_param:
            norm_status = valid_statuses.get(
                status_param.lower()
            )

            if not norm_status:
                return jsonify({
                    "error": (
                        "Invalid status parameter. "
                        "Allowed values: Available, Low Stock, Critical."
                    )
                }), 400

        # Create a unique cache key for each filter combination
        cache_key = (
            f"resources:"
            f"category={category_param.lower()}|"
            f"status={norm_status or ''}|"
            f"search={search_param.lower()}"
        )

        # Check Key-Value Store cache
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return jsonify(cached_data), 200

        # Cache miss: fetch data from SQLite
        where_clauses = ["1=1"]
        params = []

        if category_param:
            where_clauses.append("category LIKE ?")
            params.append(f"%{category_param}%")

        if norm_status:
            where_clauses.append("status = ?")
            params.append(norm_status)

        if search_param:
            search_term = f"%{search_param}%"

            where_clauses.append(
                "(resource_name LIKE ? OR warehouse_location LIKE ?)"
            )

            params.extend([
                search_term,
                search_term
            ])

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT
                resource_id,
                resource_name,
                category,
                unit,
                total_quantity,
                available_quantity,
                allocated_quantity,
                warehouse_location,
                status,
                is_demo_data
            FROM resources
            WHERE {where_sql}
            ORDER BY resource_id ASC;
        """

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(query, params)

        resources_list = [
            dict(row) for row in cursor.fetchall()
        ]

        # Prepare API response
        response_data = {
            "resources": resources_list,
            "total": len(resources_list)
        }

        # Store result in persistent Key-Value Store
        cache.set(cache_key, response_data)

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to fetch resources: {str(e)}"
        }), 500

    finally:
        if conn:
            conn.close()



# -----------------------------------------------------------------------------
# 9. Add New Resource Endpoint: POST /api/resources
# -----------------------------------------------------------------------------
@app.route("/api/resources", methods=["POST"])
def add_resource():
    """
    Adds a new relief resource to inventory.
    Validates all required fields, ensures non-negative quantities,
    sets is_demo_data = 0, and automatically computes stock status.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        required_fields = ["resource_name", "category", "unit", "total_quantity", "warehouse_location"]
        for field in required_fields:
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                return jsonify({"error": f"Missing required field: '{field}'."}), 400

        # Validate total_quantity
        try:
            total_qty = int(data["total_quantity"])
            if total_qty < 0:
                return jsonify({"error": "total_quantity must be a non-negative integer."}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "total_quantity must be a valid integer."}), 400

        # Validate available_quantity (defaults to total_quantity if not provided)
        available_qty_val = data.get("available_quantity")
        if available_qty_val is None:
            available_qty = total_qty
        else:
            try:
                available_qty = int(available_qty_val)
                if available_qty < 0:
                    return jsonify({"error": "available_quantity must be a non-negative integer."}), 400
                if available_qty > total_qty:
                    return jsonify({"error": "available_quantity cannot exceed total_quantity."}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "available_quantity must be a valid integer."}), 400

        allocated_qty = total_qty - available_qty
        auto_status = compute_stock_status(available_qty, total_qty)

       
conn = get_db()
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO resources (
        resource_name, category, unit, total_quantity, available_quantity,
        allocated_quantity, warehouse_location, status, is_demo_data
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
    RETURNING resource_id;
""", (
    data["resource_name"].strip(),
    data["category"].strip(),
    data["unit"].strip(),
    total_qty,
    available_qty,
    allocated_qty,
    data["warehouse_location"].strip(),
    auto_status
))

new_id = cursor.fetchone()["resource_id"]
conn.commit()
invalidate_resource_cache()


        # Fetch the newly created record
        cursor.execute("SELECT * FROM resources WHERE resource_id = ?;", (new_id,))
        created_resource = dict(cursor.fetchone())

        return jsonify({
            "message": "Resource created successfully.",
            "resource": created_resource
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to create resource: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 10. Update Resource Endpoint: PUT /api/resources/<int:resource_id>
# -----------------------------------------------------------------------------
@app.route("/api/resources/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    """
    Updates quantities, warehouse location, name, or category for an existing resource.
    Validates non-negative quantities, maintains quantity consistency,
    and recalculates status automatically.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Check existence
        cursor.execute("SELECT * FROM resources WHERE resource_id = ?;", (resource_id,))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"error": f"Resource with ID {resource_id} was not found."}), 404

        existing_dict = dict(existing)

        # Update text fields if provided
        resource_name = data.get("resource_name", existing_dict["resource_name"])
        category = data.get("category", existing_dict["category"])
        unit = data.get("unit", existing_dict["unit"])
        warehouse_location = data.get("warehouse_location", existing_dict["warehouse_location"])

        if isinstance(resource_name, str) and not resource_name.strip():
            return jsonify({"error": "resource_name cannot be empty."}), 400
        if isinstance(category, str) and not category.strip():
            return jsonify({"error": "category cannot be empty."}), 400
        if isinstance(unit, str) and not unit.strip():
            return jsonify({"error": "unit cannot be empty."}), 400
        if isinstance(warehouse_location, str) and not warehouse_location.strip():
            return jsonify({"error": "warehouse_location cannot be empty."}), 400

        # Validate total_quantity
        total_qty = existing_dict["total_quantity"]
        if "total_quantity" in data:
            try:
                total_qty = int(data["total_quantity"])
                if total_qty < 0:
                    return jsonify({"error": "total_quantity must be a non-negative integer."}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "total_quantity must be a valid integer."}), 400

        # Validate available_quantity
        available_qty = existing_dict["available_quantity"]
        if "available_quantity" in data:
            try:
                available_qty = int(data["available_quantity"])
                if available_qty < 0:
                    return jsonify({"error": "available_quantity must be a non-negative integer."}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "available_quantity must be a valid integer."}), 400

        # Check quantity consistency
        if available_qty > total_qty:
            return jsonify({
                "error": f"available_quantity ({available_qty}) cannot exceed total_quantity ({total_qty})."
            }), 400

        allocated_qty = total_qty - available_qty
        new_status = compute_stock_status(available_qty, total_qty)

        cursor.execute("""
            UPDATE resources
            SET resource_name = ?,
                category = ?,
                unit = ?,
                total_quantity = ?,
                available_quantity = ?,
                allocated_quantity = ?,
                warehouse_location = ?,
                status = ?
            WHERE resource_id = ?;
        """, (
            resource_name.strip() if isinstance(resource_name, str) else resource_name,
            category.strip() if isinstance(category, str) else category,
            unit.strip() if isinstance(unit, str) else unit,
            total_qty,
            available_qty,
            allocated_qty,
            warehouse_location.strip() if isinstance(warehouse_location, str) else warehouse_location,
            new_status,
            resource_id
        ))
        conn.commit()
        invalidate_resource_cache()

        # Fetch updated row
        cursor.execute("SELECT * FROM resources WHERE resource_id = ?;", (resource_id,))
        updated_row = dict(cursor.fetchone())

        return jsonify({
            "message": "Resource updated successfully.",
            "resource": updated_row
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to update resource: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 11. Delete Resource Endpoint: DELETE /api/resources/<int:resource_id>
# -----------------------------------------------------------------------------
@app.route("/api/resources/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    """
    Deletes an unused resource from inventory.
    Prevents deletion if referenced by existing requests in resource_requests table.
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check existence
        cursor.execute("SELECT * FROM resources WHERE resource_id = ?;", (resource_id,))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"error": f"Resource with ID {resource_id} was not found."}), 404

        # Check references in resource_requests
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM resource_requests
            WHERE resource_id = ?;
        """, (resource_id,))
        ref_count = cursor.fetchone()["count"]

        if ref_count > 0:
            return jsonify({
                "error": f"Cannot delete resource with ID {resource_id} because it is referenced by {ref_count} existing resource request(s)."
            }), 409

        cursor.execute("DELETE FROM resources WHERE resource_id = ?;", (resource_id,))
        conn.commit()
        invalidate_resource_cache()

        return jsonify({
            "message": f"Resource with ID {resource_id} was deleted successfully.",
            "resource_id": resource_id
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to delete resource: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 12. Submit Relief Resource Request: POST /api/resources/request
# -----------------------------------------------------------------------------
@app.route("/api/resources/request", methods=["POST"])
def submit_resource_request():
    """
    Submits a new relief resource request for an affected district.
    Validates required fields, checks that district and resource exist,
    computes priority score using calculate_request_priority_score(),
    and stores the request in 'Pending' status.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        # Required fields check
        required_fields = ["district_id", "resource_id", "requester_name", "requester_contact", "quantity_requested", "urgency_level"]
        for field in required_fields:
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                return jsonify({"error": f"Missing required field: '{field}'."}), 400

        # Validate district_id
        try:
            district_id = int(data["district_id"])
        except (ValueError, TypeError):
            return jsonify({"error": "district_id must be an integer."}), 400

        # Validate resource_id
        try:
            resource_id = int(data["resource_id"])
        except (ValueError, TypeError):
            return jsonify({"error": "resource_id must be an integer."}), 400

        # Validate quantity_requested
        try:
            quantity_requested = int(data["quantity_requested"])
            if quantity_requested <= 0:
                return jsonify({"error": "quantity_requested must be a positive integer greater than 0."}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "quantity_requested must be a valid integer."}), 400

        # Validate urgency_level
        urgency_raw = str(data["urgency_level"]).strip()
        valid_urgencies = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
        urgency_level = valid_urgencies.get(urgency_raw.lower())
        if not urgency_level:
            return jsonify({"error": "Invalid urgency_level. Allowed values: Critical, High, Medium, Low."}), 400

        reason_notes = data.get("reason_notes", "").strip() if data.get("reason_notes") else None

        conn = get_db()
        cursor = conn.cursor()

        # Check district existence and get its risk_tier
        cursor.execute("SELECT district_id, district_name, risk_tier FROM districts WHERE district_id = ?;", (district_id,))
        district_row = cursor.fetchone()
        if not district_row:
            return jsonify({"error": f"District with ID {district_id} was not found."}), 404

        # Check resource existence and get its available_quantity
        cursor.execute("SELECT resource_id, resource_name, available_quantity FROM resources WHERE resource_id = ?;", (resource_id,))
        resource_row = cursor.fetchone()
        if not resource_row:
            return jsonify({"error": f"Resource with ID {resource_id} was not found."}), 404

        # Calculate dispatch priority score using project heuristic algorithm
        priority_score = calculate_request_priority_score(
            urgency_level=urgency_level,
            district_risk_tier=district_row["risk_tier"],
            quantity_requested=quantity_requested,
            available_quantity=resource_row["available_quantity"]
        )

        
# Insert new request with status 'Pending'
cursor.execute("""
    INSERT INTO resource_requests (
        district_id, resource_id, requester_name, requester_contact,
        quantity_requested, urgency_level, calculated_priority_score,
        status, reason_notes
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', %s)
    RETURNING request_id;
""", (
    district_id,
    resource_id,
    data["requester_name"].strip(),
    data["requester_contact"].strip(),
    quantity_requested,
    urgency_level,
    priority_score,
    reason_notes
))

new_request_id = cursor.fetchone()["request_id"]
conn.commit()


        # Fetch newly created request joined with district and resource info
       cursor.execute("""
    SELECT 
        r.request_id,
        r.district_id,
        d.district_name,
        d.state_id,
        s.state_name,
        d.risk_tier AS district_risk_tier,
        r.resource_id,
        res.resource_name,
        res.unit AS resource_unit,
        r.requester_name,
        r.requester_contact,
        r.quantity_requested,
        r.urgency_level,
        r.calculated_priority_score,
        r.status,
        r.reason_notes,
        r.requested_at
    FROM resource_requests r
    JOIN districts d ON r.district_id = d.district_id
    JOIN states s ON d.state_id = s.state_id
    JOIN resources res ON r.resource_id = res.resource_id
    WHERE r.request_id = %s;
""", (new_request_id,))
created_req = dict(cursor.fetchone())

        return jsonify({
            "message": "Resource request submitted successfully.",
            "request": created_req
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to submit resource request: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 13. Resource Requests List Endpoint: GET /api/resources/requests
# -----------------------------------------------------------------------------
@app.route("/api/resources/requests", methods=["GET"])
def get_resource_requests():
    """
    Returns all relief resource requests, joined with district, state, and resource details.
    Sorted by calculated_priority_score DESC.
    Supports filtering by:
    - status ('Pending', 'Approved', 'Rejected', 'Dispatched')
    - urgency ('Critical', 'High', 'Medium', 'Low')
    - district_id
    - resource_id
    """
    conn = None
    try:
        status_param = request.args.get("status")
        urgency_param = request.args.get("urgency")
        district_id_param = request.args.get("district_id")
        resource_id_param = request.args.get("resource_id")

        where_clauses = ["1=1"]
        params = []

        if status_param and status_param.strip():
            valid_statuses = {"pending": "Pending", "approved": "Approved", "rejected": "Rejected", "dispatched": "Dispatched"}
            norm_status = valid_statuses.get(status_param.strip().lower())
            if not norm_status:
                return jsonify({"error": "Invalid status parameter. Allowed values: Pending, Approved, Rejected, Dispatched."}), 400
            where_clauses.append("r.status = ?")
            params.append(norm_status)

        if urgency_param and urgency_param.strip():
            valid_urgencies = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
            norm_urgency = valid_urgencies.get(urgency_param.strip().lower())
            if not norm_urgency:
                return jsonify({"error": "Invalid urgency parameter. Allowed values: Critical, High, Medium, Low."}), 400
            where_clauses.append("r.urgency_level = ?")
            params.append(norm_urgency)

        if district_id_param:
            try:
                where_clauses.append("r.district_id = ?")
                params.append(int(district_id_param))
            except ValueError:
                return jsonify({"error": "district_id must be an integer."}), 400

        if resource_id_param:
            try:
                where_clauses.append("r.resource_id = ?")
                params.append(int(resource_id_param))
            except ValueError:
                return jsonify({"error": "resource_id must be an integer."}), 400

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT 
                r.request_id,
                r.district_id,
                d.district_name,
                d.state_id,
                s.state_name,
                d.risk_tier AS district_risk_tier,
                d.risk_score AS district_risk_score,
                r.resource_id,
                res.resource_name,
                res.category AS resource_category,
                res.unit AS resource_unit,
                res.available_quantity AS current_resource_available,
                r.requester_name,
                r.requester_contact,
                r.quantity_requested,
                r.urgency_level,
                r.calculated_priority_score,
                r.status,
                r.reason_notes,
                r.requested_at,
                r.reviewed_at,
                r.reviewed_by
            FROM resource_requests r
            JOIN districts d ON r.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            JOIN resources res ON r.resource_id = res.resource_id
            WHERE {where_sql}
            ORDER BY r.calculated_priority_score DESC, r.request_id ASC;
        """

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        requests_list = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "requests": requests_list,
            "total": len(requests_list)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch resource requests: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 14. Review Resource Request (Approve/Reject): PUT /api/resources/requests/<int:request_id>/status
# -----------------------------------------------------------------------------
@app.route("/api/resources/requests/<int:request_id>/status", methods=["PUT"])
def review_resource_request(request_id):
    """
    Reviews a pending resource request (Approve or Reject).
    
    Approval rules:
    - Only 'Pending' requests can be approved.
    - Uses an atomic SQLite transaction.
    - Checks that available_quantity >= quantity_requested.
    - If insufficient, rolls back and returns 422 Unprocessable Entity.
    - If sufficient, deducts available_quantity, increases allocated_quantity,
      recalculates resource stock status, sets request status to 'Approved',
      and records reviewed_at and reviewed_by.
      
    Rejection rules:
    - Only 'Pending' requests can be rejected.
    - Updates request status to 'Rejected' without modifying inventory.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        # Validate status decision
        status_raw = data.get("status")
        if not status_raw or not str(status_raw).strip():
            return jsonify({"error": "Missing required field: 'status'."}), 400

        valid_decisions = {"approved": "Approved", "rejected": "Rejected"}
        decision = valid_decisions.get(str(status_raw).strip().lower())
        if not decision:
            return jsonify({"error": "Invalid status. Allowed values: 'Approved' or 'Rejected'."}), 400

        reviewed_by = data.get("reviewed_by")
        if not reviewed_by or not str(reviewed_by).strip():
            return jsonify({"error": "Missing required field: 'reviewed_by'."}), 400
        reviewed_by_clean = str(reviewed_by).strip()

        conn = get_db()
        cursor = conn.cursor()

        # Step 1: Verify request exists
        cursor.execute("SELECT * FROM resource_requests WHERE request_id = ?;", (request_id,))
        req = cursor.fetchone()
        if not req:
            return jsonify({"error": f"Resource request with ID {request_id} was not found."}), 404

        req_dict = dict(req)

        # Step 2: Verify request is in 'Pending' status
        if req_dict["status"] != "Pending":
            return jsonify({
                "error": f"Cannot review request {request_id}. It is already '{req_dict['status']}'."
            }), 409

        # Step 3: Handle REJECTION
        if decision == "Rejected":
            cursor.execute("""
                UPDATE resource_requests
                SET status = 'Rejected',
                    reviewed_at = datetime('now'),
                    reviewed_by = ?
                WHERE request_id = ?;
            """, (reviewed_by_clean, request_id))
            conn.commit()

            cursor.execute("SELECT * FROM resource_requests WHERE request_id = ?;", (request_id,))
            updated_req = dict(cursor.fetchone())
            return jsonify({
                "message": f"Resource request {request_id} was rejected.",
                "request": updated_req
            }), 200

        # Step 4: Handle APPROVAL (Atomic transaction)
        res_id = req_dict["resource_id"]
        qty_requested = req_dict["quantity_requested"]

        # Fetch current resource stock
        cursor.execute("SELECT * FROM resources WHERE resource_id = ?;", (res_id,))
        res = cursor.fetchone()
        if not res:
            return jsonify({"error": f"Associated resource with ID {res_id} was not found."}), 404

        res_dict = dict(res)
        current_available = res_dict["available_quantity"]
        total_qty = res_dict["total_quantity"]
        current_allocated = res_dict["allocated_quantity"]

        # Check sufficiency of stock
        if current_available < qty_requested:
            conn.rollback()
            return jsonify({
                "error": f"Insufficient inventory for approval. Available: {current_available}, Requested: {qty_requested}."
            }), 422

        new_available = current_available - qty_requested
        new_allocated = current_allocated + qty_requested
        new_status = compute_stock_status(new_available, total_qty)

        # Atomic inventory deduction with conditional guard against concurrent overdrafts
        cursor.execute("""
            UPDATE resources
            SET available_quantity = available_quantity - ?,
                allocated_quantity = allocated_quantity + ?,
                status = ?
            WHERE resource_id = ? AND available_quantity >= ?;
        """, (qty_requested, qty_requested, new_status, res_id, qty_requested))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({
                "error": "Failed to allocate inventory due to concurrent stock modification. Please retry."
            }), 422

        # Update the request record
        cursor.execute("""
            UPDATE resource_requests
            SET status = 'Approved',
                reviewed_at = CURRENT_TIMESTAMP,
reviewed_by = %s

            WHERE request_id = ? AND status = 'Pending';
        """, (reviewed_by_clean, request_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({
                "error": "Failed to update request status. Request may have already been reviewed."
            }), 409

        # Commit transaction atomically
        conn.commit()
        # Invalidate resource cache after inventory allocation
        invalidate_resource_cache()


        # Fetch updated request and resource
        cursor.execute("SELECT * FROM resource_requests WHERE request_id = ?;", (request_id,))
        updated_req = dict(cursor.fetchone())

        cursor.execute("SELECT * FROM resources WHERE resource_id = ?;", (res_id,))
        updated_res = dict(cursor.fetchone())

        return jsonify({
            "message": f"Resource request {request_id} was successfully approved and inventory allocated.",
            "request": updated_req,
            "resource": updated_res
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to process request review: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# Helper: Phone Number Format Validation
# -----------------------------------------------------------------------------
def is_valid_phone(phone_str):
    """
    Validates phone number format:
    Must contain valid phone characters (+, digits, spaces, hyphens, parentheses)
    and have between 10 and 15 total digits.
    """
    if not phone_str or not isinstance(phone_str, str):
        return False
    p = phone_str.strip()
    digits_only = re.sub(r"\D", "", p)
    if not (10 <= len(digits_only) <= 15):
        return False
    return bool(re.match(r"^[\+]?[0-9\-\s\(\)\.]{10,20}$", p))


# -----------------------------------------------------------------------------
# 15. Report Disaster Incident: POST /api/incidents/report
# -----------------------------------------------------------------------------
@app.route("/api/incidents/report", methods=["POST"])
def report_incident():
    """
    Submits a new disaster incident report from citizens or local observers.
    Validates mandatory fields, checks that district exists, validates phone format,
    validates severity level and non-negative affected count, sets verification_status = 'Unverified',
    and stores incident using database-generated reported_at timestamp.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be a valid JSON object."}), 400

        # Mandatory fields
        required_fields = ["district_id", "reporter_name", "reporter_phone", "severity_level", "description"]
        for field in required_fields:
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                return jsonify({"error": f"Missing required field: '{field}'."}), 400

        # Validate reporter_name
        reporter_name = str(data["reporter_name"]).strip()
        if len(reporter_name) < 2:
            return jsonify({"error": "reporter_name must be at least 2 characters long."}), 400

        # Validate district_id
        try:
            district_id = int(data["district_id"])
        except (ValueError, TypeError):
            return jsonify({"error": "district_id must be an integer."}), 400

        # Validate reporter_phone
        reporter_phone = str(data["reporter_phone"]).strip()
        if not is_valid_phone(reporter_phone):
            return jsonify({"error": "Invalid phone number format. Must contain 10 to 15 digits."}), 400

        # Validate severity_level
        valid_severities = {"critical": "Critical", "severe": "Severe", "moderate": "Moderate", "minor": "Minor"}
        severity_level = valid_severities.get(str(data["severity_level"]).strip().lower())
        if not severity_level:
            return jsonify({"error": "Invalid severity_level. Allowed values: Critical, Severe, Moderate, Minor."}), 400

        # Validate estimated_affected_people
        affected_val = data.get("estimated_affected_people", 0)
        try:
            estimated_affected = int(affected_val)
            if estimated_affected < 0:
                return jsonify({"error": "estimated_affected_people must be a non-negative integer."}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "estimated_affected_people must be a valid integer."}), 400

        # Validate description
        description = str(data["description"]).strip()
        if not description:
            return jsonify({"error": "description cannot be blank."}), 400

        disaster_type = str(data.get("disaster_type", "Flood")).strip()
        if not disaster_type:
            disaster_type = "Flood"

        conn = get_db()
        cursor = conn.cursor()

        # Check district existence
        cursor.execute("SELECT district_id, district_name, state_id FROM districts WHERE district_id = ?;", (district_id,))
        dist_row = cursor.fetchone()
        if not dist_row:
            return jsonify({"error": f"District with ID {district_id} was not found."}), 404

        
# Insert incident with verification_status = 'Unverified'
cursor.execute("""
    INSERT INTO reported_incidents (
        district_id, reporter_name, reporter_phone, disaster_type,
        severity_level, estimated_affected_people, description,
        verification_status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'Unverified')
    RETURNING incident_id;
""", (
    district_id,
    reporter_name,
    reporter_phone,
    disaster_type,
    severity_level,
    estimated_affected,
    description
))

new_incident_id = cursor.fetchone()["incident_id"]
conn.commit()


        # Fetch newly created record joined with district and state
        cursor.execute("""
            SELECT 
                i.incident_id,
                i.district_id,
                d.district_name,
                d.state_id,
                s.state_name,
                i.reporter_name,
                i.reporter_phone,
                i.disaster_type,
                i.severity_level,
                i.estimated_affected_people,
                i.description,
                i.reported_at,
                i.verification_status
            FROM reported_incidents i
            LEFT JOIN districts d ON i.district_id = d.district_id
            LEFT JOIN states s ON d.state_id = s.state_id
            WHERE i.incident_id = ?;
        """, (new_incident_id,))
        created_incident = dict(cursor.fetchone())

        return jsonify({
            "message": "Disaster incident reported successfully.",
            "incident": created_incident
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Failed to report incident: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# -----------------------------------------------------------------------------
# 16. List Reported Incidents: GET /api/incidents
# -----------------------------------------------------------------------------
@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    """
    Returns reported incidents joined with district and state names.
    Sorted newest incidents first (ORDER BY incident_id DESC).
    Supports filtering by:
    - severity_level: Critical, Severe, Moderate, Minor
    - verification_status: Unverified, Verified, Resolved
    - district_id: integer filter
    - disaster_type: substring search
    """
    conn = None
    try:
        severity_param = request.args.get("severity_level")
        status_param = request.args.get("verification_status")
        district_id_param = request.args.get("district_id")
        type_param = request.args.get("disaster_type")

        where_clauses = ["1=1"]
        params = []

        if severity_param and severity_param.strip():
            valid_severities = {"critical": "Critical", "severe": "Severe", "moderate": "Moderate", "minor": "Minor"}
            norm_sev = valid_severities.get(severity_param.strip().lower())
            if not norm_sev:
                return jsonify({"error": "Invalid severity_level. Allowed values: Critical, Severe, Moderate, Minor."}), 400
            where_clauses.append("i.severity_level = ?")
            params.append(norm_sev)

        if status_param and status_param.strip():
            valid_statuses = {"unverified": "Unverified", "verified": "Verified", "resolved": "Resolved"}
            norm_stat = valid_statuses.get(status_param.strip().lower())
            if not norm_stat:
                return jsonify({"error": "Invalid verification_status. Allowed values: Unverified, Verified, Resolved."}), 400
            where_clauses.append("i.verification_status = ?")
            params.append(norm_stat)

        if district_id_param:
            try:
                where_clauses.append("i.district_id = ?")
                params.append(int(district_id_param))
            except ValueError:
                return jsonify({"error": "district_id must be an integer."}), 400

        if type_param and type_param.strip():
            where_clauses.append("i.disaster_type LIKE ?")
            params.append(f"%{type_param.strip()}%")

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT 
                i.incident_id,
                i.district_id,
                d.district_name,
                d.state_id,
                s.state_name,
                i.reporter_name,
                i.reporter_phone,
                i.disaster_type,
                i.severity_level,
                i.estimated_affected_people,
                i.description,
                i.reported_at,
                i.verification_status
            FROM reported_incidents i
            LEFT JOIN districts d ON i.district_id = d.district_id
            LEFT JOIN states s ON d.state_id = s.state_id
            WHERE {where_sql}
            ORDER BY i.incident_id DESC;
        """

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(query, params)
        incidents_list = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "incidents": incidents_list,
            "total": len(incidents_list)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch incidents: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
