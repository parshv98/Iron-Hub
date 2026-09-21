import os
import pymysql
from localhost import db_connection

def init_db():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            # Read and execute schema
            print("Running schema.sql...")
            with open('schema.sql', 'r') as f:
                sql_script = f.read()
                # PyMySQL doesn't support executing multiple statements natively well without tweaks,
                # but connections might if client_flag is set. 
                # For safety, simplistic split:
                for statement in sql_script.split(';'):
                    if statement.strip():
                        try:
                            cur.execute(statement)
                        except Exception as e:
                            print(f"Statement failed: {e}")
            
            print("Running new_tables.sql...")
            with open('new_tables.sql', 'r') as f:
                sql_script = f.read()
                for statement in sql_script.split(';'):
                    if statement.strip():
                        try:
                            cur.execute(statement)
                        except Exception as e:
                            print(f"Statement failed: {e}")
                            
        conn.commit()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize database: {e}")

if __name__ == "__main__":
    print(f"Targeting host: {os.environ.get('DB_HOST', 'localhost')}")
    init_db()
