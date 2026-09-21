import pymysql.cursors
import os

def db_connection():
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "Patel@@2112"),
        database=os.environ.get("DB_NAME", "gym_management"),
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn
