from flask import render_template, request, redirect, url_for, session, jsonify, flash
from models import app, db, User, Theme, Debat, Argument, EvaluationArgument, FavoriArgument, Vote
from datetime import datetime
import functools



# CALCUL DES FORCES DES ARGUMENTS (version soutiens + attaques)

def calculer_forces_avec_soutiens(id_debat, max_iter=100, epsilon=1e-6):
    """
    Calcule la force de chaque argument d’un débat en prenant en compte
    les soutiens (qui aident) et les attaques (qui affaiblissent).

    PARAMÈTRES:
        id_debat (int) : l’identifiant du débat
        max_iter (int) : nombre maximum d’itérations pour stabiliser le calcul
        (par défaut 100). Plus il est grand, plus le calcul
        est précis mais plus il prend du temps.
        epsilon (float) : seuil de précision. Quand les forces changent de
        moins de epsilon entre deux itérations, on s’arrête.

    RETOURNE:
        dict : { id_argument (int) : force (float entre 0 et 1) }

    LOGIQUE DÉTAILLÉE:
        1. On récupère tous les arguments du débat depuis la base de données.
        2. Pour chaque argument, on calcule son “poids initial” w(a) à partir
           des notes (1 à 5 étoiles) que les utilisateurs lui ont attribuées.
           - La moyenne des notes est transformée en nombre entre 0 et 1 avec
             la formule: (moyenne - 1) / 4. Ainsi, 1 donne 0, 5 donne 1.
           - Si personne n’a noté l’argument, on prend 0.5 (neutre).
        3. On construit deux dictionnaires:
           - soutiens[a] : liste des arguments qui soutiennent a
           - attaquants[a] : liste des arguments qui attaquent a
           Ces relations sont déterminées par le champ “type_arg” (soutien/attaque)
           et le lien “id_parent” (l’enfant soutient ou attaque son parent).
        4. On initialise toutes les forces à 0.5 (valeur de départ neutre).
        5. On répète le calcul max_iter fois ou jusqu’à convergence:
           - Pour chaque argument, on additionne les forces de ses soutiens
             et celles de ses attaquants (en prenant les valeurs de l’itération
             précédente).
           - On applique la formule:
               v(a) = (w(a) + somme_des_soutiens) / (1 + somme_des_soutiens + somme_des_attaques)
           - Cette formule garantit que le résultat est toujours entre 0 et 1.
           - On calcule la plus grande différence entre l’ancienne et la nouvelle
             force (pour savoir si le calcul a convergé).
        6. Si la plus grande différence est plus petite que epsilon, on arrête
           (le système est stable). Sinon, on continue.
    """
    # récupération des arguments
    arguments = Argument.query.filter_by(id_debat=id_debat).all()
    if not arguments:
        return {}

    #poids initial w(a) à partir des évaluations
    w = {}
    for arg in arguments:
        # On récupère toutes les évaluations (notes) que les utilisateurs ont données à cet argument
        evaluations = EvaluationArgument.query.filter_by(id_argument=arg.id_argument).all()
        if evaluations:
            # Moyenne des notes 
            moyenne = sum(e.note for e in evaluations) / len(evaluations)
            # Transformation : note 1 → 0, note 5 → 1
            w[arg.id_argument] = (moyenne - 1) / 4.0
        else:
            w[arg.id_argument] = 0.5   # note neutre quand personne n’a voté

    #construction des listes de soutiens et d’attaquants
    # On initialise deux dictionnaires : clé = id_argument, valeur = liste vide
    soutiens = {arg.id_argument: [] for arg in arguments}
    attaquants = {arg.id_argument: [] for arg in arguments}

    # Pour chaque argument, on regarde ses “enfants”
    for arg in arguments:
        for enfant in arg.enfants:
            if enfant.type_arg == 'soutien':
                soutiens[arg.id_argument].append(enfant.id_argument)
            elif enfant.type_arg == 'attaque':
                attaquants[arg.id_argument].append(enfant.id_argument)

    #initialisation des forces à 0.5
    v = {arg.id_argument: 0.5 for arg in arguments}

    # itérations (point fixe)
    for _ in range(max_iter):
        v_new = {}
        plus_grande_difference = 0.0

        for id_arg in v:
            # Somme des forces des soutiens de l’itération précédente
            somme_soutiens = sum(v.get(s_id, 0) for s_id in soutiens[id_arg])
            # Somme des forces des attaquants de l’itération précédente
            somme_attaques = sum(v.get(a_id, 0) for a_id in attaquants[id_arg])

            numerateur = w[id_arg] + somme_soutiens
            denominateur = 1 + somme_soutiens + somme_attaques
            v_new[id_arg] = numerateur / denominateur

            # On garde la différence la plus grande pour savoir si on a convergé
            diff = abs(v_new[id_arg] - v[id_arg])
            if diff > plus_grande_difference:
                plus_grande_difference = diff

        v = v_new
        # Si les forces ont très peu changé, on arrête
        if plus_grande_difference < epsilon:
            break

    return v



# CONSTRUCTION DE L'ARBRE JSON POUR D3.JS

def construire_arbre(id_debat, user_id, user_role):
    """
    Fabrique un arbre JSON (utilisable par la bibliothèque D3.js) à partir
    de tous les arguments d’un débat.

    PARAMÈTRES:
        id_debat (int) : l’identifiant du débat
        user_id (int) : l’identifiant de l’utilisateur connecté (pour savoir
                        quels arguments il a mis en favori)
        user_role (str) : son rôle (admin, prof, etudiant). Cela sert à déterminer
                         s’il a le droit de supprimer un argument.

    RETOURNE:
        dict : un arbre JSON avec une racine nommée "root". Chaque nœud contient:
            - id (int) : identifiant unique de l’argument
            - texte (str) : le contenu de l’argument
            - type (str) : "soutien" ou "attaque"
            - force_bh (float) : force calculée par la fonction ci-dessus
            - auteur (str) : prénom et nom de la personne qui a posté l’argument
            - date (str) : date de création formatée
            - est_favori (bool) : True si l’utilisateur connecté a mis une étoile
            - peut_supprimer (bool) : True si l’utilisateur a le droit de supprimer
            - children (list) : liste des arguments qui répondent directement à celui-ci

    LOGIQUE DÉTAILLÉE:
        - On récupère le débat. S’il n’existe pas, on retourne None.
        - On calcule les forces de tous les arguments du débat.
        - On récupère la liste des favoris de l’utilisateur (sous forme d’ensemble d’IDs).
        - On définit une fonction récursive “noeud” qui transforme un argument
          en dictionnaire. Les “enfants” sont les arguments dont le “id_parent”
          vaut l’ID de l’argument courant.
        - Les arguments “racines” sont ceux qui n’ont pas de parent (id_parent = None).
        - On retourne un dictionnaire racine spécial (root) avec le titre du débat
          et la liste des racines comme enfants.
    """
    debat = Debat.query.get(id_debat)
    if not debat:
        return None

    # Forces de tous les arguments (calculées avec soutiens + attaques)
    forces = calculer_forces_avec_soutiens(id_debat)

    # Ensemble des ids des arguments que l’utilisateur a mis en favori
    # Un ensemble permet de tester l’appartenance très rapidement
    favoris_ids = {f.id_argument for f in FavoriArgument.query.filter_by(id_user=user_id).all()}

    # Tous les arguments du débat (nécessaire pour la récursion)
    tous_arguments = Argument.query.filter_by(id_debat=id_debat).all()

    # Fonction récursive qui transforme un argument et tous ses descendants
    def noeud(arg):
        force_bh = forces.get(arg.id_argument, 0.5)
        # On cherche les enfants de l’argument courant
        enfants = [e for e in tous_arguments if e.id_parent == arg.id_argument]
        # Droit de suppression: l’utilisateur est l’auteur OU son rôle est admin ou prof
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

    # Les arguments racines (ceux qui n’ont pas de parent)
    racines = [arg for arg in tous_arguments if arg.id_parent is None]

    # Arbre final avec une racine artificielle "root"
    return {
        "id": "root",
        "texte": debat.titre,
        "type": "debat",
        "force_bh": None,
        "est_favori": False,
        "peut_supprimer": False,
        "children": [noeud(r) for r in racines]
    }


# DÉCORATEUR : OBLIGATION D'ÊTRE CONNECTÉ

def login_required(f):
    """
    Décorateur qui s’applique aux routes protégées.
    Quand on écrit @login_required au-dessus d’une fonction, cette fonction
    ne sera exécutée que si l’utilisateur est connecté (c’est-à-dire si la
    session contient la clé "user_id").

    Si l’utilisateur n’est pas connecté:
        - On affiche un message flash "Veuillez vous identifier"
        - On le redirige vers la page d’accueil ("/")
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Veuillez vous identifier", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function



# PAGE D’ENTRÉE (première arrivée sur le site)

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Page d’entrée du site.
    - GET : affiche le formulaire pour saisir nom, prénom et rôle.
    - POST : crée l’utilisateur s’il n’existe pas, le connecte (enregistrement
             de son id dans la session) et redirige vers la page d’accueil.
    """
    if request.method == "POST":
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        role = request.form["role"]

        # On cherche un utilisateur avec exactement le même nom et prénom
        user = User.query.filter_by(nom=nom, prenom=prenom).first()
        if not user:
            user = User(nom=nom, prenom=prenom, role=role)
            db.session.add(user)
            db.session.commit()

        # Connexion : on stocke l’id dans la session 
        session["user_id"] = user.iduser
        return redirect(url_for("accueil"))
    return render_template("index.html")



# PAGE D’ACCUEIL (liste des débats après connexion)

@app.route("/accueil")
@login_required   # Protégée : on ne peut y accéder sans être connecté
def accueil():
    """
    Page d’accueil après connexion.
    Affiche les débats regroupés par thème, séparés en deux sections:
        - Débats ouverts (couleur violette)
        - Débats fermés (couleur grise)
    Calcule aussi pour chaque débat le nombre de soutiens et d’attaques.
    """
    user = User.query.get(session["user_id"])
    maintenant = datetime.now()
    themes = Theme.query.all()
    debats = Debat.query.all()

    # Création de deux dictionnaires: un pour les débats ouverts, un pour les fermés
    # Chaque thème a sa propre liste de débats
    ouverts_par_theme = {t.id_theme: {"theme": t, "debats": []} for t in themes}
    fermes_par_theme = {t.id_theme: {"theme": t, "debats": []} for t in themes}

    for d in debats:
        # Un débat est fermé si son statut n’est plus "ouvert" ou si la date limite est dépassée
        est_ferme = (d.statut != "ouvert") or (d.date_limite and maintenant > d.date_limite)

        # Compteurs pour l’affichage (nombre d’arguments de soutien et d’attaque)
        d.nb_soutien = Argument.query.filter_by(id_debat=d.id_debat, type_arg='soutien').count()
        d.nb_attaque = Argument.query.filter_by(id_debat=d.id_debat, type_arg='attaque').count()

        if est_ferme:
            fermes_par_theme[d.id_theme]["debats"].append(d)
        else:
            ouverts_par_theme[d.id_theme]["debats"].append(d)

    return render_template("accueil.html", user=user, ouverts_par_theme=ouverts_par_theme,
fermes_par_theme=fermes_par_theme, themes=themes)


# CRÉATION D’UN NOUVEAU DÉBAT

@app.route("/creer_debat", methods=["GET", "POST"])
@login_required
def creer_debat():
    """
    Formulaire pour créer un nouveau débat.
    - GET : affiche le formulaire avec la liste des thèmes.
    - POST : vérifie les champs, crée le débat (un thème est obligatoire)
             et redirige vers l’accueil.
    """
    user = User.query.get(session["user_id"])
    themes = Theme.query.all()

    if request.method == "POST":
        titre = request.form.get("titre", "").strip()
        description = request.form.get("description", "").strip()
        id_theme = request.form.get("id_theme")
        date_str = request.form.get("date_limite")

        # Vérifier si le titre existe déjà dans ce thème
        if titre and id_theme:
            existant = Debat.query.filter(
                Debat.titre.ilike(titre), 
                Debat.id_theme == int(id_theme)
            ).first()
            
            if existant:
                flash(f"Le débat '{titre}' existe déjà dans ce thème.", "warning")
                return render_template("creer_debat.html", user=user, themes=themes)

        # Gestion de la date
        dt_limite = None
        if date_str:
            try:
                dt_limite = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        nouveau_debat = Debat(
            titre=titre, 
            description=description,
            id_theme=int(id_theme),
            id_createur=user.iduser, 
            date_limite=dt_limite, 
            statut="ouvert"
        )
        db.session.add(nouveau_debat)
        db.session.commit()
        flash("Débat créé !", "success")
        return redirect(url_for("debat", id_debat=nouveau_debat.id_debat))
    return render_template("creer_debat.html", user=user, themes=themes)


# PAGE D’UN DÉBAT (graphe interactif + ajout d’arguments)

@app.route("/debat/<int:id_debat>", methods=["GET", "POST"])
@login_required
def debat(id_debat):
    """
    Page principale d’un débat.
    - GET : affiche le graphe interactif construit par construire_arbre().
    - POST : ajoute un nouvel argument en réponse à l’argument parent choisi.
             Le débat ne doit pas être clos.
    """
    user = User.query.get(session["user_id"])
    debat_obj = Debat.query.get_or_404(id_debat)
    maintenant = datetime.now()

    est_clos = (debat_obj.statut != "ouvert") or (debat_obj.date_limite and maintenant > debat_obj.date_limite)

    if request.method == "POST" and not est_clos:
        texte = request.form.get("texte", "").strip()
        type_arg = request.form.get("type_arg")
        id_parent_raw = request.form.get("id_parent")

        if not texte:
            flash("L'argument ne peut pas être vide.", "danger")
            return redirect(url_for("debat", id_debat=id_debat))

        # On regarde si cet argument exact existe déjà DANS CE DÉBAT
        doublon = Argument.query.filter(
            Argument.id_debat == id_debat,
            Argument.texte.ilike(texte)
        ).first()

        if doublon:
            flash("Cet argument a déjà été proposé dans ce débat.", "warning")
            return redirect(url_for("debat", id_debat=id_debat))

        # Gestion du parent
        parent_id = None
        if id_parent_raw and id_parent_raw not in ["", "None", "root"]:
            try:
                parent_id = int(id_parent_raw)
            except ValueError:
                pass

        arg = Argument(texte=texte, type_arg=type_arg, id_debat=id_debat,
                       id_auteur=user.iduser, id_parent=parent_id)
        db.session.add(arg)
        db.session.commit()
        flash("Argument ajouté", "success")
        return redirect(url_for("debat", id_debat=id_debat))

    arbre = construire_arbre(id_debat, user.iduser, user.role)
    return render_template("debat.html", user=user, debat=debat_obj,
                           arbre=arbre, maintenant=maintenant, est_clos=est_clos)


# ÉVALUATION D’UN ARGUMENT (note 1-5 étoiles)

@app.route("/evaluer_argument/<int:id_argument>", methods=["POST"])
@login_required
def evaluer_argument(id_argument):
    """
    Permet à l’utilisateur de noter la pertinence d’un argument (1 à 5 étoiles).
    - id_argument : l’argument noté.
    - La note est prise dans le formulaire (champ "note").
    """
    user_id = session.get("user_id")
    note = request.form.get("note", type=int)

    if note is None or note < 1 or note > 5:
        flash("Note invalide (1-5)", "danger")
        return redirect(request.referrer or url_for("accueil"))

    # On vérifie si l’utilisateur a déjà noté cet argument
    eval_existante = EvaluationArgument.query.filter_by(id_user=user_id, id_argument=id_argument).first()
    if eval_existante:
        eval_existante.note = note        # on écrase l’ancienne note
    else:
        nouvelle_eval = EvaluationArgument(id_user=user_id, id_argument=id_argument, note=note)
        db.session.add(nouvelle_eval)

    db.session.commit()
    flash("Évaluation enregistrée", "success")
    return redirect(request.referrer or url_for("debat", id_debat=Argument.query.get(id_argument).id_debat))


# AJOUT / RETRAIT D’UN ARGUMENT DANS LES FAVORIS

@app.route("/favori_argument/<int:id_argument>", methods=["GET","POST"])
@login_required
def basculer_favori_argument(id_argument):
    """
    Ajoute ou retire un argument des favoris de l’utilisateur.
    Un favori signifie que cet argument a changé son avis.
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


# API : RENVOIE LES FORCES BH (utilisée par D3.js)

@app.route("/api/debat/<int:id_debat>/forces")
@login_required
def api_forces_bh(id_debat):
    """
    API (interface pour le JavaScript) qui renvoie les forces BH de tous les
    arguments du débat au format JSON.
    Utilisé par le front D3.js pour rafraîchir les forces sans recharger la page.
    """
    forces = calculer_forces_avec_soutiens(id_debat)
    return jsonify(forces)



# API : STATISTIQUES DES ÉVALUATIONS D’UN ARGUMENT

@app.route("/api/argument/<int:id_argument>/stats")
@login_required
def api_stats_argument(id_argument):
    """
    API qui renvoie les statistiques des évaluations (notes 1-5) pour un argument.
    Retourne un JSON avec:
        - stats : nombre de notes pour chaque valeur (1 à 5)
        - total : nombre total d’évaluations
        - moyenne : note moyenne (sur 5)
        - note_utilisateur : note donnée par l’utilisateur connecté (ou None)
    """
    arg = Argument.query.get_or_404(id_argument)
    evaluations = EvaluationArgument.query.filter_by(id_argument=id_argument).all()

    # Initialisation du compteur (aucune note au départ)
    stats = {1:0, 2:0, 3:0, 4:0, 5:0}
    for e in evaluations:
        stats[e.note] += 1

    total = len(evaluations)
    moyenne = sum(e.note for e in evaluations) / total if total > 0 else 3
    user_id = session.get("user_id")

    # On cherche si l’utilisateur a déjà voté pour cet argument
    note_user = next((e.note for e in evaluations if e.id_user == user_id), None)

    return jsonify({
        "stats": stats,
        "total": total,
        "moyenne": round(moyenne, 1),
        "note_utilisateur": note_user
    })



# API : RÉSULTAT DU DÉBAT (qui a gagné)

@app.route("/api/debat/<int:id_debat>/resultat")
@login_required
def api_resultat_debat(id_debat):
    """
    API qui calcule quel camp (POUR ou CONTRE) a gagné le débat.
    Prend en compte:
        - La force BH des arguments racines (ceux sans parent)
        - Le nombre de favoris (un argument qui a changé beaucoup d’avis
          voit son poids augmenté)
    Retourne un JSON avec:
        - pour : score du camp "pour"
        - contre : score du camp "contre"
        - gagnant : "POUR" ou "CONTRE"
    """
    # On ne prend que les arguments racines (sans parent)
    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()
    forces = calculer_forces_avec_soutiens(id_debat)

    score_pour = 0
    poids_pour = 0
    score_contre = 0
    poids_contre = 0

    for arg in racines:
        force = forces.get(arg.id_argument, 0.5)
        nb_favoris = FavoriArgument.query.filter_by(id_argument=arg.id_argument).count()
        # Poids social: chaque favori augmente le poids de 10% (ex: 1 favori → 1.1, 5 favoris → 1.5)
        poids_social = 1 + nb_favoris / 10

        if arg.type_arg == 'soutien':
            score_pour += force * poids_social
            poids_pour += poids_social
        else:   # attaque
            score_contre += force * poids_social
            poids_contre += poids_social

    resultat_pour = score_pour / poids_pour if poids_pour > 0 else 0
    resultat_contre = score_contre / poids_contre if poids_contre > 0 else 0

    return jsonify({
        "pour": round(resultat_pour, 3),
        "contre": round(resultat_contre, 3),
        "gagnant": "POUR" if resultat_pour > resultat_contre else "CONTRE"
    })



# SUPPRESSION D’UN DÉBAT

@app.route("/debat/<int:id_debat>/supprimer", methods=["POST"])
@login_required
def supprimer_debat(id_debat):
    """
    Supprime un débat et tout son contenu (arguments, évaluations, favoris…).
    - Seul le créateur du débat ou un administrateur peut le faire.
    - Les autres utilisateurs voient un message d’erreur.
    """
    debat_obj = Debat.query.get_or_404(id_debat)
    user = User.query.get(session["user_id"])

    if user.role == 'admin':
        db.session.delete(debat_obj)
        db.session.commit()
        flash("Débat supprimé avec succès", "success")
    elif user.iduser == debat_obj.id_createur:
        db.session.delete(debat_obj)
        db.session.commit()
        flash("Débat supprimé avec succès", "success")
    else:
        flash("Vous n'avez pas les droits nécessaires pour supprimer ce débat. Seul son auteur ou un administrateur peut le faire.", "danger")

    return redirect(url_for("accueil"))



# SUPPRESSION D’UN ARGUMENT

@app.route("/argument/<int:id_argument>/supprimer", methods=["POST"])
@login_required
def supprimer_argument(id_argument):
    """
    Supprime un argument (et tous ses enfants, car la relation en base de données
    est configurée avec "cascade").
    - Seul l’auteur de l’argument ou un administrateur peut le faire.
    """
    arg = Argument.query.get_or_404(id_argument)
    id_debat = arg.id_debat
    user = User.query.get(session["user_id"])

    if user.role == 'admin':
        db.session.delete(arg)
        db.session.commit()
        flash("Argument supprimé avec succès", "success")
    elif user.iduser == arg.id_auteur:
        db.session.delete(arg)
        db.session.commit()
        flash("Argument supprimé avec succès", "success")
    else:
        flash("Vous n'avez pas les droits pour supprimer cet argument. Seul son auteur ou un administrateur peut le faire.", "danger")

    return redirect(url_for("debat", id_debat=id_debat))


# AJOUT D’UN THÈME (admin uniquement)

@app.route("/ajouter_theme", methods=["POST"])
@login_required
def ajouter_theme():
    """
    Ajoute un nouveau thème. Seuls les administrateurs peuvent le faire. Verifie si il n'y a pas de doublons
    """
    user = User.query.get(session["user_id"])
    if user and user.role == 'admin':
        nom = request.form.get("nom_theme", "").strip()
        
        if nom:
            existant = Theme.query.filter(Theme.nom_theme.ilike(nom)).first()
            
            if existant:
                flash(f"Le thème '{nom}' existe déjà.", "warning")
            else:
                nouveau_theme = Theme(nom_theme=nom, id_admin=user.iduser)
                db.session.add(nouveau_theme)
                db.session.commit()
                flash("Thème ajouté", "success")
                
    return redirect(url_for("accueil"))


# SUPPRESSION D’UN THÈME (admin uniquement)

@app.route("/supprimer_theme/<int:id_theme>", methods=["POST"])
@login_required
def supprimer_theme(id_theme):
    """
    Supprime un thème (et tous ses débats, grâce à la cascade SQLAlchemy).
    Seuls les administrateurs peuvent le faire.
    """
    user = User.query.get(session["user_id"])
    if user and user.role == 'admin':
        theme = Theme.query.get_or_404(id_theme)
        db.session.delete(theme)
        db.session.commit()
        flash("Thème supprimé", "success")
    else:
        flash("Vous n'avez pas les droits", "danger")
    return redirect(url_for("accueil"))


# DÉCONNEXION

@app.route("/logout")
def logout():
    """
    Déconnecte l’utilisateur en vidant la session.
    Redirige vers la page d’accueil (index).
    """
    session.clear()
    return redirect(url_for("index"))


# HISTORIQUE DE L’UTILISATEUR

@app.route("/mon_historique")
@login_required
def mon_historique():
    """
    Affiche l’historique complet de l’utilisateur connecté :
        - arguments qu’il a créés
        - votes (pour/contre) qu’il a émis sur les débats
        - évaluations (notes 1-5) qu’il a données
        - arguments qu’il a mis en favori
    Le tout est trié du plus récent au plus ancien.
    """
    user = User.query.get(session["user_id"])

    # Récupération des Créations (Thèmes et Débats)
    mes_themes = Theme.query.filter_by(id_admin=user.iduser).all()
    mes_debats_crees = Debat.query.filter_by(id_createur=user.iduser).all()

    # Récupération des autres activités
    arguments = Argument.query.filter_by(id_auteur=user.iduser).all()
    evaluations = EvaluationArgument.query.filter_by(id_user=user.iduser).all()
    favoris = FavoriArgument.query.filter_by(id_user=user.iduser).all()

    activites = []

    # Ajouter les Thèmes créés
    for t in mes_themes:
        activites.append({
            "type": "theme",
            "date": datetime.utcnow(), # Ou ajoute un champ date_creation à ton modèle Theme
            "id_debat": None,
            "titre_debat": t.nom_theme
        })

    # Ajouter les Débats créés
    for d in mes_debats_crees:
        activites.append({
            "type": "debat",
            "date": d.date_creation,
            "id_debat": d.id_debat,
            "titre_debat": d.titre
        })

    # Ajouter tes Arguments avec Statistiques
    for arg in arguments:
        # Calcul simple des stats pour l'affichage
        nb_favs = len(arg.favoris_recus)
        notes = [e.note for e in arg.evaluations]
        moyenne = sum(notes) / len(notes) if notes else 0
        
        activites.append({
            "type": "argument",
            "date": arg.date_creation,
            "texte": arg.texte,
            "type_arg": arg.type_arg,
            "id_debat": arg.id_debat,
            "titre_debat": arg.debat_backref.titre,
            "nb_favoris": nb_favs,
            "moyenne_eval": round(moyenne, 1),
            "nb_votes": len(notes),
            "force_bh": getattr(arg, 'force_bh', 0) # Si tu as le champ, sinon 0
        })

    # Ajouter les Évaluations que tu as données
    for ev in evaluations:
        arg_cible = Argument.query.get(ev.id_argument)
        if arg_cible:
            activites.append({
                "type": "evaluation",
                "date": ev.date_evaluation,
                "note": ev.note,
                "texte_arg": arg_cible.texte,
                "id_debat": arg_cible.id_debat,
                "titre_debat": arg_cible.debat_backref.titre,
                "auteur_prenom": arg_cible.auteur.prenom,
                "auteur_nom": arg_cible.auteur.nom
            })

    # Ajouter les Favoris que tu as mis
    for fav in favoris:
        arg_cible = Argument.query.get(fav.id_argument)
        if arg_cible:
            activites.append({
                "type": "favori",
                "date": fav.date_ajout,
                "texte_arg": arg_cible.texte,
                "id_debat": arg_cible.id_debat,
                "titre_debat": arg_cible.debat_backref.titre,
                "auteur_prenom": arg_cible.auteur.prenom,
                "auteur_nom": arg_cible.auteur.nom
            })

    activites.sort(key=lambda x: x["date"], reverse=True)
    return render_template("historique.html", user=user, activites=activites)

# MODIFICATION DE LA DESCRIPTION D’UN DÉBAT (auteur ou admin)

@app.route("/debat/<int:id_debat>/modifier_description", methods=["POST"])
@login_required
def modifier_description(id_debat):
    """
    Permet à l’auteur du débat ou à un administrateur de modifier la description.
    Le formulaire envoie une nouvelle description qui remplace l’ancienne.
    """
    debat = Debat.query.get_or_404(id_debat)
    user = User.query.get(session["user_id"])

    if user.role != 'admin' and user.iduser != debat.id_createur:
        flash("Vous n'avez pas le droit de modifier ce débat", "danger")
        return redirect(url_for("debat", id_debat=id_debat))

    nouvelle_description = request.form.get("description", "").strip()
    debat.description = nouvelle_description
    db.session.commit()
    flash("Description mise à jour", "success")
    return redirect(url_for("accueil"))



# LANCEMENT DE L’APPLICATION

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)