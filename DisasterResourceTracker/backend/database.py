"""
Database connection and schema definitions for Disaster Resource Tracker.
Uses SQLite with strict foreign key constraints and indexed queries.
"""

import os
import sqlite3

# Path to the SQLite database file
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BACKEND_DIR, "disaster_tracker.db")

def get_db_connection(db_path=None):
    """
    Establish and return a connection to the SQLite database.
    Enforces foreign key constraints and dictionary-like row access.
    """
    path = db_path if db_path else DB_PATH
    conn = sqlite3.connect(path)
    # Enable foreign key enforcement for every connection
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn):
    """
    Creates all relational tables, foreign key constraints,
    check constraints, and performance indexes.
    """
    cursor = conn.cursor()

    # 1. States Master Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS states (
        state_id INTEGER PRIMARY KEY AUTOINCREMENT,
        state_name TEXT UNIQUE NOT NULL COLLATE NOCASE
    );
    """)

    # 2. Districts Master & Risk Profile Table (Integrated from Datasets 1, 2, 3)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS districts (
        district_id INTEGER PRIMARY KEY AUTOINCREMENT,
        district_name TEXT NOT NULL COLLATE NOCASE,
        state_id INTEGER NOT NULL,
        dfsi_score REAL,
        population INTEGER NOT NULL DEFAULT 0,
        human_fatality_total INTEGER NOT NULL DEFAULT 0,
        human_injured_total INTEGER NOT NULL DEFAULT 0,
        mean_flood_duration_days REAL DEFAULT 0.0,
        percent_flooded_area REAL DEFAULT 0.0,
        permanent_water_percent REAL DEFAULT 0.0,
        corrected_flooded_area REAL DEFAULT 0.0,
        risk_score REAL DEFAULT 0.0,
        risk_tier TEXT DEFAULT 'Low' CHECK(risk_tier IN ('High', 'Moderate', 'Low')),
        FOREIGN KEY (state_id) REFERENCES states (state_id) ON DELETE RESTRICT,
        UNIQUE (district_name, state_id)
    );
    """)

    # 3. Flood Events Table (Integrated from Dataset 4: India Flood Inventory)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flood_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        uei TEXT UNIQUE NOT NULL,
        start_date TEXT,
        end_date TEXT,
        duration_days REAL DEFAULT 0.0,
        main_cause TEXT,
        state_name TEXT,
        districts_mentioned TEXT,
        human_fatality INTEGER DEFAULT 0,
        human_injured INTEGER DEFAULT 0,
        human_displaced TEXT,
        animal_fatality TEXT,
        description TEXT,
        extent_of_damage TEXT,
        event_source TEXT,
        district_lgd_codes TEXT,
        state_codes TEXT
    );
    """)

    # 4. Annual Disaster Impact Table (Integrated from Dataset 5: Disaster Dataset 1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS annual_impact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year TEXT UNIQUE NOT NULL,
        lives_lost INTEGER NOT NULL,
        cattle_lost INTEGER NOT NULL,
        houses_damaged INTEGER NOT NULL,
        cropped_area_affected_lakh_ha REAL NOT NULL
    );
    """)

    # 5. Resources Inventory Table (Disaster Resource Management)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit TEXT NOT NULL,
        total_quantity INTEGER NOT NULL CHECK (total_quantity >= 0),
        available_quantity INTEGER NOT NULL CHECK (available_quantity >= 0),
        allocated_quantity INTEGER NOT NULL DEFAULT 0 CHECK (allocated_quantity >= 0),
        warehouse_location TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Available' CHECK (status IN ('Available', 'Low Stock', 'Critical')),
        is_demo_data INTEGER NOT NULL DEFAULT 1 CHECK (is_demo_data IN (0, 1))
    );
    """)

    # 6. Resource Requests Table (Workflow & Approvals)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resource_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        district_id INTEGER NOT NULL,
        resource_id INTEGER NOT NULL,
        requester_name TEXT NOT NULL,
        requester_contact TEXT NOT NULL,
        quantity_requested INTEGER NOT NULL CHECK (quantity_requested > 0),
        urgency_level TEXT NOT NULL CHECK (urgency_level IN ('Critical', 'High', 'Medium', 'Low')),
        calculated_priority_score REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Dispatched')),
        reason_notes TEXT,
        requested_at TEXT NOT NULL DEFAULT (datetime('now')),
        reviewed_at TEXT,
        reviewed_by TEXT,
        FOREIGN KEY (district_id) REFERENCES districts (district_id) ON DELETE CASCADE,
        FOREIGN KEY (resource_id) REFERENCES resources (resource_id) ON DELETE RESTRICT
    );
    """)

    # 7. Reported Incidents Table (Citizen/Field Disaster Reporting)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reported_incidents (
        incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
        district_id INTEGER,
        reporter_name TEXT NOT NULL,
        reporter_phone TEXT NOT NULL,
        disaster_type TEXT NOT NULL DEFAULT 'Flood',
        severity_level TEXT NOT NULL CHECK (severity_level IN ('Critical', 'Severe', 'Moderate', 'Minor')),
        estimated_affected_people INTEGER DEFAULT 0 CHECK (estimated_affected_people >= 0),
        description TEXT NOT NULL,
        reported_at TEXT NOT NULL DEFAULT (datetime('now')),
        verification_status TEXT NOT NULL DEFAULT 'Unverified' CHECK (verification_status IN ('Unverified', 'Verified', 'Resolved')),
        FOREIGN KEY (district_id) REFERENCES districts (district_id) ON DELETE SET NULL
    );
    """)

    # 8. Indexes for Performance and Query Optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_districts_state ON districts (state_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_districts_risk ON districts (risk_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_state ON flood_events (state_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start ON flood_events (start_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON resource_requests (status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_district ON resource_requests (district_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_resource ON resource_requests (resource_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_district ON reported_incidents (district_id);")

    conn.commit()
