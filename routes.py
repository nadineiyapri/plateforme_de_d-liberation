from flask import render_template, request, redirect, url_for, session
from models import app, db, User, Theme, Debat, Argument, Vote
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
    tous_les_themes = Theme.query.all() # Ajouté pour afficher la gestion des thèmes
    maintenant = datetime.now()
    
    return render_template(
        "accueil.html", 
        user=user, 
        debats=tous_les_debats, 
        themes=tous_les_themes, # Transmis au template
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
    
    est_clos_par_temps = (debat_obj.date_limite and maintenant > debat_obj.date_limite)
    est_ferme = (debat_obj.statut != "ouvert" or est_clos_par_temps)

    if request.method == "POST":
        if est_ferme:
            return redirect(url_for("debat", id_debat=id_debat))

        texte     = request.form["texte"]
        type_arg  = request.form["type_arg"]
        id_parent = request.form.get("id_parent")
        
        # Gestion du parent vide (argument racine)
        actual_parent = None
        if id_parent and id_parent.strip() != "" and id_parent != "None":
            actual_parent = int(id_parent)

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
        return {
            "id":      arg.id_argument,
            "texte":   arg.texte,
            "type":    arg.type_arg,
            "enfants": [noeud(e) for e in arg.enfants]
        }

    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()
    return {
        "id":      "root",
        "texte":   debat.titre,
        "type":    "debat",
        "enfants": [noeud(r) for r in racines]
    }


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