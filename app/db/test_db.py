import os
from dotenv import load_dotenv
import oracledb

load_dotenv()

# DEBUG: Let's see what is being loaded
user = os.getenv("DB_USER")
dsn = os.getenv("DB_DSN")
pw = os.getenv("DB_PASSWORD")

print(f"--- Environment Check ---")
print(f"DB_USER: {user}")
print(f"DB_DSN: {dsn}")
print(f"DB_PASSWORD Loaded: {'Yes' if pw else 'No (EMPTY!)'}")
print(f"-------------------------")

if not user or not pw:
    print("CRITICAL: Environment variables are missing. Check your .env file location.")
else:
    # ... rest of your connection code ...
    try:
        oracledb.init_oracle_client(lib_dir=r"/opt/oracle/instantclient_23_26")
        conn = oracledb.connect(user=user, password=pw, dsn=dsn)
        print("Connected successfully!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")