

from flask import Flask 
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uvoice.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__='users'
    iduser=db.Column(db.Integer, primary_key=True)
    nom=db.Column(db.String(100),nullable=False)
    prenom=db.Column(db.String(100),nullable=False)


class Etudiant(db.Model):
    __tablename__='etudiant'
    idetu=db.Column(db.Integer, db.ForeignKey('users.iduser'),primary_key=True)
    filiere=db.Column(db.String(100))

class Prof(db.Model):
    __tablename__ ='prof'
    idprof=db.Column(db.Integer,db.ForeignKey('users.iduser'),primary_key=True)
    module=db.Column(db.String(50))

class Admin(db.Model):
    __tablename__ = 'admin'
    idadmin=db.Column(db.Integer,db.ForeignKey('users.iduser'),primary_key=True)



# creation de la table de données 
if __name__ == '__main__':
    with app.app_context():
        # 1. On recrée la base proprement
        db.drop_all()
        db.create_all()
        print("Base de données initialisée.")

        # 2. Création d'un utilisateur "humain"
        nouvel_utilisateur = User(nom="Sekher", prenom="Nadine")
        db.session.add(nouvel_utilisateur)
        db.session.commit() # On commit pour générer l'ID
        print(f"Utilisateur {nouvel_utilisateur.nom} créé avec l'ID {nouvel_utilisateur.iduser}")

        # 3. On lui donne le rôle d'Etudiant (en utilisant son ID)
        nouvel_etudiant = Etudiant(idetu=nouvel_utilisateur.iduser, filiere="Informatique")
        db.session.add(nouvel_etudiant)
        db.session.commit()
        print(f"Rôle Etudiant ajouté pour {nouvel_utilisateur.prenom} en {nouvel_etudiant.filiere}")

        # 4. Vérification finale : On cherche l'étudiant et on affiche son nom (qui vient de la table User)
        test_etu = Etudiant.query.first()
        # On remonte vers la table User pour avoir le nom
        parent_info = User.query.get(test_etu.idetu)
        print(f"BRAVO NADINE LA STAR: {parent_info.prenom} {parent_info.nom} est bien dans la base ! ---")