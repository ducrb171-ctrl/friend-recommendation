import os
import random

from dotenv import load_dotenv
from faker import Faker
from neo4j import GraphDatabase

load_dotenv()
fake = Faker("vi_VN")
random.seed(42)
Faker.seed(42)

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (
    os.getenv("NEO4J_USER", "neo4j"),
    os.getenv("NEO4J_PASSWORD", "password123")
)
DATABASE = os.getenv("NEO4J_DATABASE", "socialnetwork")

TOTAL_USERS = 80
TOTAL_FRIEND_PAIRS = 130
TOTAL_FOLLOWS = 130

def generate_dummy_data():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    try:
        driver.verify_connectivity()

        users = []
        for i in range(1, TOTAL_USERS + 1):
            uid = f"user_{i}"
            users.append({
                "id": uid,
                "name": fake.name(),
                "email": f"{uid}@example.com",
                "bio": fake.sentence(),
            })

        all_pairs = [
            (users[i]["id"], users[j]["id"])
            for i in range(TOTAL_USERS)
            for j in range(i + 1, TOTAL_USERS)
        ]
        random.shuffle(all_pairs)

        friend_pairs = all_pairs[:TOTAL_FRIEND_PAIRS]
        remaining_pairs = all_pairs[TOTAL_FRIEND_PAIRS:]
        random.shuffle(remaining_pairs)
        follow_pairs = remaining_pairs[:TOTAL_FOLLOWS]

        with driver.session(database=DATABASE) as session:
            print("Dang xoa du lieu mau cu...")
            session.run("""
                MATCH (n)
                WHERE n.id STARTS WITH 'user_'
                   OR n.id STARTS WITH 'post_'
                DETACH DELETE n
            """).consume()

            print("Dang tao nguoi dung...")
            session.run("""
                UNWIND $users AS row
                CREATE (:Person {
                    id: row.id,
                    name: row.name,
                    username: row.id,
                    email: row.email,
                    bio: row.bio,
                    createdAt: datetime()
                })
            """, users=users).consume()

            print("Dang tao cac cap ban be (xu ly 2 chieu)...")
            session.run("""
                UNWIND $pairs AS pair
                MATCH (a:Person {id: pair[0]})
                MATCH (b:Person {id: pair[1]})
                MERGE (a)-[:FRIEND {since: datetime()}]->(b)
                MERGE (b)-[:FRIEND {since: datetime()}]->(a)
            """, pairs=[list(pair) for pair in friend_pairs]).consume()

            print("Dang tao quan he theo doi...")
            session.run("""
                UNWIND $pairs AS pair
                MATCH (a:Person {id: pair[0]})
                MATCH (b:Person {id: pair[1]})
                CREATE (a)-[:FOLLOW {createdAt: datetime()}]->(b)
            """, pairs=[list(pair) for pair in follow_pairs]).consume()

            print("Dang tao bai viet...")
            posts = [
                {
                    "id": f"post_{i}",
                    "authorId": users[i - 1]["id"],
                    "content": f"Bai viet mau so {i}: {fake.sentence()}",
                }
                for i in range(1, TOTAL_USERS + 1)
            ]

            session.run("""
                UNWIND $posts AS row
                MATCH (author:Person {id: row.authorId})
                CREATE (post:Post {
                    id: row.id,
                    content: row.content,
                    createdAt: datetime()
                })
                CREATE (author)-[:CREATED]->(post)
            """, posts=posts).consume()

            print("Dang tao luot thich (LIKES)...")
            session.run("""
                MATCH (u:Person), (p:Post)
                WITH u, p, rand() AS r
                WHERE r < 0.05
                MERGE (u)-[:LIKES {createdAt: datetime()}]->(p)
            """).consume()

            print("\n=== KET QUA ===")
            result = session.run("MATCH (p:Person) RETURN count(p) AS total")
            print("Tong Person:", result.single()["total"])

            result = session.run("MATCH (p:Post) RETURN count(p) AS total")
            print("Tong Post:", result.single()["total"])

            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(r) AS total
                ORDER BY type
            """)
            for record in result:
                print(f"{record['type']}: {record['total']}")

            print("\nNAP DU LIEU MAU HOAN TAT!")

    finally:
        driver.close()

if __name__ == "__main__":
    generate_dummy_data()