import os
import re
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from neo4j import GraphDatabase
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
# Cấu hình thư mục lưu ảnh
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this-secret"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
CORS(app, supports_credentials=True)

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "socialnetwork")

driver = GraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def current_user_id(): return session.get("user_id")
def error(message, status=400): return jsonify({"error": message}), status
def require_login():
    user_id = current_user_id()
    return (user_id, None) if user_id else (None, error("Vui lòng đăng nhập.", 401))

def save_image(file):
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # Thêm random uuid để tránh trùng tên file
        import uuid
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        return f"/static/uploads/{unique_filename}"
    return None

@app.get("/")
def index(): return render_template("index.html")

# ================= API ĐĂNG KÝ =================
@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not name or not username or not password:
        return error("Vui lòng điền đầy đủ thông tin", 400)

    try:
        with driver.session(database=DATABASE) as db:
            # 1. Kiểm tra username đã tồn tại chưa
            check = db.run("MATCH (p:Person {username: $u}) RETURN p LIMIT 1", u=username).single()
            if check:
                return error("Tên đăng nhập đã có người sử dụng", 409)

            # 2. Băm mật khẩu và tạo tài khoản mới
            hashed_pw = generate_password_hash(password)
            db.run("""
                CREATE (p:Person { 
                    id: randomUUID(), 
                    name: $n, 
                    username: $u, 
                    passwordHash: $p, 
                    avatar: 'https://ui-avatars.com/api/?name=' + $n, 
                    bio: 'Xin chào! Mình là thành viên mới.', 
                    createdAt: datetime() 
                })
            """, n=name, u=username, p=hashed_pw)
            
        return jsonify({"message": "Đăng ký thành công"}), 201
    except Exception as e:
        return error(str(e), 500)

# ================= CÁC API KHÁC =================
@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username, password = str(data.get("username", "")).strip().lower(), str(data.get("password", ""))
    with driver.session(database=DATABASE) as db:
        record = db.run("MATCH (p:Person) WHERE p.username=$u OR p.email=$u RETURN p LIMIT 1", u=username).single()
    if not record or not check_password_hash(record["p"]["passwordHash"], password): return error("Sai thông tin.", 401)
    session.clear(); session["user_id"] = record["p"]["id"]
    return jsonify({"message": "OK"})

@app.post("/api/logout")
def logout(): session.clear(); return jsonify({"message": "Đã đăng xuất."})

@app.get("/api/me")
def me():
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        record = db.run("MATCH (p:Person {id: $id}) RETURN p.id AS id, p.name AS name, p.bio AS bio, p.avatar AS avatar", id=uid).single()
    return jsonify(dict(record)) if record else error("Không tìm thấy", 404)

@app.patch("/api/me")
def update_profile():
    uid, fail = require_login()
    if fail: return fail
    name, bio = request.form.get("name", "").strip(), request.form.get("bio", "").strip()
    avatar_url = save_image(request.files.get("avatar"))
    
    with driver.session(database=DATABASE) as db:
        query = "MATCH (p:Person {id: $id}) SET p.name = coalesce(NULLIF($n, ''), p.name), p.bio = coalesce(NULLIF($b, ''), p.bio)"
        params = {"id": uid, "n": name, "b": bio}
        if avatar_url:
            query += ", p.avatar = $a"
            params["a"] = avatar_url
        db.run(query, **params)
    return jsonify({"message": "Đã cập nhật hồ sơ"})

@app.get("/api/friends")
def friends():
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        return jsonify([dict(row) for row in db.run("MATCH (me:Person {id: $uid})-[:FRIEND]-(f:Person) RETURN DISTINCT f.id AS id, f.name AS name, f.avatar AS avatar, f.bio AS bio ORDER BY f.name", uid=uid)])

@app.delete("/api/friends/<target_id>")
def unfriend(target_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (a:Person {id: $u})-[r:FRIEND]-(b:Person {id: $t}) DELETE r", u=uid, t=target_id)
    return jsonify({"message": "Đã hủy"})

@app.get("/api/recommendations")
def recommendations():
    uid, fail = require_login()
    if fail: return fail
    hops = int(request.args.get("hops", 2))
    with driver.session(database=DATABASE) as db:
        q = """MATCH (me:Person {id: $u})-[:FRIEND]-(f:Person)-[:FRIEND]-(c:Person)
               WHERE c <> me AND NOT (me)-[:FRIEND]-(c) AND NOT (me)-[:FOLLOW]->(c)
               WITH c, count(DISTINCT f) AS score WHERE score > 0
               RETURN c.id AS id, c.name AS name, c.avatar AS avatar, c.bio AS bio, score AS mutualFriendsCount
               ORDER BY score DESC, name ASC LIMIT 10""" if hops == 2 else """
               MATCH (me:Person {id: $u})-[:FRIEND]-(f1:Person)-[:FRIEND]-(f2:Person)-[:FRIEND]-(c:Person)
               WHERE c <> me AND NOT (me)-[:FRIEND]-(c) AND NOT (me)-[:FOLLOW]->(c)
               WITH c, count(DISTINCT f2) AS score WHERE score > 0
               RETURN c.id AS id, c.name AS name, c.avatar AS avatar, c.bio AS bio, score AS mutualFriendsCount
               ORDER BY score DESC, name ASC LIMIT 10"""
        return jsonify([dict(r) for r in db.run(q, u=uid)])

@app.get("/api/friend-requests")
def incoming_requests():
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        return jsonify([dict(r) for r in db.run("MATCH (s:Person)-[r:FRIEND_REQUEST]->(m:Person {id: $u}) RETURN s.id AS senderId, s.name AS name, s.avatar AS avatar", u=uid)])

@app.post("/api/friend-requests")
def send_friend_request():
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (a:Person {id: $u}), (b:Person {id: $t}) CREATE (a)-[:FRIEND_REQUEST {createdAt: datetime()}]->(b)", u=uid, t=request.json.get("receiverId"))
    return jsonify({"message": "Đã gửi"})

@app.delete("/api/friend-requests/<target_id>")
def cancel_friend_request(target_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (a:Person {id: $u})-[r:FRIEND_REQUEST]->(b:Person {id: $t}) DELETE r", u=uid, t=target_id)
    return jsonify({"message": "Đã hủy"})

@app.post("/api/friend-requests/<sender_id>/accept")
def accept_friend_request(sender_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (s:Person {id: $sid})-[r:FRIEND_REQUEST]->(m:Person {id: $uid}) DELETE r MERGE (s)-[:FRIEND]->(m) MERGE (m)-[:FRIEND]->(s)", sid=sender_id, uid=uid)
    return jsonify({"message": "Đã chấp nhận"})

@app.post("/api/friend-requests/<sender_id>/reject")
def reject_friend_request(sender_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (s:Person {id: $sid})-[r:FRIEND_REQUEST]->(m:Person {id: $uid}) DELETE r", sid=sender_id, uid=uid)
    return jsonify({"message": "Đã từ chối"})

@app.post("/api/follow/<target_id>")
def follow_user(target_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (me:Person {id: $u}), (t:Person {id: $t_id}) MERGE (me)-[:FOLLOW]->(t)", u=uid, t_id=target_id)
    return jsonify({"message": "Đã follow"})

@app.delete("/api/follow/<target_id>")
def unfollow_user(target_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (me:Person {id: $u})-[r:FOLLOW]->(t:Person {id: $t_id}) DELETE r", u=uid, t_id=target_id)
    return jsonify({"message": "Đã bỏ follow"})

@app.get("/api/feed")
def get_feed():
    uid, fail = require_login()
    if fail: return fail
    try:
        with driver.session(database=DATABASE) as db:
            records = db.run("""
                MATCH (me:Person {id: $uid})
                MATCH (author:Person)-[:CREATED]->(post:Post)
                WHERE author.id = $uid OR (me)-[:FRIEND]-(author)
                
                OPTIONAL MATCH (liker:Person)-[:LIKES]->(post)
                WITH me, post, author, collect(liker) AS likers
                
                // 1. Tính toán tuổi của bài viết (tính bằng Giờ)
                WITH me, post, author, likers, 
                     duration.inSeconds(post.createdAt, datetime()).seconds / 3600.0 AS ageInHours
                
                // 2. Tính Điểm Xếp Hạng (Rank Score) dựa trên Gravity Formula
                WITH me, post, author, likers, ageInHours,
                     (size(likers) * 2.0 + 1.0) / (ageInHours + 2.0)^1.5 AS rankScore
                
                RETURN post.id AS id, post.content AS content, post.image AS image, toString(post.createdAt) AS createdAt,
                       author.id AS authorId, author.name AS authorName, author.avatar AS authorAvatar,
                       size(likers) AS likes, me IN likers AS isLikedByMe,
                       rankScore
                ORDER BY rankScore DESC, post.createdAt DESC LIMIT 30
            """, uid=uid)
            return jsonify([dict(r) for r in records])
    except Exception as e: 
        print("LỖI FEED:", e)
        return jsonify({"error": str(e)}), 500

@app.get("/api/users/<target_id>/posts")
def get_user_posts(target_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        records = db.run("""
            MATCH (me:Person {id: $uid})
            MATCH (author:Person {id: $tid})-[:CREATED]->(post:Post)
            OPTIONAL MATCH (liker:Person)-[:LIKES]->(post)
            WITH me, post, author, collect(liker) AS likers
            RETURN post.id AS id, post.content AS content, post.image AS image, toString(post.createdAt) AS createdAt,
                   author.id AS authorId, author.name AS authorName, author.avatar AS authorAvatar,
                   size(likers) AS likes, me IN likers AS isLikedByMe
            ORDER BY post.createdAt DESC LIMIT 20
        """, uid=uid, tid=target_id)
        return jsonify([dict(r) for r in records])

@app.post("/api/posts")
def create_post():
    uid, fail = require_login()
    if fail: return fail
    content = request.form.get("content", "").strip()
    image_url = save_image(request.files.get("image"))
    if not content and not image_url: return error("Nội dung không được để trống")
    
    with driver.session(database=DATABASE) as db:
        db.run("""MATCH (p:Person {id: $u})
                  CREATE (po:Post {id: randomUUID(), content: $c, image: $img, createdAt: datetime()})
                  CREATE (p)-[:CREATED]->(po)""", u=uid, c=content, img=image_url)
    return jsonify({"message": "Đã đăng bài"})

@app.delete("/api/posts/<post_id>")
def delete_post(post_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (p:Person {id: $u})-[:CREATED]->(po:Post {id: $p}) DETACH DELETE po", u=uid, p=post_id)
    return jsonify({"message": "Đã xóa"})

@app.post("/api/posts/<post_id>/like")
def like_post(post_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (p:Person {id: $u}), (po:Post {id: $p}) MERGE (p)-[r:LIKES]->(po) SET r.createdAt = datetime()", u=uid, p=post_id)
    return jsonify({"message": "Đã thích"})

@app.delete("/api/posts/<post_id>/like")
def unlike_post(post_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db: db.run("MATCH (p:Person {id: $u})-[r:LIKES]->(po:Post {id: $p}) DELETE r", u=uid, p=post_id)
    return jsonify({"message": "Đã bỏ thích"})

@app.get("/api/following")
def get_following():
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        records = db.run("MATCH (me:Person {id: $u})-[:FOLLOW]->(f:Person) RETURN f.id AS id, f.name AS name, f.avatar AS avatar, f.bio AS bio ORDER BY f.name", u=uid)
        return jsonify([dict(r) for r in records])

@app.get("/api/followers")
def get_followers():
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        records = db.run("MATCH (f:Person)-[:FOLLOW]->(me:Person {id: $u}) RETURN f.id AS id, f.name AS name, f.avatar AS avatar, f.bio AS bio ORDER BY f.name", u=uid)
        return jsonify([dict(r) for r in records])

@app.get("/api/posts/<post_id>/comments")
def get_comments(post_id):
    uid, fail = require_login()
    if fail: return fail
    with driver.session(database=DATABASE) as db:
        records = db.run("""
            MATCH (c:Comment)-[:ON_POST]->(p:Post {id: $pid})
            MATCH (author:Person)-[:WROTE]->(c)
            RETURN c.id AS id, c.content AS content, toString(c.createdAt) AS createdAt,
                   author.id AS authorId, author.name AS authorName, author.avatar AS authorAvatar
            ORDER BY c.createdAt ASC
        """, pid=post_id)
        return jsonify([dict(r) for r in records])

@app.post("/api/posts/<post_id>/comments")
def add_comment(post_id):
    uid, fail = require_login()
    if fail: return fail
    
    data = request.get_json(silent=True) or {}
    content = str(data.get("content", "")).strip()
    
    if not content: return error("Nội dung không được để trống")
    with driver.session(database=DATABASE) as db:
        db.run("""
            MATCH (u:Person {id: $uid}), (p:Post {id: $pid})
            CREATE (c:Comment {id: randomUUID(), content: $content, createdAt: datetime()})
            CREATE (u)-[:WROTE]->(c)-[:ON_POST]->(p)
        """, uid=uid, pid=post_id, content=content)
    return jsonify({"message": "Đã bình luận"})
@app.get("/api/users/search")
def search_users():
    search_term = request.args.get("q", "")
    with driver.session(database=DATABASE) as db:
        query = """
        MATCH (p:Person)
        WHERE toLower(p.name) CONTAINS toLower($term) 
           OR toLower(p.username) CONTAINS toLower($term)
        RETURN p.username AS username, p.name AS name, p.avatar AS avatar 
        ORDER BY p.name ASC LIMIT 10
        """
        result = db.run(query, term=search_term)
        users = [record.data() for record in result]
        return jsonify(users)
@app.get("/api/users/<username>")
def get_user_profile(username):
    my_id = session.get("user_id")
    if not my_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    with driver.session(database=DATABASE) as db:
        query = """
        MATCH (u:Person {username: $target_username})
        MATCH (me:Person {id: $my_id})
        RETURN u.id AS id, u.username AS username, u.name AS name, 
               u.avatar AS avatar, u.bio AS bio,
               EXISTS((me)-[:FRIEND]-(u)) AS isFriend,
               EXISTS((me)-[:FOLLOW]->(u)) AS isFollowing,
               EXISTS((me)-[:FRIEND_REQUEST]->(u)) AS sentRequest,
               EXISTS((u)-[:FRIEND_REQUEST]->(me)) AS receivedRequest
        """
        result = db.run(query, target_username=username, my_id=my_id).single()
        
        if not result:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(result.data())
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)