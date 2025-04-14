import fitz  # PyMuPDF
import os
import logging
import sys

# Importazioni aggiuntive per OCR
import pytesseract
from PIL import Image
import io

# Configurazione del logging di base
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configurazione Tesseract (Modifica se necessario) ---
# Su macOS con Homebrew, potrebbe essere:
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
# Su Windows, potrebbe essere il percorso dove hai installato Tesseract, es:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Lascia commentato se tesseract è già nel PATH di sistema.
# ---------------------------------------------------------

def extract_text_directly(pdf_path):
    """Estrae il testo direttamente dalle pagine PDF usando PyMuPDF (fitz)."""
    logging.info(f"Tentativo di estrazione diretta del testo da: {pdf_path}")
    try:
        full_text = ""
        with fitz.open(pdf_path) as doc:
            num_pages = len(doc)
            logging.info(f"Il PDF ha {num_pages} pagine.")
            
            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                full_text += page_text + "\n\n"  # Aggiungi separatore di pagina
                logging.info(f"Pagina {page_num + 1}: estratti {len(page_text)} caratteri")
        
        logging.info(f"Estrazione diretta completata. Lunghezza testo: {len(full_text)} caratteri")
        return full_text.strip()
    
    except fitz.FileNotFoundError:
        logging.error(f"Errore: File PDF non trovato: {pdf_path}")
        return None
    except Exception as e:
        logging.error(f"Errore durante l'estrazione diretta del testo: {e}", exc_info=True)
        return None

def ocr_pdf_page(page, page_num, lang='eng'):
    """Esegue OCR su una singola pagina PDF resa come immagine usando Tesseract."""
    logging.info(f"Tentativo OCR sulla pagina {page_num + 1} con lingua '{lang}'...")
    try:
        # Renderizza la pagina come immagine PNG in memoria.
        # DPI più alto = migliore qualità OCR ma più lento. 300 è un buon compromesso.
        zoom = 300 / 72  # Calcola il fattore di zoom per ottenere circa 300 DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False) # alpha=False per rimuovere trasparenza

        # Converti i bytes dell'immagine Pixmap in un oggetto Image di Pillow
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))

        # Esegui OCR usando Tesseract
        # Aggiungere '-l ita' per l'italiano, o altre lingue es: 'eng+ita'
        # '--psm 6' assume un blocco di testo uniforme, può essere adattato.
        custom_config = f'-l {lang} --psm 6'
        page_text = pytesseract.image_to_string(img, config=custom_config)

        logging.info(f"OCR pagina {page_num + 1} completato. Caratteri estratti: {len(page_text)}")
        return page_text.strip() # Rimuovi spazi bianchi iniziali/finali

    except pytesseract.TesseractNotFoundError:
         logging.error("Errore Tesseract: Eseguibile 'tesseract' non trovato o non nel PATH.")
         logging.error("Assicurati che Tesseract sia installato e che `pytesseract.pytesseract.tesseract_cmd` sia configurato correttamente se necessario.")
         # Ritorna un messaggio di errore specifico per questa pagina
         return f"[Errore OCR: Tesseract non trovato sulla pagina {page_num+1}]"
    except Exception as e:
        logging.error(f"Errore durante l'OCR della pagina {page_num + 1}: {e}", exc_info=True)
        return f"[Errore OCR generico sulla pagina {page_num+1}]" # Ritorna un messaggio di errore

def process_pdf(pdf_path, force_ocr=False, ocr_lang='eng'):
    """
    Funzione principale per processare un file PDF.
    Tenta prima l'estrazione diretta del testo. Se fallisce, produce poco testo
    (soglia < 200 caratteri), o se force_ocr è True, esegue l'OCR su tutte le pagine.

    Args:
        pdf_path (str): Percorso del file PDF.
        force_ocr (bool): Se True, esegue l'OCR anche se l'estrazione diretta ha successo.
        ocr_lang (str): Codice lingua per Tesseract (es. 'eng', 'ita', 'eng+ita').

    Returns:
        str: Il testo estratto (direttamente o via OCR), oppure None se il file non esiste
             o si verifica un errore grave e irrecuperabile. Ritorna stringa vuota se
             né l'estrazione diretta né l'OCR producono testo.
    """
    logging.info(f"--- Inizio processo PDF per: {pdf_path} (force_ocr={force_ocr}, lang='{ocr_lang}') ---")
    if not os.path.exists(pdf_path):
        logging.error(f"Errore: File PDF non trovato: {pdf_path}")
        return None # File non esiste

    extracted_text = ""
    run_ocr = False

    # 1. Tentativo di estrazione diretta
    if not force_ocr:
        logging.info("Fase 1: Tentativo di estrazione diretta del testo.")
        direct_text_result = extract_text_directly(pdf_path)

        if direct_text_result is None:
            # Errore grave durante l'estrazione diretta (es. file corrotto?)
            logging.error("Estrazione diretta fallita a causa di un errore. Tentativo con OCR.")
            run_ocr = True
            extracted_text = "" # Assicurati che sia vuoto per la fase OCR
        elif len(direct_text_result) < 200:
            # Estrazione diretta riuscita ma testo scarso, proviamo OCR
            logging.warning(f"Estrazione diretta ha prodotto solo {len(direct_text_result)} caratteri (< 200). Si procederà con OCR.")
            run_ocr = True
            extracted_text = direct_text_result # Conserviamo il poco testo, l'OCR lo sostituirà se migliore
        else:
            # Estrazione diretta sufficiente
            logging.info("Estrazione diretta del testo riuscita e considerata sufficiente.")
            extracted_text = direct_text_result
            run_ocr = False # Non serve OCR
    else:
        # OCR forzato dall'utente
        logging.info("Fase 1: Saltata estrazione diretta (force_ocr=True). Si procederà direttamente con OCR.")
        run_ocr = True
        extracted_text = "" # Inizializza vuoto per OCR

    # 2. Esecuzione OCR (se necessario o forzato)
    if run_ocr:
        logging.info("Fase 2: Esecuzione OCR.")
        ocr_full_text = ""
        try:
            with fitz.open(pdf_path) as doc:
                num_pages = len(doc)
                logging.info(f"Il PDF ha {num_pages} pagine. Inizio OCR pagina per pagina.")
                for page_num in range(num_pages):
                    page = doc.load_page(page_num)
                    # Esegui OCR sulla pagina corrente
                    page_ocr_text = ocr_pdf_page(page, page_num, lang=ocr_lang)
                    # Aggiungi il testo della pagina al risultato completo, con separatore
                    ocr_full_text += page_ocr_text + "\n\n" # Doppio a capo per separare pagine

            logging.info("OCR completato per tutte le pagine.")
            # Pulisci il testo OCR complessivo rimuovendo linee vuote risultanti
            cleaned_ocr_text = "\n".join([line for line in ocr_full_text.splitlines() if line.strip() or "[Errore OCR:" in line]) # Mantieni righe con errori OCR

            # Se l'OCR ha prodotto più testo dell'estrazione diretta (se c'era), usa l'OCR
            if len(cleaned_ocr_text.strip()) > len(extracted_text.strip()):
                 logging.info("Il risultato dell'OCR è più lungo dell'estrazione diretta, verrà usato l'output OCR.")
                 extracted_text = cleaned_ocr_text
            elif not extracted_text and cleaned_ocr_text:
                 logging.info("L'estrazione diretta non aveva prodotto testo, verrà usato l'output OCR.")
                 extracted_text = cleaned_ocr_text
            elif extracted_text and not cleaned_ocr_text.strip():
                 logging.warning("L'OCR non ha prodotto testo significativo, mantenendo il risultato dell'estrazione diretta.")
            # Altrimenti (se OCR <= diretto), manteniamo il testo diretto (già in extracted_text)

        except fitz.FileNotFoundError:
            logging.error(f"Errore: File PDF non trovato durante l'apertura per OCR: {pdf_path}")
            return None # Errore grave
        except pytesseract.TesseractNotFoundError:
             logging.error("Errore critico: Tesseract non trovato. Impossibile eseguire OCR.")
             # Ritorna il testo estratto direttamente se disponibile, altrimenti None o vuoto
             if extracted_text:
                 logging.warning("Ritorno il testo estratto direttamente (potrebbe essere incompleto).")
                 return extracted_text
             else:
                 return "" # Nessun testo ottenuto
        except Exception as e:
            logging.error(f"Errore generale imprevisto durante il processo OCR: {e}", exc_info=True)
            # In caso di errore OCR, proviamo a ritornare almeno il testo diretto se lo avevamo
            if extracted_text:
                 logging.warning("Processo OCR fallito a causa di un errore. Ritorno il testo estratto direttamente (potrebbe essere incompleto).")
                 return extracted_text
            else:
                 # Se anche l'estrazione diretta era fallita o non eseguita, non abbiamo nulla
                 logging.error("Fallimento sia dell'estrazione diretta che dell'OCR.")
                 return "" # Ritorna vuoto per indicare fallimento nel recupero testo

    # 3. Fine processo
    logging.info(f"--- Fine processo PDF per: {pdf_path}. Lunghezza testo finale: {len(extracted_text)} ---")
    return extracted_text # Ritorna il testo finale (diretto o OCR)

# Blocco per permettere l'esecuzione dello script da linea di comando per test
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Errore: Manca il percorso del file PDF.")
        print("Uso: python python-backend/pdf_to_text.py <percorso_file_pdf> [--ocr] [--lang <codice_lingua>]")
        print("Esempio: python python-backend/pdf_to_text.py slides.pdf")
        print("Esempio OCR forzato (inglese): python python-backend/pdf_to_text.py image_based.pdf --ocr")
        print("Esempio OCR forzato (italiano): python python-backend/pdf_to_text.py documento_ita.pdf --ocr --lang ita")
        sys.exit(1)

    input_pdf_path = sys.argv[1]
    force_ocr_flag = '--ocr' in sys.argv
    ocr_language = 'eng' # Default a inglese

    # Cerca l'argomento --lang
    try:
        lang_index = sys.argv.index('--lang')
        if lang_index + 1 < len(sys.argv):
            ocr_language = sys.argv[lang_index + 1]
        else:
            print("Attenzione: Trovato --lang ma manca il codice lingua. Uso default 'eng'.")
    except ValueError:
        pass # --lang non presente, usa default

    print(f"\n[TEST MODE] Avvio process_pdf per: {input_pdf_path}")
    print(f"[TEST MODE] Force OCR: {force_ocr_flag}")
    print(f"[TEST MODE] OCR Language: {ocr_language}")

    # Attiva l'ambiente virtuale se non è già attivo (promemoria)
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'activate')
    if 'VIRTUAL_ENV' not in os.environ and os.path.exists(venv_path):
         print(f"[TEST MODE] Assicurati che l'ambiente virtuale sia attivo: source {venv_path}")

    # Esegui la funzione principale di processamento
    final_text = process_pdf(input_pdf_path, force_ocr=force_ocr_flag, ocr_lang=ocr_language)

    if final_text is None:
        print("\n--- Processo PDF fallito (File non trovato o errore grave). Controlla i log. ---")
    elif not final_text:
        print("\n--- Nessun testo è stato estratto dal PDF (né diretto né OCR). ---")
    else:
        print(f"\n--- Testo Estratto (Lunghezza: {len(final_text)} caratteri) ---")
        # Stampa solo le prime N righe per evitare output troppo lunghi
        lines = final_text.splitlines()
        max_lines_to_print = 50
        for i, line in enumerate(lines):
            if i < max_lines_to_print:
                print(line)
            elif i == max_lines_to_print:
                print(f"\n[... output troncato dopo {max_lines_to_print} righe ...]")
                break
        print("--- Fine Testo Estratto ---\n")

        # Opzionale: Salvare l'output in un file per ispezione
        # output_filename = os.path.splitext(os.path.basename(input_pdf_path))[0] + "_extracted.txt"
        # try:
        #     with open(output_filename, "w", encoding="utf-8") as f:
        #         f.write(final_text)
        #     print(f"Testo estratto salvato anche in: {output_filename}")
        # except Exception as e:
        #     print(f"Errore nel salvataggio del file di output: {e}") 