# Eco Travel Advisor Chatbot

An Eco Travel Advisor chatbot built with **Rasa** to help users plan more sustainable trips.  
The bot collects trip details (destination, dates, budget, preferences), estimates carbon footprints for different travel options, recommends eco-friendly accommodation, and supports escalation to a human travel advisor.

> This project was developed as part of a Level 7 module in Advanced Conversational UI Design and Chatbot Development.

---

## 1. Features

- **Trip planning conversation**
  - Collects destination, travel dates, budget per person, number of travellers
  - Captures sustainability preferences (e.g. lowest carbon, most affordable, balanced)
- **Eco-aware recommendations**
  - Designed to call external APIs (e.g. carbon/emissions, travel APIs) via custom actions
  - Ranks options by carbon impact and price
- **Carbon footprint feedback**
  - Presents approximate CO₂ values (e.g. train vs flight) in a user-friendly way
- **Human handover**
  - `request_human` intent allows users to escalate to a travel specialist
  - Packs conversation context (slots and history) for the human advisor
- **Webchat interface**
  - Simple `index.html` page with Rasa Webchat widget
  - Shows a conversation with carbon badges and an always-visible escalation button
- **Docker-based deployment (prototype)**
  - Dockerfile to build and run the Rasa project in a container
  - Designed to be compatible with Hugging Face Spaces (Docker Space)

---

## 2. Project structure

Main files and folders:

- `config.yml`  
  NLU pipeline and policy configuration (DIETClassifier, TEDPolicy, etc.).

- `domain.yml`  
  Intents, entities, slots, responses, forms, and actions.

- `data/`
  - `nlu.yml` – training examples for intents and entities  
  - `stories.yml` – conversation stories  
  - `rules.yml` – rules for forms, fallbacks, handover

- `actions.py`  
  Custom actions (e.g. fetching eco hotels, carbon estimates, packaging handover context).

- `models/`  
  Trained Rasa models (`*.tar.gz`), created by `rasa train`.

- `web/`
  - `index.html` – webchat UI using the Rasa Webchat widget.

- `Dockerfile`  
  Docker configuration for containerised deployment.

- `README.md`  
  This file.

> Note: Some external APIs (e.g. Climatiq, Amadeus) are referenced in design and `actions.py` but may use placeholders or sandbox keys depending on your setup.

---

## 3. Prerequisites

- **Python**: 3.9 (local dev) or 3.10 (for Docker image)  
- **Rasa**: 3.x (installed in a virtual environment)  
- **Node/npm**: _not required_ (webchat is loaded from a CDN)  
- **Docker** (optional, for containerised deployment)

---

## 4. Setup (local development)

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd eco-travel-chatbot
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv

   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1

   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**

   If you have a `requirements.txt`:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   Or install Rasa directly:

   ```bash
   pip install --upgrade pip
   pip install rasa==3.6.0
   ```

4. **Train the model**

   ```bash
   rasa train
   ```

   This will create a model file in the `models/` directory.

---

## 5. Running the bot

### 5.1 Rasa server (API)

To start the Rasa HTTP server:

```bash
rasa run
```

By default, this serves the API on `http://localhost:5005`.  
You can enable the API explicitly and allow CORS:

```bash
rasa run --enable-api --cors "*" --host 0.0.0.0 --port 5005
```

### 5.2 Rasa shell (CLI)

For quick CLI testing:

```bash
rasa shell
```

> Note: On some environments (e.g. Windows + Python 3.9), you may encounter `GraphComponentException` errors related to policies and featurizers. These are documented in the report as environment limitations.

---

## 6. Webchat interface

The project includes a simple HTML-based webchat:

- File: `web/index.html`
- Uses the Rasa Webchat widget loaded from a CDN
- Connects to `http://localhost:5005` (or another configured URL)

To use it:

1. Start the Rasa server:

   ```bash
   rasa run --enable-api --cors "*" --host 0.0.0.0 --port 5005
   ```

2. Open `web/index.html` in your browser (double-click or use **File → Open**).

3. You should see:
   - Page title: **Eco Travel Advisor**
   - Chat widget with title and subtitle (Eco Travel Assistant / Plan sustainable trips)
   - User and bot messages as you interact

If the widget does not load:

- Check the browser console for errors (e.g. `WebChat is not defined` or blocked scripts).  
- Try using Chrome and ensure tracking prevention or ad-blockers are not blocking `unpkg.com`.

---

## 7. Docker deployment (local)

A Dockerfile is provided to containerise the chatbot.

### 7.1 Build the image

From the project root:

```bash
docker build -t eco-travel-bot .
```

### 7.2 Run the container

```bash
docker run -p 5005:5005 eco-travel-bot
```

This exposes the chatbot API at `http://localhost:5005`.

You can then open `web/index.html` and set the webchat `socketUrl` to `http://localhost:5005` (default), allowing the frontend to talk to the containerised backend.

> For Hugging Face Spaces (Docker Spaces), the Dockerfile can be adapted to use port 7860 instead of 5005, and the code pushed to a Space repository where Hugging Face handles the build and run process.

---

## 8. Known issues and limitations

- **Windows-specific temp directory permissions**  
  On Windows with Python 3.9, `rasa train` may finish successfully but fail when cleaning temporary directories (`PermissionError: [WinError 5]`). The model files are still created in `models/`, but the error appears in logs.

- **Policy / featurizer runtime errors**  
  Under some dependency combinations, `MemoizationPolicy` and `RulePolicy` may throw `GraphComponentException` and `AttributeError: 'dict' object has no attribute 'prediction_states'` when handling messages. This can prevent `rasa shell` from working reliably.

- **API integrations**  
  Some external API calls (Climatiq, Amadeus, etc.) may be stubs or require valid API keys. Ensure environment variables or config files are set correctly before enabling them.

These issues are documented in the accompanying report and are earmarked for future work (e.g. upgrading Python, pinning Rasa and dependencies, and refining the policy configuration).

---

## 9. Future work

Planned enhancements include:

- Stabilising the environment (supported Python version, refined Rasa version pinning)
- Completing and hardening external API integrations (carbon and travel APIs)
- Improving conversation design and resolving story conflicts
- Enhancing the web UI (better carbon visualisations, accessibility improvements)
- Fully deploying to a Hugging Face Docker Space or other cloud platform

---

## 10. Acknowledgements

This project was developed as part of a university module on Conversational UI and Chatbot Development, with a focus on sustainable tourism and responsible AI practices.
