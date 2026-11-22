import os
import sys
import unittest

# Allow imports from the backend directory
BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, cache


class TestResourceCache(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        # Start every test with a clean cache
        cache.clear()

    def tearDown(self):
        # Clean up after every test
        cache.clear()

    def test_01_cache_miss_stores_resource_result(self):
        """First GET should fetch from DB and store the result in cache."""

        response = self.client.get("/api/resources")

        self.assertEqual(response.status_code, 200)

        resource_cache_keys = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(resource_cache_keys), 1)

    def test_02_second_get_uses_cache(self):
        """Second identical GET should use the existing cached result."""

        first_response = self.client.get("/api/resources")
        self.assertEqual(first_response.status_code, 200)

        keys_after_first = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(keys_after_first), 1)

        second_response = self.client.get("/api/resources")
        self.assertEqual(second_response.status_code, 200)

        keys_after_second = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(keys_after_second), 1)

        self.assertEqual(
            first_response.get_json(),
            second_response.get_json()
        )

    def test_03_different_filters_create_different_cache_keys(self):
        """Different resource filters should use different cache keys."""

        response_all = self.client.get("/api/resources")
        self.assertEqual(response_all.status_code, 200)

        response_category = self.client.get(
            "/api/resources?category=Food"
        )
        self.assertEqual(response_category.status_code, 200)

        resource_cache_keys = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertGreaterEqual(len(resource_cache_keys), 2)

    def test_04_add_resource_invalidates_cache(self):
        """Adding a resource must remove old resource-list cache entries."""

        response = self.client.get("/api/resources")
        self.assertEqual(response.status_code, 200)

        before_add = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertGreaterEqual(len(before_add), 1)

        payload = {
            "resource_name": "Cache Test Resource",
            "category": "Food",
            "unit": "units",
            "total_quantity": 100,
            "available_quantity": 100,
            "warehouse_location": "Cache Test Warehouse"
        }

        add_response = self.client.post(
            "/api/resources",
            json=payload
        )

        self.assertEqual(add_response.status_code, 201)

        after_add = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(after_add), 0)

        resource_id = add_response.get_json()["resource"]["resource_id"]

        # Clean up test resource
        delete_response = self.client.delete(
            f"/api/resources/{resource_id}"
        )

        self.assertIn(delete_response.status_code, [200, 204])

    def test_05_update_resource_invalidates_cache(self):
        """Updating a resource must remove old resource-list cache entries."""

        response = self.client.get("/api/resources")
        self.assertEqual(response.status_code, 200)

        resource = response.get_json()["resources"][0]
        resource_id = resource["resource_id"]

        cached_keys_before = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertGreaterEqual(len(cached_keys_before), 1)

        update_response = self.client.put(
            f"/api/resources/{resource_id}",
            json={
                "resource_name": resource["resource_name"],
                "category": resource["category"],
                "unit": resource["unit"],
                "total_quantity": resource["total_quantity"],
                "available_quantity": resource["available_quantity"],
                "warehouse_location": resource["warehouse_location"]
            }
        )

        self.assertEqual(update_response.status_code, 200)

        cached_keys_after = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(cached_keys_after), 0)

    def test_06_delete_resource_invalidates_cache(self):
        """Deleting a resource must remove old resource-list cache entries."""

    def test_07_approval_invalidates_cache(self):
        """Approving a resource request must clear resource-list cache entries."""

        # Fetch resources and find one with available stock
        response = self.client.get("/api/resources")
        self.assertEqual(response.status_code, 200)

        resources = response.get_json()["resources"]

        resource = next(
            (r for r in resources if r["available_quantity"] >= 1),
            None
        )

        self.assertIsNotNone(resource, "No resource has available stock.")

        # Create a pending request
        request_response = self.client.post(
            "/api/resources/request",
            json={
                "district_id": 1,
                "resource_id": resource["resource_id"],
                "requester_name": "Cache Approval Tester",
                "requester_contact": "9876543210",
                "quantity_requested": 1,
                "urgency_level": "High"
            }
        )

        self.assertEqual(request_response.status_code, 201)

        request_id = request_response.get_json()["request"]["request_id"]

        # Populate resource cache
        cache_response = self.client.get("/api/resources")
        self.assertEqual(cache_response.status_code, 200)

        cached_keys_before = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertGreaterEqual(len(cached_keys_before), 1)

        # Approve the pending request
        approval_response = self.client.put(
            f"/api/resources/requests/{request_id}/status",
            json={
                "status": "Approved",
                "reviewed_by": "Cache Test Coordinator"
            }
        )

        self.assertEqual(approval_response.status_code, 200)

        # Verify resource cache was invalidated
        cached_keys_after = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(cached_keys_after), 0)


        create_response = self.client.post(
            "/api/resources",
            json={
                "resource_name": "Cache Delete Test",
                "category": "Medical",
                "unit": "units",
                "total_quantity": 50,
                "available_quantity": 50,
                "warehouse_location": "Cache Delete Warehouse"
            }
        )

        self.assertEqual(create_response.status_code, 201)

        resource_id = create_response.get_json()["resource"]["resource_id"]

        # Create a resource-list cache entry
        get_response = self.client.get("/api/resources")
        self.assertEqual(get_response.status_code, 200)

        cached_keys_before = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertGreaterEqual(len(cached_keys_before), 1)

        delete_response = self.client.delete(
            f"/api/resources/{resource_id}"
        )

        self.assertIn(delete_response.status_code, [200, 204])

        cached_keys_after = [
            key for key in cache.keys()
            if key.startswith("resources:")
        ]

        self.assertEqual(len(cached_keys_after), 0)


if __name__ == "__main__":
    unittest.main()