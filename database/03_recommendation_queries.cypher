// ============================================================
// FRIEND RECOMMENDATION - CYPHER QUERIES
// File: database/03_recommendation_queries.cypher
//
// Data model:
// (:Person {id, name, ...})
// (:Person)-[:FRIEND {since}]->(:Person)
// (:Person)-[:FOLLOW {createdAt}]->(:Person)
// (:Person)-[:CREATED]->(:Post)
//
// FRIEND is stored as one directed relationship per pair by seed_data.py.
// Queries use undirected patterns (-[:FRIEND]-) so friendship works both ways.
//
// IMPORTANT:
// - Run each query block separately in Neo4j Browser.
// - Replace the sample IDs or supply parameters as indicated.
// - For parameterized queries, use :param userId => 'user_1' in Neo4j Browser.
// ============================================================


// ------------------------------------------------------------
// 0. OPTIONAL: Set parameters in Neo4j Browser
// Run these lines separately before parameterized queries.
// ------------------------------------------------------------
// :param userId => 'user_1'
// :param userA => 'user_1'
// :param userB => 'user_2'


// ------------------------------------------------------------
// 1. LIST DIRECT FRIENDS
// Requirement: retrieve the current user's direct friends.
// ------------------------------------------------------------
MATCH (me:Person {id: 'user_1'})-[:FRIEND]-(friend:Person)
RETURN friend.id AS friendId,
       friend.name AS friendName
ORDER BY friendName;


// ------------------------------------------------------------
// 2. FRIEND-OF-A-FRIEND (FoF), 2 HOPS
// Excludes the user themself, existing friends, and users the
// current user already follows.
// Ranks candidates by number of distinct mutual friends.
// ------------------------------------------------------------
MATCH (me:Person {id: $userId})-[:FRIEND]-(friend:Person)
      -[:FRIEND]-(candidate:Person)
WHERE candidate <> me
  AND NOT (me)-[:FRIEND]-(candidate)
  AND NOT (me)-[:FOLLOW]->(candidate)
WITH candidate, count(DISTINCT friend) AS mutualFriends
WHERE mutualFriends > 0
RETURN candidate.id AS candidateId,
       candidate.name AS candidateName,
       mutualFriends
ORDER BY mutualFriends DESC, candidateName ASC
LIMIT 10;


// ------------------------------------------------------------
// 3. FoF, 2 HOPS, WITH MUTUAL FRIEND NAMES
// Useful for the UI: "You have N mutual friends".
// ------------------------------------------------------------
MATCH (me:Person {id: $userId})-[:FRIEND]-(friend:Person)
      -[:FRIEND]-(candidate:Person)
WHERE candidate <> me
  AND NOT (me)-[:FRIEND]-(candidate)
  AND NOT (me)-[:FOLLOW]->(candidate)
WITH candidate, collect(DISTINCT friend.name) AS mutualFriendNames
WITH candidate, mutualFriendNames, size(mutualFriendNames) AS mutualFriends
WHERE mutualFriends > 0
RETURN candidate.id AS candidateId,
       candidate.name AS candidateName,
       mutualFriends,
       mutualFriendNames
ORDER BY mutualFriends DESC, candidateName ASC
LIMIT 10;


// ------------------------------------------------------------
// 4. FoF, 3 HOPS
// Finds candidates three FRIEND relationships away.
// intermediatePeople counts distinct second-hop nodes, NOT
// direct mutual friends. This is a separate score from 2-hop FoF.
// ------------------------------------------------------------
MATCH (me:Person {id: $userId})-[:FRIEND]-(f1:Person)
      -[:FRIEND]-(f2:Person)
      -[:FRIEND]-(candidate:Person)
WHERE candidate <> me
  AND NOT (me)-[:FRIEND]-(candidate)
  AND NOT (me)-[:FOLLOW]->(candidate)
WITH candidate, count(DISTINCT f2) AS intermediatePeople
WHERE intermediatePeople > 0
RETURN candidate.id AS candidateId,
       candidate.name AS candidateName,
       intermediatePeople
ORDER BY intermediatePeople DESC, candidateName ASC
LIMIT 10;


// ------------------------------------------------------------
// 5. FIND MUTUAL FRIENDS BETWEEN TWO USERS
// Set $userA and $userB in Neo4j Browser, or replace with IDs.
// ------------------------------------------------------------
MATCH (a:Person {id: $userA})-[:FRIEND]-(mutual:Person)
      -[:FRIEND]-(b:Person {id: $userB})
WHERE a <> b
RETURN DISTINCT mutual.id AS mutualId,
       mutual.name AS mutualName
ORDER BY mutualName;


// ------------------------------------------------------------
// 6. COUNT MUTUAL FRIENDS BETWEEN TWO USERS
// ------------------------------------------------------------
MATCH (a:Person {id: $userA})-[:FRIEND]-(mutual:Person)
      -[:FRIEND]-(b:Person {id: $userB})
WHERE a <> b
RETURN count(DISTINCT mutual) AS totalMutualFriends;


// ------------------------------------------------------------
// 7. RECOMMEND BY FOLLOW NETWORK
// Candidate is followed by people whom the current user follows.
// Excludes self, existing friends, and people already followed.
// commonFollowSources = number of shared follow sources.
// ------------------------------------------------------------
MATCH (me:Person {id: $userId})-[:FOLLOW]->(followed:Person)
      -[:FOLLOW]->(candidate:Person)
WHERE candidate <> me
  AND NOT (me)-[:FOLLOW]->(candidate)
  AND NOT (me)-[:FRIEND]-(candidate)
WITH candidate, count(DISTINCT followed) AS commonFollowSources
WHERE commonFollowSources > 0
RETURN candidate.id AS candidateId,
       candidate.name AS candidateName,
       commonFollowSources
ORDER BY commonFollowSources DESC, candidateName ASC
LIMIT 10;


// ------------------------------------------------------------
// 8. OPTIONAL: ALSO EXCLUDE PEOPLE WHO ALREADY FOLLOW THE USER
// This variant excludes follow in either direction.
// Use this condition in the FoF query if required by your spec:
// AND NOT (candidate)-[:FOLLOW]->(me)


// ------------------------------------------------------------
// 9. CHECK DIRECT FRIEND COUNTS FOR ALL USERS
// ------------------------------------------------------------
MATCH (p:Person)
OPTIONAL MATCH (p)-[:FRIEND]-(friend:Person)
RETURN p.id AS userId,
       p.name AS name,
       count(DISTINCT friend) AS totalFriends
ORDER BY totalFriends DESC, userId ASC;


// ------------------------------------------------------------
// 10. CHECK RELATIONSHIP COUNTS
// Expected after a clean seed run:
// Person = 80, Post = 80, FRIEND = 130, FOLLOW = 130, CREATED = 80.
// ------------------------------------------------------------
MATCH ()-[r]->()
RETURN type(r) AS relationshipType,
       count(r) AS total
ORDER BY relationshipType;


// ------------------------------------------------------------
// 11. CHECK CONSTRAINTS AND INDEXES
// Run separately in Neo4j Browser.
// ------------------------------------------------------------
// SHOW CONSTRAINTS;
// SHOW INDEXES;


// ------------------------------------------------------------
// 12. EXPLAIN FoF QUERY PLAN
// EXPLAIN does not execute the query; PROFILE executes it and
// reports actual operator metrics.
// ------------------------------------------------------------
EXPLAIN
MATCH (me:Person {id: 'user_1'})-[:FRIEND]-(friend:Person)
      -[:FRIEND]-(candidate:Person)
WHERE candidate <> me
  AND NOT (me)-[:FRIEND]-(candidate)
  AND NOT (me)-[:FOLLOW]->(candidate)
WITH candidate, count(DISTINCT friend) AS mutualFriends
RETURN candidate.id AS candidateId,
       candidate.name AS candidateName,
       mutualFriends
ORDER BY mutualFriends DESC, candidateName ASC
LIMIT 10;


// ------------------------------------------------------------
// INDEX NOTES
// Ensure a uniqueness constraint exists on Person.id, because
// the recommendation queries look up users by id.
// In Neo4j Browser, inspect with SHOW CONSTRAINTS / SHOW INDEXES.
// If a Person id uniqueness constraint is missing, run:
// CREATE CONSTRAINT person_id_unique IF NOT EXISTS
// FOR (p:Person) REQUIRE p.id IS UNIQUE;
// ------------------------------------------------------------
