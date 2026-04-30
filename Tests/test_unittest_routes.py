#afin de lancer les unittest, executer la commande suivante dans le terminal :
# python3 -m unittest discover -s tests
import unittest
from routes import app, db 
from models import User, Theme, Debat, Argument, EvaluationArgument, FavoriArgument

class UVoiceRoutesTestCase(unittest.TestCase):

    def setUp(self):
        """Configuration initiale : base de données en mémoire et client de test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test_secret'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            # Création d'un admin et d'un utilisateur standard pour les tests
            self.admin = User(nom="Admin", prenom="Boss", role="admin")
            self.user = User(nom="User", prenom="Lambda", role="etudiant")
            db.session.add_all([self.admin, self.user])
            db.session.commit()
            # On stocke les IDs pour la session
            self.admin_id = self.admin.iduser
            self.user_id = self.user.iduser

    def tearDown(self):
        """Nettoyage de la base de données après chaque test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def set_session(self, user_id):
        """Utilitaire pour simuler une session connectée."""
        with self.app.session_transaction() as sess:
            sess['user_id'] = user_id

    # --- TESTS DES ROUTES DE CONNEXION ---

    def test_index_get(self):
        """Vérifie l'affichage de la page d'index."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_login_post(self):
        """Teste la création/connexion d'un utilisateur via POST."""
        response = self.app.post('/', data={
            'nom': 'Nouveau',
            'prenom': 'Test',
            'role': 'etudiant'
        }, follow_redirects=True)
        self.assertIn(b"Accueil", response.data)

    # --- TESTS DES THÈMES (ADMIN) ---

    def test_ajouter_theme_admin(self):
        """Vérifie qu'un admin peut ajouter un thème."""
        self.set_session(self.admin_id)
        response = self.app.post('/ajouter_theme', data={'nom_theme': 'Écologie'}, follow_redirects=True)
        self.assertIn(b"Th\xc3\xa8me ajout\xc3\xa9", response.data) # "Thème ajouté"

    def test_ajouter_theme_non_admin(self):
        """Vérifie qu'un simple utilisateur ne peut pas ajouter de thème (silencieusement ignoré dans routes.py)."""
        self.set_session(self.user_id)
        self.app.post('/ajouter_theme', data={'nom_theme': 'Interdit'})
        with app.app_context():
            theme = Theme.query.filter_by(nom_theme='Interdit').first()
            self.assertIsNone(theme)

    # --- TESTS DES DÉBATS ---

    def test_creer_debat(self):
        """Teste la création d'un débat par un utilisateur."""
        self.set_session(self.user_id)
        # Création d'un thème au préalable
        with app.app_context():
            t = Theme(nom_theme="General", id_admin=self.admin_id)
            db.session.add(t)
            db.session.commit()
            t_id = t.id_theme

        response = self.app.post('/creer_debat', data={
            'titre': 'Faut-il tester son code ?',
            'description': 'Un débat crucial',
            'id_theme': t_id,
            'date_limite': '2026-12-31T23:59'
        }, follow_redirects=True)
        self.assertIn(b"Faut-il tester son code ?", response.data)

    # --- TESTS DES ARGUMENTS ---

    def test_ajouter_argument(self):
        """Teste l'ajout d'un argument (soutien/attaque) dans un débat."""
        self.set_session(self.user_id)
        with app.app_context():
            t = Theme(nom_theme="Test", id_admin=self.admin_id)
            db.session.add(t)
            db.session.commit()
            d = Debat(titre="Debat Test", id_theme=t.id_theme, id_createur=self.user_id)
            db.session.add(d)
            db.session.commit()
            d_id = d.id_debat

        response = self.app.post(f'/debat/{d_id}', data={
            'texte': 'Oui car cela évite les bugs',
            'type_arg': 'soutien',
            'id_parent': 'root'
        }, follow_redirects=True)
        self.assertIn(b"Argument ajout\xc3\xa9", response.data)

    # --- TESTS ÉVALUATIONS ET FAVORIS ---

    def test_evaluer_argument(self):
        """Teste la notation d'un argument (1-5 étoiles)."""
        self.set_session(self.user_id)
        with app.app_context():
            # Setup rapide d'un argument
            t = Theme(nom_theme="T", id_admin=self.admin_id)
            db.session.add(t)
            db.session.commit()
            d = Debat(titre="D", id_theme=t.id_theme, id_createur=self.admin_id)
            db.session.add(d)
            arg = Argument(texte="Argument à noter", type_arg="soutien", id_debat=1, id_auteur=self.admin_id)
            db.session.add(arg)
            db.session.commit()
            arg_id = arg.id_argument

        response = self.app.post(f'/evaluer_argument/{arg_id}', data={'note': 5}, follow_redirects=True)
        self.assertIn(b"\xc3\x89valuation enregistr\xc3\xa9e", response.data) # "Évaluation enregistrée"

    def test_basculer_favori(self):
        """Teste l'ajout d'un argument en favori."""
        self.set_session(self.user_id)
        
        with app.app_context():
            # 1. Créer le thème et le débat nécessaires pour l'argument
            t = Theme(nom_theme="Test Favori", id_admin=self.admin_id)
            db.session.add(t)
            db.session.commit()
            
            d = Debat(titre="Debat Favori", id_theme=t.id_theme, id_createur=self.admin_id)
            db.session.add(d)
            db.session.commit()
            
            # 2. Créer l'argument explicitement
            arg = Argument(texte="Argument pour favori", type_arg="soutien", id_debat=d.id_debat, id_auteur=self.admin_id)
            db.session.add(arg)
            db.session.commit()
            arg_id = arg.id_argument # On récupère l'ID réel généré

        # 3. Appeler la route avec l'ID valide
        response = self.app.get(f'/favori_argument/{arg_id}', follow_redirects=True)
        self.assertIn(b"Ajout\xc3\xa9 aux favoris", response.data)

    # --- TESTS SUPPRESSION ---

    def test_supprimer_debat_admin(self):
        """Vérifie qu'un admin peut supprimer n'importe quel débat."""
        self.set_session(self.admin_id)
        # Créer un débat d'un autre utilisateur
        with app.app_context():
            d = Debat(titre="A supprimer", id_theme=1, id_createur=self.user_id)
            db.session.add(d)
            db.session.commit()
            d_id = d.id_debat
        
        response = self.app.post(f'/debat/{d_id}/supprimer', follow_redirects=True)
        self.assertIn(b"D\xc3\xa9bat supprim\xc3\xa9 avec succ\xc3\xa8s", response.data)

if __name__ == '__main__':
    unittest.main()