# How to Ingest Documents for RAG

The **Retrieval-Augmented Generation (RAG)** engine allows the BEIET bot to read your course materials and ground its answers in your official bibliography.

You can add new documents at any point during the semester. The system is designed to be fully decoupled from the bot's runtime code. 

## Where to put your files

The bot looks for PDF files in specific local directories that match your subject names. These folders are located in the `data/` directory at the root of the project.

- For **Métodos de Optimización**: `data/optimizacion/`
- For **Mercados Eléctricos**: `data/mercados/`

### File Guidelines
1. Currently, the system supports **`.pdf`** files.
2. Ensure the PDFs contain text (not just scanned images). If you have scanned PDFs, run an OCR tool on them before placing them in the folder.
3. Name your files clearly, using underscores instead of spaces if possible (e.g., `Unidad_1_Flujo_Optimo.pdf`). The ingestion script uses the filename to categorize "Topics" inside the database.

---

## Running the Ingestion Script

Once you've placed your new PDFs into the correct folder:

1. Open your terminal in the project's root directory (`beiet-tutor-bot/`).
2. Activate your virtual environment: 
   ```bash
   source venv/bin/activate
   ```
3. Run the Python module for the ingestion script, passing the `--subject` flag and the path to the folder:

   **Para Optimización:**
   ```bash
   python -m scripts.ingest_documents --subject optimizacion --path data/optimizacion/
   ```

   **Para Mercados Eléctricos:**
   ```bash
   python -m scripts.ingest_documents --subject mercados --path data/mercados/
   ```

### What happens in the background?
The ingestor uses the **Gemini 2.5 Flash** Embedding API to convert the text into numerical vectors. 
- It will ignore files that have already been uploaded.
- It will chunk large chapters into 800-word pieces so the bot can search them quickly.
- A progress bar will show you the exact page it is processing.

Once the terminal says `Finished processing.`, the bot will automatically start pulling from those new documents the next time a student asks a related question. You don't even need to restart the Discord Bot!
