"""
Automated Integration Tests for Phase 2 - Step 2B:
Relief Request Submission and Approval/Rejection Workflow.

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
from algorithms import calculate_request_priority_score

TEST_DB_PATH = os.path.join(BACKEND_DIR, "disaster_tracker_test_step2b.db")

class TestPhase2Step2BRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create an isolated test database copy so real database data remains pristine."""
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

    def get_test_db(self):
        """Helper to get a connection to the test database."""
        return get_db_connection(TEST_DB_PATH)

    # -------------------------------------------------------------------------
    # 1. Submit Valid Relief Request
    # -------------------------------------------------------------------------
    def test_01_submit_valid_request(self):
        """Test POST /api/resources/request submits a valid request with status 'Pending'."""
        payload = {
            "district_id": 1,
            "resource_id": 1,
            "requester_name": "Field Officer Rajesh",
            "requester_contact": "+91-9876543210",
            "quantity_requested": 500,
            "urgency_level": "Critical",
            "reason_notes": "Immediate flood evacuation relief required in lowland areas."
        }
        resp = self.client.post("/api/resources/request", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()

        self.assertIn("request", data)
        req = data["request"]
        self.assertEqual(req["district_id"], 1)
        self.assertEqual(req["resource_id"], 1)
        self.assertEqual(req["status"], "Pending")
        self.assertEqual(req["quantity_requested"], 500)
        self.assertEqual(req["urgency_level"], "Critical")
        self.assertGreater(req["calculated_priority_score"], 0.0)

    # -------------------------------------------------------------------------
    # 2. Reject Missing Fields
    # -------------------------------------------------------------------------
    def test_02_reject_missing_fields(self):
        """Test POST /api/resources/request returns 400 when required fields are missing."""
        payload = {
            "district_id": 1,
            # missing resource_id, requester_name, contact, quantity, urgency
        }
        resp = self.client.post("/api/resources/request", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    # -------------------------------------------------------------------------
    # 3. Reject Invalid District ID
    # -------------------------------------------------------------------------
    def test_03_reject_invalid_district_id(self):
        """Test POST /api/resources/request returns 404 when district_id does not exist."""
        payload = {
            "district_id": 999999,
            "resource_id": 1,
            "requester_name": "Field Officer",
            "requester_contact": "+91-9876543210",
            "quantity_requested": 100,
            "urgency_level": "High"
        }
        resp = self.client.post("/api/resources/request", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("District with ID 999999 was not found", resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 4. Reject Invalid Resource ID
    # -------------------------------------------------------------------------
    def test_04_reject_invalid_resource_id(self):
        """Test POST /api/resources/request returns 404 when resource_id does not exist."""
        payload = {
            "district_id": 1,
            "resource_id": 888888,
            "requester_name": "Field Officer",
            "requester_contact": "+91-9876543210",
            "quantity_requested": 100,
            "urgency_level": "High"
        }
        resp = self.client.post("/api/resources/request", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Resource with ID 888888 was not found", resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 5. Reject Negative or Zero Quantity
    # -------------------------------------------------------------------------
    def test_05_reject_negative_or_zero_quantity(self):
        """Test POST /api/resources/request returns 400 when quantity is <= 0."""
        # Zero quantity
        p_zero = {
            "district_id": 1, "resource_id": 1,
            "requester_name": "Test Officer", "requester_contact": "1234567890",
            "quantity_requested": 0, "urgency_level": "High"
        }
        resp_zero = self.client.post("/api/resources/request", data=json.dumps(p_zero), content_type="application/json")
        self.assertEqual(resp_zero.status_code, 400)

        # Negative quantity
        p_neg = {
            "district_id": 1, "resource_id": 1,
            "requester_name": "Test Officer", "requester_contact": "1234567890",
            "quantity_requested": -50, "urgency_level": "High"
        }
        resp_neg = self.client.post("/api/resources/request", data=json.dumps(p_neg), content_type="application/json")
        self.assertEqual(resp_neg.status_code, 400)

    # -------------------------------------------------------------------------
    # 6. Reject Invalid Urgency
    # -------------------------------------------------------------------------
    def test_06_reject_invalid_urgency(self):
        """Test POST /api/resources/request returns 400 when urgency_level is not valid."""
        payload = {
            "district_id": 1, "resource_id": 1,
            "requester_name": "Test Officer", "requester_contact": "1234567890",
            "quantity_requested": 100, "urgency_level": "SuperUrgentExtravaganza"
        }
        resp = self.client.post("/api/resources/request", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid urgency_level", resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 7. Verify Priority Score Calculation
    # -------------------------------------------------------------------------
    def test_07_priority_score_calculation(self):
        """Test that calculated_priority_score strictly matches the algorithm's expected output."""
        # Query district 1's risk_tier and resource 1's available_quantity
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT risk_tier FROM districts WHERE district_id = 1;")
        d_tier = cursor.fetchone()["risk_tier"]
        cursor.execute("SELECT available_quantity FROM resources WHERE resource_id = 1;")
        r_avail = cursor.fetchone()["available_quantity"]
        conn.close()

        expected_score = calculate_request_priority_score(
            urgency_level="High",
            district_risk_tier=d_tier,
            quantity_requested=200,
            available_quantity=r_avail
        )

        payload = {
            "district_id": 1, "resource_id": 1,
            "requester_name": "Priority Tester", "requester_contact": "1234567890",
            "quantity_requested": 200, "urgency_level": "High"
        }
        resp = self.client.post("/api/resources/request", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        actual_score = resp.get_json()["request"]["calculated_priority_score"]
        self.assertEqual(actual_score, expected_score)

    # -------------------------------------------------------------------------
    # 8. Fetch Requests
    # -------------------------------------------------------------------------
    def test_08_fetch_requests(self):
        """Test GET /api/resources/requests returns all requests sorted by priority DESC."""
        resp = self.client.get("/api/resources/requests")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("requests", data)
        self.assertIn("total", data)
        self.assertGreater(data["total"], 0)

        # Check sorted DESC by priority score
        reqs = data["requests"]
        for i in range(len(reqs) - 1):
            self.assertGreaterEqual(reqs[i]["calculated_priority_score"], reqs[i+1]["calculated_priority_score"])

        # Check joins
        first = reqs[0]
        self.assertIn("district_name", first)
        self.assertIn("state_name", first)
        self.assertIn("resource_name", first)

    # -------------------------------------------------------------------------
    # 9. Filter Requests by Status
    # -------------------------------------------------------------------------
    def test_09_filter_requests_by_status(self):
        """Test GET /api/resources/requests?status=Pending filters correctly."""
        resp = self.client.get("/api/resources/requests?status=Pending")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for r in data["requests"]:
            self.assertEqual(r["status"], "Pending")

    # -------------------------------------------------------------------------
    # 10. Approve Valid Request
    # -------------------------------------------------------------------------
    def test_10_approve_valid_request(self):
        """Test PUT /api/resources/requests/<id>/status approves pending request and records reviewer."""
        # Create a fresh request
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 2, "resource_id": 2,
            "requester_name": "District Collector", "requester_contact": "9876543210",
            "quantity_requested": 1000, "urgency_level": "High"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        # Approve the request
        app_resp = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved",
            "reviewed_by": "NDRF Coordinator Sharma"
        }), content_type="application/json")
        self.assertEqual(app_resp.status_code, 200)
        data = app_resp.get_json()

        self.assertEqual(data["request"]["status"], "Approved")
        self.assertEqual(data["request"]["reviewed_by"], "NDRF Coordinator Sharma")
        self.assertIsNotNone(data["request"]["reviewed_at"])

    # -------------------------------------------------------------------------
    # 11. Verify Inventory Deduction on Approval
    # -------------------------------------------------------------------------
    def test_11_verify_inventory_deduction(self):
        """Test that approving a request atomically deducts available stock and increases allocated stock."""
        # Check resource 3 initial stock
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity, allocated_quantity FROM resources WHERE resource_id = 3;")
        init_res = dict(cursor.fetchone())
        conn.close()

        init_avail = init_res["available_quantity"]
        init_alloc = init_res["allocated_quantity"]

        # Submit request for 400 units
        qty = 400
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 3, "resource_id": 3,
            "requester_name": "Medical Officer", "requester_contact": "9876543210",
            "quantity_requested": qty, "urgency_level": "Critical"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        # Approve request
        self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved",
            "reviewed_by": "Chief Medical Director"
        }), content_type="application/json")

        # Verify stock updated in SQLite
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity, allocated_quantity FROM resources WHERE resource_id = 3;")
        after_res = dict(cursor.fetchone())
        conn.close()

        self.assertEqual(after_res["available_quantity"], init_avail - qty)
        self.assertEqual(after_res["allocated_quantity"], init_alloc + qty)

    # -------------------------------------------------------------------------
    # 12. Reject Request
    # -------------------------------------------------------------------------
    def test_12_reject_request(self):
        """Test PUT /api/resources/requests/<id>/status rejects request cleanly."""
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 4, "resource_id": 4,
            "requester_name": "Private Contractor", "requester_contact": "9876543210",
            "quantity_requested": 10, "urgency_level": "Low"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        rej_resp = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Rejected",
            "reviewed_by": "Disaster Relief Officer"
        }), content_type="application/json")
        self.assertEqual(rej_resp.status_code, 200)
        self.assertEqual(rej_resp.get_json()["request"]["status"], "Rejected")
        self.assertEqual(rej_resp.get_json()["request"]["reviewed_by"], "Disaster Relief Officer")

    # -------------------------------------------------------------------------
    # 13. Verify Rejection Does Not Deduct Stock
    # -------------------------------------------------------------------------
    def test_13_verify_rejection_does_not_deduct_stock(self):
        """Test that rejecting a request leaves available and allocated inventory unchanged."""
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity, allocated_quantity FROM resources WHERE resource_id = 4;")
        before_stock = dict(cursor.fetchone())
        conn.close()

        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 4, "resource_id": 4,
            "requester_name": "Commercial Entity", "requester_contact": "9876543210",
            "quantity_requested": 20, "urgency_level": "Low"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Rejected", "reviewed_by": "Relief Officer"
        }), content_type="application/json")

        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity, allocated_quantity FROM resources WHERE resource_id = 4;")
        after_stock = dict(cursor.fetchone())
        conn.close()

        self.assertEqual(before_stock["available_quantity"], after_stock["available_quantity"])
        self.assertEqual(before_stock["allocated_quantity"], after_stock["allocated_quantity"])

    # -------------------------------------------------------------------------
    # 14. Reject Insufficient Stock (HTTP 422)
    # -------------------------------------------------------------------------
    def test_14_reject_insufficient_stock(self):
        """Test that approving a request exceeding available stock returns HTTP 422."""
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity FROM resources WHERE resource_id = 5;")
        avail = cursor.fetchone()["available_quantity"]
        conn.close()

        # Request more than available
        excess_qty = avail + 50000
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 5, "resource_id": 5,
            "requester_name": "Mega Request", "requester_contact": "9876543210",
            "quantity_requested": excess_qty, "urgency_level": "Critical"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        # Attempt approval
        app_resp = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved", "reviewed_by": "Admin"
        }), content_type="application/json")
        self.assertEqual(app_resp.status_code, 422)
        self.assertIn("Insufficient inventory", app_resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 15. Reject Duplicate Approval (HTTP 409)
    # -------------------------------------------------------------------------
    def test_15_reject_duplicate_approval(self):
        """Test that attempting to approve an already approved request returns HTTP 409 Conflict."""
        # Create and approve request
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 6, "resource_id": 6,
            "requester_name": "Power Grid Officer", "requester_contact": "9876543210",
            "quantity_requested": 5, "urgency_level": "Medium"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        # First approval
        app_resp1 = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved", "reviewed_by": "Coordinator A"
        }), content_type="application/json")
        self.assertEqual(app_resp1.status_code, 200)

        # Second approval (duplicate)
        app_resp2 = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved", "reviewed_by": "Coordinator B"
        }), content_type="application/json")
        self.assertEqual(app_resp2.status_code, 409)
        self.assertIn("already 'Approved'", app_resp2.get_json()["error"])

    # -------------------------------------------------------------------------
    # 16. Reject Review of Already Reviewed Request (HTTP 409)
    # -------------------------------------------------------------------------
    def test_16_reject_review_of_rejected_request(self):
        """Test that attempting to approve or reject a previously rejected request returns HTTP 409 Conflict."""
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 7, "resource_id": 7,
            "requester_name": "Citizen Volunteer", "requester_contact": "9876543210",
            "quantity_requested": 2, "urgency_level": "Low"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        # Reject request
        self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Rejected", "reviewed_by": "Coordinator C"
        }), content_type="application/json")

        # Attempt to approve rejected request
        subsequent_resp = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved", "reviewed_by": "Coordinator D"
        }), content_type="application/json")
        self.assertEqual(subsequent_resp.status_code, 409)
        self.assertIn("already 'Rejected'", subsequent_resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # 17. Verify Rollback on Failed Approval
    # -------------------------------------------------------------------------
    def test_17_verify_rollback_on_failed_approval(self):
        """Test that a failed approval maintains exact database consistency without partial updates."""
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity, allocated_quantity FROM resources WHERE resource_id = 8;")
        before_stock = dict(cursor.fetchone())
        conn.close()

        # Submit request with quantity > available
        req_resp = self.client.post("/api/resources/request", data=json.dumps({
            "district_id": 8, "resource_id": 8,
            "requester_name": "Excessive Requester", "requester_contact": "9876543210",
            "quantity_requested": before_stock["available_quantity"] + 100,
            "urgency_level": "Critical"
        }), content_type="application/json")
        req_id = req_resp.get_json()["request"]["request_id"]

        # Attempt approval
        resp = self.client.put(f"/api/resources/requests/{req_id}/status", data=json.dumps({
            "status": "Approved", "reviewed_by": "Admin"
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 422)

        # Verify stock and request status unchanged
        conn = self.get_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT available_quantity, allocated_quantity FROM resources WHERE resource_id = 8;")
        after_stock = dict(cursor.fetchone())

        cursor.execute("SELECT status FROM resource_requests WHERE request_id = ?;", (req_id,))
        req_status = cursor.fetchone()["status"]
        conn.close()

        self.assertEqual(before_stock["available_quantity"], after_stock["available_quantity"])
        self.assertEqual(before_stock["allocated_quantity"], after_stock["allocated_quantity"])
        self.assertEqual(req_status, "Pending")

if __name__ == "__main__":
    unittest.main()
