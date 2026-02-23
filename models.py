from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uvoice.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__="users"
    id_user=db.Column(db.Integer, primary_key=True)
    nom=db.Column(db.String(100), nullable=False)
    prenom=db.Column(db.String(100), nullable=False)
    role=db.Column(db.String(20), nullable=False) #admin/prof/etudiant


class Theme(db.Model):
    __tablename='themes'
    id_theme=db.Column(db.Integer, primary_key=True)
    nom_theme=db.Column(db.String(100), nullable=False, unique=True)
    id_admin=db.Column(db.Integer, db.ForeignKey('users.id_user'))
    admin=db.relationship('User')


class Debat(db.Model):
    __tablename__='debats'
    id_debat=db.Column(db.Integer, primary_key=True)
    titre=db.Column(db.Text, nullable=False)
    description=db.Column(db.Text, nullable=False)
    date_creation=db.Column(db.DateTime, default=datetime.utcnow)
    max_arguments=db.Column(db.Integer, default=20)
    statut=db.Column(db.String(20), default='ouvert') #ouvert/fermé
    
    id_theme=db.Column(db.Integer, db.ForeignKey('themes.id_theme'), nullable=False)
    theme=db.relationship('Theme', backref='debats') #racourci pour acceder a theme depuis debat
    id_createur=db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False)
    createur = db.relationship('User')


class Argument(db.Model):
    __tablename__='arguments'
    id_argument=db.Column(db.Integer, primary_key=True)
    texte=db.Column(db.Text, nullable=False)
    type_arg=db.Column(db.String(20), nullable=False)#soutien/attaque
    date_creation=db.Column(db.DateTime, default=datetime.utcnow)
    like=db.Column(db.Integer, default=0)
    dislike=db.Column(db.Integer, default=0)
    
    id_auteur=db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False)
    auteur=db.relationship('User')
    id_debat=db.Column(db.Integer, db.ForeignKey('debats.id_debat'), nullable=False)
    debat=db.relationship('Debat', backref='arguments')
    id_parent=db.Column(db.Integer, db.ForeignKey('arguments.id_argument'))
    enfants=db.relationship('Argument', backref=db.backref('parent', remote_side=[id_argument]))#pointe vers le parent automatiquement, indique quelle coloone est la cle primaire

if __name__ == '__main__':
    with app.app_context():
        # Recréation propre de la base
        db.drop_all()
        db.create_all()
        print("Base de données initialisée.")


        #Création des utilisateurs
        users = [
            User(nom="Alice", prenom="Admin", role="admin"),
            User(nom="Bob", prenom="Prof", role="prof"),
            User(nom="Charlie", prenom="Etudiant", role="etudiant")
        ]
        db.session.add_all(users)
        db.session.commit()

        #Création de 3 thèmes (1 par admin)
        themes = [
            Theme(nom_theme="Écologie", id_admin=users[0].id_user),
            Theme(nom_theme="Éducation", id_admin=users[0].id_user),
            Theme(nom_theme="Technologie", id_admin=users[0].id_user)
        ]
        db.session.add_all(themes)
        db.session.commit()

        #Création de 3 débats par utilisateur
        debats = []
        for user in users:
            for i in range(3):
                debat = Debat(
                    titre=f"Débat {i+1} de {user.prenom}",
                    description=f"Description du débat {i+1} de {user.prenom}",
                    id_theme=random.choice(themes).id_theme,
                    id_createur=user.id_user
                )
                db.session.add(debat)
                debats.append(debat)
        db.session.commit()

        #Création de 3 arguments par débat
        for debat in debats:
            debat_arguments = []  # on garde les arguments du débat
            for i in range(3):
                # Pour le 2ᵉ ou 3ᵉ argument, on peut choisir un parent parmi les arguments existants
                if i == 0:
                    parent_id = None
                else:
                    parent_id = random.choice(debat_arguments).id_argument
                
                arg = Argument(
                    texte=f"Argument {i+1} du débat {debat.titre}",
                    type_arg=random.choice(['soutien', 'attaque']),
                    id_auteur=random.choice(users).id_user,
                    id_debat=debat.id_debat,
                    id_parent=parent_id
                )
                db.session.add(arg)
                db.session.flush()  # flush pour récupérer l'id avant commit
                debat_arguments.append(arg)
        db.session.commit()

        print("3 utilisateurs, 3 thèmes, 9 débats et 27 arguments créés !")