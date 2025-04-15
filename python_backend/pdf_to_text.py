import os
import logging
from mistralai import Mistral  # Solo Mistral, niente eccezioni specifiche

# Configurazione di base del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path, update_callback=None, gui_mistral_api_key=None):
    """
    Estrae il testo da un PDF usando esclusivamente l'API Mistral AI OCR.

    Args:
        pdf_path: Percorso al file PDF.
        update_callback: Funzione callback per aggiornare lo stato nell'UI (opzionale).
        gui_mistral_api_key: Chiave API fornita dalla GUI (ha priorità).

    Returns:
        Testo estratto in formato Markdown o None in caso di errore.
    """
    # Helper function per logging con/senza callback
    def log_update(status_type, message):
        if update_callback:
            update_callback(status_type, message)
        if status_type == "error":
            logger.error(message)
        else:
            logger.info(f"{status_type.upper()}: {message}") # Logga anche status/info

    try:
        # Verifica esistenza del file PDF
        if not os.path.exists(pdf_path):
            log_update("error", f"File PDF non trovato: {pdf_path}")
            return None

        log_update("status", f"Inizio elaborazione PDF: {os.path.basename(pdf_path)} con Mistral AI...")

        # --- Logica Recupero API Key Mistral ---
        api_key = None
        using_source = ""
        if gui_mistral_api_key:
            api_key = gui_mistral_api_key
            using_source = "GUI"
            logger.info("Utilizzo API Key Mistral fornita dalla GUI.")
        else:
            logger.info("Tentativo di recuperare API Key Mistral dalla variabile d'ambiente MISTRAL_API_KEY.")
            api_key = os.getenv("MISTRAL_API_KEY")
            using_source = "Variabile d'ambiente"

        if not api_key:
            error_message = f"Errore: MISTRAL_API_KEY non trovata ({using_source}). Impostala o forniscila nella GUI. Elaborazione PDF annullata."
            log_update("error", error_message)
            return None
        # ---------------------------------------

        # Inizializza client Mistral
        try:
            client = Mistral(api_key=api_key)
            log_update("status", f"Client Mistral AI inizializzato (usando key da {using_source}).")
        except Exception as client_err:
            error_message = f"Errore inizializzazione client Mistral: {client_err}"
            log_update("error", error_message)
            return None

        uploaded_file = None
        signed_url_response = None
        try:
            # --- Upload del file a Mistral ---
            log_update("status", "Upload del PDF a Mistral AI...")
            with open(pdf_path, "rb") as f:
                uploaded_file = client.files.upload(
                    file={'file_name': os.path.basename(pdf_path), 'content': f},
                    purpose='ocr'
                )
            if not uploaded_file or not uploaded_file.id:
                raise Exception("Upload file a Mistral fallito o ID non restituito.")
            log_update("status", f"Upload completato. File ID: {uploaded_file.id}")

            # --- Ottenere Signed URL (consigliato) ---
            log_update("status", "Ottenimento URL temporaneo per l'OCR...")
            signed_url_response = client.files.get_signed_url(file_id=uploaded_file.id)
            if not signed_url_response or not signed_url_response.url:
                raise Exception("Ottenimento signed URL da Mistral fallito.")
            document_url = signed_url_response.url
            log_update("status", "URL ottenuto. Invio richiesta OCR a Mistral AI...")

            # --- Chiamata API OCR ---
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": document_url,
                }
                # Considera include_image_base64=False se non ti servono le immagini
            )

            # --- Estrazione Contenuto ---
            # --- NUOVA Logica Estrazione Contenuto ---
            if hasattr(ocr_response, 'pages') and ocr_response.pages:
                extracted_text = ""
                for page in ocr_response.pages:
                    if hasattr(page, 'markdown') and page.markdown:
                        extracted_text += page.markdown + "\n\n"  # Aggiungi markdown e spaziatura tra pagine
                    else:
                        logger.warning(f"Pagina {getattr(page, 'index', '?')} nella risposta OCR non contiene 'markdown'.")

                if extracted_text:
                    log_update("status", "OCR completato con successo da Mistral AI.")
                    return extracted_text.strip()
                else:
                    # Caso in cui 'pages' esiste ma è vuota o nessuna pagina ha 'markdown'
                    logger.warning(f"Risposta OCR da Mistral conteneva 'pages' ma nessun contenuto markdown valido.")
                    raise Exception("Risposta OCR da Mistral non conteneva testo markdown valido.")
            else:
                # Caso in cui l'attributo 'pages' non esiste o è vuoto/None
                logger.warning(f"Risposta OCR da Mistral non contiene l'attributo 'pages' o è vuoto: {ocr_response}")
                raise Exception("Risposta OCR da Mistral non valida (manca 'pages').")
            # ----------------------------------------

        except Exception as mistral_err:  # Cattura qualsiasi errore API/HTTP
            error_message = f"Errore durante chiamata API Mistral AI (OCR): {mistral_err}"
            log_update("error", error_message)
            return None
        finally:
            # --- (Opzionale ma buona pratica) Pulizia file su Mistral ---
            if uploaded_file and uploaded_file.id:
                try:
                    logger.info(f"Tentativo di eliminare file {uploaded_file.id} da Mistral AI.")
                    client.files.delete(file_id=uploaded_file.id)
                except Exception as delete_err:
                    # Non critico, logga solo l'errore
                    logger.warning(f"Impossibile eliminare file {uploaded_file.id} da Mistral AI: {delete_err}")

    except Exception as e:
        # Errore generale
        error_message = f"Errore imprevisto durante elaborazione PDF con Mistral: {str(e)}"
        log_update("error", error_message)
        return None
