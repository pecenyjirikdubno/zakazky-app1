import os
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

# Initialize DB with admin user
@app.before_first_request
def create_tables():
    db.create_all()
    if not User.query.filter_by(username=ADMIN_USERNAME).first():
        admin = User(username=ADMIN_USERNAME,
                     password_hash=generate_password_hash(ADMIN_PASSWORD),
                     is_admin=True)
        db.session.add(admin)
        db.session.commit()

# Routes zůstávají stejné (login, zakazky, new_zakazka, edit_zakazka, close_zakazka, export_zakazka, logout)

if __name__ == "__main__":
    app.run(debug=True)
