$base = "C:\Users\Manuel Rojas\Downloads\PsyAI-Connect-main"
$outDir = "$base\commits_recuperados"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Set-Location $base

$shas = @("4e9000b5daa5aafc33b755212edbeaae0894c4b9","1bb2aff2de9aedd1d8e60e393296db1138423e85","45fc7cff48660b47636303550400ffa04cff67a7","d3beda6b72771eb7c2517c1b4c4d98fcdc39e605","df33d4c3274b685d706f95eb78405f1a12d37c81","87bd17eed40ecee9759394fcbe83c753cc8b8a93","d0501b7267be93cf7b152ae30b024ee2f5809005","b59f97e4e9ab37698b00bc1b5b12eaffc7023bce","0c43f6ab374f63a8dc2135c17e033b1d6583aa63","815cb6dc9c0ed0e05b94311078873378de3f99ef","a8facee4a931fcb0a1e101b803ac4ee5f43b54a0","c439f50f26b1e3a979748eed92527a808bc74a01","4b29c7817a27922741c6a33b94f23a74567fc0e9","3117409ddc9cb6c48440e15f0929d5ccf36d0f4a","7b1e550003ce20450d89f1d297e7f1fbbadf1c56","9982e62ff6b475dee1325bc8fd45ab7caef4e64c","804bb69475f91affe2ba3b4445696b3f7e6179e4","ce4b6b8be60e0e509adb58753e967bb8de7a6cde","89afc93aa615b4ceb66f9dc35e8c73ae0bc5a943","07cf672975678c661ea5bc7f07c378593cd02a49","a9252b60d36de400aac4f5523f360df90ad97d1b","adb5291581c2f431215441f9a75960fa412e619f")
$dates = @("2025-05-21_22-52","2025-05-21_23-00","2025-05-21_23-08","2025-05-21_23-14","2025-05-22_15-29","2025-06-04_01-38","2025-06-04_01-52","2025-06-04_05-08","2025-06-04_05-34","2025-06-04_05-43","2025-06-04_05-57","2025-06-04_06-04","2025-06-04_16-04","2025-06-04_16-05","2025-06-04_21-24","2025-06-04_21-49","2025-06-04_21-50","2025-06-04_21-52","2025-06-04_21-54","2025-06-07_03-16","2025-06-07_07-21","2025-06-08_16-17")
$fullDates = @("2025-05-21T22:52:00-05:00","2025-05-21T23:00:00-05:00","2025-05-21T23:08:00-05:00","2025-05-21T23:14:00-05:00","2025-05-22T15:29:00-05:00","2025-06-04T01:38:00-05:00","2025-06-04T01:52:00-05:00","2025-06-04T05:08:00-05:00","2025-06-04T05:34:00-05:00","2025-06-04T05:43:00-05:00","2025-06-04T05:57:00-05:00","2025-06-04T06:04:00-05:00","2025-06-04T16:04:00-05:00","2025-06-04T16:05:00-05:00","2025-06-04T21:24:00-05:00","2025-06-04T21:49:00-05:00","2025-06-04T21:50:00-05:00","2025-06-04T21:52:00-05:00","2025-06-04T21:54:00-05:00","2025-06-07T03:16:00-05:00","2025-06-07T07:21:00-05:00","2025-06-08T16:17:00-05:00")
$msgs = @("Arreglo responsive acordeon, anadido citas virtuales y presenciales, modificado el sistema de pago al agendar cita","Actualizacion responsive, chat y metricas.","Arreglado responsive en moviles, actualizacion sistema de pago, elegir virtual o presencial en cita.","Delete git","Actualizacion responsive, diseno evolucion, redisenado el sistema de pago en agenda de cita, etc.","Actualizacion: Ya sirve las fotos, rediseno de login y register, ya sirve olvidar contrasena y envia al correo","Alineacion fotos","Actualizacion: Mejora diseno grafico en algunos apartados, arreglos, etc.","Actualizacion respuesta bot, bugs, etc.","Update setup_install.py","Update setup_install.py","Update setup_install.py","Update responsive-patient.css","Update agenda-quotes.html","Add initial README with project name","Update README.md, apis rest, technologies, etc.","BLACKTEME AGENDA DE CITAS","Create README.md, apis rest, etc.","Update README.md","Historia clinica pro y paciente: diseno premium, backend documentos, tablas DB","Admin dashboard: graficas Chart.js, SSE en vivo, rendimiento servidor, skeletons, filtros, export CSV, usuarios online reales, dot de chat funcional + fix imports criticos","Actualizacion dashboards paciente/profesional, repositorio y servicio professional")
$authors = @("ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ManuelRojas22","ArleyRojo","ManuelRojas22","Emmanuel","ManuelRojas22","ManuelRojas22","ArleyRojo","Emmanuel","Emmanuel")
$emails = @("manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","arleyandresrojomarin07@gmail.com","manuelalejandro.rojasquintero2@gmail.com","zapataarenasemanuel7@gmail.com","manuelalejandro.rojasquintero2@gmail.com","manuelalejandro.rojasquintero2@gmail.com","arleyandresrojomarin07@gmail.com","zapataarenasemanuel7@gmail.com","zapataarenasemanuel7@gmail.com")

# PHASE 1: Download
Write-Host "=== FASE 1: Descargar ZIPS faltantes ==="
$total = $shas.Count
for ($i = 0; $i -lt $total; $i++) {
    $sha = $shas[$i]
    $shortSha = $sha.Substring(0, 7)
    $folderName = "$($dates[$i])_$shortSha"
    $fp = "$outDir\$folderName"
    if (Test-Path $fp) { Write-Host "[$($i+1)/$total] $shortSha - OK (cache)" }
    else {
        Write-Host "[$($i+1)/$total] Descargando $shortSha ..."
        $zip = "$env:TEMP\$shortSha.zip"
        try {
            Invoke-WebRequest -Uri "https://api.github.com/repos/ArleyRojo/PsyAI-Connect/zipball/$sha" -OutFile $zip -UseBasicParsing -ErrorAction Stop
            New-Item -ItemType Directory -Path $fp -Force | Out-Null
            Expand-Archive -Path $zip -DestinationPath $fp -Force
            $inner = Get-ChildItem -Path $fp -Directory | Select-Object -First 1
            if ($inner) {
                Get-ChildItem -Path $inner.FullName -Recurse | ForEach-Object {
                    $rel = $_.FullName.Substring($inner.FullName.Length + 1)
                    $dest = Join-Path $fp $rel
                    if ($_.PSIsContainer) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
                    else { $dir = Split-Path $dest -Parent; if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }; Copy-Item $_.FullName $dest -Force }
                }
                Remove-Item -Recurse -Force $inner.FullName
            }
            Remove-Item -Force $zip
            Write-Host "  OK"
        } catch { Write-Host "  FAILED: $_" }
    }
}

# PHASE 2: Rebuild
Write-Host "`n=== FASE 2: Reconstruir historia ==="
git branch -D main_rebuild 2>&1 | Out-Null
git checkout --orphan main_rebuild 2>&1 | Out-Null
git rm -rf --cached . 2>&1 | Out-Null
Get-ChildItem -Path $base -File -Recurse | Where-Object { $_.FullName -notmatch '\\.git\\' -and $_.FullName -notmatch '\\commits_recuperados\\' -and $_.Extension -ne '.ps1' } | Remove-Item -Force
Get-ChildItem -Path $base -Directory | Where-Object { $_.Name -ne '.git' -and $_.Name -ne 'commits_recuperados' -and $_.Name -ne '.opencode' } | Remove-Item -Recurse -Force

$folders = Get-ChildItem -Path $outDir -Directory | Sort-Object Name
for ($i = 0; $i -lt $folders.Count; $i++) {
    $f = $folders[$i]
    $sha = $shas[$i]
    $shortSha = $sha.Substring(0,7)
    $dt = $fullDates[$i]
    $msg = $msgs[$i]
    $author = $authors[$i]
    $email = $emails[$i]
    Write-Host "[$($i+1)/$($folders.Count)] $shortSha - ${author}: ${msg}"
    Get-ChildItem -Path $f.FullName -File -Recurse | ForEach-Object {
        $rel = $_.FullName.Substring($f.FullName.Length + 1)
        $dest = Join-Path $base $rel
        $dir = Split-Path $dest -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item $_.FullName $dest -Force
    }
    git add -A 2>&1 | Out-Null
    $env:GIT_AUTHOR_NAME = $author
    $env:GIT_AUTHOR_EMAIL = $email
    $env:GIT_COMMITTER_NAME = $author
    $env:GIT_COMMITTER_EMAIL = $email
    $env:GIT_AUTHOR_DATE = $dt
    $env:GIT_COMMITTER_DATE = $dt
    git commit -m $msg 2>&1 | Out-Null
    # Clean for next iteration (protecting commits_recuperados)
    Get-ChildItem -Path $base -File -Recurse | Where-Object { $_.FullName -notmatch '\\.git\\' -and $_.FullName -notmatch '\\commits_recuperados\\' -and $_.Extension -ne '.ps1' } | Remove-Item -Force
    Get-ChildItem -Path $base -Directory | Where-Object { $_.Name -ne '.git' -and $_.Name -ne 'commits_recuperados' -and $_.Name -ne '.opencode' } | Remove-Item -Recurse -Force
}

# Commit 23: Arreglar modo oscuro
Write-Host "[23/23] - ManuelRojas22: Arreglar modo oscuro"
git checkout HEAD -- . 2>&1 | Out-Null
git add -A 2>&1 | Out-Null
$env:GIT_AUTHOR_NAME = "ManuelRojas22"
$env:GIT_AUTHOR_EMAIL = "manuelalejandro.rojasquintero2@gmail.com"
$env:GIT_COMMITTER_NAME = "ManuelRojas22"
$env:GIT_COMMITTER_EMAIL = "manuelalejandro.rojasquintero2@gmail.com"
$env:GIT_AUTHOR_DATE = "2026-06-09T14:25:21-05:00"
$env:GIT_COMMITTER_DATE = "2026-06-09T14:25:21-05:00"
git commit -m "Arreglar modo oscuro" 2>&1 | Out-Null

Write-Host "`n=== VERIFICACION ==="
git log --format="%h %an <%ae> %ad %s" --date=short
Write-Host "`nTotal commits:"
git rev-list --count HEAD
