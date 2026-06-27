import oracledb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv


# Oracle Thin mode setup (no Oracle Client required)
# oracledb.version = "8.3.0" 

load_dotenv()

try:
    # oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_23_26")
    oracledb.init_oracle_client(lib_dir=r"C:\\instantclient_23_0")
    
    print("Thick mode initialized.")
except Exception as err:
    print("Error initializing Oracle Client:", err)


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASS")
DB_DSN = os.getenv("DB_DSN") # e.g., localhost:1521/XEPDB1

# SQLAlchemy Oracle Connection String
SQLALCHEMY_DATABASE_URL = f"oracle+oracledb://{DB_USER}:{DB_PASSWORD}@{DB_DSN}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




# import oracledb
# import os
# from dotenv import load_dotenv


# load_dotenv()
# oracledb.init_oracle_client(lib_dir=r"C:\instantclient_23_0")


# # Create a pool to manage multiple connections efficiently
# pool = oracledb.create_pool(
#     user=os.getenv("DB_USER"),
#     password=os.getenv("DB_PASS"),
#     dsn=os.getenv("DB_DSN"),
#     min=2,
#     max=10,
#     increment=1
# )

# # Test the connection
# def test_connection():
#     try:
#         conn = pool.acquire()
#         print("Successfully connected to Oracle!")
#         conn.close()
#     except Exception as e:
#         print(f"Connection failed: {e}")

# if __name__ == "__main__":
#     test_connection()
    

# For FastAPI dependency injection (for Production use, consider using asyncpg or another async library)    
# def get_db():
#     conn = pool.acquire()
#     try:
#         yield conn
#     finally:
#         pool.release(conn)