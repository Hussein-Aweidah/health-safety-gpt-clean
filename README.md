# Health & Safety GPT

## Distribution & Setup

### For New Users/Devices

When sharing this project or running on a new device:

1. **Clean cache files** (IMPORTANT for cross-platform distribution):
   
   **On Mac/Linux** (before sharing with Windows):
   ```bash
   ./cleanup_for_distribution.sh
   ```
   
   **On Windows** (before sharing with Mac/Linux):
   ```cmd
   cleanup_for_distribution.bat
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (create `.env` file):
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. **Build the FAISS index** (if needed):
   ```bash
   python build_faiss_index.py
   ```

### Cross-Platform Distribution

#### Mac/Linux → Windows Checklist:
✓ Run `cleanup_for_distribution.sh` to remove:
  - `__pycache__/` directories (Python 3.9/3.10/3.11 bytecode)
  - `.DS_Store` files (Mac Finder cache)
  - `._*` files (Mac resource forks)
  - `.Spotlight-V100`, `.Trashes`, `.fseventsd` (Mac system files)
  - Linux swap files (`*.swp`, `*.swo`)
  - IDE configuration folders

#### Windows → Mac/Linux Checklist:
✓ Run `cleanup_for_distribution.bat` to remove:
  - `__pycache__/` directories (Windows Python bytecode)
  - `Thumbs.db` files (Windows thumbnail cache)
  - `desktop.ini` files (Windows folder configuration)
  - IDE configuration folders

### Cache Files (Auto-Removed)

The following cache files are automatically cleaned:
- `__pycache__/` - Python bytecode cache (platform-specific)
- `.vs/`, `.vscode/`, `.idea/` - IDE configuration
- `.DS_Store`, `Thumbs.db` - OS cache files
- `*.pyc`, `*.pyo`, `*.pyd` - Compiled Python files
- Platform-specific system files (`.Spotlight-V100`, etc.)

### Data Files

These directories contain project data:
- `chroma_db/` - ChromaDB embeddings
- `chromadb/` - ChromaDB data
- `faiss_index/` - FAISS vector index
- `user_data/` - User sessions and history
- `docs/` - Source documents

To rebuild from scratch, delete the above directories and run `build_faiss_index.py`.
