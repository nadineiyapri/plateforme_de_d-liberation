from models import app, db, User, Theme, init_db
from fonctions import create_theme  

if __name__ == "__main__":
    with app.app_context():
        admin, prof, etudiant = init_db()

        #vérifie que l'admin peut créer un thème
        theme = create_theme(admin, "Thème Test")
        assert theme.nom_theme == "Thème Test"
        print("Test création par admin réussi")

        #vérifie que les autres roles ne peuvent pas créer un thème
        try:
            create_theme(prof, "Thème interdit")
            assert False, "Un prof n'aurait pas dû pouvoir créer un thème"
        except PermissionError:
            print("Test permission prof réussi")

        try:
            create_theme(etudiant, "Thème interdit")
            assert False, "Un étudiant n'aurait pas dû pouvoir créer un thème"
        except PermissionError:
            print("Test permission étudiant réussi")

        #verifie
        argument = create_argument(admin,"argument ")



        create_argument(user,texte,type_arg,id_debat,id_parent=None):