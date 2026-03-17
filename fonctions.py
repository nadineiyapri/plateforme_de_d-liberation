from models import *

def create_theme(user,titre):
    """cette fonction permet uniquement  a l admin de creer un theme , elle prend en paramètres :
    un user de type User et un titre de type String  """
    if(user.role)!='admin':
        raise PermissionError("Seul un admin peut créer un thème")
    theme=Theme(nom_theme=titre,id_admin=user.iduser)
    db.session.add(theme)
    db.session.commit()
    return theme

def create_debat(user,id_theme,titre,description):
    """cette fonction permet a lutilisateur(prof,admin,etudiant) de creer un debat ,
    elle prend en paramètres : un user de type User et un titre 
    et une description  de type String et un id_theme de type int et retourne un nouveau debat """

    if user.role not in ('admin','prof','etudiant'):
        raise PermissionError("Seul un admin peut créer un thème")
    debat=Debat(titre=titre,description=description, id_theme=id_theme)
    db.session.add(debat)
    db.session.commit()
    return debat


def create_argument(user,texte,type_arg,id_debat,id_parent=None):
    """ cette fonction permet au user de créer/ajouter un argument   ,
    elle prend en paramètres user de type User ,texte et type_arg de type String,id_debatet id_parent de type int. """
    if type_arg not in ('soutien','attaque'):
        raise ValueError("Utilisateur non autorisé")
    if id_parent:
        parent=Argument.query.get(id_parent)
        if not parent or parent.id_debat !=id_debat:
            raise ValueError("Argument parent invalide")
    arg = Argument(texte=texte, type=type_arg, id_debat=id_debat, id_auteur=user.iduser, id_parent=id_parent)
    db.session.add(arg)
    db.session.commit()
    return arg

def create_argument_tree(id_debat, parent_id=None, level=0):
    """ 
    Cette fonction permet de creer l'arbre d'un argument d'un débat recursivement
    elle prend en parametre id_debat, parent_id, et level de type int et retourne l'arbre d'arguments de type list 
    """

    args = Argument.query.filter_by(id_debat=id_debat, id_parent=parent_id).all()
    tree = []
    for arg in args:
        tree.append({"texte": arg.texte, "type": arg.type, "level": level})
        tree += create_argument_tree(id_debat, arg.id_argument, level + 1)
    return tree

def display_full_debate_tree(id_debat):
    """
    Récupère récursivement tous les arguments d'un débat sous forme d'arbre.
    Chaque argument racine (id_parent=None) est listé, puis ses enfants sont
    ajoutés récursivement avec un niveau d'indentation pour refléter la hiérarchie.

    prend en param : id_debat:int ,parent_id:int(qui est null au debut car cest la racine),level:int
    retourne: une liste de dictionnaires representant l'arbre des arguments
    """
    debat = Debat.query.get(id_debat)
    if not debat:
        return []

    # Le "nœud racine" est le sujet du débat
    tree = [{"texte": debat.titre, "type": "sujet", "level": 0}]

    # On appelle la récursion pour les arguments, en commençant au level 1
    tree += create_argument_tree(id_debat, parent_id=None, level=1)
    return tree
def add_arg(texte,type_arg,id_debat,id_auteur,id_parent=None):
    """
    Ajoute un argument en vérifiant la limite de 20 arguments
    prend en paramètres un Texte de type Str , type_arg de type str (attaque ou soutien)
    id_debat,id_auteur,id_parent (optionnel) qui sont des int 
    renvoie tuple (Argument, str) ou tuple (None, str) : lobjet crée 
    ou none accompagné d un message
    """
    #Vérifier si le débat existe
    debat = Debat.query.get(id_debat)
    if not debat:
        return None, "Débat introuvable."

    # Vérification de la limite imposée 
    nb_actuel = Argument.query.filter_by(id_debat=id_debat).count()
    if nb_actuel >= 20:
        return None, "La limite de 20 arguments est atteinte pour ce débat."

    # Création de l'argument
    nouvel_arg = Argument(
        texte=texte,
        type_arg=type_arg,
        id_debat=id_debat,
        id_auteur=id_auteur,
        id_parent=id_parent
    )
    
    try:
        db.session.add(nouvel_arg)
        db.session.commit()
        return nouvel_arg, "Argument ajouté avec succès."
    except Exception as e:
        db.session.rollback()
        return None, str(e)
    



def voter_argument(id_user, id_argument, valeur):
    """
    Enregistre un vote (+1 ou -1) sur un argument.
    La contrainte d'unicité en DB empêchera les doublons.
    prend en paramètres :
    id_user, id_argument valeur qui sont des int 
    renvoie un bool : True si le vote est enregistré 
    False  si l user a deja voté 
    """
    nouveau_vote = VoteArgument(
        id_user=id_user, 
        id_argument=id_argument, 
        valeur=valeur
    )
    try:
        db.session.add(nouveau_vote)
        db.session.commit()
        return True
    except:
        db.session.rollback()
        return False



def get_graph_json(id_debat: int) -> dict:
    """
    Génère une structure de données JSON pour représenter le débat sous forme de graphe.
    Inclut les scores et les types pour la visualisation (Sprint 2).
    
    Paramètres:
        id_debat (int): L'identifiant du débat à extraire.
        
    Retourne:
        dict: Un dictionnaire contenant deux listes : 'nodes' (bulles) et 'edges' (liens).
    """
    #On récupère tous les arguments liés à ce débat
    arguments = Argument.query.filter_by(id_debat=id_debat).all()
    
    nodes = []
    edges = []

    for arg in arguments:
        # Calcul du score dynamique (Somme des votes reçus)
        # On utilise la relation 'votes_recus' définie dans models.py
        score = sum(v.valeur for v in arg.votes_recus)
        
        #Création du nœud (La bulle d'argument)
        nodes.append({
            "data": {
                "id": str(arg.id_argument),
                "label": arg.texte[:40] + ("..." if len(arg.texte) > 40 else ""),
                "type": arg.type_arg, # Utile pour colorier la bulle (vert/rouge)
                "score": score,       # Utile pour la taille de la bulle
                "auteur": arg.auteur.username if arg.auteur else "Anonyme"
            }
        })
        
        #Création du lien (L'arête) si l'argument est une réponse
        if arg.id_parent:
            edges.append({
                "data": {
                    "id": f"edge_{arg.id_argument}_{arg.id_parent}",
                    "source": str(arg.id_argument), # L'argument actuel
                    "target": str(arg.id_parent),   # L'argument auquel il répond
                    "interaction": arg.type_arg     # Pour colorier la flèche (attaque/soutien)
                }
            })

    return {"nodes": nodes, "edges": edges}