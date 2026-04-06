from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

# Inicializace Flask aplikace
app = Flask(__name__)

# Nastavení databáze (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zakazky.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model databáze
class Zakazka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(100), nullable=False)
    popis = db.Column(db.String(200))

# Inicializace databáze při prvním requestu
@app.before_first_request
def init_db():
    db.create_all()

# Hlavní stránka – seznam zakázek
@app.route('/')
def index():
    zakazky = Zakazka.query.all()
    return render_template('index.html', zakazky=zakazky)

# Přidání nové zakázky
@app.route('/add', methods=['POST'])
def add_zakazka():
    nazev = request.form.get('nazev')
    popis = request.form.get('popis')
    if nazev:
        novy = Zakazka(nazev=nazev, popis=popis)
        db.session.add(novy)
        db.session.commit()
    return redirect(url_for('index'))

# Smazání zakázky
@app.route('/delete/<int:id>')
def delete_zakazka(id):
    zak = Zakazka.query.get_or_404(id)
    db.session.delete(zak)
    db.session.commit()
    return redirect(url_for('index'))

# Spuštění aplikace na Render portu
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
