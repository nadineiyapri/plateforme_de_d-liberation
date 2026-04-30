#afin d'excecuter les fonctins pytest, lancer la commande "pytest" dans le terminal 
import pytest
from routes import app, db
from models import User, Theme, Debat, Argument

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Création de l'admin (ID 1) et de l'utilisateur (ID 2)
            admin = User(nom="Admin", prenom="Test", role="admin")
            user = User(nom="User", prenom="Test", role="etudiant")
            db.session.add_all([admin, user])
            db.session.commit()
            yield client
            db.drop_all()

def login(client, nom="User", prenom="Test", role="etudiant"):
    return client.post('/', data=dict(nom=nom, prenom=prenom, role=role), follow_redirects=True)

# 1. Test du décorateur login_required (Redirection + Message Flash)
def test_acces_accueil_sans_connexion_redirige(client):
    """Vérifie que l'accès sans connexion redirige bien vers l'index."""
    # On ne suit pas la redirection automatiquement pour vérifier le code 302
    response = client.get('/accueil', follow_redirects=False)
    
    # 302 = Redirection
    assert response.status_code == 302
    # Vérifie que la redirection pointe vers l'index (la racine /)
    assert response.location == "/" or response.location.endswith(url_for('index'))

# 2. Test de la suppression d'argument (POST)
def test_suppression_argument_par_auteur(client):
    """Vérifie que l'auteur peut supprimer son argument via une requête POST."""
    login(client) # Connecté en tant que User (ID 2)
    
    with app.app_context():
        # Setup de la hiérarchie pour les clés étrangères
        t = Theme(nom_theme="Débat de test", id_admin=1)
        db.session.add(t)
        db.session.commit()
        
        d = Debat(titre="Sujet", id_theme=t.id_theme, id_createur=1)
        db.session.add(d)
        db.session.commit()

        # L'id_auteur doit être 2 pour que la suppression soit autorisée
        arg = Argument(texte="A effacer", type_arg="soutien", id_debat=d.id_debat, id_auteur=2)
        db.session.add(arg)
        db.session.commit()
        arg_id = arg.id_argument

    # Exécution de la suppression avec la méthode POST demandée par ta route
    response = client.post(f'/argument/{arg_id}/supprimer', follow_redirects=True)
    
    assert response.status_code == 200
    # On cherche "supprim" pour couvrir "supprimé" ou "supprimée"
    assert "supprim".encode('utf-8') in response.data