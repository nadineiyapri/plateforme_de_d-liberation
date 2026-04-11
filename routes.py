from flask import render_template, request, redirect, url_for, session
from models import app, db, User, Theme, Debat, Argument
from datetime import datetime

app.secret_key = "rouge_secret"

def calculer_besnard_hunter(id_debat):
    """
    Calcule la force sémantique des arguments selon Besnard & Hunter.
    v(a) = 1 / (1 + somme(v(attaquants)))
    """
    # 1. On force SQLAlchemy à rafraîchir les objets pour voir les nouveaux enfants
    db.session.expire_all()
    
    # 2. On récupère tous les arguments du débat
    arguments = Argument.query.filter_by(id_debat=id_debat).all()
    
    # 3. Initialisation : tous les arguments commencent avec une force de 1.0
    for a in arguments:
        a.score_v = 1.0
    
    # 4. Calcul itératif (Convergence de l'algorithme)
    for _ in range(10): 
        for a in arguments:
            # On ne prend que les enfants qui sont de type 'attaque'
            # Les 'soutiens' n'affaiblissent pas le score mathématique dans ce modèle
            attaquants = [e for e in a.enfants if e.type_arg == 'attaque']
            
            if attaquants:
                somme_attaques = sum([att.score_v for att in attaquants])
                # La formule officielle :
                a.score_v = 1 / (1 + somme_attaques)
            else:
                # Si personne ne l'attaque, sa force est maximale
                a.score_v = 1.0
                
    # 5. On enregistre les scores calculés en base de données
    db.session.commit()
    db.session.commit()

def construire_arbre(id_debat):
    """
    Génère la structure hiérarchique pour l'affichage du graphe D3.js.
    """
    debat = Debat.query.get(id_debat)
    if not debat:
        return None

    def noeud(arg):
        # Cette sous-fonction crée un dictionnaire pour chaque argument
        # et s'appelle elle-même pour ses enfants (récursion)
        return {
            "id": arg.id_argument,
            "texte": arg.texte,
            "type": arg.type_arg,     # 'soutien' ou 'attaque'
            "likes": arg.likes or 0,  # Pour afficher 👍 sur les cases
            "score_v": round(arg.score_v, 2), # La force calculée
            "enfants": [noeud(e) for e in arg.enfants]
        }

    # On récupère les arguments qui n'ont pas de parent (ceux qui répondent au sujet)
    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()
    
    # On retourne l'objet racine (le titre du débat)
    return {
        "id": "root",
        "texte": debat.titre,
        "type": "root",
        "enfants": [noeud(r) for r in racines]
    }

# --- ROUTES D'ACCÈS ET AUTHENTIFICATION ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nom, prenom, role = request.form["nom"], request.form["prenom"], request.form["role"]
        user = User.query.filter_by(nom=nom, prenom=prenom).first()
        if not user:
            user = User(nom=nom, prenom=prenom, role=role)
            db.session.add(user)
            db.session.commit()
        session["user_id"] = user.iduser
        return redirect(url_for("accueil"))
    return render_template("index.html")

@app.route("/accueil")
def accueil():
    user = User.query.get(session.get("user_id"))
    if not user: return redirect(url_for("index"))
    
    debats = Debat.query.all()
    themes = Theme.query.all()
    
    for d in debats:
        d.nb_soutien = Argument.query.filter_by(id_debat=d.id_debat, type_arg='soutien').count()
        d.nb_attaque = Argument.query.filter_by(id_debat=d.id_debat, type_arg='attaque').count()
        
    return render_template("accueil.html", user=user, debats=debats, themes=themes, maintenant=datetime.now())

# --- GESTION DES THÈMES ET DÉBATS ---
@app.route("/ajouter_theme", methods=["POST"])
def ajouter_theme():
    user = User.query.get(session.get("user_id"))
    if user and user.role == 'admin':
        nom = request.form.get("nom_theme")
        if nom:
            nouveau_theme = Theme(nom_theme=nom, id_admin=user.iduser)
            db.session.add(nouveau_theme)
            db.session.commit()
    return redirect(url_for("accueil"))

@app.route("/creer_debat", methods=["GET", "POST"])
def creer_debat():
    user = User.query.get(session.get("user_id"))
    if not user: return redirect(url_for("index"))

    if request.method == "POST":
        dt_limite = None
        date_str = request.form.get("date_limite")
        if date_str:
            dt_limite = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')

        nouveau_debat = Debat(
            titre=request.form.get("titre"),
            description=request.form.get("description"),
            id_theme=int(request.form.get("id_theme")),
            id_createur=user.iduser,
            date_limite=dt_limite,
            statut="ouvert"
        )
        db.session.add(nouveau_debat)
        db.session.commit()
        return redirect(url_for("accueil"))
    
    return render_template("creer_debat.html", user=user, themes=Theme.query.all())

# --- LA ROUTE DÉBAT (AFFICHAGE ET ARGUMENTS) ---
@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
def debat(id_debat):
    user = User.query.get(session.get("user_id"))
    if not user: return redirect(url_for("index"))

    debat_obj = Debat.query.get_or_404(id_debat)

    if request.method == "POST":
        id_parent_raw = request.form.get("id_parent")
        # On nettoie l'ID parent (D3 envoie parfois "root" ou des strings vides)
        id_parent = None
        if id_parent_raw and id_parent_raw not in ["", "null", "root", "undefined"]:
            id_parent = int(id_parent_raw)

        nouveau_arg = Argument(
            texte=request.form.get("texte"),
            type_arg=request.form.get("type_arg"), # 'attaque' ou 'soutien'
            id_debat=id_debat,
            id_auteur=user.iduser,
            id_parent=id_parent,
            likes=0,
            score_v=1.0
        )
        db.session.add(nouveau_arg)
        db.session.commit() # Étape A : On enregistre
        
        calculer_besnard_hunter(id_debat) # Étape B : On calcule sur la base à jour
        return redirect(url_for("debat", id_debat=id_debat))

    # Pour l'affichage (GET)
    calculer_besnard_hunter(id_debat) 
    arbre_data = construire_arbre(id_debat)
    dominant = Argument.query.filter_by(id_debat=id_debat).order_by(Argument.score_v.desc()).first()

    return render_template("debat.html", user=user, debat=debat_obj, 
                           arbre=arbre_data, argument_dominant=dominant)

# --- ACTIONS (VOTES, SUPPRESSIONS) ---
@app.route("/argument/<int:id_argument>/vote/<string:type_vote>", methods=["POST"])
def vote_argument(id_argument, type_vote):
    arg = Argument.query.get_or_404(id_argument)
    if type_vote == "like": arg.likes += 1
    elif type_vote == "dislike": arg.likes = max(0, arg.likes - 1)
    db.session.commit()
    return redirect(url_for("debat", id_debat=arg.id_debat))

@app.route("/debat/<int:id_debat>/supprimer", methods=["POST"])
def supprimer_debat(id_debat):
    user = User.query.get(session.get("user_id"))
    if user and user.role == 'admin':
        db.session.delete(Debat.query.get(id_debat))
        db.session.commit()
    return redirect(url_for("accueil"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Crée les tables si elles n'existent pas
    app.run(debug=True)