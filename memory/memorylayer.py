import time
import datetime
from pymongo import MongoClient


class MemoryLayer:

    def __init__(self,
                 mongo_uri="mongodb://localhost:27017/",
                 mongo_db="finagent"):

        # In-memory cache
        self.cache = {}
        self.logs = []

        # MongoDB setup
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[mongo_db]
        self.collection = self.db["agent_memory"]

    # -----------------------------------
    # MAIN STORE FUNCTION
    # -----------------------------------
    def store(self, key, value, ttl=None, data_type="generic"):

        expire_at = time.time() + ttl if ttl else None

        # 1️⃣ Store in in-memory cache
        self.cache[key] = {
            "value": value,
            "expire_at": expire_at,
            "data_type": data_type
        }

        # 2️⃣ Store in MongoDB
        self._store_mongodb(key, value, data_type)

        self.logs.append({
            "event": "STORE",
            "key": key,
            "data_type": data_type,
            "timestamp": str(datetime.datetime.utcnow())
        })

    # -----------------------------------
    # MONGODB STORAGE FUNCTION
    # -----------------------------------
    def _store_mongodb(self, key, value, data_type):

        document = {
            "key": key,
            "value": value,
            "data_type": data_type,
            "updated_at": datetime.datetime.utcnow()
        }

        # Upsert (update if exists, insert if not)
        self.collection.update_one(
            {"key": key},
            {"$set": document},
            upsert=True
        )

    # -----------------------------------
    # RETRIEVE FUNCTION
    # -----------------------------------
    def retrieve(self, key):

        # 1️⃣ Check in-memory
        item = self.cache.get(key)

        if item:
            if item["expire_at"] and time.time() > item["expire_at"]:
                del self.cache[key]
                self.log_event(f"EXPIRED:{key}")
            else:
                self.log_event(f"HIT_MEMORY:{key}")
                return item["value"]

        # 2️⃣ Fallback to MongoDB
        doc = self.collection.find_one({"key": key})
        if doc:
            self.log_event(f"HIT_MONGO:{key}")
            return doc["value"]

        self.log_event(f"MISS:{key}")
        return None

    # -----------------------------------
    # LOGGING
    # -----------------------------------
    def log_event(self, message):
        self.logs.append({
            "event": message,
            "timestamp": str(datetime.datetime.utcnow())
        })

    def get_logs(self):
        return self.logs