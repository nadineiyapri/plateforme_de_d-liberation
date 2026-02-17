from models import db, User, Theme, Debat , Argument

def create_theme(user,titre):
    """cette fonction permet uniquement  a l admin de creer un theme , elle prend en paramètres : un user de type User et un titre de type String  """
    if(user.role)!='admin':
        raise PermissionError("Seul un admin peut créer un thème")
    theme=Theme(nom_theme=titre,id_admin=user.iduser)
    db.session.add(theme)
    db.session.commit()
    return theme

def create_debat(user,id_theme,titre,description):
    """cette fonction permet a lutilisateur(prof,admin,etudiant) de creer un debat , elle prend en paramètres : un user de type User et un titre et une description  de type String et un id_theme de type int et retourne un nouveau debat """

    if user.role not in ('admin','prof','etudiant'):
        raise PermissionError("Seul un admin peut créer un thème") 
    debat=Debat(titre=titre,description=description, id_theme=id_theme)
    db.session.add(debat)
    db.session.commit()
    return debat


def create_argument(user,texte,type_arg,id_debat,id_parent=None):
    """ cette fonction permet a luser de créer/ajouter un argument   , elle prend en paramètres user de type User ,texte et type_arg de type String,id_debatet id_parent  de type int """
    if type_arg not in ('soutien ','attaque'):
        raise ValueError("Utilisateur non autorisé")
    if id_parent:
        parent=Argument.query.get(id_parent)
        if not parent or parent.id_debat !=id_debat:
            raise ValueError("Argument parent invalide")
    arg = Argument(texte=texte, type=type_arg, id_debat=id_debat, id_auteur=user.iduser, id_parent=id_parent)
    db.session.add(arg)
    db.session.commit()
    return arg



 
