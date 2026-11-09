/*
  DE TAI 11: FRIEND RECOMMENDATION
  STEP 1 - SCHEMA, CONSTRAINTS, INDEXES
*/

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT person_username_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.username IS UNIQUE;

CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.email IS UNIQUE;

CREATE CONSTRAINT post_id_unique IF NOT EXISTS
FOR (p:Post)
REQUIRE p.id IS UNIQUE;

CREATE INDEX person_name_index IF NOT EXISTS
FOR (p:Person)
ON (p.name);

CREATE INDEX post_created_index IF NOT EXISTS 
FOR (p:Post) 
ON (p.createdAt);