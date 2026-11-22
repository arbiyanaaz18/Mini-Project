"""
Automated Integration Tests for Phase 2 - Step 2A: Resource Inventory Management.
Covers resource fetching, filtering, creation, updating, deletion constraints,
and automatic stock status calculations.
"""

import os
import sys
import unittest
import json

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import DB_PATH, get_db_connection

class TestPhase2Step2AResources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure database exists and initialize Flask test client."""
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f"Database not found at {DB_PATH}. Run init_db.py first!")
        app.testing = True
        cls.client = app.test_client()

    # -------------------------------------------------------------------------
    # 1. Fetch Resources
    # -------------------------------------------------------------------------
    def test_01_fetch_all_resources(self):
        """Test GET /api/resources returns all seeded resources with actual stock metrics."""
        response = self.client.get("/api/resources")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertIn("resources", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 8)

        first_res = data["resources"][0]
        self.assertIn("resource_id", first_res)
        self.assertIn("resource_name", first_res)
        self.assertIn("category", first_res)
        self.assertIn("unit", first_res)
        self.assertIn("total_quantity", first_res)
        self.assertIn("available_quantity", first_res)
        self.assertIn("allocated_quantity", first_res)
        self.assertIn("status", first_res)
        self.assertIn("is_demo_data", first_res)

    # -------------------------------------------------------------------------
    # 2. Filter Resources
    # -------------------------------------------------------------------------
    def test_02_filter_resources_by_category_and_status(self):
        """Test GET /api/resources with category and status query filters."""
        # Filter by category
        cat_resp = self.client.get("/api/resources?category=Food")
        self.assertEqual(cat_resp.status_code, 200)
        cat_data = cat_resp.get_json()
        self.assertGreater(cat_data["total"], 0)
        for r in cat_data["resources"]:
            self.assertIn("food", r["category"].lower())

        # Filter by status
        stat_resp = self.client.get("/api/resources?status=Available")
        self.assertEqual(stat_resp.status_code, 200)
        stat_data = stat_resp.get_json()
        self.assertGreater(stat_data["total"], 0)
        for r in stat_data["resources"]:
            self.assertEqual(r["status"], "Available")

        # Invalid status filter
        bad_stat_resp = self.client.get("/api/resources?status=UnknownStatus")
        self.assertEqual(bad_stat_resp.status_code, 400)
        self.assertIn("error", bad_stat_resp.get_json())

    # -------------------------------------------------------------------------
    # 3. Add Valid Resource
    # -------------------------------------------------------------------------
    def test_03_add_valid_resource(self):
        """Test POST /api/resources successfully creates resource with is_demo_data = 0."""
        payload = {
            "resource_name": "Emergency Blankets",
            "category": "Shelter & Comfort",
            "unit": "Pieces",
            "total_quantity": 2000,
            "warehouse_location": "Bhopal Central Depot"
        }
        response = self.client.post(
            "/api/resources",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()

        self.assertIn("resource", data)
        res = data["resource"]
        self.assertEqual(res["resource_name"], "Emergency Blankets")
        self.assertEqual(res["total_quantity"], 2000)
        self.assertEqual(res["available_quantity"], 2000)
        self.assertEqual(res["allocated_quantity"], 0)
        self.assertEqual(res["is_demo_data"], 0)
        self.assertEqual(res["status"], "Available")

        # Clean up created resource
        self.client.delete(f"/api/resources/{res['resource_id']}")

    # -------------------------------------------------------------------------
    # 4. Reject Missing Fields
    # -------------------------------------------------------------------------
    def test_04_reject_missing_fields(self):
        """Test POST /api/resources rejects payloads missing required fields."""
        incomplete_payload = {
            "resource_name": "Incomplete Resource",
            "total_quantity": 500
            # missing category, unit, warehouse_location
        }
        response = self.client.post(
            "/api/resources",
            data=json.dumps(incomplete_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    # -------------------------------------------------------------------------
    # 5. Reject Negative Quantities
    # -------------------------------------------------------------------------
    def test_05_reject_negative_quantities(self):
        """Test POST /api/resources rejects negative total or available quantities."""
        negative_payload = {
            "resource_name": "Negative Stock Resource",
            "category": "Medical Supplies",
            "unit": "Boxes",
            "total_quantity": -50,
            "warehouse_location": "Nagpur Hub"
        }
        response = self.client.post(
            "/api/resources",
            data=json.dumps(negative_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

        # Test available > total
        exceed_payload = {
            "resource_name": "Exceeding Stock Resource",
            "category": "Medical Supplies",
            "unit": "Boxes",
            "total_quantity": 100,
            "available_quantity": 150,
            "warehouse_location": "Nagpur Hub"
        }
        response2 = self.client.post(
            "/api/resources",
            data=json.dumps(exceed_payload),
            content_type="application/json"
        )
        self.assertEqual(response2.status_code, 400)
        self.assertIn("error", response2.get_json())

    # -------------------------------------------------------------------------
    # 6. Update Resource
    # -------------------------------------------------------------------------
    def test_06_update_resource(self):
        """Test PUT /api/resources/<id> updates attributes and maintains quantity consistency."""
        # Create temporary resource
        create_resp = self.client.post(
            "/api/resources",
            data=json.dumps({
                "resource_name": "Temporary Test Kits",
                "category": "Testing",
                "unit": "Kits",
                "total_quantity": 1000,
                "warehouse_location": "Warehouse A"
            }),
            content_type="application/json"
        )
        res_id = create_resp.get_json()["resource"]["resource_id"]

        # Update available_quantity to 200 (20% of 1000 -> Low Stock)
        update_payload = {
            "available_quantity": 200,
            "warehouse_location": "Warehouse B"
        }
        put_resp = self.client.put(
            f"/api/resources/{res_id}",
            data=json.dumps(update_payload),
            content_type="application/json"
        )
        self.assertEqual(put_resp.status_code, 200)
        updated = put_resp.get_json()["resource"]
        self.assertEqual(updated["available_quantity"], 200)
        self.assertEqual(updated["allocated_quantity"], 800)
        self.assertEqual(updated["warehouse_location"], "Warehouse B")
        self.assertEqual(updated["status"], "Low Stock")

        # Clean up
        self.client.delete(f"/api/resources/{res_id}")

    # -------------------------------------------------------------------------
    # 7. Reject Invalid Resource ID
    # -------------------------------------------------------------------------
    def test_07_reject_invalid_resource_id(self):
        """Test PUT and DELETE return 404 Not Found for non-existent resource ID."""
        put_resp = self.client.put(
            "/api/resources/999999",
            data=json.dumps({"warehouse_location": "Nowhere"}),
            content_type="application/json"
        )
        self.assertEqual(put_resp.status_code, 404)
        self.assertIn("error", put_resp.get_json())

        del_resp = self.client.delete("/api/resources/999999")
        self.assertEqual(del_resp.status_code, 404)
        self.assertIn("error", del_resp.get_json())

    # -------------------------------------------------------------------------
    # 8. Delete Unused Resource
    # -------------------------------------------------------------------------
    def test_08_delete_unused_resource(self):
        """Test DELETE /api/resources/<id> successfully deletes unreferenced resource."""
        create_resp = self.client.post(
            "/api/resources",
            data=json.dumps({
                "resource_name": "Disposable Masks",
                "category": "Medical Supplies",
                "unit": "Boxes",
                "total_quantity": 500,
                "warehouse_location": "Hub D"
            }),
            content_type="application/json"
        )
        res_id = create_resp.get_json()["resource"]["resource_id"]

        # Delete resource
        del_resp = self.client.delete(f"/api/resources/{res_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn("deleted successfully", del_resp.get_json()["message"])

        # Subsequent delete returns 404
        del_resp2 = self.client.delete(f"/api/resources/{res_id}")
        self.assertEqual(del_resp2.status_code, 404)

    # -------------------------------------------------------------------------
    # 9. Prevent Deleting Referenced Resources
    # -------------------------------------------------------------------------
    def test_09_prevent_deleting_referenced_resource(self):
        """Test DELETE /api/resources/<id> returns 409 if referenced by a resource_request."""
        # Create resource
        create_resp = self.client.post(
            "/api/resources",
            data=json.dumps({
                "resource_name": "Referenced Resource",
                "category": "Rescue",
                "unit": "Units",
                "total_quantity": 100,
                "warehouse_location": "Base Z"
            }),
            content_type="application/json"
        )
        res_id = create_resp.get_json()["resource"]["resource_id"]

        # Insert a temporary referencing request directly into SQLite
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resource_requests (
                district_id, resource_id, requester_name, requester_contact,
                quantity_requested, urgency_level, status
            ) VALUES (1, ?, 'Test Officer', '9999999999', 10, 'High', 'Pending');
        """, (res_id,))
        conn.commit()
        req_id = cursor.lastrowid
        conn.close()

        # Attempt to delete referenced resource
        del_resp = self.client.delete(f"/api/resources/{res_id}")
        self.assertEqual(del_resp.status_code, 409)
        self.assertIn("referenced by", del_resp.get_json()["error"])

        # Clean up referencing request and resource
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resource_requests WHERE request_id = ?;", (req_id,))
        cursor.execute("DELETE FROM resources WHERE resource_id = ?;", (res_id,))
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # 10. Verify Automatic Stock Status
    # -------------------------------------------------------------------------
    def test_10_automatic_stock_status_thresholds(self):
        """
        Test automatic calculation of stock status:
        - Available: > 25% remaining
        - Low Stock: 10% to 25% remaining
        - Critical: < 10% remaining or 0
        """
        # Test 1: Available (500/1000 = 50%)
        p1 = {
            "resource_name": "Status Test 1",
            "category": "General",
            "unit": "Units",
            "total_quantity": 1000,
            "available_quantity": 500,
            "warehouse_location": "Depot 1"
        }
        r1 = self.client.post("/api/resources", data=json.dumps(p1), content_type="application/json")
        res1 = r1.get_json()["resource"]
        self.assertEqual(res1["status"], "Available")

        # Test 2: Low Stock (200/1000 = 20%)
        p2 = {
            "resource_name": "Status Test 2",
            "category": "General",
            "unit": "Units",
            "total_quantity": 1000,
            "available_quantity": 200,
            "warehouse_location": "Depot 2"
        }
        r2 = self.client.post("/api/resources", data=json.dumps(p2), content_type="application/json")
        res2 = r2.get_json()["resource"]
        self.assertEqual(res2["status"], "Low Stock")

        # Test 3: Critical (50/1000 = 5%)
        p3 = {
            "resource_name": "Status Test 3",
            "category": "General",
            "unit": "Units",
            "total_quantity": 1000,
            "available_quantity": 50,
            "warehouse_location": "Depot 3"
        }
        r3 = self.client.post("/api/resources", data=json.dumps(p3), content_type="application/json")
        res3 = r3.get_json()["resource"]
        self.assertEqual(res3["status"], "Critical")

        # Test 4: Critical when zero (0/1000)
        p4 = {
            "resource_name": "Status Test 4",
            "category": "General",
            "unit": "Units",
            "total_quantity": 1000,
            "available_quantity": 0,
            "warehouse_location": "Depot 4"
        }
        r4 = self.client.post("/api/resources", data=json.dumps(p4), content_type="application/json")
        res4 = r4.get_json()["resource"]
        self.assertEqual(res4["status"], "Critical")

        # Clean up
        for item in [res1, res2, res3, res4]:
            self.client.delete(f"/api/resources/{item['resource_id']}")

if __name__ == "__main__":
    unittest.main()
