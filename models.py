from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'uvoice.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "rouge_secret"

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    iduser = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    favoris = db.relationship('FavoriArgument', backref='user', cascade="all, delete-orphan")

class Theme(db.Model):
    __tablename__ = 'themes'
    id_theme = db.Column(db.Integer, primary_key=True)
    nom_theme = db.Column(db.String(100), nullable=False, unique=True)
    id_admin = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    admin = db.relationship('User')
    debats = db.relationship('Debat', backref='theme_backref', cascade="all, delete-orphan")

class Debat(db.Model):
    __tablename__ = 'debats'
    id_debat = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_limite = db.Column(db.DateTime, nullable=True)
    max_arguments = db.Column(db.Integer, default=50)
    statut = db.Column(db.String(20), default="ouvert")
    arguments = db.relationship('Argument', backref='debat_backref', cascade="all, delete-orphan")
    votes = db.relationship('Vote', backref='debat_backref', cascade="all, delete-orphan")
    id_theme = db.Column(db.Integer, db.ForeignKey('themes.id_theme'), nullable=False)
    id_createur = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    createur = db.relationship('User')

class Argument(db.Model):
    __tablename__ = 'arguments'
    id_argument = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.Text, nullable=False)
    type_arg = db.Column(db.String(20), nullable=False)  # soutien / attaque
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    id_debat = db.Column(db.Integer, db.ForeignKey('debats.id_debat'), nullable=False)
    id_auteur = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    auteur = db.relationship('User')
    id_parent = db.Column(db.Integer, db.ForeignKey('arguments.id_argument'), nullable=True)
    enfants = db.relationship('Argument', backref=db.backref('parent', remote_side=[id_argument]), cascade="all, delete-orphan")
    evaluations = db.relationship('EvaluationArgument', backref='argument', cascade="all, delete-orphan")
    favoris_recus = db.relationship('FavoriArgument', backref='argument', cascade="all, delete-orphan")

class EvaluationArgument(db.Model):
    __tablename__ = 'evaluations_argument'
    id_evaluation = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Integer, nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    id_argument = db.Column(db.Integer, db.ForeignKey('arguments.id_argument'), nullable=False)
    date_evaluation = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('id_user', 'id_argument', name='unique_eval_per_user_per_arg'),)

class FavoriArgument(db.Model):
    __tablename__ = 'favoris_argument'
    id_favori = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    id_argument = db.Column(db.Integer, db.ForeignKey('arguments.id_argument'), nullable=False)
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('id_user', 'id_argument', name='unique_favori_arg_per_user'),)

class Vote(db.Model):
    __tablename__ = "votes"
    id_vote = db.Column(db.Integer, primary_key=True)
    choix = db.Column(db.String(10), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    id_debat = db.Column(db.Integer, db.ForeignKey("debats.id_debat"), nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey("users.iduser"), nullable=False)
    user = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("id_debat", "id_user", name="unique_vote_per_user_per_debat"),)


class VoteArgument(db.Model):
    __tablename__ = "votes_arguments"
    id_vote_arg = db.Column(db.Integer, primary_key=True)
    valeur = db.Column(db.Integer, nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey("users.iduser"), nullable=False)
    id_argument = db.Column(db.Integer, db.ForeignKey("arguments.id_argument"), nullable=False)
    __table_args__ = (db.UniqueConstraint("id_user", "id_argument", name="unique_vote_arg_per_user"),)