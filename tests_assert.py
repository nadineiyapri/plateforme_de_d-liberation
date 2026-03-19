from models import app, db, User, Theme, init_db
from fonctions import *

if __name__ == "__main__":
    with app.app_context():
        #reinitialise la base de donnees
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


        
        # verifie que display_full_debate_tree fonctionne
        arbre_complet = display_full_debate_tree(debats[0].id_debat)

        # verifie que l'arbre n'est pas vide
        assert len(arbre_complet) > 0, "L'arbre ne devrait pas être vide"

        # verifie que le premier élément est bien le sujet du débat (Level 0)
        assert arbre_complet[0]['texte'] == debats[0].titre, "Le premier élément doit être le titre du débat"
        assert arbre_complet[0]['level'] == 0, "Le titre du débat doit être au niveau 0"
        assert arbre_complet[0]['type'] == "sujet", "Le type du premier élément doit être 'sujet' "

        # verifie que les arguments suivent (Level >= 1)
        assert len(arbre_complet) == 4, f"L'arbre devrait contenir 4 éléments, nbre reçu: {len(arbre_complet)}"

        print("Test de display_full_debate_tree réussi :) ")

        # affichage final pour vérification visuelle
        print("\nStructure complète du débat :")
        for noeud in arbre_complet:
            indent = " ->" * noeud['level']
            print(f"{indent}[{noeud['type'].upper()}] {noeud['texte']}")




        # verifie que add_arg fonctionne

        # test d'ajout réussi
        nouveau_texte = "Ceci est un test d'ajout"
        arg_ajoute, message = add_arg(nouveau_texte, "soutien", debats[0].id_debat, etudiant.iduser)

        assert arg_ajoute is not None, f"L'argument aurait dû être ajouté. Message: {message}"
        assert arg_ajoute.texte == nouveau_texte, "Le texte de l'argument ne correspond pas"
        print("Test ajout réussi ")

        # test avec un débat qui n'existe pas
        arg_fail, message_fail = add_arg("Texte", "attaque", 9999, etudiant.iduser)
        assert arg_fail is None, "L'ajout aurait dû échouer pour un débat inexistant"
        assert message_fail == "Débat introuvable.", "Le message d'erreur est incorrect"
        print("Test débat inexistant reussi ")

        # test de la limite des 20 arguments
        print("Vérification de la limite des 20 arguments...")
        # On ajoute des arguments jusqu'à atteindre 20 (on en a déjà 4 dans le débat 1)
        for i in range(16): 
            add_arg(f"Argument de remplissage {i}", "soutien", debats[0].id_debat, etudiant.iduser, id_parent = racine.id_argument)

        # Le 21ème devrait échouer
        arg_limite, message_limite = add_arg("Le 21ème argument", "soutien", debats[0].id_debat, etudiant.iduser)
        assert arg_limite is None, "La limite de 20 n'a pas été respectée"
        assert "limite de 20 arguments est atteinte" in message_limite, "Le message de limite est erroné"
        print("Test limite des 20 arguments reussi ")





        # verifie que voter_argument fonctionne 

        # On récupere l'id de l'argument racine créé par l'admin au début
        id_arg_test = racine.id_argument

        # test d'un vote réussi (le prof vote +1 sur l'argument de l'admin)
        vote_reussi = voter_argument(prof.iduser, id_arg_test, 1)
        assert vote_reussi is True, "Le prof devrait pouvoir voter sur l'argument de l'admin"
        print("Test premier vote réussi ")

        # test du doublon (le prof essaie de voter une deuxième fois sur le meme argument)
        #gerer l'erreur d'unicité de la bd et retourne False
        vote_doublon = voter_argument(prof.iduser, id_arg_test, -1)
        assert vote_doublon is False, "L'utilisateur ne devrait pas pouvoir voter deux fois pour le même argument"
        print("Test blocage doublon réussi !")

        # test d'un vote par un autre utilisateur
        vote_etudiant = voter_argument(etudiant.iduser, id_arg_test, 1)
        assert vote_etudiant is True, "L'étudiant devrait aussi pouvoir voter sur l'argument"
        print("Test vote autre utilisateur ok")


        # test de get_graph_json corrigé

        graph_data = get_graph_json(debats[0].id_debat)

        # verification structure
        assert "nodes" in graph_data and "edges" in graph_data

        # verification des noeuds
        # On compte combien d'arguments existent réellement en DB pour ce débat
        nb_args_db = Argument.query.filter_by(id_debat=debats[0].id_debat).count()
        nb_nodes = len(graph_data["nodes"])

        assert nb_nodes == nb_args_db, f"Nodes attendus: {nb_args_db}, Reçus: {nb_nodes}"
        print(f"Nombre de noeuds ({nb_nodes}) : OK")

        # verification des liens (Edges)
        # le nombre de liens doit être égal au nombre d'arguments qui ont un parent
        nb_args_avec_parent = Argument.query.filter(
            Argument.id_debat == debats[0].id_debat, 
            Argument.id_parent != None
        ).count()
        nb_edges = len(graph_data["edges"])

        assert nb_edges == nb_args_avec_parent, f"Edges attendus: {nb_args_avec_parent}, Reçus: {nb_edges}"
        print(f"Nombre de liens ({nb_edges}) : OK")

        # verification du contenu (Score et Auteur)
        if nb_nodes > 0:
            data = graph_data["nodes"][0]["data"]
            for cle in ["id", "label", "type", "score", "auteur"]:
                assert cle in data, f"Clé manquante: {cle}"
            print("Format des données du noeud : OK")