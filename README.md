
# U-Voice – Plateforme de Délibération

## members  
Do Cécilia.  
OuldLhadj Narimane.  
Tuyishime Cedrick.  
Sekher Nadine.  
Menasria AbdelDjallil.  



U-Voice est une application web permettant la création et la gestion de débats structurés sous forme d’arbre d’arguments, avec système de vote et décision finale formelle.


##  Objectif du projet

- La création de thèmes de discussion
- L’ouverture de débats associés à un thème
- L’ajout d’arguments hiérarchisés (soutien / attaque)
- La visualisation des débats sous forme d’arbre interactif
- Le vote des utilisateurs (pour / contre)
- La publication d’une décision finale justifiée



cd existing_repo
git remote add origin https://gitlabsu.sorbonne-universite.fr/lu2in013/fev2026/gr3/rouge.git
git branch -M main
git push -uf origin main


rouge/
│
├── models.py # Modèles de données (SQLAlchemy)
├── routes.py # Routes Flask et logique métier
├── templates/ # Interfaces HTML (Jinja2 + D3.js)
├── instance/ # Base SQLite locale
└── README.md



### User
Représente un utilisateur avec un rôle :
- admin
- prof
- etudiant


### Theme
Regroupe plusieurs débats.

### Debat
Contient :
- titre
- description
- statut (ouvert / fermé)
- limite maximale d’arguments


### Argument
Élément hiérarchique lié à un débat :
- type : soutien / attaque
- structure en arbre (parent / enfants)


### Vote
Permet à un utilisateur de voter :
- pour
- contre  
Un seul vote est autorisé par utilisateur et par débat.



### Decision
Décision finale d’un débat :
- résultat : accepté / rejeté
- justification obligatoire
- fermeture automatique du débat



##  Fonctionnalités principales

### Gestion des débats
- Création de débats
- Limitation du nombre d’arguments
- Blocage automatique si débat fermé

###  Visualisation graphique
- Représentation dynamique des arguments avec D3.js
- Structure hiérarchique parent / enfant

###  Système de vote
- Vote pour / contre
- Contrainte d’unicité (1 vote par utilisateur)
- Affichage des statistiques en temps réel

###  Gestion du statut
- Fermeture / réouverture d’un débat (admin / prof)
- Interdiction d’ajouter des arguments si débat fermé

### Décision finale
- Publication d’une décision officielle
- Justification obligatoire
- Fermeture automatique après décision

##  Gestion des rôles

| Rôle      | Permissions |
|-----------|------------|
| Admin     | Créer thèmes, fermer/réouvrir débats, publier décisions |
| Prof      | Fermer/réouvrir débats, publier décisions |
| Étudiant  | Participer aux débats et voter |






git clone https://gitlabsu.sorbonne-universite.fr/lu2in013/fev2026/gr3/rouge.git
cd rouge


/bash
python -m venv .venv
source .venv/bin/activate




/bash
pip install Flask Flask-SQLAlchemy 



python routes.py
# puis ouvrir dans le navigateur:
 http://127.0.0.1:5000
 


## Technologies utilisées

-Python
-Flask
-SQLAlchemy
-SQLite
-Jinja2
-D3.js

## État du projet

Application fonctionnelle comprenant :
 Gestion complète des débats
 Système de vote
 Module de décision finale
 Visualisation graphique interactive
 Projet académique – Sorbonne Universite


