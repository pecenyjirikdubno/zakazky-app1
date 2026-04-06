import os
from app import db, User
from werkzeug.security import generate_password_hash

# Admin credentials z environment proměnných
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Vytvoření tabulek
db.create_all()

# Vytvoření admin uživatele, pokud neexistuje
if not User.query.filter_by(username=ADMIN_USERNAME).first():
    admin = User(
        username=ADMIN_USERNAME,
        password_hash=generate_password_hash(ADMIN_PASSWORD),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    print(f"Admin uživatel '{ADMIN_USERNAME}' byl vytvořen.")
else:
    print(f"Admin uživatel '{ADMIN_USERNAME}' již existuje.")
