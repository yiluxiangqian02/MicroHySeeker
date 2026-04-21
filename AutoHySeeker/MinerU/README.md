# MinerU Batch PDF Parsing

This directory contains a standalone Python script that uses the official MinerU API to parse local PDF files in batch and extract each result into its own folder.

## Features

- Reads `MINERU_API_TOKEN` from `MinerU/.env`
- Scans multiple PDFs under `input/`, with recursive mode enabled by default
- Calls official `/api/v4/file-urls/batch` to get signed upload URLs
- Uploads local PDFs and polls `/api/v4/extract-results/batch/{batch_id}`
- Downloads `full_zip_url` and extracts to `output/<paper_name>/`
- Copies `full.md` to `output/<paper_name>/<paper_name>.md`
- Writes a batch manifest to `output/manifest.json`

## Usage

1. Fill `MINERU_API_TOKEN` in `MinerU/.env`
2. Put PDFs into `MinerU/input/`
3. Run:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU
..\.venv\Scripts\python.exe .\parse_pdfs.py
```

Or use the batch wrapper with automatic logging:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU
.\run_parse.bat
```

`run_parse.bat` writes logs to `MinerU/logs/run_parse_YYYYMMDD_HHMMSS.log` and prints the last 40 log lines after exit.

To parse only specific files:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU
..\.venv\Scripts\python.exe .\parse_pdfs.py --files .\input\a.pdf .\input\b.pdf
```

## Output Layout

```text
MinerU/
  input/
  output/
    paper_a/
      full.md
      paper_a.md
      ...
    paper_b/
      full.md
      paper_b.md
      ...
    manifest.json
```

## Notes

- Default model is `vlm`.
- One API batch handles up to 200 files; the script automatically splits larger sets.
- If two PDFs share the same filename, the script avoids name collisions for both upload names and output directories.
- If you see `requests.exceptions.ProxyError` during upload/download, set `MINERU_USE_ENV_PROXY=false` in `MinerU/.env` (default is false).
