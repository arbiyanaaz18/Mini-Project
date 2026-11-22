
"""
In-Memory Key-Value Store
Disaster Resource Tracker

Features:
- SET, GET, DELETE
- LRU, LFU and FIFO eviction
- JSON-based persistent storage
- Automatic recovery after restart
- Thread-safe operations
"""

import json
import os
import threading
import time
from collections import OrderedDict


class KeyValueStore:

    def __init__(
        self,
        capacity=100,
        eviction_policy="LRU",
        storage_path=None
    ):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")

        eviction_policy = eviction_policy.upper()

        if eviction_policy not in ("LRU", "LFU", "FIFO"):
            raise ValueError("Policy must be LRU, LFU or FIFO")

        self.capacity = capacity
        self.eviction_policy = eviction_policy

        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "kv_store_data.json"
        )

        self.data = OrderedDict()
        self.lock = threading.RLock()
        self.sequence = 0

        self._load_from_disk()

    def _save_to_disk(self):
        """Save the complete store using atomic file replacement."""

        directory = os.path.dirname(self.storage_path)
        os.makedirs(directory, exist_ok=True)

        temporary_path = self.storage_path + ".tmp"

        content = {
            "capacity": self.capacity,
            "eviction_policy": self.eviction_policy,
            "sequence": self.sequence,
            "entries": list(self.data.items())
        }

        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(content, file, indent=4)

        os.replace(temporary_path, self.storage_path)

    def _load_from_disk(self):
        """Recover stored entries when the application starts."""

        with self.lock:
            if not os.path.exists(self.storage_path):
                return

            try:
                with open(self.storage_path, "r", encoding="utf-8") as file:
                    content = json.load(file)

                self.sequence = int(content.get("sequence", 0))

                entries = content.get("entries", [])

                for key, metadata in entries:
                    if not isinstance(key, str):
                        continue

                    if not isinstance(metadata, dict):
                        continue

                    self.data[key] = metadata

                # Enforce the configured capacity after recovery.
                while len(self.data) > self.capacity:
                    self._evict()

            except (OSError, ValueError, TypeError, KeyError):
                raise RuntimeError(
                    "Unable to recover Key-Value Store data"
                )

    def _evict(self):
        """Remove one entry according to the selected policy."""

        if not self.data:
            return None

        if self.eviction_policy == "FIFO":
            victim = next(iter(self.data))

        elif self.eviction_policy == "LRU":
            victim = min(
                self.data,
                key=lambda key: self.data[key]["last_access"]
            )

        else:  # LFU
            victim = min(
                self.data,
                key=lambda key: (
                    self.data[key]["access_count"],
                    self.data[key]["last_access"]
                )
            )

        del self.data[victim]
        return victim

    def set(self, key, value):
        """Insert or update a key-value pair."""

        if not isinstance(key, str) or not key:
            raise ValueError("Key must be a non-empty string")

        # Check that the value can be persisted as JSON.
        json.dumps(value)

        with self.lock:
            current_time = time.time()

            if key in self.data:
                entry = self.data[key]
                entry["value"] = value
                entry["last_access"] = current_time

            else:
                if len(self.data) >= self.capacity:
                    self._evict()

                self.sequence += 1

                self.data[key] = {
                    "value": value,
                    "created_order": self.sequence,
                    "last_access": current_time,
                    "access_count": 0
                }

            self._save_to_disk()
            return True

    def get(self, key):
        """Retrieve a value and update access information."""

        with self.lock:
            if key not in self.data:
                return None

            entry = self.data[key]

            entry["access_count"] += 1
            entry["last_access"] = time.time()

            # Update order for LRU.
            if self.eviction_policy == "LRU":
                self.data.move_to_end(key)

            self._save_to_disk()

            return entry["value"]

    def delete(self, key):
        """Delete a key from the store."""

        with self.lock:
            if key not in self.data:
                return False

            del self.data[key]
            self._save_to_disk()
            return True

    def clear(self):
        """Remove all stored entries."""

        with self.lock:
            self.data.clear()
            self._save_to_disk()

    def keys(self):
        """Return all currently stored keys."""

        with self.lock:
            return list(self.data.keys())

    def stats(self):
        """Return information about the store."""

        with self.lock:
            return {
                "capacity": self.capacity,
                "current_size": len(self.data),
                "eviction_policy": self.eviction_policy,
                "remaining_capacity": self.capacity - len(self.data)
            }
