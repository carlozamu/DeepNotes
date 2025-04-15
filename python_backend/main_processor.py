import os
import time # Aggiunto per attesa finale opzionale
from .video_to_text import extract_and_transcribe
from .pdf_to_text import extract_text_from_pdf
from .ai_fusion import merge_and_summarize
# Import utils se necessario in futuro
# from .utils import common

def process_files(video_path, pdf_path, whisper_model_size="base", gemini_api_key=None, mistral_api_key=None, update_callback=None):
    """
    Orchestra l'intero processo: trascrizione video, estrazione PDF, fusione AI.
    Invoca i moduli specifici e usa update_callback per comunicare con la GUI.
    
    Args:
        video_path: Percorso al file video (può essere None).
        pdf_path: Percorso al file PDF (può essere None).
        whisper_model_size: Dimensione del modello Whisper da utilizzare.
        gemini_api_key: Chiave API per Google Gemini (opzionale).
        mistral_api_key: Chiave API per Mistral (opzionale).
        update_callback: Funzione callback per aggiornare lo stato nell'UI.
    """
    video_transcription = None
    pdf_content = None
    final_summary = None

    def log_message(message, error=False):
        if update_callback:
            update_callback("error" if error else "status", message)
        print(message)

    try:
        # --- Fase 1: Elaborazione Video (se fornito) ---
        if video_path and os.path.exists(video_path):
            log_message(f"Utilizzo modello Whisper: {whisper_model_size}")
            video_transcription = extract_and_transcribe(video_path, update_callback, whisper_model_size)
            if video_transcription is None:
                raise Exception("Elaborazione video fallita.")
        elif video_path:
            log_message(f"File video non trovato o non valido: {video_path}", error=True)
        else:
            log_message("Nessun file video fornito, saltando trascrizione.")

        # --- Fase 2: Elaborazione PDF (se fornito) ---
        if pdf_path and os.path.exists(pdf_path):
            pdf_content = extract_text_from_pdf(pdf_path, update_callback)
            if pdf_content is None:
                raise Exception("Elaborazione PDF fallita.")
        elif pdf_path:
            log_message(f"File PDF non trovato o non valido: {pdf_path}", error=True)
        else:
            log_message("Nessun file PDF fornito, saltando estrazione testo.")

        # --- Fase 3: Fusione AI (se almeno un input è presente) ---
        if video_transcription or pdf_content:
            if not gemini_api_key and not mistral_api_key:
                raise Exception("È necessario fornire almeno una chiave API (Gemini o Mistral) per la fusione AI.")
            
            final_summary = merge_and_summarize(video_transcription, pdf_content, gemini_api_key, mistral_api_key, update_callback)
            if final_summary is None:
                raise Exception("Fusione AI fallita.")
            return final_summary
        else:
            log_message("Nessun contenuto da elaborare per la fusione AI.", error=True)
            return "Nessun file valido fornito per l'elaborazione."

    except Exception as e:
        error_message = f"Errore generale nel processo: {e}"
        log_message(error_message, error=True)
        return f"ERRORE: {error_message}" 