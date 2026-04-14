from flask import render_template, request, redirect, url_for, session, jsonify, flash
from models import app, db, User, Theme, Debat, Argument, EvaluationArgument, FavoriArgument, Vote
from datetime import datetime
import functools

# calculer_forces_avec_soutiens
def calculer_forces_avec_soutiens(id_debat, max_iter=100, epsilon=1e-6):
    """
    Calcule la force de chaque argument dans un débat.
    Prend en entrée : id_debat (int), max_iter (int), epsilon (float).
    Renvoie un dictionnaire { id_argument : force (entre 0 et 1) }.

    Logique :
    - Pour chaque argument, on récupère sa note moyenne (0-4) donnée par les utilisateurs.
    - Cette note est convertie en poids initial w(a) = moyenne / 4.
    - On regarde tous les enfants de l'argument : ceux de type 'soutien' aident à augmenter la force,  
    ceux de type 'attaque' la diminuent.
    - La formule utilisée est : v(a) = (w(a) + somme des forces des soutiens) / (1 + somme des forces des soutiens + somme des forces des attaques)
    - On répète le calcul plusieurs fois (itérations) jusqu'à ce que les valeurs ne changent presque plus.
    - Ceci garantit que la force reste toujours entre 0 et 1.
    """
    arguments = Argument.query.filter_by(id_debat=id_debat).all()
    if not arguments:
        return {}

    # Poids initial à partir des évaluations
    w = {}
    for arg in arguments:
        evaluations = EvaluationArgument.query.filter_by(id_argument=arg.id_argument).all()
        if evaluations:
            moyenne = sum(e.note for e in evaluations) / len(evaluations)
            w[arg.id_argument] = moyenne / 4.0
        else:
            w[arg.id_argument] = 0.5

    # Construire les listes des soutiens et des attaquants pour chaque argument
    soutiens = {arg.id_argument: [] for arg in arguments}
    attaquants = {arg.id_argument: [] for arg in arguments}
    for arg in arguments:
        for enfant in arg.enfants:
            if enfant.type_arg == 'soutien':
                soutiens[arg.id_argument].append(enfant.id_argument)
            elif enfant.type_arg == 'attaque':
                attaquants[arg.id_argument].append(enfant.id_argument)

    # Initialiser toutes les forces à 0.5
    v = {arg.id_argument: 0.5 for arg in arguments}

    # Itérations jusqu'à convergence
    for _ in range(max_iter):
        v_new = {}
        diff_max = 0.0
        for arg_id in v:
            somme_soutiens = sum(v.get(s_id, 0) for s_id in soutiens[arg_id])
            somme_attaques = sum(v.get(a_id, 0) for a_id in attaquants[arg_id])
            numerateur = w[arg_id] + somme_soutiens
            denominateur = 1 + somme_soutiens + somme_attaques
            v_new[arg_id] = numerateur / denominateur
            diff_max = max(diff_max, abs(v_new[arg_id] - v[arg_id]))
        v = v_new
        if diff_max < epsilon:
            break
    return v


# construire_arbre
def construire_arbre(id_debat, user_id, user_role):
    """
    Construit un arbre JSON qui représente tout le débat, utilisable par le graphique D3.js.
    Prend en entrée : id_debat (int), user_id (int), user_role (str).
    Renvoie un dictionnaire avec la racine "root" et ses enfants.

    Logique :
    - Récupère les forces de tous les arguments grâce à la fonction ci-dessus.
    - Récupère les favoris de l'utilisateur (les arguments qu'il a mis en étoile).
    - Parcourt récursivement tous les arguments à partir de ceux qui n'ont pas de parent (les racines).
    - Pour chaque argument, on crée un nœud contenant : son texte, son type, sa force, son auteur, sa date,
    s'il est favori, et si l'utilisateur courant a le droit de le supprimer (auteur ou admin/prof).
    - Les enfants sont construits de la même façon.
    - Finalement on retourne l'arbre complet.
    """
    debat = Debat.query.get(id_debat)
    if not debat:
        return None

    forces = calculer_forces_avec_soutiens(id_debat)
    favoris_ids = {f.id_argument for f in FavoriArgument.query.filter_by(id_user=user_id).all()}
    tous_arguments = Argument.query.filter_by(id_debat=id_debat).all()

    def noeud(arg):
        force_bh = forces.get(arg.id_argument, 0.5)
        enfants = [e for e in tous_arguments if e.id_parent == arg.id_argument]
        nb_enfants = len(enfants)
        peut_supprimer = (user_id == arg.id_auteur) or (user_role in ['admin', 'prof'])
        return {
            "id": arg.id_argument,
            "texte": arg.texte,
            "type": arg.type_arg,
            "force_bh": round(force_bh, 3),
            "auteur": f"{arg.auteur.prenom} {arg.auteur.nom}",
            "date": arg.date_creation.strftime("%d/%m/%Y %H:%M"),
            "est_favori": arg.id_argument in favoris_ids,
            "peut_supprimer": peut_supprimer,
            "children": [noeud(e) for e in enfants]
        }

    racines = [arg for arg in tous_arguments if arg.id_parent is None]
    return {
        "id": "root",
        "texte": debat.titre,
        "type": "debat",
        "force_bh": None,
        "est_favori": False,
        "peut_supprimer": False,
        "children": [noeud(r) for r in racines]
    }


# login_required
def login_required(f):
    """
    Décorateur qui vérifie si l'utilisateur est connecté.
    Si la session ne contient pas "user_id", on affiche un message et on redirige vers la page d'accueil.
    Sinon, on exécute la fonction normalement.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Veuillez vous identifier", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


# index
@app.route("/", methods=["GET", "POST"])
def index():
    """
    Page d'entrée.
    En GET : affiche le formulaire (nom, prénom, rôle).
    En POST : crée un utilisateur s'il n'existe pas (en se basant sur nom+prénom),
    le stocke dans la session, puis redirige vers la page d'accueil des débats.
    """
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


# accueil
@app.route("/accueil")
@login_required
def accueil():
    """
    Page d'accueil après connexion.
    Affiche la liste des débats séparés en "ouverts" (non clos) et "fermés".
    Pour chaque débat, calcule le nombre de soutiens et d'attaques.
    Transmet aussi les thèmes disponibles.
    """
    user = User.query.get(session["user_id"])
    maintenant = datetime.now()

    themes = Theme.query.all()
    debats = Debat.query.all()

    ouverts_par_theme = {}
    fermes_par_theme = {}

    def init_theme_dict():
        return {t.id_theme: {"theme": t, "debats": []} for t in themes}

    ouverts_par_theme = init_theme_dict()
    fermes_par_theme = init_theme_dict()

    for d in debats:
        est_ferme = (d.statut != "ouvert") or (d.date_limite and maintenant > d.date_limite)

        d.nb_soutien = Argument.query.filter_by(id_debat=d.id_debat, type_arg='soutien').count()
        d.nb_attaque = Argument.query.filter_by(id_debat=d.id_debat, type_arg='attaque').count()

        if est_ferme:
            fermes_par_theme[d.id_theme]["debats"].append(d)
        else:
            ouverts_par_theme[d.id_theme]["debats"].append(d)

    return render_template(
        "accueil.html",
        user=user,
        ouverts_par_theme=ouverts_par_theme,
        fermes_par_theme=fermes_par_theme,
        themes=themes
    )

# creer_debat
@app.route("/creer_debat", methods=["GET", "POST"])
@login_required
def creer_debat():
    """
    Formulaire de création d'un nouveau débat.
    En GET : affiche le formulaire avec les thèmes existants.
    En POST : enregistre le débat (titre, description, thème, date limite) et redirige.
    """
    user = User.query.get(session["user_id"])
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


# debat
@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
@login_required
def debat(id_debat):
    """
    Page principale d'un débat.
    En GET : affiche le graphe interactif construit par construire_arbre().
    En POST : ajoute un nouvel argument (réponse) en lien avec le parent spécifié.
    Vérifie que le débat n'est pas clos avant d'ajouter.
    """
    user = User.query.get(session["user_id"])
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

    arbre = construire_arbre(id_debat, user.iduser, user.role)
    return render_template("debat.html", user=user, debat=debat_obj,
    arbre=arbre, maintenant=maintenant, est_clos=est_ferme)


# evaluer_argument
@app.route("/evaluer_argument/<int:id_argument>", methods=["POST"])
@login_required
def evaluer_argument(id_argument):
    """
    Permet à l'utilisateur de noter un argument (0 à 4).
    Récupère la note depuis le formulaire, crée ou modifie l'évaluation dans la base.
    Redirige ensuite vers la page précédente (le débat).
    """
    user_id = session.get("user_id")
    note = request.form.get("note", type=int)
    if note is None or note < 0 or note > 4:
        flash("Note invalide (0-4)", "danger")
        return redirect(request.referrer or url_for("accueil"))
    eval_existante = EvaluationArgument.query.filter_by(id_user=user_id, id_argument=id_argument).first()
    if eval_existante:
        eval_existante.note = note
    else:
        nouvelle_eval = EvaluationArgument(id_user=user_id, id_argument=id_argument, note=note)
        db.session.add(nouvelle_eval)
    db.session.commit()
    flash("Évaluation enregistrée", "success")
    return redirect(request.referrer or url_for("debat", id_debat=Argument.query.get(id_argument).id_debat))


# basculer_favori_argument
@app.route("/favori_argument/<int:id_argument>", methods=["POST"])
@login_required
def basculer_favori_argument(id_argument):
    """
    Ajoute ou retire un argument des favoris de l'utilisateur.
    Si l'argument est déjà favori, on le supprime ; sinon on l'ajoute.
    """
    user_id = session.get("user_id")
    favori = FavoriArgument.query.filter_by(id_user=user_id, id_argument=id_argument).first()
    if favori:
        db.session.delete(favori)
        flash("Retiré des favoris", "info")
    else:
        nouveau_favori = FavoriArgument(id_user=user_id, id_argument=id_argument)
        db.session.add(nouveau_favori)
        flash("Ajouté aux favoris", "success")
    db.session.commit()
    arg = Argument.query.get(id_argument)
    return redirect(url_for("debat", id_debat=arg.id_debat))


# api_forces_bh
@app.route("/api/debat/<int:id_debat>/forces")
@login_required
def api_forces_bh(id_debat):
    """
    API utilisée par le frontend (JavaScript) pour récupérer les forces des arguments sans recharger la page.
    Renvoie un JSON { id_argument: force }.
    """
    forces = calculer_forces_avec_soutiens(id_debat)
    return jsonify(forces)


# supprimer_debat
@app.route("/debat/<int:id_debat>/supprimer", methods=["POST"])
@login_required
def supprimer_debat(id_debat):
    """
    Supprime un débat. Seul son créateur, un professeur ou un administrateur peut le faire.
    """
    debat_obj = Debat.query.get_or_404(id_debat)
    user = User.query.get(session["user_id"])
    if user and (user.role in ['admin', 'prof'] or debat_obj.id_createur == user.iduser):
        db.session.delete(debat_obj)
        db.session.commit()
        flash("Débat supprimé", "success")
    return redirect(url_for("accueil"))


# supprimer_argument
@app.route("/argument/<int:id_argument>/supprimer", methods=["POST"])
@login_required
def supprimer_argument(id_argument):
    """
    Supprime un argument. Seul son auteur, un professeur ou un administrateur peut le faire.
    """
    arg = Argument.query.get_or_404(id_argument)
    id_debat = arg.id_debat
    user = User.query.get(session["user_id"])
    if user and (user.role in ['admin', 'prof'] or arg.id_auteur == user.iduser):
        db.session.delete(arg)
        db.session.commit()
        flash("Argument supprimé", "success")
    else:
        flash("Vous n'avez pas le droit de supprimer cet argument", "danger")
    return redirect(url_for("debat", id_debat=id_debat))


# ajouter_theme
@app.route("/ajouter_theme", methods=["POST"])
@login_required
def ajouter_theme():
    """
    Ajoute un nouveau thème. Réservé aux administrateurs.
    Récupère le nom du thème depuis le formulaire et le sauvegarde.
    """
    user = User.query.get(session["user_id"])
    if user and user.role == 'admin':
        nom = request.form.get("nom_theme")
        if nom:
            nouveau_theme = Theme(nom_theme=nom, id_admin=user.iduser)
            db.session.add(nouveau_theme)
            db.session.commit()
            flash("Thème ajouté", "success")
    return redirect(url_for("accueil"))


# logout
@app.route("/logout")
def logout():
    """
    Déconnecte l'utilisateur en vidant la session, puis redirige vers la page d'accueil.
    """
    session.clear()
    return redirect(url_for("index"))


# mon_historique
@app.route("/mon_historique")
@login_required
def mon_historique():
    """
    Affiche l'historique de l'utilisateur connecté : arguments, votes, évaluations et favoris.
    Trie le tout par date décroissante.
    """
    user = User.query.get(session["user_id"])
    arguments = Argument.query.filter_by(id_auteur=user.iduser).order_by(Argument.date_creation.desc()).all()
    votes = Vote.query.filter_by(id_user=user.iduser).order_by(Vote.date_creation.desc()).all()
    evaluations = EvaluationArgument.query.filter_by(id_user=user.iduser).order_by(EvaluationArgument.date_evaluation.desc()).all()
    favoris = FavoriArgument.query.filter_by(id_user=user.iduser).order_by(FavoriArgument.date_ajout.desc()).all()

    activites = []

    for arg in arguments:
        activites.append({
            "type": "argument",
            "date": arg.date_creation,
            "texte": arg.texte,
            "type_arg": arg.type_arg,
            "id_debat": arg.id_debat,
            "titre_debat": arg.debat_backref.titre
        })

    for vote in votes:
        activites.append({
            "type": "vote",
            "date": vote.date_creation,
            "choix": vote.choix,
            "id_debat": vote.id_debat,
            "titre_debat": vote.debat_backref.titre
        })

    for eval in evaluations:
        arg = Argument.query.get(eval.id_argument)
        if arg:
            activites.append({
                "type": "evaluation",
                "date": eval.date_evaluation,
                "note": eval.note,
                "texte_arg": arg.texte,
                "id_debat": arg.id_debat,
                "titre_debat": arg.debat_backref.titre
            })

    for favori in favoris:
        arg = Argument.query.get(favori.id_argument)
        if arg:
            activites.append({
                "type": "favori",
                "date": favori.date_ajout,
                "texte_arg": arg.texte,
                "id_debat": arg.id_debat,
                "titre_debat": arg.debat_backref.titre
            })

    activites.sort(key=lambda x: x["date"], reverse=True)
    return render_template("historique.html", user=user, activites=activites)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)