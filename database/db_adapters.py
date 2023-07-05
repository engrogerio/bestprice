import pymongo
import dotenv
import os
import sqlite3
import psycopg2
from . import operations

dotenv.load_dotenv()
username = os.getenv('USERNAME')
password = os.getenv('PASSWD')

"""
this adapter should folow PEP 249 – Python Database API Specification v2.0
https://peps.python.org/pep-0249/
"""

class SqliteDatabase:
    def __init__(self, db_filepath):
        self.db = db_filepath

    def exists_key(self, key):
        with sqlite3.connect(self.db) as conn:
            return operations.exists_key(key, conn)

    def insert_header(self, data):
        with sqlite3.connect(self.db) as conn:
            return operations.insert_header(data, conn)

    def insert_item(self, header_id, data_list):
        with sqlite3.connect(self.db) as conn:
            return operations.insert_item(header_id, data_list, conn)


class MongoDatabase:
    def __init__(self):
        client = pymongo.MongoClient(f"mongodb+srv://{username}:{password}@bestprice.uizfzp3.mongodb.net/?retryWrites=true&w=majority", 
                                    ) #server_api=ServerApi('1'))
        db = client["bestprice"]
        self.collection = db["bpcollection"]

    def insert_dict(self, data:dict)-> int:

        # insert the dictionary into the collection
        result = self.collection.insert_one(data)

        # print the ID of the inserted document
        return result.inserted_id
    

class PostgresDatabase:
    def __init__(self, connection_string):
        self.db = connection_string

    def exists_key(self, key):
        with psycopg2.connect(self.db) as conn:
            return operations.exists_key(key, conn)

    def insert_header(self, data):
        with psycopg2.connect(self.db) as conn:
            return operations.insert_header(data, conn)

    def insert_item(self, header_id, data_list):
        with psycopg2.connect(self.db) as conn:
            return operations.insert_item(header_id, data_list, conn)

    def is_product_on_db(self, gtin):
        with psycopg2.connect(self.db) as conn:
            return operations.is_product_on_db(gtin, conn)
        
    def insert_product_json(self, data):
        with psycopg2.connect(self.db) as conn:
            return operations.insert_product_json(data, conn)
        
    def insert_product(self, data, product_api):
        with psycopg2.connect(self.db) as conn:
            return operations.insert_product(data, product_api, conn)