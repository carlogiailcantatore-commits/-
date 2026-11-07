param(
  [Parameter(Mandatory=$true)][ValidateSet('libreoffice','tesseract')][string]$Tool,
  [switch]$Authorized
)
if (-not $Authorized) {
  Write-Output 'AUTHORIZATION_REQUIRED: 用户明确同意后才能联网下载/安装'
  exit 2
}
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $winget) {
  Write-Output 'WINGET_MISSING: 请手动下载安装'
  if ($Tool -eq 'libreoffice') { Write-Output 'https://www.libreoffice.org/download/' }
  else { Write-Output 'https://github.com/UB-Mannheim/tesseract/wiki' }
  exit 3
}
if ($Tool -eq 'libreoffice') {
  & winget install --id TheDocumentFoundation.LibreOffice -e --accept-source-agreements --accept-package-agreements
} else {
  & winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements
}
exit $LASTEXITCODE
