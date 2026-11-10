"""Tests de caractérisation figés sur cotisations.db (voir PROBLEMES.md §3)."""

import sqlite3

import cotisations as C
import parametres as P
import tableau_de_bord as T


def test_integrite(con):
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_cles_etrangeres(con):
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []


def test_volumetrie(con):
    attendu = {
        "clans": 7,
        "grandes_familles": 46,
        "lignees": 46,
        "familles": 391,
        "membres": 599,
        "campagnes": 3,
        "paiements": 227,
        "affectations": 1805,
    }
    for table, n in attendu.items():
        assert con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == n, table


def test_total_affectations(con):
    assert con.execute("SELECT SUM(montant) FROM affectations").fetchone()[0] == 1807000.0


def test_total_paiements(con):
    assert con.execute("SELECT SUM(montant_total) FROM paiements").fetchone()[0] == 1807000.0


def test_totaux_par_annee(con):
    rows = {r["annee"]: r["total"] for r in C.totaux_par_annee(con)}
    assert rows[2024] == 1453000.0
    assert rows[2025] == 338000.0
    assert rows[2026] == 16000.0


def test_paiements_multi_annees(con):
    n = con.execute(
        "SELECT COUNT(*) FROM paiements p "
        "WHERE (SELECT COUNT(DISTINCT annee) FROM affectations a "
        "WHERE a.paiement_id = p.id) > 1"
    ).fetchone()[0]
    assert n == 49


def test_membres_en_retard_2025(con):
    assert len(T.membres_en_retard(con, 2025)) == 596


def test_clan_le_plus_contributeur_2024(con):
    rows = T.par_niveau(con, 2024, "clan")
    assert rows[0]["libelle"] == "KOUADIO AMBOFF"
    assert rows[0]["encaisse"] == 614000.0


def test_vue_ensemble_2025(con):
    v = T.vue_ensemble(con, 2025)
    assert v["nb_membres"] == 599
    assert v["nb_cotisants"] == 49
    assert v["encaisse"] == 338000.0
    assert v["attendu"] == 599 * 1000 * 12  # 2025 est une année passée -> 12 mois échus


def test_mois_echus_2024(con):
    assert C.mois_echus(con, 2024) == 12


def test_situation_membre_222(con):
    # Mariam -> renommé TANO (voir RESUME §0.8)
    s = C.situation(con, 222, 2024)
    assert s["montant_mensuel"] == 1000
    assert s["mois_echus"] == 12


def test_parametres_table(con):
    # recu_numeros doit exister
    r = con.execute("SELECT valeur FROM parametres WHERE cle = 'recu_numeros'").fetchone()
    assert r is not None


def test_statuts_membres(con):
    # tous les membres importés sont actifs
    assert con.execute("SELECT COUNT(*) FROM membres WHERE statut <> 'actif'").fetchone()[0] == 0


def test_parent_meme_famille(con):
    # invariant : parent_id pointe vers un membre de la même famille
    bad = con.execute("""
        SELECT COUNT(*) FROM membres m
        JOIN membres p ON p.id = m.parent_id
        WHERE p.famille_id <> m.famille_id
    """).fetchone()[0]
    assert bad == 0


def test_anti_cycle(con):
    # aucun membre n'est son propre ancêtre
    import sqlite3
    rows = con.execute("SELECT id FROM membres WHERE parent_id IS NOT NULL").fetchall()
    for r in rows:
        # remonter la chaîne
        seen = set()
        cur = r["id"]
        while True:
            pid = con.execute("SELECT parent_id FROM membres WHERE id = ?", (cur,)).fetchone()[0]
            if pid is None:
                break
            assert pid not in seen, f"cycle détecté autour de {r['id']}"
            if pid == r["id"]:
                raise AssertionError("cycle self-parent")
            seen.add(pid)
            cur = pid
            if len(seen) > 1000:
                raise AssertionError("chaîne trop longue")