"""
installer.py — Installateur de Fond-Entraide.

Extrait la charge utile (payload.zip, embarquée) vers un dossier d'installation
choisi par l'utilisateur, puis crée les raccourcis (menu Démarrer + bureau).
"""
import os
import sys
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


def ressource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def creer_raccourci(cible, raccourci, icone=None, description=""):
    """Crée un raccourci .lnk via PowerShell."""
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        "$s = $ws.CreateShortcut('%s'); "
        "$s.TargetPath = '%s'; "
        "$s.WorkingDirectory = '%s'; "
        "%s"
        "$s.Save()"
    ) % (
        raccourci.replace("'", "''"),
        cible.replace("'", "''"),
        os.path.dirname(cible).replace("'", "''"),
        ("$s.IconLocation = '%s,0'; " % icone.replace("'", "''")) if icone else "",
    )
    try:
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                      check=True, capture_output=True)
        return True
    except Exception as e:
        print("raccourci:", e)
        return False


def main():
    root = tk.Tk()
    root.title("Fond-Entraide — Installation")
    root.geometry("520x260")
    root.resizable(False, False)

    tk.Label(root, text="Installation de Fond-Entraide",
             font=("Segoe UI", 13, "bold")).pack(pady=(16, 4))
    tk.Label(root, text="Choisissez le dossier d'installation.",
             font=("Segoe UI", 9)).pack()

    var_dir = tk.StringVar(value=os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "Programs", "Fond-Entraide"))
    ent = tk.Entry(root, textvariable=var_dir, width=60)
    ent.pack(pady=8, padx=16)

    def parcourir():
        d = filedialog.askdirectory(title="Dossier d'installation")
        if d:
            var_dir.set(d)

    tk.Button(root, text="Parcourir…", command=parcourir).pack()

    statut = tk.StringVar(value="")
    lbl = tk.Label(root, textvariable=statut, font=("Segoe UI", 9),
                   foreground="#1f4e5f")
    lbl.pack(pady=8)

    def installer():
        dest = var_dir.get().strip()
        if not dest:
            messagebox.showerror("Erreur", "Dossier d'installation vide.")
            return
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Erreur", str(e))
            return
        statut.set("Extraction en cours…")
        root.update()
        try:
            with zipfile.ZipFile(ressource("payload.zip")) as z:
                z.extractall(dest)
        except Exception as e:
            messagebox.showerror("Erreur d'extraction", str(e))
            return
        # raccourcis
        cible = os.path.join(dest, "Fond-Entraide.exe")
        icone = os.path.join(dest, "relation.ico")
        menu = os.path.join(os.environ.get("APPDATA", ""),
                            "Microsoft", "Windows", "Start Menu", "Programs")
        os.makedirs(menu, exist_ok=True)
        lnk_menu = os.path.join(menu, "Fond-Entraide.lnk")
        creer_raccourci(cible, lnk_menu, icone, "Fonds d'Entraide")
        bureau = os.path.join(os.path.expanduser("~"), "Desktop")
        lnk_bureau = os.path.join(bureau, "Fond-Entraide.lnk")
        creer_raccourci(cible, lnk_bureau, icone, "Fonds d'Entraide")
        statut.set("Installation terminée.")
        messagebox.showinfo("Terminé",
                            "Fond-Entraide a été installé dans :\n" + dest +
                            "\n\nRaccourcis créés (menu Démarrer + bureau).")
        root.destroy()

    tk.Button(root, text="Installer", width=20, command=installer).pack(pady=8)
    root.mainloop()


if __name__ == "__main__":
    main()