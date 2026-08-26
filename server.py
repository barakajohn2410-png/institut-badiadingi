#!/usr/bin/env python3
"""Application locale de publication des resultats - Institut Badiadingi.
Sans dependance externe : Python 3.10+ et SQLite suffisent.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http import cookies
import hashlib, hmac, json, os, secrets, sqlite3, sys

ROOT = Path(__file__).parent
DB_FILE = ROOT / "badiadingi.db"
SESSIONS = {}

def db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, school_year TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, matricule TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL, class_id INTEGER NOT NULL REFERENCES classes(id));
    CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, coefficient REAL NOT NULL DEFAULT 1, class_id INTEGER NOT NULL REFERENCES classes(id), UNIQUE(name,class_id));
    CREATE TABLE IF NOT EXISTS grades (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE, period TEXT NOT NULL, score REAL NOT NULL CHECK(score >= 0 AND score <= 20), UNIQUE(student_id,subject_id,period));
    CREATE TABLE IF NOT EXISTS publications (id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id), period TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0, UNIQUE(class_id,period));
    """)
    if not con.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        password = os.environ.get("BADIADINGI_ADMIN_PASSWORD", "changez-moi")
        con.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", ("admin", hash_password(password)))
        print("Compte initial : admin / " + password)
        print("Changez le mot de passe en definissant BADIADINGI_ADMIN_PASSWORD avant le premier lancement.")
    con.commit(); con.close()

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return salt + "$" + digest

def verify_password(password, stored):
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return hmac.compare_digest(check, digest)

class App(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=str(ROOT / "static"), **kw)
    def log_message(self, fmt, *args): print("[web]", fmt % args)
    def send_json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
        except json.JSONDecodeError: raise ValueError("Données JSON invalides.")
    def session_user(self):
        c = cookies.SimpleCookie(self.headers.get("Cookie")); sid = c.get("sid")
        return SESSIONS.get(sid.value) if sid else None
    def require_admin(self):
        if not self.session_user(): self.send_json({"error":"Authentification requise."},401); return False
        return True
    def do_GET(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"): return super().do_GET()
        q = parse_qs(parsed.query); con = db()
        try:
            if parsed.path == "/api/me": return self.send_json({"authenticated": bool(self.session_user()), "username":self.session_user()})
            if parsed.path == "/api/classes":
                if not self.require_admin(): return
                return self.send_json([dict(r) for r in con.execute("SELECT * FROM classes ORDER BY school_year DESC,name")])
            if parsed.path == "/api/students":
                if not self.require_admin(): return
                return self.send_json([dict(r) for r in con.execute("SELECT s.*,c.name class_name FROM students s JOIN classes c ON c.id=s.class_id WHERE s.class_id=? ORDER BY last_name,first_name",(q.get("class_id",[0])[0],))])
            if parsed.path == "/api/subjects":
                if not self.require_admin(): return
                return self.send_json([dict(r) for r in con.execute("SELECT * FROM subjects WHERE class_id=? ORDER BY name",(q.get("class_id",[0])[0],))])
            if parsed.path == "/api/grades":
                if not self.require_admin(): return
                sql="SELECT g.*,s.matricule,s.first_name,s.last_name,sub.name subject_name FROM grades g JOIN students s ON s.id=g.student_id JOIN subjects sub ON sub.id=g.subject_id WHERE s.class_id=? AND g.period=?"
                return self.send_json([dict(r) for r in con.execute(sql,(q.get("class_id",[0])[0],q.get("period",[""])[0]))])
            if parsed.path == "/api/publication":
                if not self.require_admin(): return
                r=con.execute("SELECT published FROM publications WHERE class_id=? AND period=?",(q.get("class_id",[0])[0],q.get("period",[""])[0])).fetchone()
                return self.send_json({"published":bool(r and r['published'])})
            if parsed.path == "/api/result":
                mat=q.get("matricule",[""])[0].strip(); period=q.get("period",[""])[0].strip()
                st=con.execute("SELECT s.*,c.name class_name,c.school_year FROM students s JOIN classes c ON c.id=s.class_id WHERE lower(s.matricule)=lower(?)",(mat,)).fetchone()
                if not st: return self.send_json({"error":"Matricule introuvable."},404)
                pub=con.execute("SELECT published FROM publications WHERE class_id=? AND period=?",(st['class_id'],period)).fetchone()
                if not pub or not pub['published']: return self.send_json({"error":"Résultats non publiés pour cette période."},403)
                rows=con.execute("SELECT sub.name,sub.coefficient,g.score FROM subjects sub LEFT JOIN grades g ON g.subject_id=sub.id AND g.student_id=? AND g.period=? WHERE sub.class_id=? ORDER BY sub.name",(st['id'],period,st['class_id'])).fetchall()
                total=sum((r['score'] or 0)*r['coefficient'] for r in rows); coef=sum(r['coefficient'] for r in rows if r['score'] is not None)
                return self.send_json({"student":dict(st),"period":period,"grades":[dict(r) for r in rows],"average":round(total/coef,2) if coef else None})
            self.send_json({"error":"Route inconnue."},404)
        finally: con.close()
    def do_POST(self):
        path=urlparse(self.path).path
        try: data=self.body()
        except ValueError as e: return self.send_json({"error":str(e)},400)
        if path == "/api/login":
            con=db(); u=con.execute("SELECT * FROM users WHERE username=?",(data.get("username",""),)).fetchone(); con.close()
            if not u or not verify_password(data.get("password",""),u['password_hash']): return self.send_json({"error":"Identifiants incorrects."},401)
            sid=secrets.token_urlsafe(32); SESSIONS[sid]=u['username']; self.send_response(200); self.send_header("Set-Cookie",f"sid={sid}; HttpOnly; SameSite=Lax; Path=/"); self.send_header("Content-Type","application/json"); self.end_headers(); return self.wfile.write(b'{"ok":true}')
        if path == "/api/logout":
            c=cookies.SimpleCookie(self.headers.get("Cookie")); sid=c.get("sid");
            if sid: SESSIONS.pop(sid.value,None)
            return self.send_json({"ok":True})
        if not self.require_admin(): return
        con=db()
        try:
            if path == "/api/classes": con.execute("INSERT INTO classes(name,school_year) VALUES(?,?)",(data['name'].strip(),data['school_year'].strip()))
            elif path == "/api/students": con.execute("INSERT INTO students(matricule,first_name,last_name,class_id) VALUES(?,?,?,?)",(data['matricule'].strip(),data['first_name'].strip(),data['last_name'].strip(),data['class_id']))
            elif path == "/api/subjects": con.execute("INSERT INTO subjects(name,coefficient,class_id) VALUES(?,?,?)",(data['name'].strip(),float(data['coefficient']),data['class_id']))
            elif path == "/api/grades":
                con.execute("INSERT INTO grades(student_id,subject_id,period,score) VALUES(?,?,?,?) ON CONFLICT(student_id,subject_id,period) DO UPDATE SET score=excluded.score",(data['student_id'],data['subject_id'],data['period'].strip(),float(data['score'])))
            elif path == "/api/publication": con.execute("INSERT INTO publications(class_id,period,published) VALUES(?,?,?) ON CONFLICT(class_id,period) DO UPDATE SET published=excluded.published",(data['class_id'],data['period'].strip(),int(bool(data['published']))))
            else: return self.send_json({"error":"Route inconnue."},404)
            con.commit(); self.send_json({"ok":True})
        except (KeyError,ValueError,sqlite3.IntegrityError) as e: self.send_json({"error":"Enregistrement impossible : "+str(e)},400)
        finally: con.close()

if __name__ == "__main__":
    init_db(); port=int(os.environ.get("PORT","8000")); print(f"Institut Badiadingi : http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0",port),App).serve_forever()
