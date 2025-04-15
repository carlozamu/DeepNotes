import os
import time
import tempfile
import logging
import ffmpeg
from faster_whisper import WhisperModel

# Configurazione di base del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_and_transcribe(video_path, update_callback=None, model_size="base"):
    """
    Estrae l'audio da un video usando ffmpeg e lo trascrive con faster-whisper.
    
    Args:
        video_path: Percorso al file video.
        update_callback: Funzione callback per aggiornare lo stato nell'UI (opzionale).
        model_size: Dimensione del modello Whisper da utilizzare.
        
    Returns:
        Testo trascritto o None in caso di errore.
    """
    try:
        # Helper function for logging with or without callback
        def log_update(status_type, message):
            if update_callback:
                update_callback(status_type, message)
            if status_type == "error":
                logger.error(message)
            else:
                logger.info(message)
                
        # Verifica esistenza del file video
        if not os.path.exists(video_path):
            log_update("error", f"File video non trovato: {video_path}")
            return None
            
        log_update("status", f"Inizio elaborazione video: {os.path.basename(video_path)}...")
        
        # Creazione directory temporanea per l'audio estratto
        with tempfile.TemporaryDirectory() as temp_dir:
            # Definizione percorso del file audio temporaneo
            audio_output_path = os.path.join(temp_dir, "audio.wav")
            
            # Estrazione audio con ffmpeg
            log_update("status", "Inizio estrazione audio...")
            try:
                # Utilizzo di ffmpeg per estrarre l'audio in formato WAV
                ffmpeg.input(video_path).output(
                    audio_output_path,
                    acodec='pcm_s16le',  # Codec audio WAV standard
                    ar='16000',          # Frequenza di campionamento per Whisper
                    ac=1                 # Mono canale
                ).run(
                    cmd='ffmpeg',
                    capture_stdout=True,
                    capture_stderr=True
                )
            except ffmpeg.Error as e:
                error_message = f"Errore durante l'estrazione audio con FFmpeg: {e.stderr.decode() if e.stderr else str(e)}"
                logger.error(error_message)
                log_update("error", error_message)
                return None
                
            log_update("status", f"Estrazione audio completata. Inizio trascrizione con modello '{model_size}'...")
            
            # Inizializzazione del modello Whisper
            try:
                log_update("status", f"Inizializzazione modello Whisper '{model_size}'...")
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                
                # Trascrizione dell'audio
                log_update("status", "Modello pronto, inizio trascrizione...")
                segments, _ = model.transcribe(audio_output_path, word_timestamps=False)
                
                # Costruzione del testo completo dai segmenti
                transcription = ""
                for segment in segments:
                    transcription += segment.text + " "
                
                log_update("status", "Trascrizione video completata.")
                return transcription.strip()
                
            except Exception as whisper_error:
                error_message = f"Errore durante la trascrizione con Whisper: {str(whisper_error)}"
                logger.error(error_message)
                log_update("error", error_message)
                return None
                
    except Exception as e:
        error_message = f"Errore durante l'elaborazione video: {str(e)}"
        logger.error(error_message)
        if update_callback:
            update_callback("error", error_message)
        return None
