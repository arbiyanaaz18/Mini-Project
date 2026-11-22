"""
Automated Verification Tests for Phase 1: Database & Dataset Ingestion.
Tests schema, constraints, foreign keys, row counts, and data integrity.
"""

import os
import sys
import unittest
import sqlite3

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import DB_PATH, get_db_connection

class TestPhase1Database(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure database exists before testing."""
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f"Database not found at {DB_PATH}. Run init_db.py first!")

    def setUp(self):
        """Get a fresh connection for each test with foreign keys enabled."""
        self.conn = get_db_connection()

    def tearDown(self):
        self.conn.close()

    def test_01_all_tables_exist(self):
        """Verify that all seven required tables exist in SQLite."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row['name'] for row in cursor.fetchall()}
        
        expected_tables = {
            "states",
            "districts",
            "flood_events",
            "annual_impact",
            "resources",
            "resource_requests",
            "reported_incidents"
        }
        for table in expected_tables:
            self.assertIn(table, tables, f"Expected table '{table}' is missing from database!")

    def test_02_imported_row_counts(self):
        """Verify exact row counts match cleaned dataset inputs."""
        cursor = self.conn.cursor()

        # States: All Indian states/UTs present in datasets
        cursor.execute("SELECT COUNT(*) AS cnt FROM states;")
        states_cnt = cursor.fetchone()['cnt']
        self.assertGreaterEqual(states_cnt, 35, "Expected at least 35 States/UTs.")

        # Districts: Exactly 732 districts from cleaned_District_FloodImpact and Area
        cursor.execute("SELECT COUNT(*) AS cnt FROM districts;")
        dist_cnt = cursor.fetchone()['cnt']
        self.assertEqual(dist_cnt, 732, f"Expected 732 districts, found {dist_cnt}!")

        # Historical Flood Events: Exactly 6,876 events from cleaned_India_Flood_Inventory_v3
        cursor.execute("SELECT COUNT(*) AS cnt FROM flood_events;")
        events_cnt = cursor.fetchone()['cnt']
        self.assertEqual(events_cnt, 6876, f"Expected 6,876 flood events, found {events_cnt}!")

        # Annual Impact: Exactly 12 longitudinal years from cleaned_disaster_dataset_1
        cursor.execute("SELECT COUNT(*) AS cnt FROM annual_impact;")
        annual_cnt = cursor.fetchone()['cnt']
        self.assertEqual(annual_cnt, 12, f"Expected 12 annual impact records, found {annual_cnt}!")

        # Demo Resources: Exactly 8 initial resources
        cursor.execute("SELECT COUNT(*) AS cnt FROM resources;")
        res_cnt = cursor.fetchone()['cnt']
        self.assertEqual(res_cnt, 8, f"Expected 8 initial resources, found {res_cnt}!")

    def test_03_foreign_key_enforcement(self):
        """Verify that foreign key constraints prevent inserting orphan districts."""
        cursor = self.conn.cursor()
        # Attempt to insert a district pointing to a non-existent state_id (e.g. 99999)
        with self.assertRaises(sqlite3.IntegrityError, msg="Foreign key violation should raise IntegrityError"):
            cursor.execute("""
            INSERT INTO districts (district_name, state_id, dfsi_score, population)
            VALUES ('InvalidDistrict', 99999, 10.0, 50000);
            """)
            self.conn.commit()

    def test_04_district_risk_scores_and_tiers(self):
        """Verify that all districts have valid heuristic risk scores and valid risk tiers."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT district_name, risk_score, risk_tier FROM districts;")
        rows = cursor.fetchall()
        self.assertEqual(len(rows), 732)
        valid_tiers = {"High", "Moderate", "Low"}
        for r in rows:
            self.assertGreaterEqual(r['risk_score'], 0.0, f"Negative risk score in {r['district_name']}")
            self.assertLessEqual(r['risk_score'], 100.0, f"Risk score > 100 in {r['district_name']}")
            self.assertIn(r['risk_tier'], valid_tiers, f"Invalid tier in {r['district_name']}")

    def test_05_demo_data_flagging(self):
        """Verify that all initial seeded resources are explicitly marked as demo data."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_demo_data FROM resources;")
        rows = cursor.fetchall()
        for r in rows:
            self.assertEqual(r['is_demo_data'], 1, "Initial resources must be flagged as demo data (is_demo_data = 1)!")

    def test_06_unique_constraints(self):
        """Verify unique constraints on states and event UEIs."""
        cursor = self.conn.cursor()
        # Test duplicate state name
        cursor.execute("SELECT state_name FROM states LIMIT 1;")
        existing_state = cursor.fetchone()['state_name']
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO states (state_name) VALUES (?);", (existing_state,))
            self.conn.commit()

        # Test duplicate UEI
        cursor.execute("SELECT uei FROM flood_events LIMIT 1;")
        existing_uei = cursor.fetchone()['uei']
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO flood_events (uei) VALUES (?);", (existing_uei,))
            self.conn.commit()

if __name__ == "__main__":
    unittest.main()
