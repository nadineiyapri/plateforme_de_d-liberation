# rouge 
   
# U-Voice – Plateforme de Délibération

U-Voice est une application web permettant la création et la gestion de débats structurés sous forme d’arbre d’arguments, avec système de vote et décision finale formelle.

---

## Membres du groupe

- Do Cécilia  
- OuldLhadj Narimane  
- Tuyishime Cedrick  
- Sekher Nadine  
- Menasria AbdelDjallil  

---

##  Objectif du projet

Le projet U-Voice vise à proposer une plateforme permettant :

- La création de thèmes de discussion
- L’ouverture de débats associés à un thème
- L’ajout d’arguments hiérarchisés (soutien / attaque)
- La visualisation des débats sous forme d’arbre interactif
- Le vote des utilisateurs (pour / contre)
- La publication d’une décision finale justifiée

Le système met en place une logique de délibération structurée avec gestion des rôles et contrôle des permissions.

---

## 🧱 Architecture du projet

rouge/
│
├── models.py # Modèles de données (SQLAlchemy)
├── routes.py # Routes Flask et logique métier
├── fonctions.py # Construction et manipulation de l’arbre d’arguments
├── templates/ # Interfaces HTML (Jinja2 + D3.js)
├── instance/ # Base SQLite locale
└── README.md


---

## 🗄️ Modèles de données

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

---

## ⚙️ Fonctionnalités principales

### 🔹 Gestion des débats
- Création de débats
- Limitation du nombre d’arguments
- Blocage automatique si débat fermé

### 🔹 Visualisation graphique
- Représentation dynamique des arguments avec D3.js
- Structure hiérarchique parent / enfant

### 🔹 Système de vote
- Vote pour / contre
- Contrainte d’unicité (1 vote par utilisateur)
- Affichage des statistiques en temps réel

### 🔹 Gestion du statut
- Fermeture / réouverture d’un débat (admin / prof)
- Interdiction d’ajouter des arguments si débat fermé

### 🔹 Décision finale
- Publication d’une décision officielle
- Justification obligatoire
- Fermeture automatique après décision

---

## 🔒 Gestion des rôles

| Rôle      | Permissions |
|-----------|------------|
| Admin     | Créer thèmes, fermer/réouvrir débats, publier décisions |
| Prof      | Fermer/réouvrir débats, publier décisions |
| Étudiant  | Participer aux débats et voter |

---

## 🚀 Installation et lancement

### 1️⃣ Cloner le dépôt

```bash
git clone https://gitlabsu.sorbonne-universite.fr/lu2in013/fev2026/gr3/rouge.git
cd rouge

### 2️⃣ Créer un environnement virtue

/bash
python -m venv .venv
source .venv/bin/activate

### 3️⃣ Installer les dépendances

/bash
pip install Flask Flask-SQLAlchemy 

### 4️⃣ Lancer l’application

//bash
python routes.py
# puis ouvrir dans le navigateur:
 http://127.0.0.1:5000
 

##Technologies utilisées

-Python
-Flask
-SQLAlchemy
-SQLite
-Jinja2
-D3.js

##État du projet

Application fonctionnelle comprenant :
 Gestion complète des débats
 Système de vote
 Module de décision finale
 Visualisation graphique interactive
 Projet académique – Sorbonne Université
 
 
 

.


# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.


or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
