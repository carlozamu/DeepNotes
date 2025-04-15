# DeepNotes

<img src="./assets/logo.png" alt="DeepNotes Logo" width="120" />

DeepNotes is a desktop application for taking and managing notes with advanced features.

## Project Structure

```
deepnotes/
├── assets/              # Images and assets
│   └── logo.png
├── output/              # Generated text files
├── python-backend/      # Python backend services
├── src/                 # React frontend code
├── src-tauri/           # Tauri/Rust code
└── ... (other configuration files)
```

## Development

### Prerequisites

- [Node.js](https://nodejs.org/) (v16+)
- [Rust](https://www.rust-lang.org/tools/install)
- [Tauri CLI](https://tauri.app/v1/guides/getting-started/setup)

### Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run tauri dev
   ```

### Building

Build the application:
```bash
npm run tauri build
```

## License

See the LICENSE file for details.

## 1. Overview & Objectives
- **Primary Objective:**
  Create a native macOS desktop app with a Google Material Design-style interface that:
  - Loads a video, extracts its transcription (without timestamps), and saves it to a `.txt` file.
  - Loads a PDF (slides/documents) and extracts text using OCR and/or direct reading methods.
  - Merges the video and PDF content using Google Gemini APIs to generate high-quality lecture notes.

- **Target User:**
  Students, educators, or professionals who need accurate summaries of lessons integrated from various sources (video and written material).

---

## 2. Key Features & Functionality
- **Video Upload & Transcription:**
  - Video file upload (MP4, MKV, AVI).
  - Audio extraction via FFmpeg.
  - Offline audio transcription with `faster-whisper` (without timestamps).

- **PDF Upload & Text Extraction:**
  - PDF file upload.
  - Direct text extraction (`PyMuPDF`/`pdfplumber`) or via OCR (`pytesseract` or Mistral OCR API) if the PDF is image/slide-based.

- **Content Merging:**
  - Sending extracted texts (video and PDF) to the Google Gemini API.
  - Generation of an intelligent summary (notes) combining the information.

- **Final Output:**
  - Saving the summary to a `.txt` file.
  - Ability to view and download results from the app.

---

## 3. Target Platform & User Experience
- **Platform:**
  macOS (with potential extension to Windows and Linux)

- **User Experience:**
  - Modern interface inspired by Google Material Design.
  - Intuitive navigation and clear feedback (spinners, success/error notifications).
  - Quick access to local files and processing tools.

---

## 4. Technology Stack

### Frontend / Interface
- **Desktop Framework:** Tauri
  - *Advantages:* Native apps, small bundle size, excellent OS integration.
- **UI Library:**
  - React (or Svelte) + Material UI (MUI) for a modern interface.
- **Tooling:**
  - Vite (for rapid development)
  - Node.js (npm or pnpm for dependency management)

### Backend / Processing
- **Language:** Python 3.8+
- **Video Processing:**
  - `ffmpeg-python` for audio extraction
  - `faster-whisper` for offline transcription
- **PDF Processing:**
  - `PyMuPDF` or `pdfplumber` for direct text extraction
  - `pytesseract` or Mistral OCR API for image-based documents
- **AI Integration:**
  - Google Gemini API for content merging and high-quality note generation
- **HTTP Client:**
  - `requests` for interacting with external APIs

---

## 5. System Architecture

                   ┌─────────────────────────────────────────┐
                   │    Frontend (React + Material UI)       │
                   │   [Handles Upload, Feedback, UI]        │
                   └─────────────────────────────────────────┘
                                 │
                                 │ (Tauri Bridge)
                                 ▼
                   ┌─────────────────────────────────────────┐
                   │       Tauri Layer (Rust)                │
                   │  - Command to launch Python scripts   │
                   └─────────────────────────────────────────┘
                                 │
                                 │ Invokes
                                 ▼
                   ┌─────────────────────────────────────────┐
                   │       Backend (Python)                  │
                   │ ┌───────────────┐   ┌───────────────┐   │
                   │ │ Video Processor│  │  PDF Processor│   │
                   │ │ - FFmpeg       │  │ - PyMuPDF/    │   │
                   │ │ - Faster-      │  │   pdfplumber  │   │
                   │ │   whisper      │  │ - pytesseract │   │
                   │ └───────────────┘   └───────────────┘   │
                   │             └─────────────────┘         │
                   │                  AI Engine               │
                   │         (Google Gemini API Integration)  │
                   └─────────────────────────────────────────┘
                                 │
                                 ▼
                   ┌─────────────────────────────────────────┐
                   │         Output (.txt file)              │
                   └─────────────────────────────────────────┘

---

## 6. Project Structure / Directory

    deepnotes/
    ├── src-tauri/                    # Tauri code (Rust)
    │   ├── tauri.conf.json           # Tauri configuration
    │   └── src/
    │       └── main.rs               # Entry point, defines Tauri commands to invoke Python scripts
    ├── frontend/                     # React frontend code
    │   ├── public/                   # Static files (favicon, index.html, etc.)
    │   └── src/
    │       ├── App.jsx               # Main application component
    │       ├── components/           # React components (upload, notifications, etc.)
    │       ├── pages/                # Pages and views (Home, Results, etc.)
    │       └── api/                  # Functions to interface with Tauri commands
    │   └── package.json              # Node.js dependency management
    ├── python-backend/               # Python code for processing
    │   ├── video_to_text.py          # Script to extract audio and transcribe video
    │   ├── pdf_to_text.py            # Script for PDF text extraction/OCR
    │   ├── ai_fusion.py              # Script for text merging and Google Gemini API invocation
    │   ├── utils/
    │   │   └── common.py             # Common utility functions (e.g., file handling, formatting)
    │   └── requirements.txt          # List of Python dependencies
    ├── assets/                       # Graphic assets (icons, images, logos)
    ├── README.md                     # Project documentation and guidelines
    └── .gitignore                    # Files/directories to exclude from version control

---

## 7. Integration & Communication
- **Tauri Bridge:**
  The Tauri layer (Rust) acts as an intermediary between the frontend (React) and the Python backend.
- **Use of Native Commands:**
  (via `Command::new("python3")` or similar) to invoke Python scripts.
- **Communication:**
  - The frontend sends requests via Tauri commands.
  - Python scripts process the files (video/PDF) and return results.
  - The frontend displays notifications, handles errors, and allows downloading the output file.

---

## 8. Tools, Packaging & Deployment
- **Development:**
  - Tauri CLI (`tauri dev`, `tauri build`)
  - Node.js/Vite for the frontend
  - Virtual Environment (`venv` or `poetry`) for the Python backend
  - FFmpeg (installed on the system and in PATH)
- **Packaging:**
  - Creation of a `.app` bundle for macOS using Tauri
  - Code signing and notarization processes for macOS distribution
- **Testing & Debugging:**
  - Test functionalities (upload, transcription, OCR, API fusion) in the development environment and on macOS
  - Error handling and logging in the backend and across layers

---

## 9. Roadmap & Next Steps
1.  **Initial Setup:**
    - Create the Tauri + React boilerplate with the basic structure.
    - Set up the Python environment and install all dependencies.
2.  **Backend Module Development:**
    - *Video Module:* Implement `video_to_text.py` (audio extraction and transcription).
    - *PDF Module:* Implement `pdf_to_text.py` (text/OCR extraction).
    - *AI Module:* Implement `ai_fusion.py` to interface with Google Gemini.
3.  **Frontend-Backend Integration:**
    - Implement the Tauri bridge to run Python scripts from the frontend.
    - Create the interface for file uploads, displaying feedback, and enabling downloads.
4.  **Testing, Optimization & Packaging:**
    - Perform functional tests and optimize performance.
    - Package the app for macOS, including code signing and notarization.

---

## 10. Final Considerations
- Maintain updated and detailed documentation in the `README.md`.
- Design modularly to facilitate future updates (e.g., support for new formats or local AI models).
- Implement robust error handling to ensure a good user experience.
