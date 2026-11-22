
import os
import tempfile
import unittest

from backend.kv_store import KeyValueStore


class TestKeyValueStore(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name, "test_store.json"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_set_and_get(self):
        store = KeyValueStore(5, "LRU", self.path)
        store.set("name", "Priya")
        self.assertEqual(store.get("name"), "Priya")

    def test_delete(self):
        store = KeyValueStore(5, "LRU", self.path)
        store.set("name", "Priya")
        self.assertTrue(store.delete("name"))
        self.assertIsNone(store.get("name"))

    def test_lru_eviction(self):
        store = KeyValueStore(2, "LRU", self.path)
        store.set("A", 1)
        store.set("B", 2)
        store.get("A")
        store.set("C", 3)

        self.assertIsNone(store.get("B"))
        self.assertEqual(store.get("A"), 1)
        self.assertEqual(store.get("C"), 3)

    def test_fifo_eviction(self):
        store = KeyValueStore(2, "FIFO", self.path)
        store.set("A", 1)
        store.set("B", 2)
        store.get("A")
        store.set("C", 3)

        self.assertIsNone(store.get("A"))
        self.assertEqual(store.get("B"), 2)

    def test_lfu_eviction(self):
        store = KeyValueStore(2, "LFU", self.path)
        store.set("A", 1)
        store.set("B", 2)

        store.get("A")
        store.get("A")

        store.set("C", 3)

        self.assertIsNone(store.get("B"))
        self.assertEqual(store.get("A"), 1)

    def test_persistence_and_recovery(self):
        store1 = KeyValueStore(5, "LRU", self.path)
        store1.set("incident", "Flood")
        store1.set("district", "Dakshina Kannada")

        # Simulate application restart
        store2 = KeyValueStore(5, "LRU", self.path)

        self.assertEqual(store2.get("incident"), "Flood")
        self.assertEqual(
            store2.get("district"), "Dakshina Kannada"
        )

    def test_capacity(self):
        store = KeyValueStore(2, "LRU", self.path)

        store.set("A", 1)
        store.set("B", 2)
        store.set("C", 3)

        self.assertEqual(store.stats()["current_size"], 2)


if __name__ == "__main__":
    unittest.main()
