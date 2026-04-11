from flask import render_template, request, redirect, url_for, session, jsonify, flash
from models import app, db, User, Theme, Debat, Argument, VoteArgument, Vote
from datetime import datetime
import functools

# ------------------ Fonction Besnard & Hunter ------------------
def calculer_forces_besnard_hunter(id_debat, max_iter=100, epsilon=1e-6):
    arguments = Argument.query.filter_by(id_debat=id_debat).all()
    if not arguments:
        return {}
    attaquants = {arg.id_argument: [] for arg in arguments}
    for arg in arguments:
        for enfant in arg.enfants:
            if enfant.type_arg == 'attaque':
                attaquants[arg.id_argument].append(enfant.id_argument)
    v = {arg.id_argument: 0.5 for arg in arguments}
    for _ in range(max_iter):
        v_new = {}
        diff_max = 0.0
        for arg_id, att_list in attaquants.items():
            somme = sum(v.get(attaquant_id, 0) for attaquant_id in att_list)
            v_new[arg_id] = 1.0 / (1.0 + somme)
            diff_max = max(diff_max, abs(v_new[arg_id] - v[arg_id]))
        v = v_new
        if diff_max < epsilon:
            break
    return v

def construire_arbre(id_debat):
    debat = Debat.query.get(id_debat)
    if not debat:
        return None
    forces = calculer_forces_besnard_hunter(id_debat)
    tous_arguments = Argument.query.filter_by(id_debat=id_debat).all()
    def noeud(arg):
        score_classique = sum(v.valeur for v in arg.votes_recus)
        force_bh = forces.get(arg.id_argument, 0.5)
        enfants = [e for e in tous_arguments if e.id_parent == arg.id_argument]
        return {
            "id": arg.id_argument,
            "texte": arg.texte,
            "type": arg.type_arg,
            "score": score_classique,
            "force_bh": round(force_bh, 3),
            "auteur": f"{arg.auteur.prenom} {arg.auteur.nom}",
            "date": arg.date_creation.strftime("%d/%m/%Y %H:%M"),
            "children": [noeud(e) for e in enfants]
        }
    racines = [arg for arg in tous_arguments if arg.id_parent is None]
    return {
        "id": "root",
        "texte": debat.titre,
        "type": "debat",
        "score": 0,
        "force_bh": None,
        "children": [noeud(r) for r in racines]
    }

# ------------------ Routes ------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        role = request.form["role"]
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
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    user = User.query.get(user_id)
    maintenant = datetime.now()
    tous_les_debats = Debat.query.all()
    debats_ouverts = []
    debats_fermes = []
    for d in tous_les_debats:
        est_ferme = (d.statut != "ouvert") or (d.date_limite and maintenant > d.date_limite)
        if not est_ferme:
            debats_ouverts.append(d)
        else:
            debats_fermes.append(d)
    debats_ouverts.sort(key=lambda d: d.date_creation, reverse=True)
    debats_fermes.sort(key=lambda d: d.date_creation, reverse=True)
    for d in tous_les_debats:
        d.nb_soutien = Argument.query.filter_by(id_debat=d.id_debat, type_arg='soutien').count()
        d.nb_attaque = Argument.query.filter_by(id_debat=d.id_debat, type_arg='attaque').count()
    themes = Theme.query.all()
    return render_template("accueil.html", user=user, debats_ouverts=debats_ouverts,
                           debats_fermes=debats_fermes, themes=themes, maintenant=maintenant)

@app.route("/creer_debat", methods=["GET", "POST"])
def creer_debat():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    user = User.query.get(user_id)
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
                pass
        nouveau_debat = Debat(
            titre=titre, description=description,
            id_theme=int(id_theme) if id_theme and id_theme != "" else None,
            id_createur=user.iduser, date_limite=dt_limite, statut="ouvert"
        )
        db.session.add(nouveau_debat)
        db.session.commit()
        flash("Débat créé", "success")
        return redirect(url_for("accueil"))
    return render_template("creer_debat.html", user=user, themes=themes)

@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
def debat(id_debat):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    user = User.query.get(user_id)
    debat_obj = Debat.query.get_or_404(id_debat)
    maintenant = datetime.now()
    est_clos_par_temps = (debat_obj.date_limite and maintenant > debat_obj.date_limite)
    est_ferme = (debat_obj.statut != "ouvert" or est_clos_par_temps)

    if request.method == "POST" and not est_ferme:
        texte = request.form.get("texte")
        type_arg = request.form.get("type_arg")
        id_p_raw = request.form.get("id_parent")
        actual_parent = None
        if id_p_raw and id_p_raw not in ["", "None", "root"]:
            try:
                actual_parent = int(id_p_raw)
            except ValueError:
                pass
        arg = Argument(texte=texte, type_arg=type_arg, id_debat=id_debat,
                       id_auteur=user.iduser, id_parent=actual_parent)
        db.session.add(arg)
        db.session.commit()
        flash("Argument ajouté", "success")
        return redirect(url_for("debat", id_debat=id_debat))

    arbre = construire_arbre(id_debat)
    return render_template("debat.html", user=user, debat=debat_obj,
                           arbre=arbre, maintenant=maintenant, est_clos=est_ferme)

@app.route("/vote_argument/<int:id_argument>/<int:valeur>", methods=["POST"])
def vote_arg(id_argument, valeur):
    user_id = session.get("user_id")
    if not user_id:
        return "Non connecté", 401
    vote_existant = VoteArgument.query.filter_by(id_user=user_id, id_argument=id_argument).first()
    if vote_existant:
        if vote_existant.valeur == valeur:
            db.session.delete(vote_existant)
        else:
            vote_existant.valeur = valeur
    else:
        nouveau_vote = VoteArgument(id_user=user_id, id_argument=id_argument, valeur=valeur)
        db.session.add(nouveau_vote)
    db.session.commit()
    return "", 200

@app.route("/debat/<int:id_debat>/supprimer", methods=["POST"])
def supprimer_debat(id_debat):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    debat_obj = Debat.query.get_or_404(id_debat)
    user = User.query.get(user_id)
    if user and (user.role in ['admin', 'prof'] or debat_obj.id_createur == user.iduser):
        db.session.delete(debat_obj)
        db.session.commit()
        flash("Débat supprimé", "success")
    return redirect(url_for("accueil"))

@app.route("/argument/<int:id_argument>/supprimer", methods=["POST"])
def supprimer_argument(id_argument):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    arg = Argument.query.get_or_404(id_argument)
    id_debat = arg.id_debat
    user = User.query.get(user_id)
    if user and (user.role in ['admin', 'prof'] or arg.id_auteur == user.iduser):
        db.session.delete(arg)
        db.session.commit()
        flash("Argument supprimé", "success")
    return redirect(url_for("debat", id_debat=id_debat))

@app.route("/ajouter_theme", methods=["POST"])
def ajouter_theme():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    user = User.query.get(user_id)
    if user and user.role == 'admin':
        nom = request.form.get("nom_theme")
        if nom:
            nouveau_theme = Theme(nom_theme=nom, id_admin=user.iduser)
            db.session.add(nouveau_theme)
            db.session.commit()
            flash("Thème ajouté", "success")
    return redirect(url_for("accueil"))

@app.route("/api/debat/<int:id_debat>/forces")
def api_forces_bh(id_debat):
    forces = calculer_forces_besnard_hunter(id_debat)
    return jsonify(forces)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)