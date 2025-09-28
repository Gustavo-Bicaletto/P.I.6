import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://pi6time5:remanejamento123@resumai.hlueghe.mongodb.net/")
MONGO_DB  = os.getenv("MONGO_DB", "resumAI")

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[MONGO_DB]
    return _db
