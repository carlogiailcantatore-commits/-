#requires -Version 5
# Create a workspace-local venv and install deps for the bilingual-literature skill.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = $env:BILINGUAL_VENV
if (-not $venv) { $venv = Join-Path (Get-Location) '.bilingual-venv' }
$py = Join-Path $venv 'Scripts\python.exe'
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
  & $uv.Source venv $venv
  & $uv.Source pip install --python $py python-docx lxml pymupdf openpyxl
} else {
  if (-not (Test-Path $py)) { python -m venv $venv }
  & $py -m pip install --upgrade pip
  & $py -m pip install python-docx lxml pymupdf openpyxl
}
Write-Output ('VENV ' + $py)
Write-Output 'Run from a writable workspace; vocabulary DB lives under ./vocab/vocab.db by default.'
