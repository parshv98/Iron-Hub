import pymysql.cursors
import os

def db_connection():
    conn_args = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", 3306)),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD", "Patel@@2112"),
        "database": os.environ.get("DB_NAME", "gym_management"),
        "cursorclass": pymysql.cursors.DictCursor
    }
    
    if os.environ.get("DB_SSL_MODE") == "REQUIRED":
        # Minimal secure transport requirement for some providers like Aiven
        conn_args["ssl"] = {} 
        
    return pymysql.connect(**conn_args)
