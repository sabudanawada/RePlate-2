from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, os, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "food-donation-demo-secret"
DB = os.path.join(os.path.dirname(__file__), "replate.db")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('donor','ngo','admin')),
        phone TEXT,
        location TEXT,
        lat REAL,
        lng REAL,
        verified INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL,
        food_type TEXT NOT NULL,
        quantity TEXT NOT NULL,
        category TEXT NOT NULL,
        pickup_location TEXT NOT NULL,
        pickup_date TEXT NOT NULL,
        pickup_time TEXT NOT NULL,
        contact TEXT NOT NULL,
        image TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Submitted',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(donor_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_id INTEGER NOT NULL,
        ngo_id INTEGER NOT NULL,
        distance REAL,
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(donation_id) REFERENCES donations(id),
        FOREIGN KEY(ngo_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS pickups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_id INTEGER NOT NULL,
        ngo_id INTEGER NOT NULL,
        pickup_time TEXT,
        delivery_status TEXT DEFAULT 'Scheduled',
        FOREIGN KEY(donation_id) REFERENCES donations(id),
        FOREIGN KEY(ngo_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(donation_id) REFERENCES donations(id)
    );
    """)

    # Demo accounts and NGOs
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO users(name,email,password,role,phone,location,lat,lng,verified)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, [
            ("Demo Donor", "donor@replate.demo", "1234", "donor", "9876543210", "Pune", 18.5204, 73.8567, 1),
            ("Helping Hands NGO", "ngo@replate.demo", "1234", "ngo", "9876500001", "Shivajinagar, Pune", 18.5308, 73.8475, 1),
            ("Annadan Food Bank", "foodbank@replate.demo", "1234", "ngo", "9876500002", "Kothrud, Pune", 18.5074, 73.8077, 1),
            ("Care & Share NGO", "care@replate.demo", "1234", "ngo", "9876500003", "Hadapsar, Pune", 18.5089, 73.9260, 1),
            ("Administrator", "admin@replate.demo", "admin123", "admin", "9000000000", "Pune", 18.5204, 73.8567, 1),
        ])
        conn.commit()
    conn.close()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return u

def distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 999
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

@app.context_processor
def inject_user():
    return {"user": current_user()}

@app.route("/")
def home():
    conn = db()
    stats = {
        "donations": conn.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
        "ngos": conn.execute("SELECT COUNT(*) FROM users WHERE role='ngo' AND verified=1").fetchone()[0],
        "donors": conn.execute("SELECT COUNT(*) FROM users WHERE role='donor'").fetchone()[0],
        "delivered": conn.execute("SELECT COUNT(*) FROM donations WHERE status='Delivered'").fetchone()[0],
    }
    conn.close()
    return render_template("index.html", stats=stats)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]
        phone = request.form.get("phone","")
        location = request.form.get("location","")
        try:
            conn = db()
            conn.execute("""INSERT INTO users(name,email,password,role,phone,location,verified)
                            VALUES(?,?,?,?,?,?,?)""",
                         (name,email,password,role,phone,location,1 if role=="donor" else 0))
            conn.commit()
            conn.close()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = db()
        u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()
        conn.close()
        if u:
            session["user_id"] = u["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    if u["role"] == "donor":
        return redirect(url_for("donor_dashboard"))
    if u["role"] == "ngo":
        return redirect(url_for("ngo_dashboard"))
    return redirect(url_for("admin_dashboard"))

@app.route("/donor")
def donor_dashboard():
    u = current_user()
    if not u or u["role"] != "donor":
        return redirect(url_for("login"))
    conn = db()
    donations = conn.execute("""
        SELECT d.*, m.status AS match_status, m.distance, n.name AS ngo_name
        FROM donations d
        LEFT JOIN matches m ON d.id=m.donation_id
        LEFT JOIN users n ON m.ngo_id=n.id
        WHERE d.donor_id=? ORDER BY d.id DESC
    """, (u["id"],)).fetchall()
    total = len(donations)
    delivered = sum(1 for d in donations if d["status"]=="Delivered")
    conn.close()
    return render_template("donor_dashboard.html", donations=donations, total=total, delivered=delivered)

@app.route("/donate", methods=["GET","POST"])
def donate():
    u = current_user()
    if not u or u["role"] != "donor":
        return redirect(url_for("login"))
    if request.method == "POST":
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO donations(donor_id,food_type,quantity,category,pickup_location,
                                  pickup_date,pickup_time,contact,image,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            u["id"], request.form["food_type"], request.form["quantity"],
            request.form["category"], request.form["pickup_location"],
            request.form["pickup_date"], request.form["pickup_time"],
            request.form["contact"], request.form.get("image",""),
            request.form.get("notes","")
        ))
        donation_id = cur.lastrowid

        # Nearest suitable NGO matching
        ngos = cur.execute("SELECT * FROM users WHERE role='ngo' AND verified=1").fetchall()
        donor_lat = u["lat"] or 18.5204
        donor_lng = u["lng"] or 73.8567
        ranked = []
        for ngo in ngos:
            dist = distance_km(donor_lat, donor_lng, ngo["lat"], ngo["lng"])
            ranked.append((dist, ngo))
        ranked.sort(key=lambda x: x[0])
        if ranked:
            dist, ngo = ranked[0]
            cur.execute("INSERT INTO matches(donation_id,ngo_id,distance,status) VALUES(?,?,?,?)",
                        (donation_id, ngo["id"], round(dist,2), "Pending"))
            # Above string construction keeps SQL visually compact.
        conn.commit()
        conn.close()
        flash("Donation submitted and the nearest verified NGO has been matched.", "success")
        return redirect(url_for("donor_dashboard"))
    return render_template("donate.html")

@app.route("/ngo")
def ngo_dashboard():
    u = current_user()
    if not u or u["role"] != "ngo":
        return redirect(url_for("login"))
    conn = db()
    requests = conn.execute("""
        SELECT d.*, donor.name AS donor_name, donor.phone AS donor_phone,
               m.id AS match_id, m.distance, m.status AS match_status
        FROM matches m
        JOIN donations d ON d.id=m.donation_id
        JOIN users donor ON donor.id=d.donor_id
        WHERE m.ngo_id=? ORDER BY m.id DESC
    """, (u["id"],)).fetchall()
    accepted = sum(1 for r in requests if r["match_status"]=="Accepted")
    completed = sum(1 for r in requests if r["status"]=="Delivered")
    conn.close()
    return render_template("ngo_dashboard.html", requests=requests, accepted=accepted, completed=completed)

@app.route("/ngo/action/<int:match_id>/<action>", methods=["POST"])
def ngo_action(match_id, action):
    u = current_user()
    if not u or u["role"] != "ngo" or action not in ("accept","reject"):
        return jsonify({"ok":False}), 403
    conn = db()
    m = conn.execute("SELECT * FROM matches WHERE id=? AND ngo_id=?", (match_id,u["id"])).fetchone()
    if not m:
        conn.close()
        return jsonify({"ok":False}), 404
    if action == "accept":
        conn.execute("UPDATE matches SET status='Accepted' WHERE id=?", (match_id,))
        conn.execute("UPDATE donations SET status='Accepted' WHERE id=?", (m["donation_id"],))
        conn.execute("INSERT INTO pickups(donation_id,ngo_id,pickup_time) VALUES(?,?,?)",
                     (m["donation_id"],u["id"],datetime.now().strftime("%Y-%m-%d %H:%M")))
    else:
        conn.execute("UPDATE matches SET status='Rejected' WHERE id=?", (match_id,))
        conn.execute("UPDATE donations SET status='Rejected' WHERE id=?", (m["donation_id"],))
    conn.commit()
    conn.close()
    return redirect(url_for("ngo_dashboard"))

@app.route("/ngo/status/<int:donation_id>/<status>", methods=["POST"])
def update_status(donation_id,status):
    u = current_user()
    allowed = ["Picked Up","Delivered"]
    if not u or u["role"]!="ngo" or status not in allowed:
        return jsonify({"ok":False}), 403
    conn = db()
    row = conn.execute("""
        SELECT d.id FROM donations d JOIN matches m ON d.id=m.donation_id
        WHERE d.id=? AND m.ngo_id=? AND m.status='Accepted'
    """, (donation_id,u["id"])).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok":False}), 404
    conn.execute("UPDATE donations SET status=? WHERE id=?", (status,donation_id))
    if status=="Delivered":
        conn.execute("UPDATE pickups SET delivery_status='Delivered' WHERE donation_id=?", (donation_id,))
    else:
        conn.execute("UPDATE pickups SET delivery_status='Picked Up' WHERE donation_id=?", (donation_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("ngo_dashboard"))

@app.route("/admin")
def admin_dashboard():
    u = current_user()
    if not u or u["role"]!="admin":
        return redirect(url_for("login"))
    conn = db()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    donations = conn.execute("""
        SELECT d.*, u.name AS donor_name, n.name AS ngo_name
        FROM donations d
        JOIN users u ON u.id=d.donor_id
        LEFT JOIN matches m ON m.donation_id=d.id
        LEFT JOIN users n ON n.id=m.ngo_id
        ORDER BY d.id DESC
    """).fetchall()
    stats = {
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "ngos": conn.execute("SELECT COUNT(*) FROM users WHERE role='ngo'").fetchone()[0],
        "donations": conn.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
        "delivered": conn.execute("SELECT COUNT(*) FROM donations WHERE status='Delivered'").fetchone()[0],
    }
    conn.close()
    return render_template("admin_dashboard.html", users=users, donations=donations, stats=stats)

@app.route("/admin/verify/<int:user_id>", methods=["POST"])
def verify_user(user_id):
    u = current_user()
    if not u or u["role"]!="admin":
        return redirect(url_for("login"))
    conn=db()
    conn.execute("UPDATE users SET verified=1 WHERE id=? AND role='ngo'",(user_id,))
    conn.commit(); conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/api/stats")
def api_stats():
    conn=db()
    result = {
        "donations": conn.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
        "delivered": conn.execute("SELECT COUNT(*) FROM donations WHERE status='Delivered'").fetchone()[0],
        "ngos": conn.execute("SELECT COUNT(*) FROM users WHERE role='ngo' AND verified=1").fetchone()[0],
        "donors": conn.execute("SELECT COUNT(*) FROM users WHERE role='donor'").fetchone()[0]
    }
    conn.close()
    return jsonify(result)

# Initialize the database when Flask/Gunicorn imports this module.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
