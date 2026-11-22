\# Disaster Resource Tracker

\# DBMS Implementation Documentation



\## 1. Introduction



The Disaster Resource Tracker uses SQLite as its primary relational database and a custom in-memory Key-Value Store for resource caching.



The DBMS implementation improves data organization, retrieval performance, inventory consistency, and data persistence.



\## 2. Database Architecture



The system consists of two storage components:



1\. SQLite relational database – stores permanent application data.

2\. Custom Key-Value Store – caches frequently requested resource information.



The Flask backend connects these components and provides REST API operations.



\## 3. Key-Value Store



The project implements a custom Key-Value Store in `backend/kv\_store.py`.



It supports the following operations:



\- SET: Insert or update a key-value pair.

\- GET: Retrieve a value using its key.

\- DELETE: Remove a key-value pair.

\- CLEAR: Remove all entries.

\- KEYS: Return all stored keys.

\- STATS: Display storage statistics.



\## 4. Cache Eviction Policies



The Key-Value Store supports three eviction policies.



\### 4.1 FIFO (First In First Out)



FIFO removes the oldest inserted entry when the storage capacity is reached.



\### 4.2 LRU (Least Recently Used)



LRU removes the entry that has not been accessed for the longest time.



The application currently uses LRU with a capacity of 100 entries.



\### 4.3 LFU (Least Frequently Used)



LFU removes the entry with the lowest access frequency. When frequencies are equal, the least recently accessed entry is selected.



\## 5. Data Persistence and Recovery



The Key-Value Store saves its contents in JSON format.



The implementation uses:



\- JSON serialization.

\- Temporary file creation.

\- Atomic file replacement using `os.replace()`.

\- Automatic loading of saved entries during initialization.



This allows stored cache entries to be recovered when the application restarts.



Note: This implementation uses JSON-based persistence and does not claim to implement Write-Ahead Logging (WAL).



\## 6. Thread Safety



The implementation uses Python's `threading.RLock()` to protect shared Key-Value Store operations.



This helps prevent concurrent threads from modifying shared cache data simultaneously.



\## 7. Resource Cache Implementation



The resource-list API uses the Key-Value Store to improve repeated GET request performance.



The implementation is located in `backend/app.py`.



The cache uses unique keys based on resource filter combinations.



\### Cache Hit



When a requested key exists in the cache, the cached response is returned.



\### Cache Miss



When the requested key does not exist, resource information is retrieved from SQLite and stored in the cache.



\## 8. Cache Invalidation



Cache invalidation ensures that outdated resource information is not returned after inventory changes.



The application invalidates resource-list cache entries after:



1\. Adding a resource.

2\. Updating a resource.

3\. Deleting a resource.

4\. Approving a resource request and allocating inventory.



The `invalidate\_resource\_cache()` function removes keys beginning with `resources:`.



\## 9. Database Integrity



The SQLite database uses relational constraints, including:



\- Primary keys.

\- Foreign keys.

\- NOT NULL constraints.

\- UNIQUE constraints.

\- CHECK constraints.



These constraints help maintain valid and consistent database records.



\## 10. Testing and Verification



Automated tests are implemented using Python's unittest framework.



The Key-Value Store tests cover:



\- SET and GET operations.

\- DELETE operation.

\- FIFO eviction.

\- LRU eviction.

\- LFU eviction.

\- Persistence and recovery.

\- Capacity enforcement.



The resource cache tests cover:



\- Cache miss and storage.

\- Repeated GET requests.

\- Different filter combinations.

\- ADD invalidation.

\- UPDATE invalidation.

\- DELETE invalidation.

\- APPROVAL invalidation.



The complete backend test suite was executed successfully.



\*\*Latest verification result: 81 tests passed, with 0 failures.\*\*



\## 11. Conclusion



The Disaster Resource Tracker combines SQLite relational storage with a custom persistent Key-Value Store.



The implementation supports multiple eviction policies, JSON-based persistence, automatic recovery, thread-safe operations, and resource cache invalidation.



These features improve data management, retrieval efficiency, and inventory consistency.

