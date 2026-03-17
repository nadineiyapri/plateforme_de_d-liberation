from models import app, db, User, Theme, init_db
from fonctions import create_theme, create_debat, create_argument, create_argument_tree

if __name__ == "__main__":
    with app.app_context():
        # Réinitialisation de la base
        db.drop_all()
        db.create_all()
        admin, prof, etudiant = init_db()

        #verifie que create_theme fonctionne
        theme = create_theme(admin, "Thème Test")
        assert theme.nom_theme == "Thème Test"
        print("Test création par admin réussi")
        print(f"Tous les débats seront créés sous le thème : {theme.nom_theme}\n")

        # Test permissions pour création de thème
        for user in [prof, etudiant]:
            try:
                create_theme(user, "Thème interdit")
                assert False, f"Un {user.role} n'aurait pas dû pouvoir créer un thème"
            except PermissionError:
                print(f"Test permission {user.role} réussi")

        #verifie que create_debat fonctionne
        users = [admin, prof, etudiant]
        titres = ["Débat 1", "Débat 2", "Débat 3"]
        debats = []

        for i in range(len(users)):
            debat = create_debat(users[i], id_theme=theme.id_theme, titre=titres[i], description=f"Test {titres[i]}")
            debats.append(debat)
            assert debat.titre == titres[i]
            assert debat.id_theme == theme.id_theme
            assert debat.id_createur == users[i].iduser
            print(f"{users[i].role} a créé le débat : {debats[i].titre} (Thème : {theme.nom_theme})")

        # Tous les arguments concernent le Débat 1
        print(f"\nTous les arguments suivants concernent le débat : {debats[0].titre}\n")

        # Admin crée l'argument racine
        racine = create_argument(admin, "Argument racine", "soutien", id_debat=debats[0].id_debat)
        assert racine.id_debat == debats[0].id_debat
        assert racine.id_parent is None
        assert racine.type_arg == "soutien"
        print(f"Admin a créé l'argument racine : {racine.texte} sur l'argument de l'admin")

        # Prof crée un argument soutien qui soutient la racine
        arg_prof = create_argument(prof, "Argument soutien du prof", "soutien", id_debat=debats[0].id_debat, id_parent=racine.id_argument)
        assert arg_prof.id_parent == racine.id_argument
        assert arg_prof.type_arg == "soutien"
        assert arg_prof.id_debat == debats[0].id_debat
        print(f"Prof a créé un argument soutenant la racine : {arg_prof.texte} sur l'argument de l'admin")

        # Étudiant crée un argument attaque qui attaque la racine
        arg_etudiant = create_argument(etudiant, "Argument attaque de l'étudiant", "attaque", id_debat=debats[0].id_debat, id_parent=racine.id_argument)
        assert arg_etudiant.id_parent == racine.id_argument
        assert arg_etudiant.type_arg == "attaque"
        assert arg_etudiant.id_debat == debats[0].id_debat
        print(f"Étudiant a créé un argument attaquant la racine : {arg_etudiant.texte} sur l'argument de l'admin")

        print("\nTous les tests des arguments ont réussi !")


        #vérifie que create_argument_tree fonctionne

        arbre_arguments = create_argument_tree(id_debat=debats[0].id_debat)

        # Vérifie que tous les arguments du débat 1 appartiennent bien à ce débat et à ce thème
        for arg in debats[0].arguments:
            assert arg.id_debat == debats[0].id_debat, "L'argument n'appartient pas au bon débat"
            assert arg.debat.theme.nom_theme == "Thème Test", "L'argument n'appartient pas au bon thème"

        print("Tous les arguments du débat 1 sont correctement associés au débat et au thème.")

        print("\nArbre des arguments pour le Débat 1 (Thème Test) :\n")
        for arg in arbre_arguments:
            print(f"{'    ' * arg['level']}- [{arg['type']}] {arg['texte']}")