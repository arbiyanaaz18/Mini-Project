"""
Automated Integration Tests for Phase 2 - Step 1: Core REST API Endpoints.
Covers normal requests, filter combinations, pagination, edge cases, and negative tests.
"""

import os
import sys
import unittest

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import DB_PATH

class TestPhase2Step1API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure database exists and initialize Flask test client."""
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f"Database not found at {DB_PATH}. Run init_db.py first!")
        app.testing = True
        cls.client = app.test_client()

    # -------------------------------------------------------------------------
    # 1. Tests for GET /api/stats
    # -------------------------------------------------------------------------
    def test_01_stats_endpoint(self):
        """Test that /api/stats returns verified database aggregates."""
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data["total_disasters"], 6876)
        self.assertEqual(data["total_districts"], 732)
        self.assertEqual(data["total_states"], 37)
        self.assertGreater(data["total_fatalities"], 70000)
        self.assertGreater(data["total_injured"], 10000)

        # Risk distribution checks
        self.assertIn("High", data["risk_distribution"])
        self.assertIn("Moderate", data["risk_distribution"])
        self.assertIn("Low", data["risk_distribution"])
        total_risk_dist = sum(data["risk_distribution"].values())
        self.assertEqual(total_risk_dist, 732)

        # Resource stats checks
        self.assertGreater(data["resources"]["total_quantity"], 0)
        self.assertEqual(data["resources"]["total_resource_types"], 8)

        # Top causes
        self.assertIsInstance(data["top_causes"], list)
        self.assertGreater(len(data["top_causes"]), 0)

    # -------------------------------------------------------------------------
    # 2. Tests for GET /api/states
    # -------------------------------------------------------------------------
    def test_02_states_endpoint(self):
        """Test that /api/states returns all 37 Indian states/UTs with district counts."""
        response = self.client.get("/api/states")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data["total"], 37)
        self.assertEqual(len(data["states"]), 37)

        first_state = data["states"][0]
        self.assertIn("state_id", first_state)
        self.assertIn("state_name", first_state)
        self.assertIn("district_count", first_state)
        self.assertGreater(first_state["district_count"], 0)

    # -------------------------------------------------------------------------
    # 3. Tests for GET /api/districts (Normal & Negative)
    # -------------------------------------------------------------------------
    def test_03_districts_all(self):
        """Test that /api/districts returns all 732 districts when no filter is applied."""
        response = self.client.get("/api/districts")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 732)
        self.assertEqual(len(data["districts"]), 732)

    def test_04_districts_filter_by_state(self):
        """Test filtering districts by valid state_id."""
        response = self.client.get("/api/districts?state_id=1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["count"], 0)
        for d in data["districts"]:
            self.assertEqual(d["state_id"], 1)

    def test_05_districts_filter_by_risk_tier(self):
        """Test filtering districts by risk_tier ('High')."""
        response = self.client.get("/api/districts?risk_tier=High")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["count"], 0)
        for d in data["districts"]:
            self.assertEqual(d["risk_tier"], "High")

    def test_06_districts_search(self):
        """Test searching districts by name keyword."""
        response = self.client.get("/api/districts?search=Patna")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreaterEqual(data["count"], 1)
        names = [d["district_name"].upper() for d in data["districts"]]
        self.assertIn("PATNA", names)

    def test_07_districts_invalid_state_id_negative(self):
        """Negative test: Non-integer state_id should return 400 Bad Request."""
        response = self.client.get("/api/districts?state_id=invalid_text")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_08_districts_invalid_risk_tier_negative(self):
        """Negative test: Invalid risk_tier should return 400 Bad Request."""
        response = self.client.get("/api/districts?risk_tier=SevereDanger")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    # -------------------------------------------------------------------------
    # 4. Tests for GET /api/districts/<id> (Normal & Negative)
    # -------------------------------------------------------------------------
    def test_09_district_by_id_success(self):
        """Test fetching a single valid district profile."""
        response = self.client.get("/api/districts/1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["district_id"], 1)
        self.assertIn("district_name", data)
        self.assertIn("state_name", data)
        self.assertIn("dfsi_score", data)
        self.assertIn("risk_tier", data)

    def test_10_district_by_id_not_found_negative(self):
        """Negative test: Non-existent district ID returns 404 Not Found."""
        response = self.client.get("/api/districts/999999")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("error", data)

    # -------------------------------------------------------------------------
    # 5. Tests for GET /api/disasters (Pagination, Filters, Negative)
    # -------------------------------------------------------------------------
    def test_11_disasters_default_pagination(self):
        """Test /api/disasters with default pagination (page=1, limit=25)."""
        response = self.client.get("/api/disasters")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 25)
        self.assertEqual(data["total_records"], 6876)
        self.assertEqual(data["total_pages"], 276)
        self.assertEqual(len(data["disasters"]), 25)

    def test_12_disasters_custom_pagination(self):
        """Test /api/disasters with custom page and limit."""
        response = self.client.get("/api/disasters?page=2&limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(len(data["disasters"]), 10)

    def test_13_disasters_filter_by_state(self):
        """Test filtering flood disasters by state name."""
        response = self.client.get("/api/disasters?state=Assam&limit=50")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["total_records"], 0)
        for item in data["disasters"]:
            self.assertIn("assam", item["state_name"].lower())

    def test_14_disasters_filter_by_year(self):
        """Test filtering flood disasters by year."""
        response = self.client.get("/api/disasters?year=2010&limit=50")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["total_records"], 0)
        for item in data["disasters"]:
            start_has_year = "2010" in (item["start_date"] or "")
            uei_has_year = "2010" in (item["uei"] or "")
            self.assertTrue(start_has_year or uei_has_year)

    def test_15_disasters_filter_by_cause(self):
        """Test filtering flood disasters by cause."""
        response = self.client.get("/api/disasters?cause=rain&limit=25")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["total_records"], 0)
        for item in data["disasters"]:
            self.assertIn("rain", item["main_cause"].lower())

    def test_16_disasters_invalid_page_negative(self):
        """Negative test: page < 1 should return 400 Bad Request."""
        response = self.client.get("/api/disasters?page=0")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

        response2 = self.client.get("/api/disasters?page=-5")
        self.assertEqual(response2.status_code, 400)

        response3 = self.client.get("/api/disasters?page=abc")
        self.assertEqual(response3.status_code, 400)

    def test_17_disasters_invalid_limit_negative(self):
        """Negative test: limit out of bounds (< 1 or > 100) should return 400 Bad Request."""
        response1 = self.client.get("/api/disasters?limit=0")
        self.assertEqual(response1.status_code, 400)

        response2 = self.client.get("/api/disasters?limit=105")
        self.assertEqual(response2.status_code, 400)

        response3 = self.client.get("/api/disasters?limit=xyz")
        self.assertEqual(response3.status_code, 400)

    # -------------------------------------------------------------------------
    # 6. Tests for GET /api/disasters/<id> (Normal & Negative)
    # -------------------------------------------------------------------------
    def test_18_disaster_by_id_success(self):
        """Test fetching a single valid historical flood event."""
        response = self.client.get("/api/disasters/1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["event_id"], 1)
        self.assertIn("uei", data)
        self.assertIn("main_cause", data)
        self.assertIn("state_name", data)

    def test_19_disaster_by_id_not_found_negative(self):
        """Negative test: Non-existent disaster event ID returns 404 Not Found."""
        response = self.client.get("/api/disasters/9999999")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("error", data)

    # -------------------------------------------------------------------------
    # 7. Tests for GET /api/trends
    # -------------------------------------------------------------------------
    def test_20_trends_endpoint(self):
        """Test /api/trends returns all 12 years of longitudinal data with summary."""
        response = self.client.get("/api/trends")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data["total_years"], 12)
        self.assertEqual(len(data["trends"]), 12)

        first_trend = data["trends"][0]
        self.assertIn("year", first_trend)
        self.assertIn("lives_lost", first_trend)
        self.assertIn("cattle_lost", first_trend)
        self.assertIn("houses_damaged", first_trend)
        self.assertIn("cropped_area_affected_lakh_ha", first_trend)

        # Summary checks
        summary = data["summary"]
        self.assertGreater(summary["total_lives_lost"], 0)
        self.assertGreater(summary["total_houses_damaged"], 0)
        self.assertIsNotNone(summary["peak_lives_lost_year"])
        self.assertIsNotNone(summary["peak_houses_damaged_year"])

if __name__ == "__main__":
    unittest.main()
