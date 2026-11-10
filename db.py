"""
db.py — Accès à la base et règles communes à tous les écrans de saisie.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "familles.db"
SCHEMA = BASE_DIR / "schema.sql"
CONFIG_BASE = BASE_DIR / "base_choisie.json"


class ErreurSaisie(Exception):
    """Erreur métier destinée à être affichée à l'utilisateur."""


def connecter(db_path: str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(db_path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def connecter_lecture_seule(db_path: str) -> sqlite3.Connection:
    """Ouvre une base sans aucun droit d'écriture.

    Utilisé par l'aperçu du tableau de bord : on peut consulter et
    exporter la base de référence sans risque de la modifier (SQLite refuse alors
    toute écriture, y compris par accident).
    """
    chemin = Path(db_path).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(chemin, uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _migrer_recus(con):
    """Migration idempotente : numérotation des reçus dans `paiements`.

    - ajoute la colonne `numero_recu` si elle manque (bases anciennes) ;
    - migre les numéros stockés dans `parametres` (`recu_paiement_<id>`) ;
    - peuple `recu_sequences` depuis `parametres` (`recu_numeros`) et/ou
      depuis les numéros déjà présents dans `paiements`.
    """
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(paiements)")}
    except sqlite3.Error:
        return
    if "numero_recu" not in cols:
        try:
            con.execute("ALTER TABLE paiements ADD COLUMN numero_recu TEXT")
            con.commit()
        except sqlite3.Error:
            return
    # index d'unicité (créé après l'ajout de la colonne)
    try:
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_paiements_numero_recu ON paiements(numero_recu)")
        con.commit()
    except sqlite3.Error:
        pass
    # migre les numéros déjà attribués (parametres -> paiements)
    try:
        import parametres as P
        P._assurer_table(con)
        for (pid,) in con.execute("SELECT id FROM paiements").fetchall():
            if con.execute(
                    "SELECT numero_recu FROM paiements WHERE id = ?", (pid,)
            ).fetchone()[0] is not None:
                continue
            val = P.lire_parametre(con, "recu_paiement_%d" % pid, None)
            if val:
                try:
                    con.execute(
                        "UPDATE paiements SET numero_recu = ? WHERE id = ?",
                        (val, pid))
                except sqlite3.Error:
                    pass
        con.commit()
    except Exception:
        pass

    # peuple recu_sequences
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS recu_sequences (
            annee INTEGER PRIMARY KEY, dernier INTEGER NOT NULL DEFAULT 0)""")
        con.commit()
    except sqlite3.Error:
        return

    # depuis parametres.recu_numeros
    try:
        import json
        import parametres as P
        brut = P.lire_parametre(con, "recu_numeros", "")
        if brut:
            data = json.loads(brut)
            if isinstance(data, dict):
                for an, val in data.items():
                    try:
                        a = int(an); d = int(val)
                    except (TypeError, ValueError):
                        continue
                    con.execute("""INSERT INTO recu_sequences (annee, dernier)
                                   VALUES (?, ?)
                                   ON CONFLICT(annee) DO UPDATE SET
                                     dernier = MAX(dernier, excluded.dernier)""",
                                (a, d))
        con.commit()
    except Exception:
        pass

    # depuis les numéros déjà en base (RECU-AAAA-NNNNNN)
    try:
        for (num,) in con.execute(
                "SELECT numero_recu FROM paiements WHERE numero_recu IS NOT NULL"
        ).fetchall():
            # format RECU-<annee>-<num>
            parts = str(num).split("-")
            if len(parts) >= 3:
                try:
                    a = int(parts[1]); d = int(parts[2])
                except ValueError:
                    continue
                con.execute("""INSERT INTO recu_sequences (annee, dernier)
                               VALUES (?, ?)
                               ON CONFLICT(annee) DO UPDATE SET
                                 dernier = MAX(dernier, excluded.dernier)""",
                            (a, d))
        con.commit()
    except Exception:
        pass


import json as _json


def lire_chemin_base() -> "Path | None":
    """Chemin de la base choisie par l'utilisateur, ou None si aucune."""
    try:
        if CONFIG_BASE.exists():
            data = _json.loads(CONFIG_BASE.read_text(encoding="utf-8"))
            chemin = data.get("db_path")
            if chemin and Path(chemin).exists():
                return Path(chemin)
    except (OSError, ValueError):
        pass
    return None


def memoriser_chemin_base(chemin: "Path") -> None:
    """Mémorise le choix de base pour les prochains lancements."""
    try:
        CONFIG_BASE.write_text(
            _json.dumps({"db_path": str(chemin)}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    except OSError:
        pass


def initialiser(db_path: str | None = None) -> sqlite3.Connection:
    """Crée les tables et les vues si nécessaire. Retourne la connexion."""
    chemin = db_path or DB_PATH
    con = connecter(chemin)
    # recréer les vues (pour prendre en compte les évolutions de schema.sql)
    for v in ("v_membre_complet", "v_cotisations_mensuelles",
              "v_solde_membre_campagne"):
        try:
            con.execute("DROP VIEW IF EXISTS " + v)
        except sqlite3.Error:
            pass
    con.commit()
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()
    _migrer_recus(con)
    # version de schéma (P14) : permet de détecter une base ancienne
    try:
        con.execute("PRAGMA user_version = 1")
        con.commit()
    except sqlite3.Error:
        pass
    return con


# ---------------------------------------------------------------------
#  Colonnes autorisées par table (P12 : évite qu'un appelant injecte
#  n'importe quelle colonne via **autres).
# ---------------------------------------------------------------------
COLONNES_AUTORISEES = {
    "clans": {"nom", "description"},
    "grandes_familles": {"nom", "clan_id", "description"},
    "lignees": {"nom", "grande_famille_id", "description"},
    "familles": {"nom", "lignee_id", "ordre", "description"},
    "membres": {"nom", "prenom", "famille_id", "parent_id", "telephone",
                "ordre_fratrie", "sexe", "statut", "date_statut", "notes"},
}


# ---------------------------------------------------------------------
#  Niveaux de la hiérarchie : table, clé du parent, libellé affiché
# ---------------------------------------------------------------------
NIVEAUX = {
    "clan": {
        "table": "clans",
        "parent_table": None,
        "parent_col": None,
        "singulier": "Clan",
        "pluriel": "Clans",
        "article": "Ce clan",
    },
    "grande_famille": {
        "table": "grandes_familles",
        "parent_table": "clans",
        "parent_col": "clan_id",
        "singulier": "Grande famille",
        "pluriel": "Grandes familles",
        "article": "Cette grande famille",
    },
    "lignee": {
        "table": "lignees",
        "parent_table": "grandes_familles",
        "parent_col": "grande_famille_id",
        "singulier": "Lignée",
        "pluriel": "Lignées",
        "article": "Cette lignée",
    },
    "famille": {
        "table": "familles",
        "parent_table": "lignees",
        "parent_col": "lignee_id",
        "singulier": "Famille",
        "pluriel": "Familles",
        "article": "Cette famille",
    },
    "membre": {
        "table": "membres",
        "parent_table": "familles",
        "parent_col": "famille_id",
        "singulier": "Membre",
        "pluriel": "Membres",
        "article": "Ce membre",
    },
}


def nettoyer_nom(valeur):
    """Normalise un libellé saisi : espaces multiples et bords retirés."""
    if valeur is None:
        return ""
    return " ".join(str(valeur).split())


def exiger_nom(valeur, libelle="Le nom"):
    nom = nettoyer_nom(valeur)
    if not nom:
        raise ErreurSaisie(f"{libelle} est obligatoire.")
    if len(nom) > 120:
        raise ErreurSaisie(f"{libelle} ne doit pas dépasser 120 caractères.")
    return nom


def parents_disponibles(con, niveau):
    """
    Retourne la liste (id, libellé) des nœuds parents possibles
    pour un niveau donné. Vide pour le niveau « clan ».
    """
    cfg = NIVEAUX[niveau]
    if cfg["parent_table"] is None:
        return []
    return [
        (r["id"], r["nom"])
        for r in con.execute(
            f"SELECT id, nom FROM {cfg['parent_table']} ORDER BY nom COLLATE NOCASE"
        )
    ]


def nom_parent(con, niveau, parent_id):
    """Libellé du parent d'un nœud, pour l'affichage hiérarchique."""
    cfg = NIVEAUX[niveau]
    if cfg["parent_table"] is None or parent_id is None:
        return ""
    row = con.execute(
        f"SELECT nom FROM {cfg['parent_table']} WHERE id = ?", (parent_id,)
    ).fetchone()
    return row["nom"] if row else ""


def lister(con, niveau, parent_id=None):
    """
    Retourne (id, nom, nb_enfants) pour chaque nœud du niveau,
    filtré sur son parent. nb_enfants = descendants directs.
    """
    cfg = NIVEAUX[niveau]
    table = cfg["table"]
    enfant = None
    for n, c in NIVEAUX.items():
        if c["parent_col"] and c["parent_table"] == table:
            enfant = c
            break

    sql = f"SELECT id, nom FROM {table}"
    params = []
    if cfg["parent_col"]:
        sql += f" WHERE {cfg['parent_col']} = ?"
        params.append(parent_id)
    sql += " ORDER BY nom COLLATE NOCASE"
    lignes = con.execute(sql, params).fetchall()

    if enfant is None:
        return [(r["id"], r["nom"], None) for r in lignes]

    compteur = {
        r["p"]: r["n"]
        for r in con.execute(
            f"SELECT {enfant['parent_col']} AS p, COUNT(*) AS n "
            f"FROM {enfant['table']} GROUP BY {enfant['parent_col']}"
        )
    }
    return [(r["id"], r["nom"], compteur.get(r["id"], 0)) for r in lignes]


def ajouter(con, niveau, nom, parent_id=None, **autres):
    """Insère un nœud après validation. Lève ErreurSaisie en cas de conflit.

    `parent_id` désigne TOUJOURS le nœud parent dans la hiérarchie
    (clan → grande famille → lignée → famille → membre).
    Pour un membre, le lien généalogique s'appelle `lien_parent_id` afin
    d'éviter toute confusion.
    """
    if "lien_parent_id" in autres:
        autres["parent_id"] = autres.pop("lien_parent_id")
    cfg = NIVEAUX[niveau]
    nom = exiger_nom(nom, f"Le nom du {cfg['singulier'].lower()}")

    # P12 : liste blanche des colonnes modifiables
    autorisees = COLONNES_AUTORISEES.get(cfg["table"], set())
    for k in autres:
        if k not in autorisees:
            raise ErreurSaisie(
                f"Colonne non autorisée pour {cfg['table']} : {k!r}.")
    cols, vals = ["nom"], [nom]
    if cfg["parent_col"]:
        if parent_id is None:
            raise ErreurSaisie(
                f"Choisissez d'abord le parent (un {cfg['singulier']} "
                f"appartient obligatoirement à un nœud supérieur)."
            )
        cols.append(cfg["parent_col"])
        vals.append(parent_id)
    for k, v in autres.items():
        cols.append(k)
        vals.append(v)

    placeholders = ", ".join("?" * len(cols))
    try:
        cur = con.execute(
            f"INSERT INTO {cfg['table']} ({', '.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        con.commit()
    except sqlite3.IntegrityError as e:
        con.rollback()
        if "UNIQUE" in str(e).upper():
            raise ErreurSaisie(
                f"{cfg['article']} « {nom} » existe déjà sous ce même parent."
            ) from e
        raise ErreurSaisie(str(e)) from e
    return cur.lastrowid


def modifier(con, niveau, id_, nom, **autres):
    """Modifie un nœud. Voir `ajouter` pour `lien_parent_id`."""
    if "lien_parent_id" in autres:
        autres["parent_id"] = autres.pop("lien_parent_id")
    cfg = NIVEAUX[niveau]
    nom = exiger_nom(nom, f"Le nom du {cfg['singulier'].lower()}")

    # P12 : liste blanche des colonnes modifiables
    autorisees = COLONNES_AUTORISEES.get(cfg["table"], set())
    for k in autres:
        if k not in autorisees:
            raise ErreurSaisie(
                f"Colonne non autorisée pour {cfg['table']} : {k!r}.")
    sets, vals = ["nom = ?"], [nom]
    for k, v in autres.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(id_)
    try:
        con.execute(
            f"UPDATE {cfg['table']} SET {', '.join(sets)} WHERE id = ?", vals
        )
        con.commit()
    except sqlite3.IntegrityError as e:
        con.rollback()
        if "UNIQUE" in str(e).upper():
            raise ErreurSaisie(
                f"{cfg['article']} « {nom} » existe déjà sous ce même parent."
            ) from e
        raise ErreurSaisie(str(e)) from e


def _ordre_descendant(con, ids):
    """Trie des membres pour qu'aucun parent ne soit supprimé avant
    ses enfants (contrainte parent_id ON DELETE RESTRICT)."""
    profondeur = {}

    def calculer(mid, vus=None):
        if mid in profondeur:
            return profondeur[mid]
        vus = vus or set()
        if mid in vus:
            return 0
        row = con.execute("SELECT parent_id FROM membres WHERE id = ?", (mid,)).fetchone()
        if not row or row[0] is None:
            profondeur[mid] = 0
        else:
            profondeur[mid] = 1 + calculer(row[0], vus | {mid})
        return profondeur[mid]

    for i in ids:
        calculer(i)
    return sorted(ids, key=lambda i: profondeur.get(i, 0), reverse=True)


def supprimer(con, niveau, id_, force=False):
    """
    Supprime un nœud. Refusé s'il a des descendants, sauf si force=True
    (suppression en chaîne de tout le sous-arbre).
    """
    cfg = NIVEAUX[niveau]
    table = cfg["table"]

    # niveau enfant direct
    enfant = None
    for n, c in NIVEAUX.items():
        if c["parent_col"] and c["parent_table"] == table:
            enfant = c
            break

    if enfant is not None:
        nb = con.execute(
            f"SELECT COUNT(*) FROM {enfant['table']} WHERE {enfant['parent_col']} = ?",
            (id_,),
        ).fetchone()[0]
        if nb and not force:
            raise ErreurSaisie(
                f"{cfg['article']} contient {nb} "
                f"{(enfant['singulier'] if nb == 1 else enfant['pluriel']).lower()}. "
                f"Supprimez-les d'abord, ou utilisez la suppression en chaîne."
            )
        if nb and force:
            ids = [r[0] for r in con.execute(
                f"SELECT id FROM {enfant['table']} WHERE {enfant['parent_col']} = ?",
                (id_,),
            ).fetchall()]
            if n == "membre":
                # les membres sont liés entre eux par parent_id :
                # on supprime du plus profond au plus haut
                ids = _ordre_descendant(con, ids)
            for child_id in ids:
                supprimer(con, n, child_id, force=True)

    try:
        con.execute(f"DELETE FROM {table} WHERE id = ?", (id_,))
        con.commit()
    except sqlite3.IntegrityError as e:
        con.rollback()
        raise ErreurSaisie(
            "Suppression impossible : cet élément est encore référencé "
            f"({e})."
        ) from e
