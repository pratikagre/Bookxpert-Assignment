# Talk-a-Tive: Grounded Document Q&A Bot with RAG

Talk-a-Tive is a Retrieval-Augmented Generation (RAG) system built from scratch in Python to answer natural language questions against a custom document collection. By integrating text extraction from diverse file formats (PDF, DOCX, TXT) with semantic vector search (ChromaDB) and Google Gemini large language models, the bot delivers highly accurate, context-grounded answers accompanied by precise, inline source citations.

---

## 🛠️ Tech Stack & Dependencies

All dependencies are pinned and configured for Python 3.11+. The libraries used include:

*   **Language & Runtime:** Python 3.12.4
*   **LLM & Embeddings Integration:** `google-generativeai` (v0.8.6)
*   **Vector Database:** `chromadb` (v1.5.9) - Local, disk-persistent vector storage.
*   **Document Parsers:** 
    *   `pypdf` (v6.13.3) - Fast, page-level PDF text extraction.
    *   `python-docx` (v1.2.0) - Paragraph and heading extraction for Microsoft Word documents.
*   **PDF Generation (Testing):** `reportlab` (v4.5.1) - Used to programmatically generate non-trivial PDF test documents.
*   **UI & Interactive Clients:**
    *   `streamlit` (v1.58.0) - Premium web-based interface.
    *   Standard library CLI loop client.
*   **Utilities:** `python-dotenv` (v1.2.2), `tqdm` (v4.68.3)

---

## 🧠 Architecture Overview

Below is the conceptual flow of the Talk-a-Tive RAG pipeline:

```
[ Ingestion Phase ]
  📂 Custom Documents (PDF, DOCX, TXT)
          │
          ▼
  📄 Text Extraction (pypdf, python-docx, open)
          │
          ▼
  ✂️ Recursive Text Chunking (with 200-char overlap & metadata)
          │
          ▼
  🧬 Batch Embedding (models/text-embedding-004)
          │
          ▼
  💾 Persistent Local Vector DB (ChromaDB under ./db)

[ Query & Generation Phase ]
  💬 User Query (from CLI or Streamlit)
          │
          ▼
  🧬 Query Embedding (models/text-embedding-004)
          │
          ▼
  🔍 Similarity Search (Cosine distance in ChromaDB)
          │
          ├────────────────────────┐
          ▼                        ▼
  📄 Top-k Context Chunks   📍 Source Citations
          │                        │
          └───────────┬────────────┘
                      ▼
             📝 Grounding Prompt
                      │
                      ▼
            🧠 LLM (gemini-2.5-flash)
                      │
                      ▼
         ✨ Grounded Answer + Citations
```

---

## 📐 Key Design Decisions

### 1. Chunking Strategy: Recursive Character Splitting
*   **Choice:** Custom recursive paragraph, sentence, and word-boundary text splitter.
*   **Why:** Rather than cutting text arbitrarily at a fixed character limit (which breaks sentences and words in half), our recursive splitter splits on paragraphs (`\n\n`), single line breaks (`\n`), sentences (`. `), and words (` `) sequentially. This guarantees that each chunk is a semantically coherent unit.
*   **Configuration:** `CHUNK_SIZE = 1000` characters with a `CHUNK_OVERLAP = 200` characters. The overlap ensures that context spanning across boundaries is preserved in both adjacent chunks, reducing retrieval loss.

### 2. Embedding Model: Google `text-embedding-004`
*   **Choice:** Google's state-of-the-art `text-embedding-004` via the Google GenAI API.
*   **Why:** It generates dense 768-dimensional vector representations optimized for semantic similarity, outperforming standard open-source models while integrating natively with the Gemini generative suite. All embedding operations are batched during ingestion.

### 3. Vector Database: ChromaDB
*   **Choice:** ChromaDB (disk-persistent mode).
*   **Why:** ChromaDB is a lightweight, serverless database that runs entirely inside the local Python project space, removing the operational complexity of hosting external database instances. By setting the persistence directory to `./db`, we run the embedding process only once—thereafter, the Q&A bot reuses the database state instantly on launch.

---

## 🚀 Setup & Installation Instructions

Follow these step-by-step instructions to clone, configure, and run Talk-a-Tive locally:

### 1. Prerequisite
*   Ensure **Python 3.11** or higher is installed on your system.
*   Get a Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

### 2. Workspace Setup & Virtual Environment
```bash
# Clone the repository (or navigate to the workspace directory)
git clone <repository_url>
cd Bookxpert-Assignment

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (Command Prompt / PowerShell):
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install all required packages
pip install -r requirements.txt
```

### 3. Environment Variable Configuration
1.  In the project root folder, locate the `.env` template file.
2.  Open the file and add your Gemini API Key:
    ```env
    GEMINI_API_KEY=your_actual_google_gemini_api_key_here
    ```
    *(Note: `.env` is listed in `.gitignore` and will never be committed to source control).*

### 4. Step 1: Run Ingestion (Document Indexing)
Before running the Q&A Bot, you must index the source documents:
```bash
python src/ingest.py
```
*Expected Output:*
*   The script reads 5 documents from the `data/` folder: `artificial_intelligence_guide.pdf`, `quantum_computing_intro.docx`, `space_exploration_history.txt`, `renewable_energy_future.pdf`, and `mental_health_and_sleep.txt`.
*   It splits the text into chunks and saves the vectors to `./db/`.
*   A progress bar will indicate batch embedding progress.

### 5. Step 2: Querying the Bot (Two User Interfaces)

#### Option A: Command Line Interface (CLI Loop)
To run the bot inside your terminal as an interactive loop:
```bash
python src/cli.py
```
Type your question and press `Enter`. Type `exit` or `quit` to close the loop.

#### Option B: Streamlit Web UI (Recommended)
To run the high-fidelity web application:
```bash
streamlit run src/app.py
```
A browser window will open automatically at `http://localhost:8501`. 
*   **Sidebar features:** Adjust the number of chunks ($k$) to retrieve, run re-indexing, and view the currently indexed files.
*   **Interface features:** Dynamic markdown answers and expandable citation cards showing the source text, page/section, and similarity scores.

---

## 📝 Example Queries

Test the RAG pipeline using the following queries to verify multi-document coverage:

1.  **Query:** *"What is quantum superposition and how does it differ from classical bits?"*
    *   *Source:* `quantum_computing_intro.docx` (Section 1)
    *   *Theme:* Explains qubits, the ability to exist in multiple states simultaneously ($2^N$ states for $N$ qubits), and contrast with binary 0/1 bits.
2.  **Query:** *"What were the key achievements of the Apollo program?"*
    *   *Source:* `space_exploration_history.txt` (Section 2)
    *   *Theme:* Explains the July 1969 landing of Neil Armstrong and Buzz Aldrin, landing 12 astronauts, and bringing back 382kg of lunar rock.
3.  **Query:** *"Explain the Transformer architecture in deep learning."*
    *   *Source:* `artificial_intelligence_guide.pdf` (Section 3)
    *   *Theme:* Contrasts Transformers with sequential RNNs/LSTMs, highlighting the self-attention and multi-head attention mechanisms.
4.  **Query:** *"What are the main challenges of integrating renewable energy into smart grids?"*
    *   *Source:* `renewable_energy_future.pdf` (Section 4)
    *   *Theme:* Explains intermittency, power imbalances, the role of Battery Energy Storage Systems (BESS), and smart load coordination.
5.  **Query:** *"How does sleep hygiene impact cognitive performance?"*
    *   *Source:* `mental_health_and_sleep.txt` (Section 4)
    *   *Theme:* Outlines guidelines (schedule, sleep environment, avoiding blue light, restricting caffeine/alcohol, exercise).
6.  **Out-of-Context Query:** *"What is the recipe for baking a chocolate chip cookie?"*
    *   *Expected Output:* *"I am sorry, but the provided documents do not contain the answer to your question."* (Demonstrating protection against hallucination).

---

## ⚠️ Known Limitations

1.  **Table and Image Extraction:** The system uses `pypdf` which extracts raw textual streams. It struggles to preserve grid alignment for tabular data and cannot parse visual details from images embedded within PDFs.
2.  **Long-Context Reasoning:** The vector database retrieves the top-$k$ discrete chunks. If a question requires synthesising thematic points spread across 10 pages, retrieving only the top-4 chunks may leave out key parts of the story.
3.  **No Dialogue History (CLI & Single Session):** The current CLI and Streamlit interfaces treat each question as an independent session. The bot does not remember previous questions in the conversation (no multi-turn memory).
