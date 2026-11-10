"""
ecran_grandes_familles.py — Étape 2 : saisie des GRANDES FAMILLES.

Implémenté sur le squelette générique `EcranHierarchique` (ecran_base) :
seuls les champs spécifiques (description) et la requête de liste
(sous-total de lignées) sont redéfinis. Cela évite la duplication avec
les autres niveaux (P10).

Lancement autonome pour tester : python ecran_grandes_familles.py
"""
import tkinter as tk
from tkinter import ttk, messagebox

import db
from ecran_base import EcranHierarchique


class EcranGrandesFamilles(EcranHierarchique):
    NIVEAU = "grande_famille"
    TITRE = "Étape 2 — Les grandes familles"
    LABEL_PARENT = "Clan"
    ARTICLE_PARENT = "un clan"
    TEXTE_AIDE = ("Une grande famille appartient à un seul clan.\n"
                  "Son nom doit être unique dans ce clan.")
    TEXTE_VIDE = ("Aucune grande famille enregistrée.\n"
                  "Choisissez un clan parent puis « Nouveau ».")

    COLONNES = (
        ("clan", "Clan (parent)", 190, "w"),
        ("nom", "Grande famille", 200, "w"),
        ("lignees", "Lignées", 80, "center"),
        ("desc", "Description", 200, "w"),
    )
    CHAMPS = (("description", "Description", "text"),)

    # ----------------------------------------------------------------
    def requete_liste(self):
        return ("""
            SELECT t.id, t.nom, t.description, t.clan_id,
                   c.nom AS clan,
                   (SELECT COUNT(*) FROM lignees l
                     WHERE l.grande_famille_id = t.id) AS nb
            FROM grandes_familles t
            JOIN clans c ON c.id = t.clan_id
            __FILTRE__
            ORDER BY c.nom COLLATE NOCASE, t.nom COLLATE NOCASE
        """, [])

    def valeurs_ligne(self, row):
        desc = (row["description"] or "").replace("\n", " ")
        return (row["clan"], row["nom"], row["nb"], desc)

    def charger_champs(self, row):
        self.txt_desc = self.widgets["description"][0]
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", row["description"] or "")

    def lire_champs(self):
        w = self.widgets["description"][0]
        return {"description": w.get("1.0", "end").strip() or None}

    def libelle_parent(self, row):
        return row["clan"]

    # alias pour la compatibilité avec app.py
    def recharger_clans(self):
        self.recharger_parents()

    @property
    def clans(self):
        return self.parents

    @clans.setter
    def clans(self, value):
        self.parents = value


# ---------------------------------------------------------------------
#  Lancement autonome (test de l'écran seul)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    class _Etat(ttk.Frame):
        def __init__(self, p):
            super().__init__(p, relief="sunken", padding=(8, 4))
            self.var = tk.StringVar()
            ttk.Label(self, textvariable=self.var).pack(side="left")

        def info(self, t):
            self.var.set(t)

    root = tk.Tk()
    try:
        from app import appliquer_icone
        appliquer_icone(root)
    except Exception:
        pass
    root.title("Test — Grandes familles")
    root.geometry("1060x620")
    con = db.initialiser()
    etat = _Etat(root)
    etat.pack(side="bottom", fill="x")
    ecran = EcranGrandesFamilles(root, con, etat)
    ecran.pack(fill="both", expand=True)
    root.mainloop()
    con.close()