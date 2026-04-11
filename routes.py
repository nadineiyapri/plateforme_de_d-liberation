from flask import render_template, request, redirect, url_for, session
from models import app, db, User, Theme, Debat, Argument, VoteArgument
from datetime import datetime

app.secret_key = "rouge_secret"

# PAGE D'ENTRÉE
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nom    = request.form["nom"]
        prenom = request.form["prenom"]
        role   = request.form["role"]

        user = User.query.filter_by(nom=nom, prenom=prenom).first()
        if not user:
            user = User(nom=nom, prenom=prenom, role=role)
            db.session.add(user)
            db.session.commit()

        session["user_id"] = user.iduser
        return redirect(url_for("accueil"))

    return render_template("index.html")


# ACCUEIL : Liste des débats + Gestion des Thèmes
@app.route("/accueil")
def accueil():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("index"))
    
    tous_les_debats = Debat.query.all()
    
    # --- AJOUT ICI : Calculer les compteurs pour chaque débat ---
    for d in tous_les_debats:
        d.nb_soutien = Argument.query.filter_by(id_debat=d.id_debat, type_arg='soutien').count()
        d.nb_attaque = Argument.query.filter_by(id_debat=d.id_debat, type_arg='attaque').count()
    # ------------------------------------------------------------

    tous_les_themes = Theme.query.all()
    maintenant = datetime.now()
    
    return render_template(
        "accueil.html", 
        user=user, 
        debats=tous_les_debats, 
        themes=tous_les_themes,
        maintenant=maintenant
    )


# --- GESTION DES THÈMES (Nouveau) ---

@app.route("/ajouter_theme", methods=["POST"])
def ajouter_theme():
    # On récupère l'ID de l'utilisateur depuis la session
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    
    # On vérifie que l'utilisateur existe et qu'il est admin
    if user and user.role == 'admin':
        nom = request.form.get("nom_theme")
        if nom:
            # On passe l'id_admin (l'id de l'utilisateur actuel) pour respecter la contrainte SQL
            nouveau_theme = Theme(nom_theme=nom, id_admin=user.iduser)
            try:
                db.session.add(nouveau_theme)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Erreur SQL : {e}")
                
    return redirect(url_for("accueil"))


# --- GESTION DES DÉBATS ---

@app.route("/creer_debat", methods=["GET", "POST"])
def creer_debat():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    themes = Theme.query.all()

    if request.method == "POST":
        titre = request.form.get("titre")
        description = request.form.get("description")
        id_theme = request.form.get("id_theme")
        date_str = request.form.get("date_limite")
        
        dt_limite = None
        if date_str:
            try:
                dt_limite = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                dt_limite = None

        nouveau_debat = Debat(
            titre=titre,
            description=description,
            id_theme=int(id_theme) if id_theme and id_theme != "" else None,
            id_createur=user.iduser,
            date_limite=dt_limite,
            statut="ouvert"
        )

        db.session.add(nouveau_debat)
        db.session.commit()
        return redirect(url_for("accueil"))

    return render_template("creer_debat.html", user=user, themes=themes)


@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
def debat(id_debat):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))
        
    debat_obj = Debat.query.get_or_404(id_debat)
    maintenant = datetime.now()
    
    # Vérification si le débat est clos
    est_clos_par_temps = (debat_obj.date_limite and maintenant > debat_obj.date_limite)
    est_ferme = (debat_obj.statut != "ouvert" or est_clos_par_temps)

    if request.method == "POST":
        if est_ferme:
            return redirect(url_for("debat", id_debat=id_debat))
            
        texte = request.form.get("texte")
        type_arg = request.form.get("type_arg")
        id_p_raw = request.form.get("id_parent")
        
        # Sécurité : On nettoie l'ID parent pour Flask
        actual_parent = None
        if id_p_raw and id_p_raw not in ["", "None", "root"]:
            try:
                actual_parent = int(id_p_raw)
            except ValueError:
                actual_parent = None

        arg = Argument(
            texte=texte,
            type_arg=type_arg,
            id_debat=id_debat,
            id_auteur=user.iduser,
            id_parent=actual_parent
        )
        db.session.add(arg)
        db.session.commit()
        return redirect(url_for("debat", id_debat=id_debat))

    return render_template(
        "debat.html", 
        user=user, 
        debat=debat_obj, 
        arbre=construire_arbre(id_debat),
        maintenant=maintenant,
        est_clos=est_ferme
    )



# LOGIQUE DE L'ARBRE
def construire_arbre(id_debat):
    debat = Debat.query.get(id_debat)
    if not debat: return None
    
    def noeud(arg):
        # Calcul du score : Somme des +1 et -1
        score = sum(v.valeur for v in arg.votes_recus)
        return {
            "id": arg.id_argument,
            "texte": arg.texte,
            "type": arg.type_arg,
            "score": score, # Pour la taille de la bulle
            "children": [noeud(e) for e in arg.enfants]
        }
        
    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()
    return {
        "id": "root",
        "texte": debat.titre,
        "type": "debat",
        "score": 0,
        "children": [noeud(r) for r in racines]
    }
@app.route("/vote_argument/<int:id_argument>/<int:valeur>", methods=["POST"])
def vote_arg(id_argument, valeur):
    user_id = session.get("user_id")
    if not user_id: 
        return redirect(url_for("index"))
    
    # On cherche si l'utilisateur a déjà voté pour cet argument
    vote_existant = VoteArgument.query.filter_by(id_user=user_id, id_argument=id_argument).first()
    
    if vote_existant:
        if vote_existant.valeur == valeur:
            # Si on clique sur le même vote, on le retire (annuler)
            db.session.delete(vote_existant)
        else:
            # Si on change d'avis (ex: de like à dislike), on met à jour
            vote_existant.valeur = valeur
    else:
        # Nouveau vote (+1 pour like, -1 pour dislike)
        nouveau_vote = VoteArgument(id_user=user_id, id_argument=id_argument, valeur=valeur)
        db.session.add(nouveau_vote)
    
    db.session.commit()
    return redirect(request.referrer)

# SUPPRESSIONS
@app.route("/debat/<int:id_debat>/supprimer", methods=["POST"])
def supprimer_debat(id_debat):
    debat_obj = Debat.query.get_or_404(id_debat)
    user = User.query.get(session.get("user_id"))
    if user and (user.role in ['admin', 'prof'] or debat_obj.id_createur == user.iduser):
        db.session.delete(debat_obj)
        db.session.commit()
    return redirect(url_for("accueil"))


@app.route("/argument/<int:id_argument>/supprimer", methods=["POST"])
def supprimer_argument(id_argument):
    arg = Argument.query.get_or_404(id_argument)
    id_debat = arg.id_debat
    user = User.query.get(session.get("user_id"))
    if user and (user.role in ['admin', 'prof'] or arg.id_auteur == user.iduser):
        db.session.delete(arg)
        db.session.commit()
    return redirect(url_for("debat", id_debat=id_debat))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)