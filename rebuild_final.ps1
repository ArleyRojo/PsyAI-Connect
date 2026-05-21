$base = "C:\Users\Manuel Rojas\Downloads\PsyAI-Connect-main"
$srcRoot = "$base\commits_recuperados"
Set-Location $base

$commits = @(
    @{ sha = "4e9000b"; dt = "2025-05-21T22:52:00-05:00"; msg = "Arreglo responsive acordeon, anadido citas virtuales y presenciales, modificado el sistema de pago al agendar cita"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "1bb2aff"; dt = "2025-05-21T23:00:00-05:00"; msg = "Actualizacion responsive, chat y metricas."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "45fc7cf"; dt = "2025-05-21T23:08:00-05:00"; msg = "Arreglado responsive en moviles, actualizacion sistema de pago, elegir virtual o presencial en cita."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "d3beda6"; dt = "2025-05-21T23:14:00-05:00"; msg = "Delete git"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "df33d4c"; dt = "2025-05-22T15:29:00-05:00"; msg = "Actualizacion responsive, diseno evolucion, redisenado el sistema de pago en agenda de cita, etc."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "87bd17e"; dt = "2025-06-04T01:38:00-05:00"; msg = "Actualizacion: Ya sirve las fotos, rediseno de login y register, ya sirve olvidar contrasena y envia al correo"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "d0501b7"; dt = "2025-06-04T01:52:00-05:00"; msg = "Alineacion fotos"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "b59f97e"; dt = "2025-06-04T05:08:00-05:00"; msg = "Actualizacion: Mejora diseno grafico en algunos apartados, arreglos, etc."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "0c43f6a"; dt = "2025-06-04T05:34:00-05:00"; msg = "Actualizacion respuesta bot, bugs, etc."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "815cb6d"; dt = "2025-06-04T05:43:00-05:00"; msg = "Update setup_install.py"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "a8facee"; dt = "2025-06-04T05:57:00-05:00"; msg = "Update setup_install.py"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "c439f50"; dt = "2025-06-04T06:04:00-05:00"; msg = "Update setup_install.py"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "4b29c78"; dt = "2025-06-04T16:04:00-05:00"; msg = "Update responsive-patient.css"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "3117409"; dt = "2025-06-04T16:05:00-05:00"; msg = "Update agenda-quotes.html"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "7b1e550"; dt = "2025-06-04T21:24:00-05:00"; msg = "Add initial README with project name"; author = "ArleyRojo"; email = "arleyandresrojomarin07@gmail.com" }
    @{ sha = "9982e62"; dt = "2025-06-04T21:49:00-05:00"; msg = "Update README.md, apis rest, technologies, etc."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "804bb69"; dt = "2025-06-04T21:50:00-05:00"; msg = "BLACKTEME AGENDA DE CITAS"; author = "Emmanuel"; email = "zapataarenasemanuel7@gmail.com" }
    @{ sha = "ce4b6b8"; dt = "2025-06-04T21:52:00-05:00"; msg = "Create README.md, apis rest, etc."; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "89afc93"; dt = "2025-06-04T21:54:00-05:00"; msg = "Update README.md"; author = "ManuelRojas22"; email = "manuelalejandro.rojasquintero2@gmail.com" }
    @{ sha = "07cf672"; dt = "2025-06-07T03:16:00-05:00"; msg = "Historia clinica pro y paciente: diseno premium, backend documentos, tablas DB"; author = "ArleyRojo"; email = "arleyandresrojomarin07@gmail.com" }
    @{ sha = "a9252b6"; dt = "2025-06-07T07:21:00-05:00"; msg = "Admin dashboard: graficas Chart.js, SSE en vivo, rendimiento servidor, skeletons, filtros, export CSV, usuarios online reales, dot de chat funcional + fix imports criticos"; author = "Emmanuel"; email = "zapataarenasemanuel7@gmail.com" }
    @{ sha = "adb5291"; dt = "2025-06-08T16:17:00-05:00"; msg = "Actualizacion dashboards paciente/profesional, repositorio y servicio professional"; author = "Emmanuel"; email = "zapataarenasemanuel7@gmail.com" }
)

# Create orphan branch
git checkout --orphan nuevo_main 2>&1 | Out-Null
git rm -rf --cached . 2>&1 | Out-Null

# Remove all working files except commits_recuperados and .git
Get-ChildItem -Path $base -File -Recurse | Where-Object { $_.FullName -notmatch '\\.git\\' -and $_.FullName -notmatch '\\commits_recuperados\\' -and $_.Extension -ne '.ps1' } | Remove-Item -Force
Get-ChildItem -Path $base -Directory | Where-Object { $_.Name -ne '.git' -and $_.Name -ne 'commits_recuperados' -and $_.Name -ne '.opencode' } | Remove-Item -Recurse -Force

$folders = Get-ChildItem -Path $srcRoot -Directory | Sort-Object Name
$total = $folders.Count

for ($i = 0; $i -lt $total; $i++) {
    $f = $folders[$i]
    $c = $commits[$i]
    $sha = $c.sha
    $dt = $c.dt
    $msg = $c.msg
    $author = $c.author
    $email = $c.email

    Write-Host "[$($i+1)/$total] $sha - ${author}: ${msg}"

    # Copy snapshot files
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

    # Clean working tree for next iteration
    Get-ChildItem -Path $base -File -Recurse | Where-Object { $_.FullName -notmatch '\\.git\\' -and $_.FullName -notmatch '\\commits_recuperados\\' -and $_.Extension -ne '.ps1' } | Remove-Item -Force
    Get-ChildItem -Path $base -Directory | Where-Object { $_.Name -ne '.git' -and $_.Name -ne 'commits_recuperados' -and $_.Name -ne '.opencode' } | Remove-Item -Recurse -Force
}

# Add Arreglar modo oscuro as commit 23
Write-Host "[23/23] - ManuelRojas22: Arreglar modo oscuro"
# Restore files from HEAD (adb5291 tree) into working tree
git checkout HEAD -- . 2>&1 | Out-Null
git add -A 2>&1 | Out-Null
$env:GIT_AUTHOR_NAME = "ManuelRojas22"
$env:GIT_AUTHOR_EMAIL = "manuelalejandro.rojasquintero2@gmail.com"
$env:GIT_COMMITTER_NAME = "ManuelRojas22"
$env:GIT_COMMITTER_EMAIL = "manuelalejandro.rojasquintero2@gmail.com"
$env:GIT_AUTHOR_DATE = "2026-06-09T14:25:21-05:00"
$env:GIT_COMMITTER_DATE = "2026-06-09T14:25:21-05:00"
git commit -m "Arreglar modo oscuro" 2>&1 | Out-Null

Write-Host "`n=== COMPLETADO ==="
git log --oneline --format="%h %an <%ae> %ad %s" --date=short
