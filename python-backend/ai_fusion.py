import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
import sys
import time

# Configurazione del logging di base
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carica le variabili d'ambiente dal file .env nella stessa directory
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Configurazione API Gemini ---
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-1.5-flash-latest" # O un altro modello disponibile es. "gemini-pro"

# Controllo chiave API all'avvio
if not API_KEY:
    logging.error("Errore critico: La variabile d'ambiente GOOGLE_API_KEY non è impostata nel file .env")
    # Potremmo voler sollevare un'eccezione o uscire se la chiave è fondamentale
    # raise ValueError("GOOGLE_API_KEY non trovata. Impostala nel file python-backend/.env")
else:
    try:
        genai.configure(api_key=API_KEY)
        logging.info("API Key Google Gemini caricata e configurata correttamente.")
    except Exception as e:
        logging.error(f"Errore durante la configurazione dell'API Gemini: {e}", exc_info=True)
        API_KEY = None # Invalida la chiave se la configurazione fallisce

# Configurazioni di sicurezza per l'API (opzionale, ma consigliato)
# Blocca contenuti potenzialmente dannosi con soglia media o alta
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Configurazioni generazione (opzionale)
GENERATION_CONFIG = {
    "temperature": 0.7,       # Controlla la "creatività" (0=deterministico, 1=molto creativo)
    "top_p": 0.9,             # Nucleus sampling
    "top_k": 40,              # Considera solo i top K token più probabili
    "max_output_tokens": 8192,# Limite massimo token in output (adatta al modello)
}
# ----------------------------------

def build_prompt(video_transcript, pdf_text):
    """Costruisce il prompt da inviare a Gemini, combinando i testi."""

    # Istruzioni chiare per il modello AI
    prompt = f"""
Sei un assistente AI specializzato nella creazione di appunti dettagliati e ben strutturati da lezioni o presentazioni.
Hai ricevuto due input:

1.  **Trascrizione Video:** Il testo parlato estratto da una lezione video.
2.  **Testo Documento/Slide (PDF):** Il contenuto testuale estratto da un documento PDF (probabilmente slide o materiale di supporto).

**Il tuo compito è:**
Analizzare entrambi i testi, integrare le informazioni in modo coerente e generare un riassunto completo sotto forma di appunti di lezione. Gli appunti dovrebbero:
- Essere scritti in **Italiano**.
- Seguire una struttura logica (es. introduzione, argomenti principali, conclusioni).
- Usare titoli, sottotitoli (Markdown: #, ##, ###) e elenchi puntati/numerati per organizzare le informazioni.
- Evidenziare i concetti chiave, le definizioni importanti e gli esempi significativi.
- Integrare le informazioni dal PDF dove arricchiscono o chiariscono i punti della trascrizione video. Se ci sono discrepanze evidenti, segnalale brevemente.
- Mantenere un tono formale ed educativo.
- Essere il più completo possibile basandosi sui testi forniti. Non aggiungere informazioni esterne non presenti nei testi.
- Ignora eventuali artefatti di trascrizione (rumori, parole incerte) o errori OCR evidenti, concentrandoti sul contenuto significativo.

**Ecco i testi forniti:**

--- INIZIO TRASCRIZIONE VIDEO ---
{video_transcript if video_transcript else "[Trascrizione video non disponibile o vuota]"}
--- FINE TRASCRIZIONE VIDEO ---

--- INIZIO TESTO PDF ---
{pdf_text if pdf_text else "[Testo PDF non disponibile o vuoto]"}
--- FINE TESTO PDF ---

**Output richiesto:**
Genera gli appunti di lezione strutturati come descritto sopra. Inizia direttamente con il titolo principale della lezione (se deducibile) o con "Appunti della Lezione".
"""
    return prompt.strip()

def generate_notes_with_gemini(video_transcript, pdf_text):
    """Invia i testi a Gemini e ottiene le note generate."""
    if not API_KEY:
        logging.error("Impossibile generare note: API Key Google Gemini non configurata.")
        return None

    # Costruisci il prompt completo
    prompt = build_prompt(video_transcript, pdf_text)
    logging.info(f"Prompt costruito. Lunghezza approssimativa: {len(prompt)} caratteri.")
    # Potremmo voler aggiungere un controllo sulla lunghezza massima del prompt accettata dal modello

    try:
        logging.info(f"Invio richiesta all'API Gemini con modello '{MODEL_NAME}'...")
        # Inizializza il modello generativo
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            safety_settings=SAFETY_SETTINGS,
            generation_config=GENERATION_CONFIG
        )

        # Invia il prompt al modello
        start_time = time.time()
        response = model.generate_content(prompt)
        end_time = time.time()
        logging.info(f"Risposta ricevuta da Gemini in {end_time - start_time:.2f} secondi.")

        # Gestione della risposta e potenziali blocchi di sicurezza
        if not response.candidates:
             logging.error("La risposta di Gemini non contiene candidati. Possibile blocco per sicurezza o altri problemi.")
             # Prova a vedere se c'è un feedback sul prompt
             if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                 logging.error(f"Feedback sul prompt: {response.prompt_feedback}")
             return "[Errore: La generazione delle note è fallita. Controllare i log per dettagli. Potrebbe essere dovuto a filtri di sicurezza.]"

        # Estrai il testo generato dal primo candidato
        generated_notes = response.text

        # Log del motivo di fine generazione (es. STOP, MAX_TOKENS, SAFETY)
        finish_reason = response.candidates[0].finish_reason if response.candidates else "N/A"
        logging.info(f"Generazione completata. Motivo fine: {finish_reason}")
        if finish_reason == "MAX_TOKENS":
            logging.warning("L'output potrebbe essere stato troncato a causa del limite massimo di token.")
        elif finish_reason == "SAFETY":
            logging.warning("La generazione è stata interrotta a causa delle impostazioni di sicurezza.")
            return "[Errore: La generazione è stata bloccata per motivi di sicurezza.]"
        elif finish_reason != "STOP":
             logging.warning(f"Motivo di fine generazione non standard: {finish_reason}")


        logging.info(f"Note generate con successo. Lunghezza: {len(generated_notes)} caratteri.")
        return generated_notes

    except Exception as e:
        logging.error(f"Errore durante la chiamata all'API Google Gemini: {e}", exc_info=True)
        return f"[Errore durante la comunicazione con l'API Gemini: {e}]"

def process_and_generate(video_transcript_path, pdf_text_path, output_dir):
    """
    Carica i testi, genera le note con Gemini e salva il risultato.

    Args:
        video_transcript_path (str): Percorso del file .txt con la trascrizione video.
        pdf_text_path (str): Percorso del file .txt con il testo estratto dal PDF.
        output_dir (str): Directory dove salvare il file .txt con le note finali.

    Returns:
        str: Il percorso del file di output generato, o None se fallisce.
    """
    logging.info(f"--- Inizio fusione AI per video '{video_transcript_path}' e PDF '{pdf_text_path}' ---")

    # Leggi il contenuto dei file di testo
    try:
        with open(video_transcript_path, 'r', encoding='utf-8') as f:
            video_text = f.read()
        logging.info(f"Letto file trascrizione video: {len(video_text)} caratteri.")
    except FileNotFoundError:
        logging.warning(f"File trascrizione video non trovato: {video_transcript_path}. Procedo senza.")
        video_text = ""
    except Exception as e:
        logging.error(f"Errore nella lettura del file trascrizione video {video_transcript_path}: {e}")
        return None # Errore lettura file

    try:
        with open(pdf_text_path, 'r', encoding='utf-8') as f:
            pdf_text = f.read()
        logging.info(f"Letto file testo PDF: {len(pdf_text)} caratteri.")
    except FileNotFoundError:
        logging.warning(f"File testo PDF non trovato: {pdf_text_path}. Procedo senza.")
        pdf_text = ""
    except Exception as e:
        logging.error(f"Errore nella lettura del file testo PDF {pdf_text_path}: {e}")
        return None # Errore lettura file

    # Verifica se abbiamo almeno un input testuale
    if not video_text and not pdf_text:
        logging.error("Errore: Entrambi i file di input (trascrizione video e testo PDF) sono mancanti o vuoti.")
        return None

    # Genera le note usando Gemini
    generated_notes = generate_notes_with_gemini(video_text, pdf_text)

    if generated_notes is None or "[Errore:" in generated_notes:
        logging.error("Generazione delle note fallita o ha prodotto un errore. Nessun file di output verrà creato.")
        # Potremmo voler ritornare il messaggio di errore stesso invece di None
        # return f"output_error_{int(time.time())}.txt" # Nome file fittizio per indicare errore
        return None

    # Crea la directory di output se non esiste
    os.makedirs(output_dir, exist_ok=True)

    # Crea un nome file significativo per l'output
    base_name_video = os.path.splitext(os.path.basename(video_transcript_path))[0].replace("_transcript", "") if video_text else "no_video"
    base_name_pdf = os.path.splitext(os.path.basename(pdf_text_path))[0].replace("_extracted", "") if pdf_text else "no_pdf"
    output_filename = f"DeepNotes_{base_name_video}_{base_name_pdf}_{int(time.time())}.txt"
    output_path = os.path.join(output_dir, output_filename)

    # Salva le note generate nel file di output
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(generated_notes)
        logging.info(f"Note finali salvate con successo in: {output_path}")
        return output_path # Ritorna il percorso del file creato
    except Exception as e:
        logging.error(f"Errore durante il salvataggio delle note finali in {output_path}: {e}")
        return None

# Blocco per permettere l'esecuzione dello script da linea di comando per test
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Errore: Mancano i percorsi dei file di input.")
        print("Uso: python python-backend/ai_fusion.py <percorso_trascrizione_video.txt> <percorso_testo_pdf.txt> [output_directory]")
        print("Esempio: python python-backend/ai_fusion.py video_transcript.txt pdf_extract.txt ../output")
        print("Se un file non è disponibile, usa 'None' o un percorso fittizio (verrà gestito).")
        print("Esempio solo video: python python-backend/ai_fusion.py video_transcript.txt None ../output")
        sys.exit(1)

    video_file_path = sys.argv[1] if sys.argv[1].lower() != 'none' else ""
    pdf_file_path = sys.argv[2] if sys.argv[2].lower() != 'none' else ""
    output_directory = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), '..', 'output') # Default a ../output

    print(f"\n[TEST MODE] Avvio AI Fusion per:")
    print(f"[TEST MODE] - Video Transcript: {video_file_path if video_file_path else 'N/A'}")
    print(f"[TEST MODE] - PDF Text: {pdf_file_path if pdf_file_path else 'N/A'}")
    print(f"[TEST MODE] - Output Directory: {output_directory}")

    # Assicurati che la chiave API sia caricata (controllo ridondante ma utile per test)
    if not API_KEY:
        print("\n[ERRORE TEST] GOOGLE_API_KEY non trovata nel file .env. Impossibile procedere.")
        sys.exit(1)

    # Attiva l'ambiente virtuale (promemoria)
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'activate')
    if 'VIRTUAL_ENV' not in os.environ and os.path.exists(venv_path):
         print(f"[TEST MODE] Assicurati che l'ambiente virtuale sia attivo: source {venv_path}")

    # Esegui la funzione principale
    result_file = process_and_generate(video_file_path, pdf_file_path, output_directory)

    if result_file:
        print(f"\n--- Successo! Note generate e salvate in: {result_file} ---")
    else:
        print("\n--- Processo di generazione note fallito. Controlla i log sopra per errori. ---") 