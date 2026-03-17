from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
import os


import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'uvoice.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
    

class User(db.Model):
    __tablename__ = 'users'
    iduser = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / prof / etudiant

class Theme(db.Model):
    __tablename__ = 'themes'
    id_theme = db.Column(db.Integer, primary_key=True)
    nom_theme = db.Column(db.String(100), nullable=False, unique=True)
    id_admin = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    admin = db.relationship('User')


class Debat(db.Model):
    __tablename__ = 'debats'
    id_debat = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    max_arguments = db.Column(db.Integer, default=50)
    statut = db.Column(db.String(20), default="ouvert")  # "ouvert" ou "fermé"

    # Clés étrangères
    id_theme = db.Column(db.Integer, db.ForeignKey('themes.id_theme'), nullable=False)
    theme = db.relationship('Theme', backref='debats')
    id_createur = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    createur = db.relationship('User')

class Argument(db.Model):
    __tablename__ = 'arguments'
    id_argument = db.Column(db.Integer, primary_key=True)
    texte = db.Column(db.Text, nullable=False)
    type_arg = db.Column(db.String(20), nullable=False)  # soutien / attaque
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    id_debat = db.Column(db.Integer, db.ForeignKey('debats.id_debat'), nullable=False)
    debat = db.relationship('Debat', backref='arguments')
    id_auteur = db.Column(db.Integer, db.ForeignKey('users.iduser'), nullable=False)
    auteur = db.relationship('User')
    id_parent = db.Column(db.Integer, db.ForeignKey('arguments.id_argument'), nullable=True)
    #quand on supprime un parent , on supprime les enfants 
    enfants = db.relationship('Argument', backref=db.backref('parent', remote_side=[id_argument]), cascade="all,delete-orphan")
    votes_recus=db.relationship('VoteArgument',backref='argument_concerne',cascade="all,delete-orphan")


class VoteArgument(db.Model):
    __tablename__ = "votes_arguments"
    id_vote_arg = db.Column(db.Integer, primary_key=True)
    valeur = db.Column(db.Integer, nullable=False) # +1 pour like, -1 pour dislike
    
    id_user = db.Column(db.Integer, db.ForeignKey("users.iduser"), nullable=False)
    id_argument = db.Column(db.Integer, db.ForeignKey("arguments.id_argument"), nullable=False)

    # Sécurité : Un utilisateur ne vote qu'une fois par argument
    __table_args__ = (
        db.UniqueConstraint("id_user", "id_argument", name="unique_vote_arg_per_user"),
    )



class Vote(db.Model):
    __tablename__ = "votes"

    id_vote = db.Column(db.Integer, primary_key=True)

    # "pour" ou "contre"
    choix = db.Column(db.String(10), nullable=False)

    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    id_debat = db.Column(db.Integer, db.ForeignKey("debats.id_debat"), nullable=False)
    debat = db.relationship("Debat", backref="votes")

    id_user = db.Column(db.Integer, db.ForeignKey("users.iduser"), nullable=False)
    user = db.relationship("User")

    # Empêche un user de voter deux fois sur le même débat
    __table_args__ = (
        db.UniqueConstraint("id_debat", "id_user", name="unique_vote_per_user_per_debat"),
    )

def init_db():
    db.create_all()
    admin = User(nom="Alice", prenom="Admin", role="admin")
    prof = User(nom="Bob", prenom="Prof", role="prof")
    etudiant = User(nom="Charlie", prenom="Etudiant", role="etudiant")
    db.session.add_all([admin, prof, etudiant])
    db.session.commit()
    return admin, prof, etudiant
    
if __name__ == '__main__':
    with app.app_context():
        # Recréation propre de la base
        db.drop_all()
        db.create_all()
        print("Base de données initialisée.")

        # Création utilisateurs
        admin = User(nom="Alice", prenom="Admin", role="admin")
        prof = User(nom="Bob", prenom="Prof", role="prof")
        etudiant = User(nom="Charlie", prenom="Etudiant", role="etudiant")
        db.session.add_all([admin, prof, etudiant])
        db.session.commit()



        print("Test complet terminé.")
