import time
import os
import logging
import google.generativeai as genai
import requests

# Configurazione di base del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def merge_and_summarize(video_text, pdf_text, gemini_api_key=None, mistral_api_key=None, update_callback=None):
    """
    Invia i testi estratti a Google Gemini API o Mistral API per generare note di lezione strutturate.
    
    Args:
        video_text: Testo trascritto dal video (può essere None).
        pdf_text: Testo estratto dal PDF (può essere None).
        gemini_api_key: Chiave API per Google Gemini (opzionale).
        mistral_api_key: Chiave API per Mistral (opzionale).
        update_callback: Funzione callback per aggiornare lo stato nell'UI.
        
    Returns:
        Testo delle note generate o None in caso di errore.
    """
    try:
        # Helper function to handle updates with or without callback
        def log_update(status_type, message):
            if update_callback:
                update_callback(status_type, message)
            logger.info(f"{status_type.upper()}: {message}")
    
        # --- Logica recupero API Keys ---
        gemini_key = None
        mistral_key = None
        using_gemini_source = ""
        using_mistral_source = ""
        
        # Recupera Gemini API Key
        if gemini_api_key:
            gemini_key = gemini_api_key
            using_gemini_source = "GUI"
            logger.info("Utilizzo Gemini API Key fornita dalla GUI.")
        else:
            logger.info("Tentativo di recuperare Gemini API Key dalla variabile d'ambiente GOOGLE_API_KEY.")
            gemini_key = os.getenv("GOOGLE_API_KEY")
            using_gemini_source = "Variabile d'ambiente"
            
        # Recupera Mistral API Key
        if mistral_api_key:
            mistral_key = mistral_api_key
            using_mistral_source = "GUI"
            logger.info("Utilizzo Mistral API Key fornita dalla GUI.")
        else:
            logger.info("Tentativo di recuperare Mistral API Key dalla variabile d'ambiente MISTRAL_API_KEY.")
            mistral_key = os.getenv("MISTRAL_API_KEY")
            using_mistral_source = "Variabile d'ambiente"

        # Verifica che almeno una API key sia disponibile
        if not gemini_key and not mistral_key:
            error_message = "Errore: Nessuna API key disponibile. Imposta GOOGLE_API_KEY o MISTRAL_API_KEY o forniscile nella GUI."
            logger.error(error_message)
            log_update("error", error_message)
            return None
            
        # Costruisci il prompt
        prompt_parts = [
            "Sei un assistente esperto nella creazione di appunti di lezione dettagliati e ben organizzati.",
            "Il tuo compito è sintetizzare le informazioni provenienti da una trascrizione video e/o da un documento PDF (slide/testo) per creare note complete.",
            "Struttura le note utilizzando Markdown per chiarezza (titoli, elenchi puntati, grassetto per termini chiave).",
            "Fondi le informazioni in modo coerente, non limitarti a riassumere le fonti separatamente.",
            "Se una fonte manca, basa le note solo su quella disponibile.",
            "Evita frasi come 'Basandomi sul video...' o 'Dal PDF emerge che...'. Presenta direttamente le informazioni.",
            "\n--- INIZIO CONTENUTO ---\n"
        ]
        
        if video_text:
            prompt_parts.append("--- Trascrizione Video ---")
            prompt_parts.append(video_text)
            prompt_parts.append("--- Fine Trascrizione Video ---\n")
            
        if pdf_text:
            prompt_parts.append("--- Testo PDF ---")
            prompt_parts.append(pdf_text)
            prompt_parts.append("--- Fine Testo PDF ---\n")
            
        prompt_parts.append("--- FINE CONTENUTO ---\n")
        prompt_parts.append("Genera ora le note di lezione dettagliate:")
        
        final_prompt = "\n".join(prompt_parts)
        
        # Prova prima con Gemini se disponibile
        if gemini_key:
            try:
                log_update("status", f"Connessione a Google Gemini (usando key da {using_gemini_source})...")
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
                
                log_update("status", "Invio richiesta a Gemini e generazione note (potrebbe richiedere tempo)...")
                response = model.generate_content(final_prompt)
                
                # Gestisci la risposta
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason
                    error_message = f"La richiesta è stata bloccata da Gemini per motivi di sicurezza: {block_reason}"
                    logger.error(error_message)
                    log_update("error", error_message)
                    # Non ritornare None, prova con Mistral se disponibile
                elif hasattr(response, 'text') and response.text:
                    log_update("status", "Note generate con successo usando Gemini.")
                    return response.text
                else:
                    error_message = "Risposta vuota ricevuta da Gemini."
                    logger.error(error_message)
                    log_update("error", error_message)
                    # Non ritornare None, prova con Mistral se disponibile
            except Exception as gemini_error:
                error_message = f"Errore durante la comunicazione con Google Gemini: {str(gemini_error)}"
                logger.error(error_message)
                log_update("error", error_message)
                # Non ritornare None, prova con Mistral se disponibile
        
        # Se Gemini non è disponibile o ha fallito, prova con Mistral
        if mistral_key:
            try:
                log_update("status", f"Connessione a Mistral (usando key da {using_mistral_source})...")
                
                # Configura la richiesta a Mistral
                headers = {
                    "Authorization": f"Bearer {mistral_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "mistral-medium",
                    "messages": [
                        {"role": "system", "content": "Sei un assistente esperto nella creazione di appunti di lezione dettagliati e ben organizzati."},
                        {"role": "user", "content": final_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
                
                log_update("status", "Invio richiesta a Mistral e generazione note (potrebbe richiedere tempo)...")
                response = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        summary = result["choices"][0]["message"]["content"]
                        log_update("status", "Note generate con successo usando Mistral.")
                        return summary
                    else:
                        error_message = "Risposta vuota ricevuta da Mistral."
                        logger.error(error_message)
                        log_update("error", error_message)
                else:
                    error_message = f"Errore nella risposta di Mistral: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    log_update("error", error_message)
            except Exception as mistral_error:
                error_message = f"Errore durante la comunicazione con Mistral: {str(mistral_error)}"
                logger.error(error_message)
                log_update("error", error_message)
        
        # Se arriviamo qui, entrambi i servizi hanno fallito
        error_message = "Impossibile generare note: entrambi i servizi AI hanno fallito."
        logger.error(error_message)
        log_update("error", error_message)
        return None
            
    except Exception as e:
        error_message = f"Errore durante la fusione AI: {str(e)}"
        logger.error(error_message)
        log_update("error", error_message)
        return None
