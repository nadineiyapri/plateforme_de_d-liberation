from models import db, User, Theme, Debat , Argument

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
    """ cette fonction permet a luser de créer/ajouter un argument   ,
    elle prend en paramètres user de type User ,texte et type_arg de type String,id_debatet id_parent  de type int """
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

def display_argument_tree(id_debat, parent_id=None, level=0):
    """ cette fonction prend en paramètres id_debat,parent_id,level qui sont tous les trois des int 
        Parcourt le débat de manière récursive pour lier chaque 'père' à ses 'fils'.
         Cherche tous les arguments qui partagent le même identifiant de parent (parent_id)
         et descend dans l'arborescence pour construire la hiérarchie du graphe.
    
         Retourne une liste ordonnée par niveau de profondeur (level).
     """

    args = Argument.query.filter_by(id_debat=id_debat, id_parent=parent_id).all()
    tree = []
    for arg in args:
        tree.append({"texte": arg.texte, "type": arg.type, "level": level})
        tree += display_argument_tree(id_debat, arg.id_argument, level + 1)
    return tree

def display_full_debate_tree(id_debat):
    """
    Récupère récursivement tous les arguments d'un débat sous forme d'arbre.
    Chaque argument racine (id_parent=None) est listé, puis ses enfants sont
    ajoutés récursivement avec un niveau d'indentation pour refléter la hiérarch                                                                             ie.

    prend en param : id_debat:int ,parent_id:int(qui est null au debut car cest                                                                              la racine),level:int
    retourne: une liste de dictionnaires representant l arbre des arguments
    """
    debat = Debat.query.get(id_debat)
    if not debat:
        return []

    # Le "nœud racine" est le sujet du débat
    tree = [{"texte": debat.titre, "type": "sujet", "level": 0}]

    # On appelle la récursion pour les arguments, en commençant au level 1
    tree += display_argument_tree(id_debat, parent_id=None, level=1)
    return tree


def get_graph_json(id_debat):
    """ Cette fonction prend en arguments : id_debat : int 
    Structure produite :
    - Un nœud racine ('root') représentant le titre du débat.
    - Une liste d'enfants contenant les arguments de premier niveau.
    - Chaque argument contient récursivement ses propres réponses dans une liste 'enfants 
    Elle transforme les données "plates" de la base de données en un objet 
    imbriqué (arbre) directement exploitable par des bibliothèques de graphes (ex: D3.js).
"""
    debat = Debat.query.get(id_debat)
    if not debat:
        return None

    # On récupère les arguments "racines" (ceux qui répondent directement au titre du débat)
    racines = Argument.query.filter_by(id_debat=id_debat, id_parent=None).all()

    def build_node(arg):
        return {
            "id": arg.id_argument,
            "texte": arg.texte,
            "type": arg.type_arg,  # 'soutien' ou 'attaque'
            "enfants": [build_node(enfant) for enfant in arg.enfants]
        }

    return {
        "id": "root",
        "texte": debat.titre,
        "type": "debat",
        "enfants": [build_node(r) for r in racines]
    }

