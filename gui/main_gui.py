import dearpygui.dearpygui as dpg
import threading
import os
import sys
import logging
import pyperclip

# Configurazione di base del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Aggiungi la directory root del progetto (deepnotes) al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from python_backend.main_processor import process_files

# Tag costanti per elementi UI
TAG_VIDEO_PATH_INPUT = "video_path_input"
TAG_PDF_PATH_INPUT = "pdf_path_input"
TAG_STATUS_TEXT = "status_text"
TAG_OUTPUT_TEXT = "output_text"
TAG_PROCESS_BUTTON = "process_button"
TAG_MAIN_WINDOW = "main_window"
# Nuovi tag per i file dialog
TAG_VIDEO_FILE_DIALOG = "video_file_dialog"
TAG_PDF_FILE_DIALOG = "pdf_file_dialog"
# Nuovi tag per il salvataggio
TAG_SAVE_BUTTON = "save_button"
TAG_SAVE_FILE_DIALOG = "save_file_dialog"
# Nuovi tag per la configurazione
TAG_WHISPER_MODEL_COMBO = "whisper_model_combo"
TAG_GEMINI_API_KEY_INPUT = "gemini_api_key_input"
TAG_USE_GUI_KEY_CHECKBOX = "use_gui_key_checkbox"
# Nuovi tag per Mistral API
TAG_MISTRAL_API_KEY_INPUT = "mistral_api_key_input"
TAG_USE_GUI_MISTRAL_KEY_CHECKBOX = "use_gui_mistral_key_checkbox"
# Nuovi tag per l'indicatore di caricamento e il pulsante copia
TAG_LOADING_INDICATOR = "loading_indicator"
TAG_COPY_BUTTON = "copy_button"

def _log(message):
    """Aggiunge un messaggio all'area di stato/log."""
    current_value = dpg.get_value(TAG_STATUS_TEXT)
    new_value = f"- {message}\n{current_value}"
    dpg.set_value(TAG_STATUS_TEXT, new_value)
    print(f"LOG: {message}")

def video_file_selected_callback(sender, app_data):
    """Callback eseguita dopo la selezione (o annullamento) del file video."""
    if app_data['selections']:
        file_path = list(app_data['selections'].values())[0]
        _log(f"Video selezionato: {file_path}")
        dpg.set_value(TAG_VIDEO_PATH_INPUT, file_path)
    else:
        _log("Selezione video annullata.")

def pdf_file_selected_callback(sender, app_data):
    """Callback eseguita dopo la selezione (o annullamento) del file PDF."""
    if app_data['selections']:
        file_path = list(app_data['selections'].values())[0]
        _log(f"PDF selezionato: {file_path}")
        dpg.set_value(TAG_PDF_PATH_INPUT, file_path)
    else:
        _log("Selezione PDF annullata.")

def file_save_callback(sender, app_data):
    """Callback eseguita dopo la selezione del percorso per salvare il file."""
    if app_data['file_path_name']: # Verifica se è stato fornito un percorso
        file_path = app_data['file_path_name']
        # Assicurati che l'estensione sia .txt (DPG potrebbe non aggiungerla automaticamente)
        if not file_path.lower().endswith(".txt"):
            file_path += ".txt"

        _log(f"Tentativo di salvataggio note in: {file_path}")
        try:
            # Recupera il contenuto dall'area di output
            notes_content = dpg.get_value(TAG_OUTPUT_TEXT)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(notes_content)
            _log(f"Note salvate con successo in {file_path}")
        except Exception as e:
            error_message = f"Errore durante il salvataggio del file: {e}"
            logger.error(error_message)
            _log(error_message)
    else:
        _log("Salvataggio file annullato.")

def select_video_callback():
    """Mostra il file dialog per selezionare un file video."""
    dpg.show_item(TAG_VIDEO_FILE_DIALOG)

def select_pdf_callback():
    """Mostra il file dialog per selezionare un file PDF."""
    dpg.show_item(TAG_PDF_FILE_DIALOG)

def copy_to_clipboard_callback():
    """Copia il contenuto dell'area output negli appunti del sistema."""
    notes_content = dpg.get_value(TAG_OUTPUT_TEXT)
    try:
        pyperclip.copy(notes_content)
        _log("Note copiate negli appunti!")
    except Exception as e:
        error_message = f"Errore nella copia negli appunti: {e}"
        logger.error(error_message)
        _log(error_message)

def gui_update_callback(status_type, message_or_data):
    """
    Callback per aggiornare la GUI dal thread backend.
    status_type: 'status', 'warning', 'error', 'debug', 'finish'
    message_or_data: stringa del messaggio o dizionario con risultati/errori
    """
    if status_type == "status":
        _log(f"INFO: {message_or_data}")
        # Aggiorna l'indicatore di caricamento con un messaggio
        dpg.configure_item(TAG_LOADING_INDICATOR, label=f"Elaborazione in corso: {message_or_data}")
    elif status_type == "warning":
        _log(f"ATTENZIONE: {message_or_data}")
    elif status_type == "error":
        _log(f"ERRORE: {message_or_data}")
        dpg.set_value(TAG_OUTPUT_TEXT, f"ERRORE DURANTE L'ELABORAZIONE:\n{message_or_data}")
        dpg.configure_item(TAG_SAVE_BUTTON, enabled=False)  # Disabilita salvataggio in caso di errore
        dpg.configure_item(TAG_COPY_BUTTON, enabled=False)  # Disabilita copia in caso di errore
        dpg.hide_item(TAG_LOADING_INDICATOR)  # Nascondi indicatore di caricamento
    elif status_type == "debug":
        print(f"DEBUG: {message_or_data}")
    elif status_type == "finish":
        _log("Processo terminato (dal backend).")
        if isinstance(message_or_data, dict):
            if "summary" in message_or_data and message_or_data["summary"]:
                dpg.set_value(TAG_OUTPUT_TEXT, message_or_data["summary"])
                dpg.configure_item(TAG_SAVE_BUTTON, enabled=True)  # ABILITA SALVATAGGIO
                dpg.configure_item(TAG_COPY_BUTTON, enabled=True)  # ABILITA COPIA
            elif "error" in message_or_data:
                dpg.set_value(TAG_OUTPUT_TEXT, f"PROCESSO FALLITO:\n{message_or_data['error']}")
                dpg.configure_item(TAG_SAVE_BUTTON, enabled=False)  # DISABILITA SALVATAGGIO
                dpg.configure_item(TAG_COPY_BUTTON, enabled=False)  # DISABILITA COPIA
        else:
            # If message_or_data is a string, assume it's the summary
            dpg.set_value(TAG_OUTPUT_TEXT, message_or_data)
            dpg.configure_item(TAG_SAVE_BUTTON, enabled=True)
            dpg.configure_item(TAG_COPY_BUTTON, enabled=True)
        dpg.configure_item(TAG_PROCESS_BUTTON, enabled=True)
        dpg.hide_item(TAG_LOADING_INDICATOR)  # Nascondi indicatore di caricamento

def process_files_callback(sender, app_data, user_data):
    """Callback per il pulsante 'Processa File'."""
    # Get file paths
    video_path = dpg.get_value(TAG_VIDEO_PATH_INPUT)
    pdf_path = dpg.get_value(TAG_PDF_PATH_INPUT)
    
    # Validate file paths
    if not video_path and not pdf_path:
        _log("Errore: Seleziona almeno un file (video o PDF).")
        return
    
    # Get Whisper model
    whisper_model = dpg.get_value(TAG_WHISPER_MODEL_COMBO)
    
    # Get API keys
    use_gui_key = dpg.get_value(TAG_USE_GUI_KEY_CHECKBOX)
    use_gui_mistral_key = dpg.get_value(TAG_USE_GUI_MISTRAL_KEY_CHECKBOX)
    
    gemini_api_key = None
    mistral_api_key = None
    
    if use_gui_key:
        gemini_api_key = dpg.get_value(TAG_GEMINI_API_KEY_INPUT)
        if not gemini_api_key:
            _log("Errore: Inserisci una Gemini API key.")
            return
    
    if use_gui_mistral_key:
        mistral_api_key = dpg.get_value(TAG_MISTRAL_API_KEY_INPUT)
        if not mistral_api_key:
            _log("Errore: Inserisci una Mistral API key.")
            return
    
    # Disable buttons during processing
    dpg.configure_item(TAG_PROCESS_BUTTON, enabled=False)
    dpg.configure_item(TAG_SAVE_BUTTON, enabled=False)
    dpg.configure_item(TAG_COPY_BUTTON, enabled=False)
    
    # Show loading indicator
    dpg.show_item(TAG_LOADING_INDICATOR)
    dpg.configure_item(TAG_LOADING_INDICATOR, label="Inizializzazione elaborazione...")
    
    # Update status
    _log("Avvio elaborazione...")
    
    # Avvia thread per elaborazione
    thread = threading.Thread(
        target=lambda: process_files_thread(video_path, pdf_path, whisper_model, gemini_api_key, mistral_api_key)
    )
    thread.daemon = True
    thread.start()

def process_files_thread(video_path, pdf_path, whisper_model, gemini_api_key, mistral_api_key):
    """Esegue l'elaborazione files in un thread separato per non bloccare la GUI."""
    try:
        # Process files
        result = process_files(video_path, pdf_path, whisper_model, gemini_api_key, mistral_api_key, gui_update_callback)
        
        # Update output attraverso il callback
        if result:
            gui_update_callback("finish", result)
        
    except Exception as e:
        error_message = f"Errore: {str(e)}"
        logger.error(error_message)
        gui_update_callback("error", error_message)

# === THEME & STYLE ===
def setup_modern_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Colori principali
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (245, 247, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (230, 234, 240, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (66, 133, 244, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 193, 7, 255))  # accento giallo Google
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (52, 103, 191, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (230, 240, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (210, 230, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (245, 247, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (230, 234, 240, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (33, 33, 33, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, (210, 230, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (245, 247, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (200, 220, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (66, 133, 244, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (41, 80, 150, 255))
            # Effetto ombra e arrotondamenti
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 12)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 16)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 18)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 14, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 16, 16)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 24, 24)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 22)
    dpg.bind_theme(global_theme)

# === FONT ===
def setup_modern_font():
    font_dir = os.path.dirname(__file__)
    inter_path = os.path.join(font_dir, "Inter-Regular.ttf")
    google_sans_path = os.path.join(font_dir, "GoogleSans-Regular.ttf")
    roboto_path = os.path.join(font_dir, "Roboto-Regular.ttf")
    montserrat_path = os.path.join(font_dir, "Montserrat-Regular.ttf")
    nunito_path = os.path.join(font_dir, "Nunito-Regular.ttf")
    lato_path = os.path.join(font_dir, "Lato-Regular.ttf")
    font_to_use = None
    font_name = None
    if os.path.exists(inter_path):
        font_to_use = inter_path
        font_name = "Inter"
    elif os.path.exists(google_sans_path):
        font_to_use = google_sans_path
        font_name = "Google Sans"
    elif os.path.exists(roboto_path):
        font_to_use = roboto_path
        font_name = "Roboto"
    elif os.path.exists(montserrat_path):
        font_to_use = montserrat_path
        font_name = "Montserrat"
    elif os.path.exists(nunito_path):
        font_to_use = nunito_path
        font_name = "Nunito"
    elif os.path.exists(lato_path):
        font_to_use = lato_path
        font_name = "Lato"
    if font_to_use:
        print(f"[DeepNotes] Carico il font personalizzato: {font_name} ({font_to_use})")
        with dpg.font_registry():
            with dpg.font(font_to_use, 20) as default_font:
                dpg.bind_font(default_font)
    else:
        print("[DeepNotes] Nessun font custom trovato! Usa Inter, Google Sans, Roboto, Montserrat, Nunito o Lato. Scarica il TTF e mettilo nella cartella gui/ per un look moderno.")

# === DRAG & DROP ===
def drag_drop_file_callback(sender, app_data, user_data):
    file_path = app_data['file_path_name']
    if user_data == 'video':
        dpg.set_value(TAG_VIDEO_PATH_INPUT, file_path)
        _log(f"Video trascinato: {file_path}")
    elif user_data == 'pdf':
        dpg.set_value(TAG_PDF_PATH_INPUT, file_path)
        _log(f"PDF trascinato: {file_path}")

# === FILE PICKER NATIVO ===
def open_native_file_picker(filetype, user_data):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    if filetype == 'video':
        filetypes = [('Video files', '*.mp4 *.mkv *.avi'), ('All files', '*.*')]
    else:
        filetypes = [('PDF files', '*.pdf'), ('All files', '*.*')]
    file_path = filedialog.askopenfilename(filetypes=filetypes)
    root.destroy()
    if file_path:
        if user_data == 'video':
            dpg.set_value(TAG_VIDEO_PATH_INPUT, file_path)
            _log(f"Video selezionato: {file_path}")
        elif user_data == 'pdf':
            dpg.set_value(TAG_PDF_PATH_INPUT, file_path)
            _log(f"PDF selezionato: {file_path}")

def create_main_window():
    setup_modern_theme()
    setup_modern_font()
    with dpg.window(label="DeepNotes", tag=TAG_MAIN_WINDOW, width=820, height=980):
        # --- HEADER ---
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            dpg.add_text("🧠", color=(66, 133, 244, 255), bullet=False)
            dpg.add_text("DeepNotes AI", color=(66, 133, 244, 255), wrap=0)
            dpg.add_spacer(width=10)
            dpg.add_text("AI", color=(255, 193, 7, 255), wrap=0)
        dpg.add_spacer(height=2)
        dpg.add_text("Appunti smart, chiari e veloci", color=(52, 103, 191, 255), wrap=0)
        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        # --- ZONA FILE VIDEO ---
        dpg.add_text("1. Carica un video lezione", color=(33, 33, 33, 255), bullet=True)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Scegli Video", width=150, callback=lambda: open_native_file_picker('video', 'video'))
            dpg.add_input_text(tag=TAG_VIDEO_PATH_INPUT, readonly=True, width=420, default_value="Trascina qui il percorso o scegli un file video")
        dpg.add_spacer(height=8)
        # --- ZONA FILE PDF ---
        dpg.add_text("2. Carica un PDF (slide o testo)", color=(33, 33, 33, 255), bullet=True)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Scegli PDF", width=150, callback=lambda: open_native_file_picker('pdf', 'pdf'))
            dpg.add_input_text(tag=TAG_PDF_PATH_INPUT, readonly=True, width=420, default_value="Trascina qui il percorso o scegli un file PDF")
        dpg.add_spacer(height=14)
        # --- MODELLO WHISPER ---
        dpg.add_text("3. Modello Trascrizione", color=(33, 33, 33, 255), bullet=True)
        whisper_models = ["tiny", "base", "small", "medium", "large-v3"]
        dpg.add_combo(items=whisper_models, default_value="base", tag=TAG_WHISPER_MODEL_COMBO, width=180)
        dpg.add_spacer(height=16)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        # --- PULSANTE PROCESSA ---
        dpg.add_button(label="✨ Genera Appunti AI ✨", tag=TAG_PROCESS_BUTTON, callback=process_files_callback, width=-1, height=52)
        dpg.add_spacer(height=10)
        dpg.add_text("", tag=TAG_LOADING_INDICATOR, show=False, color=(66, 133, 244, 255))
        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        # --- LOG DI STATO ---
        dpg.add_text("Log di Stato", color=(33, 33, 33, 255), wrap=0)
        dpg.add_input_text(tag=TAG_STATUS_TEXT, multiline=True, readonly=True, default_value="Pronto.", width=-1, height=110)
        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        # --- NOTE GENERATE ---
        dpg.add_text("Note Generate", color=(33, 33, 33, 255), wrap=0)
        dpg.add_input_text(tag=TAG_OUTPUT_TEXT, multiline=True, readonly=True, default_value="L'output apparirà qui...", width=-1, height=220)
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            dpg.add_button(label="💾 Salva Note", tag=TAG_SAVE_BUTTON, callback=lambda: dpg.show_item(TAG_SAVE_FILE_DIALOG), enabled=False, width=200)
            dpg.add_button(label="📋 Copia negli Appunti", tag=TAG_COPY_BUTTON, callback=copy_to_clipboard_callback, enabled=False, width=200)
        dpg.add_spacer(height=16)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        # --- CONFIGURAZIONE API ---
        dpg.add_text("Configurazione API (Opzionale)", color=(33, 33, 33, 255), wrap=0)
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Usa API Key Gemini dalla GUI", tag=TAG_USE_GUI_KEY_CHECKBOX, default_value=False)
            dpg.add_input_text(label="Google Gemini API Key", tag=TAG_GEMINI_API_KEY_INPUT, password=True, width=260)
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Usa API Key Mistral dalla GUI", tag=TAG_USE_GUI_MISTRAL_KEY_CHECKBOX, default_value=False)
            dpg.add_input_text(label="Mistral API Key", tag=TAG_MISTRAL_API_KEY_INPUT, password=True, width=260)
        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=10)
        # --- FOOTER ---
        with dpg.group(horizontal=True):
            dpg.add_text("🤖", color=(66, 133, 244, 255))
            dpg.add_text("DeepNotes AI - Minimal Google Style UI", color=(200, 200, 200, 255))
            dpg.add_spacer(width=10)
            dpg.add_text("by Carlo Zamuner", color=(180, 180, 180, 255))

def run_app():
    dpg.create_context()
    setup_modern_theme()
    setup_modern_font()
    create_main_window()
    dpg.create_viewport(title="DeepNotes", width=820, height=980, resizable=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    run_app()
