# 🚀 Building ViralReel.AI from Scratch with Google Antigravity

This tutorial provides a step-by-step walkthrough to build the **ViralReel.AI** dashboard from absolute scratch using **Google Antigravity**, Google's autonomous agentic AI development environment. 

Rather than writing code line-by-line, you will learn how to set up Antigravity, authenticate, and prompt the agent to perform the file creation, backend configuration, and system testing automatically.

---

## 📥 Phase 1: Installing Google Antigravity

Google Antigravity is a standalone, AI-native IDE built to orchestrate autonomous coding agents.

### 1. Download the Installer
1. Go to the official portal: [antigravity.google](https://antigravity.google).
2. Download the appropriate distribution package for your OS:
   * **macOS**: Apple Silicon (M1/M2/M3) or Intel installer `.dmg`.
   * **Windows**: 64-bit installer `.exe`.
   * **Linux**: `.deb` or `.tar.gz` package.

### 2. Complete Installation
* **macOS**: Open the `.dmg` and drag **Antigravity** into your `/Applications` directory.
* **Windows**: Execute the `.exe` file and follow the setup wizard guidelines.
* **Linux**: Install via package manager:
  ```bash
  sudo dpkg -i antigravity-desktop.deb
  ```

---

## 👤 Phase 2: Sign-Up & First-Time Setup

1. **Launch the IDE**: Open the Antigravity application from your applications menu.
2. **Google Account Authentication**: On first launch, you will see a splash screen prompting you to sign in. Click **Sign in with Google** and authorize using your personal Gmail credentials.
3. **Select Preferences**:
   * Choose your editor shortcuts (you can import existing profiles from VS Code).
   * Confirm the default LLM provider (default: **Gemini 3.5 Flash** for rapid coding iterations).
4. **Prepare your Workspace**:
   * Create an empty directory on your machine:
     ```bash
     mkdir viral-reel-dashboard
     ```
   * Select **File > Open Folder...** inside Antigravity and select the new empty directory.

---

## 💬 Phase 3: Prompting the Antigravity Agent

Antigravity features an **Agent Manager** sidebar. This is where you instruct the agent to plan, execute, and verify tasks. 

### The Master Prompt
Copy and paste the following comprehensive prompt directly into the **Agent Manager** prompt input box and hit **Enter**:

```text
Create a short-form video generation dashboard (ViralReel.AI) in this directory. 
The application must generate 9:16 portrait videos (like TikToks or YouTube Shorts) using 100% free-tier APIs and local tools.

Implement the project with the following requirements:

1. Project Folder Structure:
   ├── index.html (Dashboard frontend)
   ├── style.css (Beautiful modern glassmorphism styling)
   ├── app.js (Interactive UI controls and audio waveform simulations)
   └── backend/ (FastAPI API server)
       ├── main.py (Uvicorn router & orchestrator)
       ├── requirements.txt (Dependencies: fastapi, uvicorn, edge-tts, faster-whisper, python-dotenv)
       └── services/
           ├── llm_service.py (Google Gemini configuration with model 'gemini-1.5-flash' to segment text scripts into scenes)
           ├── tts_service.py (edge-tts integration for voiceovers)
           ├── whisper_service.py (faster-whisper word-level aligner, with automatic linear alignment fallback if libraries fail)
           ├── asset_service.py (Pexels API downloader with cached media query hashes and Mixkit fallback loops)
           └── render_service.py (FFmpeg scripting to crop to 1080x1920, overlay ASS kinetic subtitles, loop background music, and apply sidechain audio ducking)

2. Core Features:
   - Structured JSON response from Gemini API for storyboard formatting.
   - Modern kinetic subtitles (word-by-word highlights using \c&H00FFFF& yellow tags in an ASS style script).
   - Sidechain compression audio ducking in FFmpeg (lowering lofi background track by -18dB when voiceover speaks).
   - Glassmorphic frontend with responsive column design, theme presets, interactive storyboard editor, and mobile mockup video preview player.

Start by creating the backend folder boilerplate, setup .env, then create requirements.txt. Once established, proceed to implement the backend services, the frontend interface, and verify that FFmpeg can run correctly.
```

---

## ⚙️ Phase 4: How Antigravity Builds the App

Once you send the prompt, watch the Antigravity Agent work through the implementation steps. The workspace lifecycle typically progresses as follows:

### Step 1: Researching & Planning
The agent will create an `implementation_plan.md` outlining the tech stack and structural outline.
> [!TIP]
> Review the agent's plan in the Editor window. If everything looks correct, click the **Approve** button in the chat interface.

### Step 2: Creating Backend Boilerplates
The agent will automatically create the directories, initialize `backend/requirements.txt`, and create a default `.env` template.

### Step 3: Implementing Python Services
The agent writes code for:
1. `services/llm_service.py`: Hooks up `google-generativeai` with a structured Pydantic schema to parse scripts.
2. `services/tts_service.py`: Sets up `edge-tts` to download audio blocks.
3. `services/whisper_service.py`: Standardizes `faster-whisper` transcriptions and fallback alignments.
4. `services/asset_service.py`: Coordinates stock retrieval and file caches.
5. `services/render_service.py`: Constructs the full FFmpeg commands to slice, compose, and style subtitles.

### Step 4: Structuring the UI
The agent designs `index.html` with a 3-column layout, styles it with modern CSS (gradients, shadows, glass cards), and writes the event listeners in `app.js` to manage storyboards and communicate with the FastAPI backend.

---

## 🔑 Phase 5: Authorizing CLI Commands & API Keys

### 1. Command Permissions
As the agent sets up python dependencies and runs diagnostics, it may propose terminal execution steps (e.g. running `pip install -r requirements.txt` or checking `ffmpeg -version`).
* Read the command preview in the chat terminal.
* Click **Allow** to let the agent execute it safely in the sandboxed terminal.

### 2. Enter Credentials
While the agent is coding, fill out the generated `backend/.env` file:
1. Get a Gemini API Key from the [Google AI Studio Console](https://aistudio.google.com/app/api-keys).
2. Get a Pexels API Key from [Pexels Developer Dashboard](https://www.pexels.com/api/).
3. Paste these keys into the respective fields in `backend/.env`:
   ```env
   GEMINI_API_KEY="AIzaSy..."
   PEXELS_API_KEY="563492..."
   ```

---

## 🧪 Phase 6: Running & Verifying the App

Once the agent indicates the code is complete, it will prompt you to launch the application.

1. **Verify Backend**:
   The agent will run the local development server in the terminal:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```
2. **Verify Frontend**:
   The agent will run a simple HTTP server in another terminal tab:
   ```bash
   python3 -m http.server 3000
   ```
3. **Launch**:
   Open Chrome and go to `http://localhost:3000`. 
   * Paste a script into the input box.
   * Click **Generate Storyboard & Script**.
   * Edit scene texts and click **Export Rendered Video**.
   * Verify the compiled output appears in `backend/static/outputs/` and includes active word subtitle overlays.
