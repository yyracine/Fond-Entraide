"""
app.py — Application de saisie de la hiérarchie du Fonds d'Entraide.

Étape 1 : saisie des CLANS.
Les étapes suivantes (grandes familles, lignées, familles, membres) seront
ajoutées progressivement, chacune dans son fichier d'écran.

Lancement : python app.py
"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

import db
from liste_pdf_mixin import BoutonListePDF
from ui_commun import CadreDefilant
from ecran_base import EcranHierarchique
from ecran_grandes_familles import EcranGrandesFamilles
from ecran_lignees import EcranLignees
from ecran_familles import EcranFamilles
from ecran_membres import EcranMembres
from ecran_cotisations import EcranCotisations
from ecran_parametres import EcranParametres
from ecran_tableau_bord import EcranTableauBord
import parametres as P
import theme

# Couleurs de repli : la palette de theme.py (DESIGN.md) fait foi.
COULEUR_FOND = theme.CLAIR["fond"]
COULEUR_ENTETE = theme.CLAIR["entete"]
COULEUR_ACCENT = theme.CLAIR["accent"]


class BarreEtat(ttk.Frame):
    """Bandeau d'information en bas de fenêtre."""

    def __init__(self, parent):
        super().__init__(parent, relief="sunken", padding=(8, 4))
        self.var = tk.StringVar()
        ttk.Label(self, textvariable=self.var).pack(side="left")

    def info(self, texte):
        self.var.set(texte)


class EcranClans(EcranHierarchique):
    """
    Étape 1 — Saisie des clans (niveau racine, sans parent).

    Implémenté sur le squelette générique `EcranHierarchique` (P10) :
    seuls les champs spécifiques (description) et la requête de liste
    (nombre de grandes familles) sont redéfinis.
    """
    NIVEAU = "clan"
    TITRE = "Étape 1 — Les clans"
    LABEL_PARENT = "Parent"
    ARTICLE_PARENT = "le parent"
    TEXTE_AIDE = ("Un clan est le sommet de la hiérarchie.\n"
                  "Son nom doit être unique dans la base.")
    TEXTE_VIDE = ("Aucun clan enregistré.\n"
                  "Commencez par « Nouveau clan » à droite.")

    COLONNES = (
        ("nom", "Clan", 200, "w"),
        ("gf", "Grandes familles", 120, "center"),
        ("desc", "Description", 240, "w"),
    )
    CHAMPS = (("description", "Description", "text"),)

    def requete_liste(self):
        return ("""
            SELECT t.id, t.nom, t.description,
                   (SELECT COUNT(*) FROM grandes_familles gf
                     WHERE gf.clan_id = t.id) AS gf
            FROM clans t
            __FILTRE__
            ORDER BY t.nom COLLATE NOCASE
        """, [])

    def valeurs_ligne(self, row):
        desc = (row["description"] or "").replace("\n", " ")
        return (row["nom"], row["gf"], desc)

    def charger_champs(self, row):
        w = self.widgets["description"][0]
        w.delete("1.0", "end")
        w.insert("1.0", row["description"] or "")

    def lire_champs(self):
        w = self.widgets["description"][0]
        return {"description": w.get("1.0", "end").strip() or None}

    def libelle_parent(self, row):
        return ""

    # Racine : création autorisée même sans parent.
    def _maj_boutons(self):
        actif = self.id_selection is not None
        self.btn_modifier.state(["!disabled"] if actif else ["disabled"])
        self.btn_supprimer.state(["!disabled"] if actif else ["disabled"])
        self.btn_annuler.state(["!disabled"] if self.en_edition else ["disabled"])
        self.btn_nouveau.state(["!disabled"])

    # alias pour compatibilité
    @property
    def var_nom_compat(self):
        return self.var_nom


ICO = "relation.ico"


def appliquer_icone(fenetre, chemin=None):
    """Remplace l'icone Tk par defaut (plume rouge) par relation.ico.

    Windows : iconbitmap (le .ico contient 16, 20, 24, 32, 40, 48, 64,
    128 et 256 px). Repli portable via PhotoImage. Ne leve jamais :
    une icone absente ne doit pas empecher le demarrage.
    """
    fichier = Path(chemin) if chemin else Path(__file__).with_name(ICO)
    if not fichier.exists():
        print(f"Icone introuvable : {fichier}")
        return False
    try:
        fenetre.iconbitmap(default=str(fichier))
        return True
    except tk.TclError:
        pass
    try:
        image = tk.PhotoImage(file=str(fichier))
        fenetre.iconphoto(True, image)
        fenetre._icone_tk = image      # garder une reference (sinon GC)
        return True
    except tk.TclError as e:
        print(f"Icone non appliquee : {e}")
        return False

def icone_autonome(racine):
    """A appeler dans les blocs `if __name__ == "__main__"` des ecrans."""
    appliquer_icone(racine)


class Application(tk.Tk):
    def __init__(self, con, icone=None):
        super().__init__()
        self.con = con
        appliquer_icone(self, icone)
        self.title("Fonds d'Entraide — Saisie de la hiérarchie")
        # la fenetre s'adapte a la taille reelle de l'ecran :
        # sur un 1366x768 elle ne debordera pas sous la barre des taches
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        largeur = min(1060, sw - 60)
        hauteur = min(800, sh - 80)
        self.geometry(f"{largeur}x{hauteur}+30+20")
        self.minsize(780, 480)
        self.configure(bg=COULEUR_FOND)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=6)
        style.configure("Treeview", rowheight=24)
        # bouton de purge : rouge pour signaler le danger
        style.configure("Danger.TButton", foreground="#b00020")

        # bandeau de titre
        bandeau = tk.Frame(self, bg=COULEUR_ENTETE, height=46)
        bandeau.pack(fill="x")
        bandeau.pack_propagate(False)
        tk.Label(
            bandeau,
            text="FONDS D'ENTRAIDE  ·  Saisie de la hiérarchie",
            bg=COULEUR_ENTETE,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16)
        self.lbl_etape = tk.Label(
            bandeau,
            text="Étape 1 / 6",
            bg=COULEUR_ENTETE,
            fg="#b8d8e0",
            font=("Segoe UI", 10),
        )
        self.lbl_etape.pack(side="right", padx=(0, 16))

        # bascule clair / sombre
        self._bandeau = bandeau
        self.btn_theme = tk.Button(
            bandeau,
            text="\u263e  Mode sombre",
            command=self.basculer_theme,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9),
            padx=10,
            pady=2,
        )
        self.btn_theme.pack(side="right", padx=(0, 12))

        self.etat = BarreEtat(self)
        self.etat.pack(side="bottom", fill="x")

        self.conteneur = ttk.Frame(self)
        self.conteneur.pack(fill="both", expand=True)

        self.onglets = ttk.Notebook(self.conteneur)
        self.onglets.pack(fill="both", expand=True, padx=6, pady=6)

        self.ecran = EcranClans(self.onglets, con, self.etat)
        self.onglets.add(self.ecran, text="  1. Clans  ")

        self.ecran_gf = EcranGrandesFamilles(self.onglets, con, self.etat)
        self.onglets.add(self.ecran_gf, text="  2. Grandes familles  ")

        self.ecran_lg = EcranLignees(self.onglets, con, self.etat)
        self.onglets.add(self.ecran_lg, text="  3. Lignées  ")

        self.ecran_fa = EcranFamilles(self.onglets, con, self.etat)
        self.onglets.add(self.ecran_fa, text="  4. Familles  ")

        self.ecran_me = EcranMembres(self.onglets, con, self.etat)
        self.onglets.add(self.ecran_me, text="  5. Membres  ")

        self.ecran_co = EcranCotisations(self.onglets, con, self.etat)
        self.onglets.add(self.ecran_co, text="  6. Cotisations  ")

        self.ecran_tb = EcranTableauBord(self.onglets, con, self.etat)
        self.onglets.add(self.ecran_tb, text="  7. Tableau de bord  ")

        self.ecran_pa = EcranParametres(self.onglets, con, self.etat,
                                        sur_restauration=self.tout_recharger)
        self.onglets.add(self.ecran_pa, text="  8. Paramètres  ")

        self.onglets.bind("<<NotebookTabChanged>>", self._sur_changement_onglet)

        # ---- thème clair / sombre ----
        self.theme = theme.Gestionnaire(self)
        theme.definir_gestionnaire(self.theme)
        self.theme.suivre_cadre(self.conteneur)
        self.theme.suivre_cadre(self)
        self.theme.charger(con)
        self._habiller_calendriers()
        self._noter_couleurs()
        self.theme.recenser_tk(self)
        self.theme.appliquer()
        self._maj_bouton_theme()

        self.ecran.focus_initial()

        # menu d'aide : diagnostic de mise en page
        barre_menu = tk.Menu(self)
        aide = tk.Menu(barre_menu, tearoff=0)
        aide.add_command(label="Diagnostic de mise en page",
                         command=self.diagnostic)
        aide.add_separator()
        aide.add_command(label="Basculer clair / sombre  (Ctrl+D)",
                         command=self.basculer_theme)
        barre_menu.add_cascade(label="Aide", menu=aide)
        self.config(menu=barre_menu)

        self.etat.info(
            "Prêt. Étapes : 1 Clans, 2 Grandes familles, 3 Lignées, 4 Familles, 5 Membres."
        )

        # sauvegarde automatique à la fermeture
        self._sauvegarde_faite = False
        self.protocol("WM_DELETE_WINDOW", self.fermer)
        self.bind_all("<Control-d>", lambda _e: self.basculer_theme())

    # ------------------------------------------------------------------
    #  Thème clair / sombre
    # ------------------------------------------------------------------
    def _habiller_calendriers(self):
        """Recolore les calendriers des écrans qui en possèdent un."""
        self._calendriers = []
        for ecran in (self.ecran_co,):
            cal = getattr(ecran, "calendrier", None)
            if cal is not None:
                self._calendriers.append(cal)
                self.theme.suivre_calendrier(cal)
            else:
                for nom in ("cal", "calendrier", "_cal"):
                    cal = getattr(ecran, nom, None)
                    if cal is not None:
                        self._calendriers.append(cal)
                        self.theme.suivre_calendrier(cal)
                        break

    def _noter_couleurs(self):
        """Recense les couleurs écrites en dur dans tous les écrans."""
        def parcourir(widget):
            for option in ("foreground", "bg", "background"):
                try:
                    valeur = widget.cget(option)
                except (tk.TclError, AttributeError):
                    continue
                if isinstance(valeur, str) and valeur.startswith("#"):
                    self.theme.enregistrer(widget, option, valeur)
            for enfant in widget.winfo_children():
                parcourir(enfant)

        parcourir(self)

    def _maj_bouton_theme(self):
        clair = not self.theme.sombre
        self.btn_theme.config(
            text="\u263e  Mode sombre" if clair else "\u2600  Mode clair")
        if hasattr(self, "_bandeau"):
            try:
                bandeau_bg = self.theme.couleur("entete")
                self._bandeau.configure(bg=bandeau_bg)
                for enfant in self._bandeau.winfo_children():
                    if isinstance(enfant, tk.Label):
                        enfant.configure(bg=bandeau_bg)
            except tk.TclError:
                pass
        try:
            self.btn_theme.configure(
                bg=self.theme.couleur("entete"),
                fg=self.theme.couleur("entete_second"),
                activebackground=self.theme.couleur("accent"),
                activeforeground=self.theme.couleur("entete_texte"))
        except tk.TclError:
            pass

    def basculer_theme(self):
        nom = self.theme.basculer()
        self._maj_bouton_theme()
        self.theme.enregistrer_choix(self.con)
        self.etat.info("Thème %s activé." %
                       ("sombre" if nom == "sombre" else "clair"))

    # ------------------------------------------------------------------
    #  Rechargement global (après restauration ou purge)
    # ------------------------------------------------------------------
    def tout_recharger(self):
        """Relit la base et remet tous les écrans à jour."""
        erreurs = []
        for ecran in (self.ecran, self.ecran_gf, self.ecran_lg,
                      self.ecran_fa, self.ecran_me):
            try:
                ecran.recharger_parents()
                ecran.recharger()
            except Exception as e:
                erreurs.append(str(e))
                print("tout_recharger:", e)
        for ecran in (self.ecran_co, self.ecran_tb, self.ecran_pa):
            try:
                if ecran is self.ecran_pa:
                    ecran.recharger()
                else:
                    ecran.recharger_annees()
            except Exception as e:
                erreurs.append(str(e))
                print("tout_recharger:", e)
        if erreurs:
            self.etat.info("Rechargement partiel : %d erreur(s). "
                           "Voir la console." % len(erreurs))
            messagebox.showwarning(
                "Rechargement",
                "Certaines vues n'ont pas pu être rechargées :\n"
                + "\n".join(erreurs[:5]))
        else:
            self.etat.info("Données rechargées.")

    # ------------------------------------------------------------------
    #  Fermeture : sauvegarde automatique (n et n-1 conservées)
    # ------------------------------------------------------------------
    def fermer(self):
        if self._sauvegarde_faite:
            self.destroy()
            return
        self._sauvegarde_faite = True
        try:
            chemin = P.sauvegarder(self.con)
            self.con.close()
            print(f"Sauvegarde automatique : {chemin}")
        except Exception as e:
            print(f"Sauvegarde automatique impossible : {e}")
        self.destroy()

    @staticmethod
    def _dans_cadre_defilant(widget):
        """Vrai si le widget est dans un canevas défilant : il reste
        atteignable même s'il dépasse la fenêtre."""
        parent = widget.master
        while parent is not None:
            if parent.winfo_class() == "Canvas":
                return True
            parent = parent.master
        return False

    def diagnostic(self):
        """Affiche la position reelle de chaque bouton : permet de verifier
        qu'aucun n'est hors fenetre."""
        ecran = self.onglets.nametowidget(self.onglets.select())
        W, H = self.winfo_width(), self.winfo_height()
        lignes = [f"Fenêtre : {W} x {H}", ""]
        boutons = []

        def walk(w):
            for c in w.winfo_children():
                if c.winfo_class() == "TButton":
                    # position DANS SON CONTENEUR (indépendante du défilement) :
                    # si le bouton est dans un cadre défilant, le défilement suffit
                    x = c.winfo_rootx() - self.winfo_rootx()
                    y = c.winfo_rooty() - self.winfo_rooty()
                    dedans = (x >= 0 and y >= 0
                              and x + c.winfo_width() <= W
                              and y + c.winfo_height() <= H)
                    defilant = self._dans_cadre_defilant(c)
                    boutons.append((c.cget("text"), x, y,
                                    c.winfo_width(), c.winfo_height(),
                                    dedans or defilant, defilant))
                walk(c)
        walk(ecran)

        if not boutons:
            lignes.append("Aucun bouton détecté sur cet onglet.")
        for t, x, y, w, h, dedans, defilant in boutons:
            if dedans and not defilant:
                etat = "OK "
            elif defilant:
                etat = "DEFILANT"
            else:
                etat = "HORS"
            lignes.append(f"{etat:9s} {t:26s} x={x:4d} y={y:4d}  {w}x{h}")
        hors = [b for b in boutons if not b[5]]
        lignes.append("")
        lignes.append("Tous les boutons sont accessibles."
                      if not hors
                      else f"{len(hors)} bouton(s) inaccessibles : agrandissez "
                           f"la fenêtre.")
        messagebox.showinfo("Diagnostic de mise en page", chr(10).join(lignes))

    def _sur_changement_onglet(self, _evt=None):
        """Chaque onglet relit ses listes de parents : un clan créé
        à l'étape 1 doit apparaître immédiatement à l'étape 2."""
        courant = self.onglets.index(self.onglets.select())
        if courant == 0:
            self.ecran.recharger()
            self.lbl_etape.config(text="Étape 1 / 6")
        elif courant == 1:
            self.ecran_gf.recharger_clans()
            self.ecran_gf.recharger(garder_id=self.ecran_gf.id_selection)
            self.lbl_etape.config(text="Étape 2 / 6")
        elif courant == 2:
            self.ecran_lg.recharger_parents()
            self.ecran_lg.recharger(garder_id=self.ecran_lg.id_selection)
            self.lbl_etape.config(text="Étape 3 / 6")
        elif courant == 3:
            self.ecran_fa.recharger_parents()
            self.ecran_fa.recharger(garder_id=self.ecran_fa.id_selection)
            self.lbl_etape.config(text="Étape 4 / 6")
        elif courant == 4:
            self.ecran_me.recharger_parents()
            self.ecran_me.recharger(garder_id=self.ecran_me.id_selection)
            self.lbl_etape.config(text="Étape 5 / 6")
        elif courant == 5:
            self.ecran_co.recharger_annees()
            self.lbl_etape.config(text="Étape 6 / 6")
        elif courant == 6:
            self.ecran_tb.recharger_annees()
            self.lbl_etape.config(text="Tableau de bord")
        elif courant == 7:
            self.ecran_pa.recharger()
            self.lbl_etape.config(text="Paramètres")


def _choisir_base(candidats):
    """Écran d'accueil : laisse l'utilisateur choisir la base à ouvrir.

    Retourne le chemin choisi (Path) ou None si annulé.
    """
    import tkinter as tk
    from tkinter import filedialog, messagebox

    choix = {"chemin": None}

    root = tk.Tk()
    root.title("Fonds d'Entraide — Choix de la base")
    root.geometry("460x260")
    root.resizable(False, False)
    try:
        appliquer_icone(root)
    except Exception:
        pass

    tk.Label(root, text="Choisissez la base de données à ouvrir",
             font=("Segoe UI", 12, "bold")).pack(pady=(16, 8))

    def choisir(chemin):
        choix["chemin"] = chemin
        root.destroy()

    for c in candidats:
        tk.Button(root, text=str(c.name), width=40,
                  command=lambda p=c: choisir(p)).pack(pady=2)

    def parcourir():
        f = filedialog.askopenfilename(
            title="Ouvrir une base SQLite",
            filetypes=[("Base SQLite", "*.db"), ("Tous", "*.*")])
        if f:
            choisir(Path(f))

    tk.Button(root, text="Parcourir…", width=40, command=parcourir).pack(pady=2)
    tk.Button(root, text="Créer une nouvelle base (familles.db)", width=40,
              command=lambda: choisir(db.BASE_DIR / "familles.db")).pack(pady=2)

    root.mainloop()
    return choix["chemin"]


def main():
    chemin = db.lire_chemin_base()
    if chemin is None:
        # détection automatique des bases existantes
        candidats = [p for p in (db.BASE_DIR / "cotisations.db",
                                 db.BASE_DIR / "familles.db")
                     if p.exists()]
        if len(candidats) == 1:
            chemin = candidats[0]
        elif len(candidats) > 1:
            chemin = _choisir_base(candidats)
        else:
            chemin = db.BASE_DIR / "familles.db"
        if chemin is not None:
            db.memoriser_chemin_base(chemin)
    if chemin is None:
        return
    con = db.initialiser(chemin)
    app = Application(con)
    try:
        app.mainloop()
    finally:
        con.close()


if __name__ == "__main__":
    main()
