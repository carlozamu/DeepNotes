import ffmpeg
import os
import tempfile
from faster_whisper import WhisperModel
import logging
import sys
import torch # Import torch per verificare la disponibilità di MPS

# Configurazione del logging di base
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configurazioni Modello Whisper ---
# Modelli disponibili: "tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"
# Scegliere in base a velocità vs accuratezza e risorse hardware.
# "base" o "small" sono un buon compromesso iniziale. "tiny" è il più veloce.
MODEL_SIZE = "base"

# Tipo di calcolo: "int8" è generalmente più veloce e usa meno memoria sulla CPU.
# Altri tipi: "float16", "float32".
COMPUTE_TYPE = "int8"

# Dispositivo: "cuda" per GPU Nvidia, "mps" per Apple Silicon (se supportato), "cpu" altrimenti.
# Verifica automatica per MPS su macOS
if torch.backends.mps.is_available() and torch.backends.mps.is_built():
    DEVICE = "mps"
    logging.info("Rilevato supporto MPS su Apple Silicon. Userò 'mps' come device.")
    # Nota: faster-whisper potrebbe richiedere tipi specifici per MPS, es. float16
    # COMPUTE_TYPE = "float16" # Potrebbe essere necessario per MPS, testare
else:
    DEVICE = "cpu"
    logging.info("Nessun supporto MPS o CUDA rilevato. Userò 'cpu' come device.")
# Se hai una GPU Nvidia e CUDA configurato, puoi forzare: DEVICE = "cuda"

# -------------------------------------

def extract_audio(video_path, audio_path):
    """Estrae la traccia audio da un file video usando ffmpeg-python."""
    logging.info(f"Inizio estrazione audio da: {video_path}")
    try:
        (
            ffmpeg
            .input(video_path)
            .output(
                audio_path,
                acodec='mp3',      # Codec audio (mp3 è comune)
                audio_bitrate='192k',# Bitrate audio
                ac=1               # Numero di canali audio (1 = mono)
            )
            .overwrite_output()    # Sovrascrive il file di output se esiste
            .run(capture_stdout=True, capture_stderr=True, quiet=False) # quiet=False per vedere output ffmpeg
        )
        logging.info(f"Audio estratto con successo in: {audio_path}")
        return True
    except ffmpeg.Error as e:
        # Stampa l'errore stderr di ffmpeg per il debug
        logging.error("Errore FFmpeg durante l'estrazione audio:")
        stderr_output = e.stderr.decode('utf8', errors='ignore') if e.stderr else "N/A"
        logging.error(f"FFmpeg stderr:\n{stderr_output}")
        return False
    except Exception as e:
        logging.error(f"Errore imprevisto durante l'estrazione audio: {e}", exc_info=True)
        return False

def transcribe_audio(audio_path):
    """Trascrive un file audio usando faster-whisper, senza timestamp."""
    logging.info(f"Caricamento modello Whisper '{MODEL_SIZE}' su device '{DEVICE}' con compute_type '{COMPUTE_TYPE}'...")
    try:
        # Carica il modello Whisper specificato
        model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

        logging.info(f"Inizio trascrizione audio: {audio_path}")
        # Esegui la trascrizione senza richiedere i timestamp
        # beam_size=5 è un valore comune per un buon compromesso velocità/accuratezza
        segments, info = model.transcribe(audio_path, beam_size=5, without_timestamps=True)

        logging.info(f"Lingua rilevata: '{info.language}' con probabilità {info.language_probability:.2f}")
        logging.info(f"Durata audio processata: {info.duration:.2f} secondi")

        # Concatena tutti i segmenti di testo trascritto
        full_transcript = "".join(segment.text for segment in segments).strip()

        logging.info(f"Trascrizione completata. Lunghezza testo: {len(full_transcript)} caratteri.")

        # Scarica il modello dalla memoria (utile se si processano molti file in sequenza)
        # del model
        # if DEVICE == 'cuda': torch.cuda.empty_cache()
        # if DEVICE == 'mps': torch.mps.empty_cache() # Se esiste una funzione simile per MPS

        return full_transcript

    except Exception as e:
        logging.error(f"Errore durante la trascrizione audio con faster-whisper: {e}", exc_info=True)
        return None

def process_video(video_path):
    """Funzione principale per processare un file video: estrae audio e lo trascrive."""
    logging.info(f"--- Inizio processo video per: {video_path} ---")
    if not os.path.exists(video_path):
        logging.error(f"Errore: File video non trovato: {video_path}")
        return None # Ritorna None se il file non esiste

    # Creare un file temporaneo per l'audio estratto
    # Usiamo delete=False perché ffmpeg ha bisogno del percorso, lo cancelliamo manualmente dopo.
    temp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_audio_path = temp_audio_file.name
    temp_audio_file.close() # Chiudiamo subito il file handle

    logging.info(f"Creato file audio temporaneo: {temp_audio_path}")

    transcript = None
    try:
        # 1. Estrarre l'audio dal video
        if extract_audio(video_path, temp_audio_path):
            # 2. Trascrivere l'audio estratto
            transcript = transcribe_audio(temp_audio_path)
            if transcript is None:
                logging.error("Trascrizione audio fallita.")
            else:
                logging.info("Processo video completato con successo.")
        else:
            logging.error("Estrazione audio fallita. Impossibile procedere con la trascrizione.")

    except Exception as e:
        logging.error(f"Errore imprevisto durante il processo video: {e}", exc_info=True)
        transcript = None # Assicura che venga ritornato None in caso di errore non gestito

    finally:
        # 3. Pulizia: rimuovere sempre il file audio temporaneo
        if os.path.exists(temp_audio_path):
            logging.info(f"Rimozione file audio temporaneo: {temp_audio_path}")
            try:
                os.remove(temp_audio_path)
            except OSError as e:
                logging.error(f"Errore durante la rimozione del file temporaneo {temp_audio_path}: {e}")

    logging.info(f"--- Fine processo video per: {video_path} ---")
    return transcript # Ritorna il testo trascritto o None se qualcosa è andato storto

# Blocco per permettere l'esecuzione dello script da linea di comando per test
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Errore: Manca il percorso del file video.")
        print("Uso: python python-backend/video_to_text.py <percorso_file_video>")
        sys.exit(1)

    input_video_path = sys.argv[1]
    print(f"\n[TEST MODE] Avvio process_video per: {input_video_path}")

    # Attiva l'ambiente virtuale se non è già attivo (per test diretti)
    # Questo è un hack e potrebbe non funzionare in tutti gli scenari
    # Si consiglia di eseguire lo script con l'ambiente già attivo
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'activate')
    if 'VIRTUAL_ENV' not in os.environ and os.path.exists(venv_path):
         print(f"[TEST MODE] Tentativo di attivare venv: {venv_path}")
         # Questo non attiva realmente l'ambiente nel processo corrente,
         # ma serve come promemoria all'utente di attivarlo manualmente.
         print(f"Assicurati che l'ambiente virtuale sia attivo: source {venv_path}")


    # Esegui la funzione principale di processamento
    final_transcript = process_video(input_video_path)

    if final_transcript:
        print("\n--- Trascrizione Ottenuta ---")
        print(final_transcript)
        print("--- Fine Trascrizione ---\n")
        # Opzionale: Salvare la trascrizione in un file di test
        # output_filename = os.path.splitext(os.path.basename(input_video_path))[0] + "_transcript.txt"
        # with open(output_filename, "w", encoding="utf-8") as f:
        #     f.write(final_transcript)
        # print(f"Trascrizione salvata in: {output_filename}")
    else:
        print("\n--- Processo di trascrizione fallito. Controlla i log sopra per errori. ---\n") 