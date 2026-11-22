"""
Automated Integration Tests for Phase 2 - Step 2C:
Community Incident Reporting API.

Uses an isolated test database copy so real project data is never modified.
"""

import os
import sys
import shutil
import unittest
import json

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import DB_PATH, get_db_connection

TEST_DB_PATH = os.path.join(BACKEND_DIR, "disaster_tracker_test_step2c.db")

class TestPhase2Step2CIncidents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create an isolated test database copy for incident reporting tests."""
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f"Source database not found at {DB_PATH}. Run init_db.py first!")

        # Make an isolated copy of the database
        shutil.copyfile(DB_PATH, TEST_DB_PATH)

        # Configure Flask app to use the isolated test database
        app.config["DATABASE"] = TEST_DB_PATH
        app.testing = True
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Clean up isolated test database after all tests complete."""
        app.config["DATABASE"] = None
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. Valid Incident Submission
    # -------------------------------------------------------------------------
    def test_01_valid_incident_submission(self):
        """Test POST /api/incidents/report successfully creates an incident with HTTP 201."""
        payload = {
            "district_id": 1,
            "reporter_name": "Citizen Amit Kumar",
            "reporter_phone": "+91-9876543210",
            "disaster_type": "Flood",
            "severity_level": "Critical",
            "estimated_affected_people": 250,
            "description": "Severe river embankment breach near northern ward; residential area inundated."
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()

        self.assertIn("incident", data)
        inc = data["incident"]
        self.assertEqual(inc["district_id"], 1)
        self.assertEqual(inc["reporter_name"], "Citizen Amit Kumar")
        self.assertEqual(inc["reporter_phone"], "+91-9876543210")
        self.assertEqual(inc["severity_level"], "Critical")
        self.assertEqual(inc["estimated_affected_people"], 250)
        self.assertIn("embankment breach", inc["description"])
        self.assertIn("district_name", inc)
        self.assertIn("state_name", inc)

    # -------------------------------------------------------------------------
    # 2. Missing Mandatory Fields
    # -------------------------------------------------------------------------
    def test_02_missing_mandatory_fields(self):
        """Test POST /api/incidents/report returns 400 when mandatory fields are missing."""
        incomplete_payload = {
            "district_id": 1,
            # missing reporter_name, phone, severity, description
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(incomplete_payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    # -------------------------------------------------------------------------
    # 3. Invalid District ID
    # -------------------------------------------------------------------------
    def test_03_invalid_district_id(self):
        """Test POST /api/incidents/report returns 404 when district_id does not exist."""
        payload = {
            "district_id": 999999,
            "reporter_name": "Observer Priya",
            "reporter_phone": "+91-9876543210",
            "severity_level": "Severe",
            "description": "Flash flooding on state highway."
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("District with ID 999999 was not found", resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 4. Invalid Phone Number
    # -------------------------------------------------------------------------
    def test_04_invalid_phone_number(self):
        """Test POST /api/incidents/report returns 400 when phone number is invalid."""
        invalid_phones = ["not_a_phone", "12345", "+91-abcde"]
        for bad_phone in invalid_phones:
            payload = {
                "district_id": 1,
                "reporter_name": "Test Reporter",
                "reporter_phone": bad_phone,
                "severity_level": "Moderate",
                "description": "Waterlogging reported."
            }
            resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
            self.assertEqual(resp.status_code, 400)
            self.assertIn("Invalid phone number format", resp.get_json()["error"])

        # Also test empty phone is rejected with 400
        empty_payload = {
            "district_id": 1,
            "reporter_name": "Test Reporter",
            "reporter_phone": "",
            "severity_level": "Moderate",
            "description": "Waterlogging reported."
        }
        resp_empty = self.client.post("/api/incidents/report", data=json.dumps(empty_payload), content_type="application/json")
        self.assertEqual(resp_empty.status_code, 400)

    # -------------------------------------------------------------------------
    # 5. Invalid Severity Level
    # -------------------------------------------------------------------------
    def test_05_invalid_severity_level(self):
        """Test POST /api/incidents/report returns 400 when severity is not in allowed enum."""
        payload = {
            "district_id": 1,
            "reporter_name": "Test Reporter",
            "reporter_phone": "+91-9876543210",
            "severity_level": "CatastrophicDoom",
            "description": "Flood water entering premises."
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid severity_level", resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 6. Negative Affected People
    # -------------------------------------------------------------------------
    def test_06_negative_affected_people(self):
        """Test POST /api/incidents/report returns 400 when estimated_affected_people < 0."""
        payload = {
            "district_id": 1,
            "reporter_name": "Test Reporter",
            "reporter_phone": "+91-9876543210",
            "severity_level": "Minor",
            "estimated_affected_people": -10,
            "description": "Minor water pooling."
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("non-negative integer", resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 7. Empty Incident Description
    # -------------------------------------------------------------------------
    def test_07_empty_incident_description(self):
        """Test POST /api/incidents/report returns 400 when description is blank."""
        payload = {
            "district_id": 1,
            "reporter_name": "Test Reporter",
            "reporter_phone": "+91-9876543210",
            "severity_level": "Moderate",
            "description": "    "
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        err = resp.get_json()["error"].lower()
        self.assertTrue("description" in err and ("blank" in err or "missing" in err or "required" in err))

    # -------------------------------------------------------------------------
    # 8. Default Unverified Status
    # -------------------------------------------------------------------------
    def test_08_default_unverified_status(self):
        """Test newly reported incident is assigned verification_status = 'Unverified'."""
        payload = {
            "district_id": 2,
            "reporter_name": "Volunteer Sneha",
            "reporter_phone": "9876543211",
            "severity_level": "Moderate",
            "description": "Road submerged under 2 feet of water near highway bridge."
        }
        resp = self.client.post("/api/incidents/report", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        inc = resp.get_json()["incident"]
        self.assertEqual(inc["verification_status"], "Unverified")
        self.assertIsNotNone(inc["reported_at"])

    # -------------------------------------------------------------------------
    # 9. Fetch All Incidents
    # -------------------------------------------------------------------------
    def test_09_fetch_all_incidents(self):
        """Test GET /api/incidents returns all submitted incidents with joins."""
        resp = self.client.get("/api/incidents")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("incidents", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 2)

        first = data["incidents"][0]
        self.assertIn("incident_id", first)
        self.assertIn("district_name", first)
        self.assertIn("state_name", first)
        self.assertIn("reporter_name", first)
        self.assertIn("severity_level", first)
        self.assertIn("verification_status", first)

    # -------------------------------------------------------------------------
    # 10. Filter by Severity
    # -------------------------------------------------------------------------
    def test_10_filter_by_severity(self):
        """Test GET /api/incidents?severity_level=Critical returns only Critical incidents."""
        resp = self.client.get("/api/incidents?severity_level=Critical")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data["total"], 0)
        for inc in data["incidents"]:
            self.assertEqual(inc["severity_level"], "Critical")

        # Invalid severity filter returns 400
        bad_resp = self.client.get("/api/incidents?severity_level=NonExistent")
        self.assertEqual(bad_resp.status_code, 400)

    # -------------------------------------------------------------------------
    # 11. Filter by Verification Status
    # -------------------------------------------------------------------------
    def test_11_filter_by_verification_status(self):
        """Test GET /api/incidents?verification_status=Unverified filters correctly."""
        resp = self.client.get("/api/incidents?verification_status=Unverified")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data["total"], 0)
        for inc in data["incidents"]:
            self.assertEqual(inc["verification_status"], "Unverified")

        # Invalid verification status filter returns 400
        bad_resp = self.client.get("/api/incidents?verification_status=FakeStatus")
        self.assertEqual(bad_resp.status_code, 400)

    # -------------------------------------------------------------------------
    # 12. Filter by District
    # -------------------------------------------------------------------------
    def test_12_filter_by_district(self):
        """Test GET /api/incidents?district_id=1 returns only incidents for that district."""
        resp = self.client.get("/api/incidents?district_id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data["total"], 0)
        for inc in data["incidents"]:
            self.assertEqual(inc["district_id"], 1)

    # -------------------------------------------------------------------------
    # 13. Filter by Disaster Type
    # -------------------------------------------------------------------------
    def test_13_filter_by_disaster_type(self):
        """Test GET /api/incidents?disaster_type=Flood returns only matching disaster types."""
        resp = self.client.get("/api/incidents?disaster_type=Flood")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data["total"], 0)
        for inc in data["incidents"]:
            self.assertIn("flood", inc["disaster_type"].lower())

    # -------------------------------------------------------------------------
    # 14. Verify Newest Incidents Appear First
    # -------------------------------------------------------------------------
    def test_14_newest_incidents_first(self):
        """Test GET /api/incidents sorts newest incident_id first (DESC)."""
        # Submit a brand new incident
        p = {
            "district_id": 3,
            "reporter_name": "Latest Reporter",
            "reporter_phone": "+91-9988776655",
            "severity_level": "Minor",
            "description": "Latest water logging observation."
        }
        create_resp = self.client.post("/api/incidents/report", data=json.dumps(p), content_type="application/json")
        newest_id = create_resp.get_json()["incident"]["incident_id"]

        # Fetch list
        resp = self.client.get("/api/incidents")
        self.assertEqual(resp.status_code, 200)
        incidents = resp.get_json()["incidents"]
        self.assertEqual(incidents[0]["incident_id"], newest_id)
        # Verify descending order across all
        for i in range(len(incidents) - 1):
            self.assertGreater(incidents[i]["incident_id"], incidents[i+1]["incident_id"])

if __name__ == "__main__":
    unittest.main()
