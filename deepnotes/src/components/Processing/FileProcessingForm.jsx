import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  Button,
  Stepper,
  Step,
  StepLabel,
  Divider,
  TextField,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  CircularProgress,
  IconButton,
  Snackbar,
  Alert,
  Checkbox,
  FormControlLabel
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import NoteAltIcon from '@mui/icons-material/NoteAlt';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import { invoke } from '@tauri-apps/api/tauri';
import { open } from '@tauri-apps/api/dialog';
import { basename } from '@tauri-apps/api/path';
import { readTextFile } from '@tauri-apps/api/fs';
import { open as openShell } from '@tauri-apps/api/shell';

const steps = ['Seleziona file', 'Elaborazione', 'Risultato'];

const FileProcessingForm = () => {
  const [activeStep, setActiveStep] = useState(0);
  // File selezionati (memorizziamo percorso e nome)
  const [selectedVideoFile, setSelectedVideoFile] = useState(null); // { path: string, name: string } | null
  const [selectedPdfFile, setSelectedPdfFile] = useState(null);   // { path: string, name: string } | null
  // Testi estratti
  const [videoTranscript, setVideoTranscript] = useState('');
  const [pdfText, setPdfText] = useState('');
  // Stato di elaborazione e messaggi
  const [isProcessingVideo, setIsProcessingVideo] = useState(false);
  const [isProcessingPdf, setIsProcessingPdf] = useState(false);
  const [isGeneratingNotes, setIsGeneratingNotes] = useState(false);
  const [finalOutputPath, setFinalOutputPath] = useState(''); // Percorso del file .txt finale
  const [error, setError] = useState(''); // Messaggio di errore generale
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  
  // Opzioni OCR
  const [forceOcr, setForceOcr] = useState(false);
  const [ocrLanguage, setOcrLanguage] = useState('eng'); // Default a inglese
  
  // Manteniamo questi per la compatibilità con il salvataggio delle note
  const [language, setLanguage] = useState('italiano'); 
  const [noteStyle, setNoteStyle] = useState('riassunto');
  const [summary, setSummary] = useState('');

  const handleSelectVideo = async () => {
    setError(''); // Resetta errore precedente
    try {
      const result = await open({
        title: 'Seleziona un File Video',
        multiple: false,
        filters: [{ name: 'Video Files', extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm'] }],
      });

      if (typeof result === 'string') { // Un solo file selezionato
        const name = await basename(result);
        setSelectedVideoFile({ path: result, name: name });
        showNotification(`Video selezionato: ${name}`, 'info');
      } else {
        // Nessun file selezionato o selezione annullata
        setSelectedVideoFile(null);
      }
    } catch (err) {
      console.error("Errore selezione video:", err);
      setError(`Errore durante la selezione del video: ${err}`);
      showNotification(`Errore selezione video: ${err}`, 'error');
    }
  };

  const handleSelectPdf = async () => {
    setError('');
    try {
      const result = await open({
        title: 'Seleziona un File PDF',
        multiple: false,
        filters: [{ name: 'PDF Files', extensions: ['pdf'] }],
      });

      if (typeof result === 'string') {
        const name = await basename(result);
        setSelectedPdfFile({ path: result, name: name });
        showNotification(`PDF selezionato: ${name}`, 'info');
      } else {
        setSelectedPdfFile(null);
      }
    } catch (err) {
      console.error("Errore selezione PDF:", err);
      setError(`Errore durante la selezione del PDF: ${err}`);
      showNotification(`Errore selezione PDF: ${err}`, 'error');
    }
  };

  // Funzione helper per mostrare notifiche
  const showNotification = (message, severity = 'info') => {
    setNotification({ open: true, message, severity });
  };

  const handleCloseNotification = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setNotification({ ...notification, open: false });
  };

  const handleProcessFilesAndGenerate = async () => {
    if (!selectedVideoFile && !selectedPdfFile) {
      setError("Seleziona almeno un file video o PDF da processare.");
      showNotification("Seleziona almeno un file video o PDF.", "warning");
      return;
    }

    setActiveStep(1); // Passa allo step di elaborazione
    setError('');
    setVideoTranscript(''); // Resetta risultati precedenti
    setPdfText('');
    setFinalOutputPath('');

    let currentVideoTranscript = '';
    let currentPdfText = '';

    // --- Processa Video (se selezionato) ---
    if (selectedVideoFile) {
      setIsProcessingVideo(true);
      showNotification(`Inizio trascrizione video: ${selectedVideoFile.name}...`, 'info');
      try {
        const transcriptResult = await invoke('process_video_command', {
          videoPath: selectedVideoFile.path,
        });
        currentVideoTranscript = transcriptResult; // Salva il risultato intermedio
        setVideoTranscript(transcriptResult); // Aggiorna stato per UI (se necessario)
        showNotification(`Trascrizione video completata!`, 'success');
      } catch (err) {
        console.error("Errore processamento video:", err);
        setError(`Errore trascrizione video: ${err}`);
        showNotification(`Errore trascrizione video: ${err}`, 'error');
        // Decidi se fermare il processo o continuare solo col PDF
        setIsProcessingVideo(false);
        setActiveStep(0); // Torna allo step iniziale in caso di errore grave? O mostra errore nello step 1?
        return; // Fermati qui per ora
      } finally {
        setIsProcessingVideo(false);
      }
    }

    // --- Processa PDF (se selezionato) ---
    if (selectedPdfFile) {
      setIsProcessingPdf(true);
      showNotification(`Inizio estrazione testo PDF: ${selectedPdfFile.name}...`, 'info');
      try {
        const pdfResult = await invoke('process_pdf_command', {
          pdfPath: selectedPdfFile.path,
          forceOcr: forceOcr,  // Usa lo stato
          ocrLang: ocrLanguage, // Usa lo stato
        });
        currentPdfText = pdfResult; // Salva risultato intermedio
        setPdfText(pdfResult); // Aggiorna stato per UI
        showNotification(`Estrazione testo PDF completata!`, 'success');
      } catch (err) {
        console.error("Errore processamento PDF:", err);
        setError(`Errore estrazione PDF: ${err}`);
        showNotification(`Errore estrazione PDF: ${err}`, 'error');
        setIsProcessingPdf(false);
        setActiveStep(0); // Torna indietro?
        return; // Fermati qui
      } finally {
        setIsProcessingPdf(false);
      }
    }

    // --- Genera Note (se almeno uno dei processi precedenti è andato a buon fine) ---
    if (currentVideoTranscript || currentPdfText) {
      setIsGeneratingNotes(true);
      showNotification("Invio testi all'AI per la generazione delle note...", 'info');
      try {
        const outputPath = await invoke('generate_notes_command', {
          videoTranscriptText: currentVideoTranscript,
          pdfExtractedText: currentPdfText,
        });
        setFinalOutputPath(outputPath); // Salva il percorso del file finale
        setSummary("Le note sono state generate e salvate. Puoi salvarle come nota in DeepNotes o accedervi direttamente dal file.");
        setActiveStep(2); // Vai allo step Risultato
        showNotification(`Note generate e salvate in: ${outputPath}`, 'success');
      } catch (err) {
        console.error("Errore generazione note:", err);
        setError(`Errore generazione note: ${err}`);
        showNotification(`Errore generazione note: ${err}`, 'error');
        setActiveStep(0); // Torna indietro?
      } finally {
        setIsGeneratingNotes(false);
      }
    } else {
      // Caso in cui entrambi i file sono stati selezionati ma entrambi hanno fallito
      // L'errore dovrebbe essere già stato gestito e mostrato
      setActiveStep(0); // Torna indietro
    }
  };

  const handleReset = () => {
    setActiveStep(0);
    setSelectedVideoFile(null);
    setSelectedPdfFile(null);
    setVideoTranscript('');
    setPdfText('');
    setIsProcessingVideo(false);
    setIsProcessingPdf(false);
    setIsGeneratingNotes(false);
    setFinalOutputPath('');
    setError('');
    setSummary('');
  };

  const handleSaveGeneratedNote = async () => {
    if (!finalOutputPath) {
      showNotification("Nessun file di output da salvare come nota.", "warning");
      return;
    }

    showNotification("Lettura del file di output...", "info");
    try {
      // Leggi il contenuto del file generato usando l'API Tauri FS
      const generatedContent = await readTextFile(finalOutputPath);

      if (!generatedContent) {
        showNotification("Il file di output è vuoto o illeggibile.", "error");
        return;
      }

      // Recupera le note esistenti o inizializza un array vuoto
      const savedNotes = localStorage.getItem('deepnotes_notes');
      const notes = savedNotes ? JSON.parse(savedNotes) : [];

      // Crea una nuova nota con il contenuto letto
      const newNote = {
        id: Date.now().toString(),
        // Titolo più significativo basato sui file originali
        title: `Nota da ${selectedVideoFile?.name ?? ''}${selectedVideoFile && selectedPdfFile ? ' e ' : ''}${selectedPdfFile?.name ?? ''}`.replace("Nota da ", "Nota da").trim() || `Nota generata ${new Date().toLocaleDateString()}`,
        content: generatedContent, // Usa il contenuto letto dal file
        // Potremmo estrarre tag dal contenuto o usare quelli di configurazione
        tags: [ocrLanguage, (selectedVideoFile ? 'video' : ''), (selectedPdfFile ? 'pdf' : '')].filter(Boolean),
        date: new Date().toISOString(),
      };

      // Aggiunge la nuova nota all'array
      notes.push(newNote);

      // Salva nel localStorage
      localStorage.setItem('deepnotes_notes', JSON.stringify(notes));

      // Mostra una notifica di successo
      showNotification('Nota salvata con successo dalla generazione!', 'success');

    } catch (err) {
      console.error("Errore lettura/salvataggio nota:", err);
      setError(`Errore nel salvare la nota: ${err}`);
      showNotification(`Errore nel salvare la nota: ${err}`, 'error');
    }
  };

  const handleOpenFile = async () => {
    if (!finalOutputPath) {
        showNotification("Nessun file di output da aprire.", "warning");
        return;
    }
    try {
        // Usa l'API shell di Tauri per aprire il file con l'applicazione predefinita
        await openShell(finalOutputPath);
        showNotification(`Tentativo di aprire: ${finalOutputPath}`, 'info');
    } catch (err) {
        console.error("Errore apertura file:", err);
        setError(`Impossibile aprire il file: ${err}`);
        showNotification(`Impossibile aprire il file: ${err}`, 'error');
    }
  };

  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom align="center">
              Seleziona i file sorgente
            </Typography>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Box sx={{ display: 'flex', justifyContent: 'space-around', mb: 3 }}>
              {/* Bottone Selezione Video */}
              <Box sx={{ textAlign: 'center' }}>
                <Button
                  variant="outlined"
                  startIcon={<CloudUploadIcon />}
                  onClick={handleSelectVideo}
                  sx={{ mb: 1 }}
                >
                  Seleziona Video (.mp4, .mkv, ...)
                </Button>
                {selectedVideoFile && (
                  <Typography variant="body2" color="text.secondary">
                    {selectedVideoFile.name}
                    <IconButton size="small" onClick={() => setSelectedVideoFile(null)} color="error">
                      <DeleteIcon fontSize="inherit"/>
                    </IconButton>
                  </Typography>
                )}
              </Box>

              {/* Bottone Selezione PDF */}
              <Box sx={{ textAlign: 'center' }}>
                <Button
                  variant="outlined"
                  startIcon={<CloudUploadIcon />}
                  onClick={handleSelectPdf}
                  sx={{ mb: 1 }}
                >
                  Seleziona PDF (.pdf)
                </Button>
                {selectedPdfFile && (
                  <Typography variant="body2" color="text.secondary">
                    {selectedPdfFile.name}
                    <IconButton size="small" onClick={() => setSelectedPdfFile(null)} color="error">
                      <DeleteIcon fontSize="inherit"/>
                    </IconButton>
                  </Typography>
                )}
              </Box>
            </Box>

            {/* Opzioni PDF (mostra solo se un PDF è selezionato) */}
            {selectedPdfFile && (
              <Box sx={{ mt: 2, p: 2, border: '1px dashed grey', borderRadius: 1, textAlign: 'left' }}>
                <Typography variant="body2" gutterBottom sx={{ fontWeight: 'bold' }}>Opzioni PDF:</Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={forceOcr}
                      onChange={(e) => setForceOcr(e.target.checked)}
                      size="small"
                    />
                  }
                  label="Forza OCR (ignora estrazione diretta)"
                />
                <FormControl size="small" sx={{ minWidth: 120, ml: 2 }}>
                  <InputLabel id="ocr-lang-label">Lingua OCR</InputLabel>
                  <Select
                    labelId="ocr-lang-label"
                    value={ocrLanguage}
                    label="Lingua OCR"
                    onChange={(e) => setOcrLanguage(e.target.value)}
                  >
                    <MenuItem value={'eng'}>Inglese (eng)</MenuItem>
                    <MenuItem value={'ita'}>Italiano (ita)</MenuItem>
                    <MenuItem value={'fra'}>Francese (fra)</MenuItem>
                    <MenuItem value={'deu'}>Tedesco (deu)</MenuItem>
                    <MenuItem value={'spa'}>Spagnolo (spa)</MenuItem>
                    {/* Aggiungere altre lingue se Tesseract le supporta */}
                  </Select>
                </FormControl>
              </Box>
            )}

            <Divider sx={{ my: 2 }}/>

            <Box sx={{ textAlign: 'center', mt: 3 }}>
              <Button
                variant="contained"
                color="primary"
                size="large"
                onClick={handleProcessFilesAndGenerate}
                disabled={!selectedVideoFile && !selectedPdfFile} // Abilita se almeno un file è selezionato
                startIcon={<NoteAltIcon />}
              >
                Avvia Elaborazione e Genera Note
              </Button>
            </Box>
          </Box>
        );
      case 1:
        return (
          <Box sx={{ textAlign: 'center', p: 4 }}>
            <Typography variant="h6" gutterBottom>
              Elaborazione in corso...
            </Typography>
            {isProcessingVideo && (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                <Typography>Trascrizione video...</Typography>
              </Box>
            )}
            {isProcessingPdf && (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                <Typography>Estrazione testo PDF...</Typography>
              </Box>
            )}
            {isGeneratingNotes && (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                <Typography>Generazione note con AI...</Typography>
              </Box>
            )}
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
            {/* Non mostriamo bottoni qui, l'avanzamento è automatico */}
          </Box>
        );
      case 2:
        return (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h5" gutterBottom color="success.main">
              Elaborazione Completata!
            </Typography>
            {finalOutputPath ? (
              <Typography paragraph>
                Le note sono state generate e salvate in: <br/>
                <code>{finalOutputPath}</code>
              </Typography>
            ) : (
              <Typography paragraph color="warning.main">
                Qualcosa è andato storto, nessun file di output generato. Controlla le notifiche o i log.
              </Typography>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
              <Button
                variant="outlined"
                onClick={handleReset}
              >
                Elabora Nuovi File
              </Button>
              <Button
                variant="contained"
                color="primary"
                startIcon={<SaveIcon />}
                onClick={handleSaveGeneratedNote} // Chiama la nuova funzione
                disabled={!finalOutputPath}
              >
                Salva come nota
              </Button>
              <Button
                variant="contained"
                color="secondary"
                startIcon={<FolderOpenIcon />}
                onClick={handleOpenFile} // Chiama la nuova funzione
                disabled={!finalOutputPath}
              >
                Apri File Generato
              </Button>
            </Box>
            {error && <Alert severity="error" sx={{ mt: 2, textAlign: 'left' }}>{error}</Alert>}
          </Box>
        );
      default:
        return null;
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mt: 4 }}>
      <Typography variant="h5" component="h2" gutterBottom align="center">
        Elabora i tuoi documenti
      </Typography>
      
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      
      {renderStepContent(activeStep)}

      <Snackbar 
        open={notification.open} 
        autoHideDuration={4000} 
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseNotification} 
          severity={notification.severity}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default FileProcessingForm; 