import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


def setup_logger(name="MailSorter"):
    """
    Configure un logger qui écrit dans un fichier et stderr.
    JAMAIS stdout car cela casserait le protocole Native Messaging.
    """
    # Chemin de log dans le dossier utilisateur ou temp pour éviter les problèmes de droits
    # TODO: Rendre ce chemin configurable via fichier de config
    log_dir = os.path.join(os.path.expanduser("~"), ".mailsorter", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "backend.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File Handler (Rotating)
    # Max 5MB, keep 3 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stderr Handler (Visible if launched from terminal for debug, safe for Native Messaging)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger()
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


def setup_logger(name="MailSorter"):
    """
    Configure un logger qui écrit dans un fichier et stderr.
    JAMAIS stdout car cela casserait le protocole Native Messaging.
    """
    # Chemin de log dans le dossier utilisateur ou temp pour éviter les problèmes de droits
    # TODO: Rendre ce chemin configurable via fichier de config
    log_dir = os.path.join(os.path.expanduser("~"), ".mailsorter", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "backend.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File Handler (Rotating)
    # Max 5MB, keep 3 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stderr Handler (Visible if launched from terminal for debug, safe for Native Messaging)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger()
