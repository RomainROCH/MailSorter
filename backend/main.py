import sys
import json
import struct
import os

# Ajout du chemin courant au path pour les imports relatifs si nécessaire
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logger import logger
from core.orchestrator import Orchestrator

# Ce code applique le Plan V5 du projet de tri d’emails LLM, avec conformité RGPD et sécurité renforcée.
# Pour toute hypothèse technique non vérifiée, voir les TODO dans le code.
# Toute modification doit être validée par audit RGPD et revue technique.


def get_message():
    """
    Lit un message depuis stdin (Native Messaging Protocol).
    Format: 4 octets (longueur, little-endian) + JSON string.
    """
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return None
    message_length = struct.unpack("@I", raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


def send_message(message_content):
    """
    Envoie un message vers stdout (Native Messaging Protocol).
    Format: 4 octets (longueur, little-endian) + JSON string.
    """
    encoded_content = json.dumps(message_content).encode("utf-8")
    encoded_length = struct.pack("@I", len(encoded_content))
    sys.stdout.buffer.write(encoded_length)
    sys.stdout.buffer.write(encoded_content)
    sys.stdout.buffer.flush()


def main():
    logger.info("MailSorter Backend Started")
    orchestrator = Orchestrator()

    while True:
        try:
            message = get_message()
            if message is None:
                logger.info("Stdin closed, exiting.")
                break

            logger.info(f"Received message type: {message.get('type')}")

            # Dispatching
            response = orchestrator.handle_message(message)

            send_message(response)

        except Exception as e:
            logger.error(f"Critical Error in Main Loop: {e}", exc_info=True)
            # On renvoie une erreur structurée au client
            send_message({"status": "error", "error": str(e)})


if __name__ == "__main__":
    main()
