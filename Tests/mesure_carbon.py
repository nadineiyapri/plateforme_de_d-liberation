"""
mesure_carbon.py
Mesure l’empreinte carbone d’une session utilisateur avec CodeCarbon.
À lancer avec : python mesure_carbon.py
"""

from codecarbon import EmissionsTracker
from routes import app
import time
import threading
import os

# On crée le dossier pour les rapports s’il n’existe pas
os.makedirs("carbon_reports", exist_ok=True)


def run_app():
    """
    Lance le serveur Flask en arrière-plan.
    On désactive le mode debug pour éviter les doublons de mesures.
    """
    app.run(debug=False, use_reloader=False)


def simulate_user():
    """
    Simule une session utilisateur typique :
    - connexion
    - création d’un débat
    - ajout de quelques arguments
    - évaluations
    - ajout d’un favori
    """
    import requests
    import time

    base_url = "http://127.0.0.1:5000"

    # On attend que le serveur soit prêt
    time.sleep(3)

    try:
        print(" Connexion...")
        requests.post(base_url + "/", data={"nom": "Test", "prenom": "Carbon", "role": "etudiant"}, timeout=5)

        print(" Création d'un débat...")
        requests.post(base_url + "/creer_debat", data={
            "titre": "Débat test CodeCarbon",
            "description": "Débat pour mesurer l'empreinte carbone",
            "id_theme": "1",
            "date_limite": ""
        }, timeout=5)

        print("🔹 Ajout d'arguments...")
        for i in range(3):
            requests.post(base_url + "/debat/1", data={
                "texte": f"Argument de test {i}",
                "type_arg": "soutien",
                "id_parent": "root"
            }, timeout=5)
            time.sleep(0.5)

        print(" Évaluations...")
        for i in range(1, 4):
            requests.post(base_url + f"/evaluer_argument/{i}", data={"note": 4}, timeout=5)
            time.sleep(0.3)

        print(" Favori...")
        requests.post(base_url + "/favori_argument/1", timeout=5)

        print(" Simulation terminée")

    except Exception as e:
        print(f" Erreur pendant la simulation : {e}")


def afficher_resultats(emissions_data):
    """
    Affiche les résultats de la mesure CodeCarbon de façon lisible.

    Paramètre :
        emissions_data : l’objet retourné par tracker.stop()
    """
    print("\n" + "=" * 50)
    print(" RAPPORT CARBONE")
    print("=" * 50)

    if hasattr(emissions_data, 'duration'):
        print(f"  Temps d'exécution : {emissions_data.duration:.2f} secondes")
    else:
        print("  Temps d'exécution : mesuré (voir fichier CSV)")

    if hasattr(emissions_data, 'energy_consumed'):
        print(f" Énergie consommée : {emissions_data.energy_consumed:.6f} kWh")
    else:
        print(" Énergie consommée : voir fichier CSV")

    if hasattr(emissions_data, 'emissions'):
        print(f" Émissions de CO₂ : {emissions_data.emissions:.6f} g")
    else:
        print(" Émissions de CO₂ : voir fichier CSV")

    print("=" * 50)
    print("\n Les résultats détaillés sont dans carbon_reports/emissions.csv")


if __name__ == "__main__":
    # On lance le serveur Flask dans un thread séparé
    server_thread = threading.Thread(target=run_app, daemon=True)
    server_thread.start()

    # On attend que le serveur démarre
    time.sleep(5)

    # On démarre la mesure CodeCarbon
    tracker = EmissionsTracker(project_name="UVoice", output_dir="carbon_reports")

    try:
        tracker.start()
        simulate_user()
    finally:
        # On arrête la mesure et on récupère les résultats
        data = tracker.stop()
        afficher_resultats(data)