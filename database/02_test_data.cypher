
/*
  STEP 1 - TEST DATA
  3 PERSON, 2 FRIEND, 1 POST, 1 FOLLOW
*/

CREATE (a:Person {
  id: 'P001',
  username: 'an01',
  name: 'Nguyen Van An',
  email: 'an01@example.com',
  passwordHash: 'DEMO_ONLY',
  bio: 'Sinh vien',
  createdAt: datetime()
});

CREATE (b:Person {
  id: 'P002',
  username: 'binh02',
  name: 'Tran Van Binh',
  email: 'binh02@example.com',
  passwordHash: 'DEMO_ONLY',
  bio: 'Sinh vien',
  createdAt: datetime()
});

CREATE (c:Person {
  id: 'P003',
  username: 'chi03',
  name: 'Le Thi Chi',
  email: 'chi03@example.com',
  passwordHash: 'DEMO_ONLY',
  bio: 'Sinh vien',
  createdAt: datetime()
});

MATCH (a:Person {id: 'P001'}),
      (b:Person {id: 'P002'})
CREATE (a)-[:FRIEND {since: date()}]->(b);

MATCH (b:Person {id: 'P002'}),
      (c:Person {id: 'P003'})
CREATE (b)-[:FRIEND {since: date()}]->(c);

MATCH (a:Person {id: 'P001'})
CREATE (a)-[:CREATED]->(:Post {
  id: 'POST001',
  content: 'Bai viet dau tien',
  createdAt: datetime()
});

MATCH (c:Person {id: 'P003'}),
      (a:Person {id: 'P001'})
CREATE (c)-[:FOLLOW {createdAt: datetime()}]->(a);
