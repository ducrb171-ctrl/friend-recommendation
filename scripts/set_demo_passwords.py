
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase
from werkzeug.security import generate_password_hash

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "socialnetwork")

if not password:
    raise RuntimeError("Chua khai bao NEO4J_PASSWORD trong file .env")

driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    # Chi dung cho tai khoan mau trong bai tap.
    demo_hash = generate_password_hash("123456")

    with driver.session(database=database) as session:
        result = session.run("""
            MATCH (p:Person)
            WHERE p.id STARTS WITH 'user_'
            SET p.passwordHash = $passwordHash
            RETURN count(p) AS updated
        """, passwordHash=demo_hash)

        print("So tai khoan mau da cap nhat:", result.single()["updated"])
finally:
    driver.close()
