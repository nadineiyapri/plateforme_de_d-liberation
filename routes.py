from flask import render_template, request, redirect, url_for, session
from models import app, db, User, Theme, Debat, Argument, Vote

app.secret_key = "rouge_secret"


# ─────────────────────────────────────────────
# PAGE D'ACCUEIL : saisir nom + prénom + rôle
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# PAGE ACCUEIL APRÈS CONNEXION
# ─────────────────────────────────────────────
@app.route("/accueil")
def accueil():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    themes = Theme.query.all()
    debats = Debat.query.all()
    return render_template("accueil.html", user=user, themes=themes, debats=debats)


# ─────────────────────────────────────────────
# CRÉER UN THÈME (admin seulement)
# ─────────────────────────────────────────────
@app.route("/creer_theme", methods=["GET", "POST"])
def creer_theme():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    erreur = None
    if request.method == "POST":
        titre = request.form["titre"]
        if user.role != "admin":
            erreur = "Seul un admin peut créer un thème."
        else:
            theme = Theme(nom_theme=titre, id_admin=user.iduser)
            db.session.add(theme)
            db.session.commit()
            return redirect(url_for("accueil"))

    return render_template("creer_theme.html", user=user, erreur=erreur)


# ─────────────────────────────────────────────
# CRÉER UN DÉBAT
# ─────────────────────────────────────────────
@app.route("/creer_debat", methods=["GET", "POST"])
def creer_debat():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    themes = Theme.query.all()

    if request.method == "POST":
        titre       = request.form["titre"]
        description = request.form["description"]
        id_theme    = int(request.form["id_theme"])

        debat = Debat(titre=titre, description=description, id_theme=id_theme, id_createur=user.iduser)
        db.session.add(debat)
        db.session.commit()
        return redirect(url_for("accueil"))

    return render_template("creer_debat.html", user=user, themes=themes)


# ─────────────────────────────────────────────
# FONCTION : construire l'arbre JSON d'un débat
# C'est la même logique que get_graph_json() dans fonctions.py
# mais on la met ici pour garder routes.py autonome
# ─────────────────────────────────────────────
def construire_arbre(id_debat):
    debat = Debat.query.get(id_debat)
    if not debat:
        return None

    # Fonction récursive : transforme un argument en dict avec ses enfants
    def noeud(arg):
        return {
            "id":      arg.id_argument,
            "texte":   arg.texte,
            "type":    arg.type_arg,   # "soutien" ou "attaque"
            "enfants": [noeud(e) for e in arg.enfants]
        }

    # Les arguments racines sont ceux sans parent
    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()

    return {
        "id":      "root",
        "texte":   debat.titre,
        "type":    "debat",
        "enfants": [noeud(r) for r in racines]
    }


## PAGE D'UN DÉBAT : graphe interactif + formulaire
# ─────────────────────────────────────────────
@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
def debat(id_debat):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    debat_obj = Debat.query.get_or_404(id_debat)

    # Empêcher d'ajouter des arguments si le débat est fermé

    if request.method == "POST" and debat_obj.statut != "ouvert":
        arbre = construire_arbre(id_debat)
        return render_template(
            "debat.html",
            user=user,
            debat=debat_obj,
            arbre=arbre,
            erreur="Ce débat est fermé. Impossible d'ajouter un argument."
        )



    # Appliquer la limite max_arguments

    if request.method == "POST":
        nb_args = Argument.query.filter_by(id_debat=id_debat).count()
        if nb_args >= debat_obj.max_arguments:
            arbre = construire_arbre(id_debat)
            return render_template(
                "debat.html",
                user=user,
                debat=debat_obj,
                arbre=arbre,
                erreur="Limite d'arguments atteinte pour ce débat."
            )

    if request.method == "POST":
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

    # On construit l'arbre JSON et on l'envoie au template
    arbre = construire_arbre(id_debat)

    pour = Vote.query.filter_by(id_debat=id_debat, choix="pour").count()
    contre = Vote.query.filter_by(id_debat=id_debat, choix="contre").count()
    mon_vote = Vote.query.filter_by(id_debat=id_debat, id_user=user.iduser).first() 

    return render_template("debat.html", user=user, debat=debat_obj, arbre=arbre, pour=pour, contre=contre, mon_vote=mon_vote)

# ─────────────────────────────────────────────
# VOTER POUR UN DÉBAT
# ─────────────────────────────────────────────
@app.route("/debat/<int:id_debat>/vote", methods=["POST"])
def voter(id_debat):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("index"))

    debat_obj = Debat.query.get_or_404(id_debat)

    choix = request.form.get("choix")  # "pour" ou "contre"
    if choix not in ("pour", "contre"):
        return redirect(url_for("debat", id_debat=id_debat))

    # Un seul vote par user et par débat : on met à jour si déjà voté
    vote = Vote.query.filter_by(id_debat=id_debat, id_user=user.iduser).first()
    if vote:
        vote.choix = choix
    else:
        vote = Vote(choix=choix, id_debat=id_debat, id_user=user.iduser)
        db.session.add(vote)

    db.session.commit()
    return redirect(url_for("debat", id_debat=id_debat))
# ─────────────────────────────────────────────
# LANCEMENT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
