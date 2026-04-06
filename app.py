import os
from flask import Flask, render_template, redirect, url_for, request, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///zakazky.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Admin credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Zakazka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    closed = db.Column(db.Boolean, default=False)
    rows = db.relationship('ZakazkaRow', backref='zakazka', cascade="all, delete-orphan")


class ZakazkaRow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_name = db.Column(db.String(200))
    material_code = db.Column(db.String(100))
    supplier = db.Column(db.String(200))
    supplier_doc = db.Column(db.String(100))
    work_hours = db.Column(db.Float)
    date = db.Column(db.Date)
    travel_time = db.Column(db.Float)
    km = db.Column(db.Float)
    zakazka_id = db.Column(db.Integer, db.ForeignKey('zakazka.id'))


# Initialize DB and admin user at startup
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username=ADMIN_USERNAME).first():
        admin = User(username=ADMIN_USERNAME,
                     password_hash=generate_password_hash(ADMIN_PASSWORD),
                     is_admin=True)
        db.session.add(admin)
        db.session.commit()


# Routes
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            return redirect(url_for("zakazky"))
        flash("Špatné přihlašovací údaje.")
    return render_template("login.html")


@app.route("/zakazky")
def zakazky():
    if "user_id" not in session:
        return redirect(url_for("login"))
    all_zakazky = Zakazka.query.all()
    return render_template("zakazky.html", zakazky=all_zakazky, admin=session.get("is_admin", False))


@app.route("/zakazka/new", methods=["GET", "POST"])
def new_zakazka():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"]
        zak = Zakazka(name=name)
        db.session.add(zak)
        db.session.commit()
        return redirect(url_for("zakazky"))
    return render_template("new_zakazka.html")


@app.route("/zakazka/<int:zakazka_id>", methods=["GET", "POST"])
def edit_zakazka(zakazka_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    zak = Zakazka.query.get_or_404(zakazka_id)
    if request.method == "POST":
        if zak.closed:
            flash("Zakázka je uzavřená.")
            return redirect(url_for("zakazky"))
        material_name = request.form["material_name"]
        material_code = request.form["material_code"]
        supplier = request.form["supplier"]
        supplier_doc = request.form["supplier_doc"]
        work_hours = float(request.form["work_hours"] or 0)
        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        travel_time = float(request.form["travel_time"] or 0)
        km = float(request.form["km"] or 0)
        row = ZakazkaRow(material_name=material_name,
                         material_code=material_code,
                         supplier=supplier,
                         supplier_doc=supplier_doc,
                         work_hours=work_hours,
                         date=date,
                         travel_time=travel_time,
                         km=km,
                         zakazka=zak)
        db.session.add(row)
        db.session.commit()
        return redirect(url_for("edit_zakazka", zakazka_id=zak.id))
    return render_template("edit_zakazka.html", zak=zak, admin=session.get("is_admin", False))


@app.route("/zakazka/<int:zakazka_id>/close")
def close_zakazka(zakazka_id):
    if not session.get("is_admin"):
        flash("Pouze admin může uzavřít zakázku.")
        return redirect(url_for("zakazky"))
    zak = Zakazka.query.get_or_404(zakazka_id)
    zak.closed = True
    db.session.commit()
    flash("Zakázka byla uzavřena.")
    return redirect(url_for("zakazky"))


@app.route("/zakazka/<int:zakazka_id>/export")
def export_zakazka(zakazka_id):
    if not session.get("is_admin"):
        flash("Pouze admin může exportovat zakázku.")
        return redirect(url_for("zakazky"))
    zak = Zakazka.query.get_or_404(zakazka_id)
    data = []
    for row in zak.rows:
        data.append({
            "Material Name": row.material_name,
            "Material Code": row.material_code,
            "Supplier": row.supplier,
            "Supplier Doc": row.supplier_doc,
            "Work Hours": row.work_hours,
            "Date": row.date,
            "Travel Time": row.travel_time,
            "KM": row.km
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, download_name=f"{zak.name}.xlsx", as_attachment=True)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
