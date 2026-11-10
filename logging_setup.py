"""Configuration minimale de la journalisation (P19).

À importer en tout début de `app.py` (et des scripts autonomes) pour que
les erreurs ne partent plus en `print` invisible quand l'application est
lancée par double-clic.
"""
import logging
from pathlib import Path

from db import BASE_DIR


def configurer(nom="fond_entraide"):
    dossier = BASE_DIR / "logs"
    try:
        dossier.mkdir(parents=True, exist_ok=True)
    except OSError:
        dossier = BASE_DIR
    fichier = dossier / (nom + ".log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(fichier, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return logging.getLogger(nom)