from pymongo import MongoClient

# Start mongoDB server: brew services start mongodb-community@7.0
# Stop mongoDB server: brew services stop mongodb-community@7.0

def connect():
    try:
        client = MongoClient("mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.1.3")

        return client
    except Exception as e:
        return e