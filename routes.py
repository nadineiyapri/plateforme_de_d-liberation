from flask import render_template, request, redirect, url_for, session
from models import app, db, User, Theme, Debat, Argument, Vote
from datetime import datetime

app.secret_key = "rouge_secret"

# PAGE D'ENTRÉE : Connexion simplifiée
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


# ACCUEIL : Liste des débats (Ouverts / Clos)
@app.route("/accueil")
def accueil():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("index"))
    
    tous_les_debats = Debat.query.all()
    maintenant = datetime.now()
    
    return render_template(
        "accueil.html", 
        user=user, 
        debats=tous_les_debats, 
        maintenant=maintenant
    )


# CRÉATION D'UN DÉBAT
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
            id_theme=int(id_theme) if id_theme else None,
            id_createur=user.iduser,
            date_limite=dt_limite,
            statut="ouvert"
        )

        try:
            db.session.add(nouveau_debat)
            db.session.commit()
            return redirect(url_for("accueil"))
        except Exception as e:
            db.session.rollback()
            return render_template("creer_debat.html", user=user, themes=themes, erreur="Erreur lors de la création.")

    return render_template("creer_debat.html", user=user, themes=themes)



# LOGIQUE DE L'ARBRE (GRAPHE D3)
def construire_arbre(id_debat):
    debat = Debat.query.get(id_debat)
    if not debat:
        return None

    def noeud(arg):
        return {
            "id":      arg.id_argument,
            "texte":   arg.texte,
            "type":    arg.type_arg,
            "enfants": [noeud(e) for e in arg.enfants] # Utilise la relation 'enfants' de ton model
        }

    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()

    return {
        "id":      "root",
        "texte":   debat.titre,
        "type":    "debat",
        "enfants": [noeud(r) for r in racines]
    }


# PAGE DÉBAT : Visualisation et Participation

@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
def debat(id_debat):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    debat_obj = Debat.query.get_or_404(id_debat)
    maintenant = datetime.now()
    
    # Vérification fermeture (Temps ou Manuel)
    est_clos_par_temps = (debat_obj.date_limite and maintenant > debat_obj.date_limite)
    est_ferme = (debat_obj.statut != "ouvert" or est_clos_par_temps)

    if request.method == "POST":
        # Interdire l'ajout si fermé
        if est_ferme:
            return redirect(url_for("debat", id_debat=id_debat))

        # Vérifier limite max
        nb_args = Argument.query.filter_by(id_debat=id_debat).count()
        if nb_args >= debat_obj.max_arguments:
            arbre = construire_arbre(id_debat)
            return render_template("debat.html", user=user, debat=debat_obj, arbre=arbre, erreur="Limite d'arguments atteinte.", maintenant=maintenant)

        texte     = request.form["texte"]
        type_arg  = request.form["type_arg"]
        id_parent = request.form.get("id_parent")
        id_parent = int(id_parent) if id_parent else None

        arg = Argument(
            texte=texte,
            type_arg=type_arg,
            id_debat=id_debat,
            id_auteur=user.iduser,
            id_parent=id_parent
        )
        db.session.add(arg)
        db.session.commit()
        return redirect(url_for("debat", id_debat=id_debat))

    # Calcul des votes
    pour = Vote.query.filter_by(id_debat=id_debat, choix="pour").count()
    contre = Vote.query.filter_by(id_debat=id_debat, choix="contre").count()
    mon_vote = Vote.query.filter_by(id_debat=id_debat, id_user=user.iduser).first() 

    return render_template(
        "debat.html", 
        user=user, 
        debat=debat_obj, 
        arbre=construire_arbre(id_debat), 
        pour=pour, 
        contre=contre, 
        mon_vote=mon_vote,
        maintenant=maintenant
    )


# ACTIONS : Votes et Statut

@app.route("/debat/<int:id_debat>/vote", methods=["POST"])
def voter(id_debat):
    user_id = session.get("user_id")
    if not user_id: return redirect(url_for("index"))

    choix = request.form.get("choix")
    vote = Vote.query.filter_by(id_debat=id_debat, id_user=user_id).first()
    
    if vote:
        vote.choix = choix
    else:
        vote = Vote(choix=choix, id_debat=id_debat, id_user=user_id)
        db.session.add(vote)

    db.session.commit()
    return redirect(url_for("debat", id_debat=id_debat))


@app.route("/debat/<int:id_debat>/toggle_statut", methods=["POST"])
def toggle_statut_debat(id_debat):
    user = User.query.get(session.get("user_id"))
    if user and user.role in ("admin", "prof"):
        debat_obj = Debat.query.get_or_404(id_debat)
        debat_obj.statut = "fermé" if debat_obj.statut == "ouvert" else "ouvert"
        db.session.commit()
    return redirect(url_for("debat", id_debat=id_debat))


# SUPPRESSIONS (Admin / Créateur / Auteur)
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


@app.route("/theme/<int:id_theme>/supprimer", methods=["POST"])
def supprimer_theme(id_theme):
    user = User.query.get(session.get("user_id"))
    if user and user.role == 'admin':
        theme_obj = Theme.query.get_or_404(id_theme)
        db.session.delete(theme_obj)
        db.session.commit()
    return redirect(url_for("accueil"))


# DÉCONNEXION
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)