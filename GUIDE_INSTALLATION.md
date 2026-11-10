# Guide d'installation — Fonds d'Entraide

Ce guide explique comment installer, lancer et mettre à jour l'application
**Fonds d'Entraide** sur un poste Windows.

---

## 1. Prérequis

- **Windows 10 ou 11** (64 bits).
- **Aucune installation de Python requise** : l'exécutable embarque son
  propre interpréteur.
- **Aucun droit administrateur** requis (installation dans le profil
  utilisateur).

---

## 2. Installation (méthode recommandée — installateur)

1. Récupérez le fichier **`Fond-Entraide-Setup.exe`** (voir § 6 pour le
   télécharger ou le générer).
2. Double-cliquez sur `Fond-Entraide-Setup.exe`.
3. Choisissez le dossier d'installation (par défaut :
   `%LOCALAPPDATA%\Programs\Fond-Entraide`).
4. Cliquez sur **Installer**.
5. L'installateur extrait l'application et crée les raccourcis :
   - **Menu Démarrer** → Fond-Entraide
   - **Bureau** → Fond-Entraide

L'installation prend environ 30 secondes (extraction de ~50 Mo).

---

## 3. Premier lancement

1. Lancez l'application via le raccourci du bureau ou du menu Démarrer.
2. Au premier démarrage, un **écran d'accueil** vous demande de choisir la
   base de données :
   - Si vous possédez déjà une base `cotisations.db` (base de référence
     importée de l'Excel), sélectionnez-la via **Parcourir…**.
   - Sinon, cliquez sur **Créer une nouvelle base (familles.db)**.
3. Le choix est mémorisé dans `base_choisie.json` : les lancements suivants
   ouvrent directement la base choisie.

> **Important** : ne déplacez pas la base `.db` après l'avoir choisie.
> Si vous la déplacez, l'application vous redemandera de la sélectionner.

---

## 4. Utilisation quotidienne

- **Lancement** : double-clic sur le raccourci (aucune console noire).
- **Données** : la base `.db`, les sauvegardes (`sauvegardes/`) et les
  journaux (`logs/`) sont stockés dans le dossier d'installation.
- **Sauvegarde automatique** : à la fermeture, une copie tournante (n et
  n-1) est écrite dans `sauvegardes/`.
- **Sauvegarde manuelle** : onglet **Paramètres** → bouton
  « Sauvegarder maintenant ».
- **Restauration** : Paramètres → « Restaurer une sauvegarde ».

---

## 5. Désinstallation

L'application ne dispose pas encore d'un désinstallateur automatique.
Pour la désinstaller :

1. Supprimez le dossier d'installation
   (ex. `%LOCALAPPDATA%\Programs\Fond-Entraide`).
2. Supprimez les raccourcis du bureau et du menu Démarrer.
3. *(Optionnel)* Supprimez `base_choisie.json` si vous souhaitez effacer
   tout souvenir de l'application.

> **Attention** : la suppression du dossier efface aussi la base de données
> et les sauvegardes. Sauvegardez vos données avant de désinstaller.

---

## 6. Obtenir l'installateur

### Option A — Télécharger l'exécutable déjà généré
L'installateur `Fond-Entraide-Setup.exe` (~58 Mo) est fourni avec le
projet dans le dossier `dist/`. Copiez-le où vous voulez et lancez-le.

### Option B — Générer l'installateur depuis les sources
Prérequis : Python 3.10+ et PyInstaller.

```bash
# 1. Installer les dépendances
pip install -r requirements.txt
pip install pyinstaller

# 2. Construire l'application
python -m PyInstaller --noconfirm --onedir --windowed \
    --name "Fond-Entraide" --icon relation.ico \
    --add-data "schema.sql;." --add-data "relation.ico;." \
    --add-data "repertoires.json;." \
    --collect-all tkcalendar --collect-all reportlab app.py

# 3. Créer la charge utile
python -c "
import zipfile, os
z = zipfile.ZipFile('payload.zip', 'w', zipfile.ZIP_DEFLATED)
for r, _, fs in os.walk('dist/Fond-Entraide'):
    for f in fs:
        if f.endswith(('.db', '.json', '.log')): continue
        if os.path.split(r)[-1] in ('logs', 'sauvegardes', 'demo'): continue
        z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), 'dist/Fond-Entraide'))
z.close()
"

# 4. Construire l'installateur
python -m PyInstaller --noconfirm --onefile --windowed \
    --name "Fond-Entraide-Setup" --add-data "payload.zip;." installer.py
```

L'installateur est généré dans `dist/Fond-Entraide-Setup.exe`.

---

## 7. Mise à jour

Pour mettre à jour l'application :

1. **Sauvegardez votre base** (copiez `cotisations.db` ou votre base
   choisie dans un dossier sûr).
2. Lancez le nouvel installateur `Fond-Entraide-Setup.exe`.
3. Installez dans le **même dossier** que la version précédente
   (l'installateur écrase les fichiers de l'application).
4. Votre base `.db` et vos sauvegardes sont **conservées** (l'installateur
   n'écrase que les fichiers de l'application, pas les `.db`).

> **Conseil** : avant une mise à jour majeure, faites une copie manuelle de
> votre base `.db` dans un dossier externe.

---

## 8. Dépannage

| Problème | Solution |
|---|---|
| « Failed to load Python DLL » | Réinstallez avec l'installateur complet (ne copiez pas uniquement le `.exe`). |
| « schema.sql introuvable » | Vérifiez que le dossier `_internal` est présent à côté de l'exe. |
| Base vide au lancement | Vous avez ouvert `familles.db` au lieu de `cotisations.db`. Relancez et choisissez la bonne base (Paramètres → Importer une base). |
| Sauvegarde automatique échoue | Vérifiez les droits d'écriture sur le dossier d'installation. |
| Application qui ne démarre pas | Consultez `logs/fond_entraide.log` à côté de l'exe. |

---

## 9. Structure du dossier installé

```
Fond-Entraide/
├── Fond-Entraide.exe          # exécutable principal
├── _internal/                 # dépendances (Python, Tk, etc.)
├── schema.sql                 # schéma de la base
├── relation.ico               # icône
├── base_choisie.json          # base sélectionnée (généré au 1er lancement)
├── cotisations.db             # base de données (votre choix)
├── sauvegardes/               # sauvegardes tournantes
└── logs/                      # journaux
```

---

## 10. Contact et support

Pour toute question ou problème, consultez le fichier `GUIDE.md` (mode
d'emploi complet) ou le fichier `PROBLEMES.md` (registre des problèmes
connus et de leur résolution).
