#!/bin/bash

# Script to clean Python project cache files before distribution
# Run this before sharing your project with others or deploying
# Works for Mac/Linux → Windows distribution

echo "🧹 Cleaning Python cache files for cross-platform distribution..."

# Remove Python cache directories
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
find . -type f -name "*.pyd" -delete 2>/dev/null

# Remove IDE files
rm -rf .vs/ .vscode/ .idea/ .DS_Store .pytest_cache/ .mypy_cache/ 2>/dev/null

# Remove Mac-specific files (important for Mac → Windows)
find . -name ".DS_Store" -delete 2>/dev/null
find . -name "._*" -delete 2>/dev/null  # Mac resource fork files
find . -name ".Spotlight-V100" -exec rm -rf {} + 2>/dev/null
find . -name ".Trashes" -exec rm -rf {} + 2>/dev/null
find . -name ".fseventsd" -exec rm -rf {} + 2>/dev/null

# Remove Linux-specific files
find . -name "*.swp" -delete 2>/dev/null
find . -name "*.swo" -delete 2>/dev/null
find . -name "*~" -delete 2>/dev/null
find . -name ".directory" -delete 2>/dev/null

# Remove Windows files (already created on Windows)
find . -name "Thumbs.db" -delete 2>/dev/null
find . -name "desktop.ini" -delete 2>/dev/null
find . -name "*.lnk" -delete 2>/dev/null

# Remove editor backup files
find . -name "*.bak" -delete 2>/dev/null
find . -name "*.tmp" -delete 2>/dev/null
find . -name "*.log" -delete 2>/dev/null

# Remove Python virtual environment caches (if any exist)
find . -type d -name "venv" -prune -o -type d -name "env" -prune -o -type d -name ".venv" -prune

echo "✅ Cleanup complete!"
echo ""
echo "📋 Files that have been removed:"
echo "   ✓ Python __pycache__ directories"
echo "   ✓ Compiled .pyc, .pyo, .pyd files"
echo "   ✓ IDE config folders (.vs, .vscode, .idea)"
echo "   ✓ Mac files: .DS_Store, ._* (resource forks), .Spotlight-V100"
echo "   ✓ Linux files: .directory, swap files (*.swp, *.swo)"
echo "   ✓ Windows files: Thumbs.db, desktop.ini, *.lnk"
echo "   ✓ Editor backups: *.bak, *.tmp, *.log"
echo ""
echo "📁 Optional: Consider removing these before distribution:"
echo "   - chroma_db/ (ChromaDB data)"
echo "   - chromadb/ (ChromaDB data)"
echo "   - user_data/ (User-specific data)"
echo "   - faiss_index/ (Unless pre-built index needed)"
echo ""
echo "🔧 Mac/Linux → Windows Notes:"
echo "   • All platform-specific cache files have been removed"
echo "   • Python bytecode will be regenerated on Windows"
echo "   • Indexes can be rebuilt: python build_faiss_index.py"
echo "   • Windows user should run: pip install -r requirements.txt"

