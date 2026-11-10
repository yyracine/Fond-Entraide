"""Tests de comportement (écriture) sur une COPIE de la base de référence."""

import shutil
import sqlite3
import tempfile
from pathlib import Path

import cotisations as C
import db
import parametres as P

BASE_DIR = Path(__file__).resolve().parent.parent
REF_DB = BASE_DIR / "cotisations.db"


def _copie_db(tmp_path):
    cible = tmp_path / "test.db"
    shutil.copy2(REF_DB, cible)
    con = db.initialiser(str(cible))
    return con, cible


def test_verifier_date_formats():
    assert C.verifier_date("2026-12-31") == "2026-12-31"
    assert C.verifier_date("31/12/2026") == "2026-12-31"
    assert C.verifier_date("31-12-2026") == "2026-12-31"
    import datetime
    assert C.verifier_date(datetime.date(2026, 12, 31)) == "2026-12-31"


def test_verifier_date_invalide():
    try:
        C.verifier_date("32/13/2026")
    except db.ErreurSaisie:
        return
    raise AssertionError("date invalide acceptée")


def test_enregistrer_versement_refuse_mois_futur(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    # 2026 : mois_echus = 11 (novembre 2026). Décembre (12) doit être refusé.
    echus = C.mois_echus(con, 2026)
    assert echus == 11
    try:
        C.enregistrer_versement(con, 1, 2026, [12], "2026-11-28")
    except db.ErreurSaisie as e:
        assert "échus" in str(e) or "échu" in str(e)
        return
    raise AssertionError("mois futur accepté")


def test_enregistrer_versement_refuse_mois_invalide(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    try:
        C.enregistrer_versement(con, 1, 2024, [0, 13], "2024-12-28")
    except db.ErreurSaisie:
        return
    raise AssertionError("mois invalide accepté")


def test_enregistrer_versement_refuse_membre_inexistant(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    impayes = C.mois_impayes(con, 1, 2024)
    if not impayes:
        import pytest
        pytest.skip("aucun mois impayé pour le membre 1")
    try:
        C.enregistrer_versement(con, 999999, 2024, [impayes[0]], "2024-12-28")
    except db.ErreurSaisie:
        return
    raise AssertionError("membre inexistant accepté")


def test_enregistrer_versement_refuse_doublon(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    # trouver un membre ayant au moins un mois payé en 2024
    membre_id = None
    mois_deja = None
    for mid in range(1, 600):
        payes = C.mois_payes(con, mid, 2024)
        if payes:
            membre_id = mid
            mois_deja = next(iter(payes))
            break
    if membre_id is None:
        import pytest
        pytest.skip("aucun membre avec mois payé en 2024")
    try:
        C.enregistrer_versement(con, membre_id, 2024, [mois_deja], "2024-12-28")
    except db.ErreurSaisie:
        return
    raise AssertionError("doublon accepté")


def test_enregistrer_versement_arrondi_exact(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    impayes = C.mois_impayes(con, 1, 2024)
    if len(impayes) < 3:
        import pytest
        pytest.skip("pas assez de mois impayés")
    pid = C.enregistrer_versement(con, 1, 2024, impayes[:3], "2024-12-28",
                                  montant_total=5000)
    parts = [r["montant"] for r in con.execute(
        "SELECT montant FROM affectations WHERE paiement_id = ?", (pid,))]
    total = con.execute(
        "SELECT montant_total FROM paiements WHERE id = ?", (pid,)).fetchone()["montant_total"]
    assert abs(sum(parts) - total) < 1e-9


def test_ouvrir_exercice_refuse_decale(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    try:
        P.ouvrir_exercice(con, "Decale", "2026-04-01", "2027-03-31", 1000, 2026)
    except db.ErreurSaisie:
        return
    raise AssertionError("exercice décalé accepté")


def test_ouvrir_exercice_accepte_civil(tmp_path):
    if not REF_DB.exists():
        import pytest
        pytest.skip("base de référence absente")
    con, _ = _copie_db(tmp_path)
    action = P.ouvrir_exercice(con, "Civil", "2027-01-01", "2027-12-31", 1000, 2027)
    assert action in ("cree", "modifie")


def test_situation_complet_logique(con):
    # sanity : situation renvoie bien les clés attendues
    s = C.situation(con, 1, 2024)
    for k in ("membre_id", "annee", "montant_mensuel", "mois_payes",
              "nb_mois", "mois_echus", "verse", "attendu", "solde", "complet"):
        assert k in s


def test_montant_en_lettres():
    import recus
    assert "zéro" in recus.montant_en_lettres(0).lower()
    assert "mille" in recus.montant_en_lettres(1000).lower()
    assert "vingt et un" in recus.montant_en_lettres(21).lower()
    assert "quatre-vingts" in recus.montant_en_lettres(80).lower()