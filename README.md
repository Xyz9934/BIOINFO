# BioExplorer

Current app entry:

- `python main.py`

Current structure:

- `main.py`
- `ui/dashboard.kv`
- `ui/widgets.kv`
- `core/dna_analyzer.py`
- `core/fasta_parser.py`
- `core/ncbi_api.py`
- `core/protein_tools.py`
- `database/storage.py`
- `database/app.db`
- `assets/nucleotide_pie.png`

Main features now:

- DNA / FASTA analysis
- GC %
- reverse complement
- protein translation
- molecular weight
- nucleotide pie chart
- local disease / gene search
- live NCBI gene + protein info
- SQLite search history
- saved sequences
- bookmarked genes
- KivyMD dashboard UI

Run:

```powershell
cd D:\BIOINFO
python main.py
```

If packages are missing:

```powershell
pip install -r requirements.txt
```
