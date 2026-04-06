import os
from flask import Flask, request, redirect, render_template, session, flash, g, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import pandas as pd
import io

# =========================
# APP
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

# =========================
# DATABASE
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODELY
# =========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100))
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Zakazka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(200))
    popis = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed = db.Column(db.Boolean, default=False)
    radky = db.relationship('Radek', backref='zakazka', lazy=True)

class Radek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zakazka_id = db.Column(db.Integer, db.ForeignKey('zakazka.id'))
    material = db.Column(db.String(200))
    kod_materialu = db.Column(db.String(100))
    dodavatel = db.Column(db.String(200))
    cislo_dokladu = db.Column(db.String(100))
    odprac_hodiny = db.Column(db.Float)
    datum = db.Column(db.Date)
    cas_na_ceste = db.Column(db.Float)
    km = db.Column(db.Float)

# =========================
# HELPER
# =========================
def current_user():
    if "user_id" in session:
        return db.session.get(User, session["user_id"])
    return None

@app.before_request
def before_request():
    g.user = current_user()

# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    if not g.user:
        return redirect("/login")
    zakazky = Zakazka.query.all()
    return render_template("index.html", zakazky=zakazky)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password_raw = request.form.get("password")
        if not username or not password_raw:
            flash("Vyplň všechny údaje")
            return redirect("/register")
        if User.query.filter_by(username=username).first():
            flash("Uživatel existuje")
            return redirect("/register")
        password = generate_password_hash(password_raw)
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registrace OK")
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Vyplň údaje")
            return redirect("/login")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            return redirect("/")
        else:
            flash("Špatné údaje")
            return redirect("/login")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/add", methods=["GET", "POST"])
def add():
    if not g.user:
        return redirect("/login")
    if request.method == "POST":
        nazev = request.form.get("nazev")
        popis = request.form.get("popis")
        if not nazev:
            flash("Zadej název")
            return redirect("/add")
        z = Zakazka(nazev=nazev, popis=popis)
        db.session.add(z)
        db.session.commit()
        return redirect("/")
    return render_template("add_zakazka.html")

@app.route("/zakazka/<int:id>/add_radek", methods=["GET","POST"])
def add_radek(id):
    zakazka = Zakazka.query.get_or_404(id)
    if zakazka.closed:
        flash("Zakázka je uzavřena")
        return redirect("/")
    if request.method == "POST":
        radek = Radek(
            zakazka_id=id,
            material=request.form.get("material"),
            kod_materialu=request.form.get("kod_materialu"),
            dodavatel=request.form.get("dodavatel"),
            cislo_dokladu=request.form.get("cislo_dokladu"),
            odprac_hodiny=float(request.form.get("odprac_hodiny",0)),
            datum=datetime.strptime(request.form.get("datum"), '%Y-%m-%d').date(),
            cas_na_ceste=float(request.form.get("cas_na_ceste",0)),
            km=float(request.form.get("km",0))
        )
        db.session.add(radek)
        db.session.commit()
        return redirect("/")
    return render_template("add_radek.html", zakazka=zakazka)

@app.route("/zakazka/<int:id>/export")
def export_zakazka(id):
    zakazka = Zakazka.query.get_or_404(id)
    if not g.user.is_admin:
        flash("Přístup odepřen")
        return redirect("/")
    data = [{
        "Materiál": r.material,
        "Kód materiálu": r.kod_materialu,
        "Dodavatel": r.dodavatel,
        "Číslo dokladu": r.cislo_dokladu,
        "Odpracované hodiny": r.odprac_hodiny,
        "Datum": r.datum,
        "Čas na cestě": r.cas_na_ceste,
        "Km": r.km
    } for r in zakazka.radky]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Zakazka")
    output.seek(0)
    return send_file(output, download_name=f"{zakazka.nazev}.xlsx", as_attachment=True)

@app.route("/zakazka/<int:id>/close")
def close_zakazka(id):
    zakazka = Zakazka.query.get_or_404(id)
    if g.user.is_admin:
        zakazka.closed = True
        db.session.commit()
    return redirect("/")

# =========================
# INIT DB + admin
# =========================
with app.app_context():
    db.create_all()

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    if not User.query.filter_by(username=admin_username).first():
        admin_user = User(
            username=admin_username,
            email="admin@example.com",
            password=generate_password_hash(admin_password),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)# Sem přijde kompletní app.py
