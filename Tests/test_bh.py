"""
test_bh.py
Tests unitaires pour la fonction de calcul des forces.
À lancer avec : pytest test_bh.py -v -s
"""

import pytest


def calculer_forces_avec_soutiens_simule(id_debat):
    """
    Version simulée de la fonction de calcul.
    On n’utilise pas la vraie base de données pour les tests.

    Paramètre :
        id_debat (int) : identifiant du débat, sert à choisir le cas de test

    Retourne :
        dict : un dictionnaire contenant les forces simulées
    """
    if id_debat == 999:         # débat sans argument
        return {}
    elif id_debat == 1:         # un argument seul → force 0.5
        return {1: 0.5}
    elif id_debat == 2:         # un argument attaqué par un autre → force 0.333
        return {1: 0.333, 2: 0.5}
    elif id_debat == 3:         # un argument soutenu par un autre → force 0.666
        return {1: 0.666, 3: 0.5}
    else:
        return {}


def test_debat_sans_argument():
    """
    Vérifie qu’un débat sans argument retourne un dictionnaire vide.
    """
    resultat = calculer_forces_avec_soutiens_simule(999)
    assert resultat == {}, "Le dictionnaire devrait être vide"


def test_argument_seul_sans_evaluation():
    """
    Vérifie qu’un argument seul sans aucune évaluation a une force de 0.5.
    """
    resultat = calculer_forces_avec_soutiens_simule(1)
    assert resultat[1] == 0.5, f"Force attendue 0.5, obtenue {resultat[1]}"


def test_argument_attaque():
    """
    Vérifie que quand un argument est attaqué par un autre, sa force diminue.
    Avec deux arguments de force 0.5, la cible tombe à 0.333.
    """
    resultat = calculer_forces_avec_soutiens_simule(2)
    assert round(resultat[1], 3) == 0.333, f"Force attendue 0.333, obtenue {round(resultat[1], 3)}"


def test_argument_soutien():
    """
    Vérifie que quand un argument est soutenu par un autre, sa force augmente.
    Avec deux arguments de force 0.5, la cible monte à 0.666.
    """
    resultat = calculer_forces_avec_soutiens_simule(3)
    assert round(resultat[1], 3) == 0.666, f"Force attendue 0.666, obtenue {round(resultat[1], 3)}"


def test_force_toujours_entre_0_et_1():
    """
    Vérifie que la force de tout argument reste toujours entre 0 et 1.
    """
    resultat = calculer_forces_avec_soutiens_simule(2)
    for force in resultat.values():
        assert 0 <= force <= 1, f"Force {force} hors intervalle [0,1]"