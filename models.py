from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Configuration de la base de données
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'uvoice.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# MODÈLE UTILISATEUR
class User(db.Model):
    __tablename__ = 'users'
    iduser = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / prof / etudiant


# MODÈLE THÈME
class Theme(db.Model):
    __tablename__ = 'themes'
    id_theme = db.Column(db.Integer, primary_key=True)
    nom_theme = db.Column(db.String(100), nullable=False, unique=True)
    id_admin = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    admin = db.relationship('User')
    # CASCADE : Supprimer un thème supprime ses débats
    debats = db.relationship('Debat', backref='theme_backref', cascade="all, delete-orphan")

# MODÈLE DÉBAT
class Debat(db.Model):
    __tablename__ = 'debats'
    id_debat = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_limite = db.Column(db.DateTime, nullable=True)
    max_arguments = db.Column(db.Integer, default=50)
    statut = db.Column(db.String(20), default="ouvert")  # "ouvert" ou "fermé"

    # CASCADE : Supprimer un débat supprime ses arguments et ses votes globaux
    arguments = db.relationship('Argument', backref='debat_backref', cascade="all, delete-orphan")
    votes = db.relationship('Vote', backref='debat_backref', cascade="all, delete-orphan")
    
    id_theme = db.Column(db.Integer, db.ForeignKey('themes.id_theme'), nullable=False)
    id_createur = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    createur = db.relationship('User')

# MODÈLE ARGUMENT
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
    
    # CASCADE : Quand on supprime un parent, on supprime les enfants (réponses)
    enfants = db.relationship('Argument', backref=db.backref('parent', remote_side=[id_argument]), cascade="all, delete-orphan")
    
    # CASCADE : Supprimer un argument supprime ses likes/dislikes (VoteArgument)
    votes_recus = db.relationship('VoteArgument', backref='argument_concerne', cascade="all, delete-orphan")


# MODÈLE VOTE SUR ARGUMENT (LIKE/DISLIKE)

class VoteArgument(db.Model):
    __tablename__ = "votes_arguments"
    id_vote_arg = db.Column(db.Integer, primary_key=True)
    valeur = db.Column(db.Integer, nullable=False) # +1 pour like, -1 pour dislike
    
    id_user = db.Column(db.Integer, db.ForeignKey("users.iduser"), nullable=False)
    id_argument = db.Column(db.Integer, db.ForeignKey("arguments.id_argument"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("id_user", "id_argument", name="unique_vote_arg_per_user"),
    )

# MODÈLE VOTE SUR DÉBAT (POUR/CONTRE)
class Vote(db.Model):
    __tablename__ = "votes"
    id_vote = db.Column(db.Integer, primary_key=True)
    choix = db.Column(db.String(10), nullable=False) # "pour" ou "contre"
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    id_debat = db.Column(db.Integer, db.ForeignKey("debats.id_debat"), nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey("users.iduser"), nullable=False)
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("id_debat", "id_user", name="unique_vote_per_user_per_debat"),
    )


# INITIALISATION

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Base de données réinitialisée avec cascades.")

        # Création des utilisateurs de base
        admin = User(nom="Alice", prenom="Admin", role="admin")
        prof = User(nom="Bob", prenom="Prof", role="prof")
        etudiant = User(nom="Charlie", prenom="Etudiant", role="etudiant")
        db.session.add_all([admin, prof, etudiant])
        db.session.commit()

        print("Utilisateurs créés. Test d'initialisation terminé.")