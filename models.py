from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configuration de la base de données (utilise un dossier 'instance' par défaut)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'uvoice.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------------------------------------------------------
# MODÈLE : UTILISATEUR
# ----------------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'
    iduser = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'prof'

# ----------------------------------------------------------------
# MODÈLE : THÈME
# ----------------------------------------------------------------
class Theme(db.Model):
    __tablename__ = 'themes'
    id_theme = db.Column(db.Integer, primary_key=True)
    nom_theme = db.Column(db.String(100), nullable=False)
    id_admin = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)

# ----------------------------------------------------------------
# MODÈLE : DÉBAT
# ----------------------------------------------------------------
class Debat(db.Model):
    __tablename__ = 'debats'
    id_debat = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_limite = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='ouvert') # 'ouvert', 'clos'
    
    id_theme = db.Column(db.Integer, db.ForeignKey('themes.id_theme'))
    id_createur = db.Column(db.Integer, db.ForeignKey('users.iduser'))

    # Relation pour accéder aux arguments du débat
    arguments = db.relationship('Argument', backref='debat', cascade="all, delete-orphan", lazy=True)

# ----------------------------------------------------------------
# MODÈLE : ARGUMENT (Le plus important pour ton graphe)
# ----------------------------------------------------------------
class Argument(db.Model):
    __tablename__ = 'arguments'
    id_argument = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.Text, nullable=False)
    type_arg = db.Column(db.String(20), nullable=False) # 'soutien' ou 'attaque'
    date_creation = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # --- DONNÉES SÉMANTIQUES ET INTERACTION ---
    likes = db.Column(db.Integer, default=0)
    score_v = db.Column(db.Float, default=1.0) # Valeur Besnard & Hunter
    
    # --- RELATIONS ---
    id_debat = db.Column(db.Integer, db.ForeignKey('debats.id_debat'), nullable=False)
    id_auteur = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    
    # Auto-relation pour la structure en arbre (Parent/Enfants)
    id_parent = db.Column(db.Integer, db.ForeignKey('arguments.id_argument'))
    enfants = db.relationship('Argument', backref=db.backref('parent', remote_side=[id_argument]), cascade="all, delete-orphan")

# ----------------------------------------------------------------
# MODÈLE : VOTE (Optionnel, pour éviter qu'un utilisateur vote 2 fois)
# ----------------------------------------------------------------
class Vote(db.Model):
    __tablename__ = 'votes'
    id_vote = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.iduser'))
    id_argument = db.Column(db.Integer, db.ForeignKey('arguments.id_argument'))