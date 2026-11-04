#Requires -Version 5.1
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
    Crea o completa il laboratorio di CTRL+ALT REVENGE su questo PC.

.DESCRIPTION
    Il laboratorio sta in $env:CAR_LAB oppure, se la variabile non c'è, in %USERPROFILE%\ctrlaltrevenge-lab
    (fuori da OneDrive). Lo script fa dieci passi:
       1. controlla git con Git Bash, Python 3.14 (comando py) e uv;
       2. Godot 4.7.2, 3. Blender 4.5.15, 4. FFmpeg 9.0.2: li scarica dai siti ufficiali e ne verifica
          l'hash con i checksum ufficiali;
       5. crea il venv di Python con i pacchetti fissati (hash di PyPI);
       6. installa PyMusicLooper 3.6.0 (hash di PyPI);
       7. copia dalla cartella privata condivisa in OneDrive: sources, music (solo la musica segnaposto),
          note-private, suno (solo i testi), ricerca-2026-11-03;
       8. installa le sei skill di Godot per Claude Code;
       9. scrive Gioca.bat con i percorsi di questo PC;
      10. importa il progetto Godot e lancia i test: run_tests.gd deve stampare DONE.
    Si può rilanciare quando si vuole: salta ciò che è già a posto. Versioni, URL e hash stanno in
    tools\setup\laboratorio.json. Non servono i diritti di amministratore.
    I file del laboratorio che arrivano dalla cartella condivisa (note, prompt, modelli, ricerca) non vengono mai
    sostituiti con file più vecchi; quelli che una copia più nuova sostituisce finiscono prima in backup\<data>.
    music\ non si tocca se contiene brani veri o file che non sono la musica segnaposto nota.

.PARAMETER Forza
    Rifà da capo le cose che si possono ricreare: reinstalla Godot, Blender e FFmpeg (riusa gli archivi già
    scaricati, se l'hash torna), ricrea i due ambienti Python (i pacchetti aggiunti a mano si perdono: l'elenco di
    quelli che c'erano finisce in logs\), ricopia le skill e riscrive Gioca.bat.
    Non vale per il passo 7: dalla cartella condivisa arrivano sempre e solo i file più nuovi.

.PARAMETER InstallaMancanti
    Se mancano git, Python 3.14 o uv, li installa con winget, solo per questo utente.
    Senza questa opzione lo script si ferma e spiega come installarli.

.PARAMETER ProgettoGodot
    Cartella del progetto Godot (con project.godot) su cui fare la verifica finale.
    Predefinita: la cartella game del repo.

.PARAMETER Solo
    Fa solo i passi indicati, per esempio  -Solo godot,verifica
    Nomi dei passi: prerequisiti, godot, blender, ffmpeg, venv, pymusiclooper, condivisi, skill, gioca, verifica.

.PARAMETER SaltaVerifica
    Non fa la verifica finale (importazione e test).

.PARAMETER Laboratorio
    Cartella del laboratorio. Vince su $env:CAR_LAB.

.PARAMETER Condiviso
    Cartella privata condivisa. Vince su $env:CAR_CONDIVISO; se mancano tutte e due è la cartella
    ctrlaltrevenge-lab-condiviso accanto al repo.

.PARAMETER CartellaSkill
    Dove installare le skill di Claude Code. Vince su $env:CAR_SKILLS_DIR; predefinita %USERPROFILE%\.claude\skills.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\setup\prepara_laboratorio.ps1"

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\setup\prepara_laboratorio.ps1" -InstallaMancanti
#>
[CmdletBinding()]
param(
    [switch]$Forza,
    [switch]$InstallaMancanti,
    [string]$ProgettoGodot = '',
    [string[]]$Solo = @(),
    [switch]$SaltaVerifica,
    [string]$Laboratorio = '',
    [string]$Condiviso = '',
    [string]$CartellaSkill = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comune.ps1')

$PassiValidi = @('prerequisiti', 'godot', 'blender', 'ffmpeg', 'venv', 'pymusiclooper', 'condivisi', 'skill', 'gioca', 'verifica')
# Con "powershell -File" una lista come "godot,verifica" arriva come una stringa sola: la divido qui.
$Solo = @($Solo | ForEach-Object { $_ -split '[,;\s]+' } | Where-Object { $_ } | ForEach-Object { $_.ToLowerInvariant() })
foreach ($passo in $Solo) {
    if ($PassiValidi -notcontains $passo) {
        Write-Host "Passo sconosciuto in -Solo: '$passo'. Passi validi: $($PassiValidi -join ', ')." -ForegroundColor Red
        exit 2
    }
}

$Script:Python = $null
$Script:Uv = $null
$Script:InfoCondivisoMostrata = $false
$Script:Esiti = New-Object System.Collections.Generic.List[object]

# ------------------------------------------------------------------ passi e riepilogo

function Test-Passo([string]$Nome) {
    if ($Nome -eq 'verifica' -and $SaltaVerifica) { return $false }
    if ($Solo.Count -eq 0) { return $true }
    return ($Solo -contains $Nome)
}

function Add-Esito([string]$Passo, [string]$Esito) {
    $Script:Esiti.Add([pscustomobject]@{ Passo = $Passo; Esito = $Esito })
}

function Show-Riepilogo {
    if ($Script:Esiti.Count -eq 0) { return }
    Write-Titolo 'Riepilogo'
    foreach ($e in $Script:Esiti) {
        $colore = 'Green'
        if ($e.Esito -like 'ERRORE*') { $colore = 'Red' }
        elseif ($e.Esito -like 'non fatto*') { $colore = 'Yellow' }
        elseif ($e.Esito -like 'saltato*') { $colore = 'DarkGray' }
        Write-Host ('  {0,-14} {1}' -f $e.Esito, $e.Passo) -ForegroundColor $colore
    }
}

function Get-StrumentoDaId([string]$Id) {
    $s = @($Manifesto.strumenti | Where-Object { $_.id -eq $Id }) | Select-Object -First 1
    if ($null -eq $s) { Stop-Errore "Nel manifesto manca lo strumento '$Id'." @('Ripristina tools/setup/laboratorio.json con git.') }
    return $s
}

# ------------------------------------------------------------------ download e archivi

function Save-Url([string]$Url, [string]$Destinazione, [switch]$Progresso) {
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if ([System.IO.File]::Exists($curl)) {
        $a = @('--fail', '--location', '--retry', '3', '--retry-delay', '5', '--connect-timeout', '30', '--output', $Destinazione)
        if ($Progresso) { $a += '--progress-bar' } else { $a += @('--silent', '--show-error') }
        $a += $Url
        & $curl @a | Out-Host
        return ($LASTEXITCODE -eq 0)
    }
    $pp = $ProgressPreference
    try {
        $ProgressPreference = 'SilentlyContinue'
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Url -OutFile $Destinazione -UseBasicParsing
        return $true
    } catch {
        Write-Avviso "Download non riuscito: $($_.Exception.Message)"
        return $false
    } finally {
        $ProgressPreference = $pp
    }
}

# Hash di $NomeFile in un file di checksum ufficiale: righe "hash  nome" (anche "hash *nome") o un hash da solo.
function Get-HashDaChecksum([string]$FileChecksum, [string]$NomeFile) {
    $soli = @()
    foreach ($riga in [System.IO.File]::ReadAllLines($FileChecksum)) {
        $t = $riga.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        $parti = @($t -split '\s+', 2)
        if ($parti[0] -notmatch '^([0-9A-Fa-f]{64}|[0-9A-Fa-f]{128})$') { continue }
        if ($parti.Count -eq 1) { $soli += $parti[0]; continue }
        if ($parti[1].Trim().TrimStart('*') -eq $NomeFile) { return $parti[0].ToLowerInvariant() }
    }
    if ($soli.Count -eq 1) { return $soli[0].ToLowerInvariant() }
    return $null
}

# Scarica un archivio (se non c'è già) e ne verifica byte e hash; prima confronta il manifesto con il checksum ufficiale.
function Get-Archivio($D, [string]$Cartella) {
    New-Cartella $Cartella
    $file = Join-Path $Cartella $D.file
    $alg = [string]$D.algoritmo
    $atteso = ([string]$D.hash).ToLowerInvariant()
    $cu = Get-Campo $D 'checksum_ufficiale'
    if ($null -ne $cu) {
        $fileSum = Join-Path $Cartella $cu.file
        Write-Info "Scarico il checksum ufficiale: $($cu.url)"
        if (Save-Url $cu.url $fileSum) {
            $ufficiale = Get-HashDaChecksum $fileSum $D.file
            if (-not $ufficiale) {
                Stop-Errore "Nel checksum ufficiale $($cu.file) non trovo la riga di $($D.file)." @(
                    'Non usare file scaricati a mano: avvisa Claude, forse il manifesto va aggiornato.')
            }
            if ($ufficiale -ne $atteso) {
                Stop-Errore "Il checksum ufficiale di $($D.file) è diverso da quello del manifesto." @(
                    "ufficiale: $ufficiale", "manifesto: $atteso",
                    'Non usare il file e avvisa Claude prima di continuare.')
            }
            Write-Ok "il checksum ufficiale ($alg) coincide con quello del manifesto."
        } else {
            Write-Avviso "Non riesco a scaricare il checksum ufficiale: uso l'hash $alg del manifesto, verificato il $($Manifesto.verificato)."
        }
    }
    if ([System.IO.File]::Exists($file)) {
        Write-Info "Controllo l'hash $alg di $($D.file), già scaricato..."
        if ((Get-Hash $file $alg) -eq $atteso) {
            Write-Ok "$($D.file) è già scaricato e integro."
            return $file
        }
        Write-Avviso "$($D.file) c'è già, ma l'hash non torna: lo riscarico."
        Remove-Item -LiteralPath $file -Force
    }
    $urls = @([string]$D.url)
    $riserva = [string](Get-Campo $D 'url_di_riserva' '')
    if ($riserva) { $urls += $riserva }
    foreach ($u in $urls) {
        Write-Info "Scarico $u ($(Format-Dimensione ([double]$D.byte)))..."
        $parziale = "$file.part"
        if ([System.IO.File]::Exists($parziale)) { Remove-Item -LiteralPath $parziale -Force }
        if (-not (Save-Url $u $parziale -Progresso)) {
            Write-Avviso 'Download non riuscito.'
            continue
        }
        $dim = (Get-Item -LiteralPath $parziale).Length
        if ($dim -ne [int64]$D.byte) {
            Write-Avviso "Il file scaricato è di $dim byte invece di $($D.byte): lo scarto."
            Remove-Item -LiteralPath $parziale -Force
            continue
        }
        Write-Info "Controllo l'hash $alg..."
        if ((Get-Hash $parziale $alg) -ne $atteso) {
            Write-Avviso "L'hash $alg non è quello atteso: scarto il file."
            Remove-Item -LiteralPath $parziale -Force
            continue
        }
        Move-Item -LiteralPath $parziale -Destination $file -Force
        Write-Ok "scaricato, hash $alg verificato."
        return $file
    }
    Stop-Errore "Non sono riuscito a scaricare $($D.file) con l'hash giusto." @(
        'Controlla la connessione a Internet e rilancia lo script: riparte da qui.',
        'Se l''hash continua a non tornare, non usare il file e avvisa Claude.')
}

# Estrae uno zip (tutto, o solo i file in $Estrai) togliendo la cartella radice $Radice.
# Estrae prima in "<destinazione>.nuovo", poi sposta: un'estrazione interrotta non rovina l'installazione.
function Expand-Archivio {
    param([string]$Zip, [string]$Destinazione, [string]$Radice = '', [string[]]$Estrai = @())
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tmp = "$Destinazione.nuovo"
    if ([System.IO.Directory]::Exists($tmp)) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    New-Cartella $tmp
    $tmpPieno = [System.IO.Path]::GetFullPath($tmp).TrimEnd('\') + '\'
    $estratti = 0
    Write-Info "Estraggo $(Split-Path -Leaf $Zip)..."
    $archivio = [System.IO.Compression.ZipFile]::OpenRead($Zip)
    try {
        foreach ($voce in $archivio.Entries) {
            $nome = $voce.FullName -replace '\\', '/'
            if ($Radice) {
                if (-not $nome.StartsWith("$Radice/")) { continue }
                $nome = $nome.Substring($Radice.Length + 1)
            }
            if (-not $nome) { continue }
            if ($Estrai.Count -gt 0 -and ($Estrai -notcontains $nome)) { continue }
            $bersaglio = [System.IO.Path]::GetFullPath((Join-Path $tmp ($nome -replace '/', '\')))
            if (-not $bersaglio.StartsWith($tmpPieno, [System.StringComparison]::OrdinalIgnoreCase)) {
                Stop-Errore "L'archivio $Zip contiene un percorso sospetto: $($voce.FullName)." @('Non usare questo archivio: cancellalo e avvisa Claude.')
            }
            if ($nome.EndsWith('/')) { New-Cartella $bersaglio; continue }
            New-Cartella (Split-Path $bersaglio -Parent)
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($voce, $bersaglio, $true)
            $estratti++
        }
    } finally {
        $archivio.Dispose()
    }
    if ($Estrai.Count -gt 0 -and $estratti -ne $Estrai.Count) {
        Stop-Errore "Nell'archivio $Zip ho trovato $estratti file su $($Estrai.Count) attesi." @('Avvisa Claude: forse il manifesto va aggiornato.')
    }
    if ($estratti -eq 0) { Stop-Errore "L'archivio $Zip non contiene i file attesi." @('Avvisa Claude: forse il manifesto va aggiornato.') }
    if (-not [System.IO.Directory]::Exists($Destinazione)) {
        New-Cartella (Split-Path $Destinazione -Parent)
        [System.IO.Directory]::Move($tmp, $Destinazione)
    } else {
        Write-Info "Sostituisco in $Destinazione i file dell'archivio; gli altri file della cartella restano dove sono..."
        # Get-OpzioniUguali (/IS /IT /IM): sostituisce anche i file con la stessa data e la stessa dimensione
        # ma un contenuto diverso, che altrimenti robocopy salterebbe.
        $uguali = @(Get-OpzioniUguali)
        & (Get-Robocopy) $tmp $Destinazione /E /MOVE @uguali /R:2 /W:2 /NP /NFL /NDL /NJH /NJS | Out-Host
        if ($LASTEXITCODE -ge 8) {
            Stop-Errore "Non riesco a sostituire i file in $Destinazione (robocopy, codice $LASTEXITCODE)." @(
                'Chiudi Godot, Blender e gli altri programmi del laboratorio, poi rilancia.')
        }
        if ([System.IO.Directory]::Exists($tmp)) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    }
    Write-Ok "$estratti file estratti."
}

# ------------------------------------------------------------------ strumenti (Godot, Blender, FFmpeg, uv di riserva)

# Restituisce $null se lo strumento è a posto, altrimenti il problema trovato.
function Test-Strumento($S, [string]$Dir) {
    foreach ($kv in @($S.file_installati.PSObject.Properties)) {
        $f = Join-Relativo $Dir $kv.Name
        if (-not [System.IO.File]::Exists($f)) { return "manca $($kv.Name)" }
        if ((Get-Hash $f) -ne ([string]$kv.Value).ToLowerInvariant()) { return "$($kv.Name) è diverso dal file ufficiale" }
    }
    $cv = Get-Campo $S 'controllo_versione'
    if ($null -ne $cv) {
        $exe = Join-Relativo $Dir $cv.eseguibile
        $argomenti = @($cv.argomenti)
        $r = Invoke-Programma $exe $argomenti -TimeoutSec 180
        $testo = [string]$r.Uscita + "`n" + [string]$r.Errori
        if ($r.Codice -ne 0 -or -not $testo.Contains([string]$cv.atteso)) {
            return "il controllo della versione ($($cv.eseguibile) $($argomenti -join ' ')) non dice '$($cv.atteso)'"
        }
    }
    return $null
}

# Piccole cose che si sistemano senza reinstallare: file vuoti (come _sc_) e copia del checksum ufficiale.
function Complete-Strumento($S, [string]$Dir, [string]$CartellaDownload) {
    foreach ($vuoto in @(Get-Campo $S 'file_vuoti' @())) {
        $f = Join-Relativo $Dir $vuoto
        if (-not [System.IO.File]::Exists($f)) {
            Write-Testo $f ''
            Write-Info "Creato il file $vuoto."
        }
    }
    if ((Get-Campo $S 'copia_checksum' $false) -eq $true) {
        $cu = $S.download.checksum_ufficiale
        $src = Join-Path $CartellaDownload $cu.file
        $dst = Join-Path $Dir $cu.file
        if ([System.IO.File]::Exists($src) -and -not [System.IO.File]::Exists($dst)) { Copy-Item -LiteralPath $src -Destination $dst }
    }
}

function Install-Strumento($S, [string]$Dir, [string]$CartellaDownload) {
    if (-not $Forza) {
        if ([System.IO.Directory]::Exists($Dir)) {
            Write-Info "Controllo l'installazione in $Dir..."
            $problema = Test-Strumento $S $Dir
            if (-not $problema) {
                Complete-Strumento $S $Dir $CartellaDownload
                $come = 'hash dei file'
                if ($null -ne (Get-Campo $S 'controllo_versione')) { $come = 'hash dei file e versione' }
                Write-Ok "già installato e integro ($come)."
                return 'già a posto'
            }
            Write-Info "Da sistemare: $problema."
        } else {
            Write-Info "Non è ancora installato in $Dir."
        }
    } else {
        Write-Info '-Forza: lo reinstallo.'
    }
    $zip = Get-Archivio $S.download $CartellaDownload
    Expand-Archivio -Zip $zip -Destinazione $Dir -Radice ([string](Get-Campo $S 'radice_zip' '')) -Estrai @(Get-Campo $S 'estrai' @())
    Complete-Strumento $S $Dir $CartellaDownload
    $problema = Test-Strumento $S $Dir
    if ($problema) {
        Stop-Errore "$($S.nome): installato, ma il controllo non torna ($problema)." @(
            'Rilancia lo script con -Forza.',
            'Se si ripete, controlla che l''antivirus non blocchi gli eseguibili e avvisa Claude.')
    }
    Write-Ok "installato e verificato in $Dir."
    return 'installato'
}

function Invoke-Strumento([string]$Id) {
    $s = Get-StrumentoDaId $Id
    $dir = Join-Relativo $Lab $s.cartella
    return (Install-Strumento $s $dir (Join-Path (Join-Path $Lab 'downloads') $s.id))
}

# ------------------------------------------------------------------ prerequisiti

function Update-PathDaRegistro {
    $attuale = @($env:Path -split ';' | Where-Object { $_ })
    $nuovi = @(([Environment]::GetEnvironmentVariable('Path', 'Machine'), [Environment]::GetEnvironmentVariable('Path', 'User')) -join ';' -split ';' | Where-Object { $_ })
    foreach ($p in $nuovi) {
        if ($attuale -notcontains $p) { $env:Path = $env:Path.TrimEnd(';') + ';' + $p; $attuale += $p }
    }
}

function Install-ConWinget([string]$Id, [string[]]$Extra = @()) {
    $w = Get-Command winget.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $w) {
        Write-Avviso 'winget non c''è: installa "Programma di installazione app" (App Installer) dal Microsoft Store.'
        return $false
    }
    $a = @('install', '--id', $Id, '--exact', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity') + $Extra
    Write-Info "winget $($a -join ' ')"
    & $w.Source @a | Out-Host
    $ok = ($LASTEXITCODE -eq 0)
    Update-PathDaRegistro
    if (-not $ok) { Write-Avviso "winget non è riuscito a installare $Id (codice $LASTEXITCODE)." }
    return $ok
}

function Find-Git {
    $c = Get-Command git.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $c) { return $null }
    $r = Invoke-Programma $c.Source @('--version') -TimeoutSec 60
    $v = $null
    if ($r.Uscita -match 'git version (\d+\.\d+(\.\d+)?)') { $v = $Matches[1] }
    return [pscustomobject]@{ Percorso = $c.Source; Versione = $v }
}

function Find-GitBash($Git) {
    $candidati = @()
    if ($env:CLAUDE_CODE_GIT_BASH_PATH) { $candidati += $env:CLAUDE_CODE_GIT_BASH_PATH }
    if ($null -ne $Git) {
        $d = Split-Path $Git.Percorso -Parent
        for ($i = 0; $i -lt 3 -and $d; $i++) {
            $candidati += (Join-Path $d 'bin\bash.exe')
            $d = Split-Path $d -Parent
        }
    }
    if ($env:ProgramFiles) { $candidati += (Join-Path $env:ProgramFiles 'Git\bin\bash.exe') }
    if ($env:LOCALAPPDATA) { $candidati += (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe') }
    foreach ($b in $candidati) { if ($b -and [System.IO.File]::Exists($b)) { return $b } }
    return $null
}

function Find-Python314 {
    $c = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $c) { return [pscustomobject]@{ Py = $null; Exe = $null; Versione = $null } }
    $codice = "import sys; print('PYEXE=' + sys.executable); print('PYVER=%d.%d.%d' % sys.version_info[:3])"
    $r = Invoke-Programma $c.Source @('-3.14', '-I', '-c', $codice) -TimeoutSec 120 -Ambiente @{ PYTHONUTF8 = '1' }
    $exe = $null
    $ver = $null
    foreach ($riga in ([string]$r.Uscita -split "`r?`n")) {
        if ($riga -like 'PYEXE=*') { $exe = $riga.Substring(6).Trim() }
        if ($riga -like 'PYVER=*') { $ver = $riga.Substring(6).Trim() }
    }
    if ($r.Codice -ne 0 -or -not $exe -or -not $ver -or -not $ver.StartsWith('3.14.') -or -not [System.IO.File]::Exists($exe)) {
        $exe = $null
        $ver = $null
    }
    return [pscustomobject]@{ Py = $c.Source; Exe = $exe; Versione = $ver }
}

function Find-Uv {
    $candidati = @()
    $c = Get-Command uv.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $c) { $candidati += $c.Source }
    if ($env:LOCALAPPDATA) { $candidati += (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\uv.exe') }
    $candidati += (Join-Path $HOME '.local\bin\uv.exe')
    $candidati += (Join-Path (Join-Relativo $Lab $Manifesto.prerequisiti.uv.cartella_di_riserva) 'uv.exe')
    foreach ($u in $candidati) {
        if ($u -and [System.IO.File]::Exists($u)) {
            $r = Invoke-Programma $u @('--version') -TimeoutSec 60
            if ($r.Codice -eq 0 -and $r.Uscita -match 'uv (\d+\.\d+\.\d+)') {
                return [pscustomobject]@{ Percorso = $u; Versione = $Matches[1] }
            }
        }
    }
    return $null
}

function Get-Python([switch]$Installa) {
    if ($null -ne $Script:Python) { return $Script:Python }
    $pr = $Manifesto.prerequisiti.python
    $p = Find-Python314
    if (-not $p.Exe -and $Installa) {
        if (-not $p.Py) {
            Write-Info 'Il comando py manca: installo il Python install manager con winget...'
            [void](Install-ConWinget $pr.winget @())
            $p = Find-Python314
        }
        if ($p.Py -and -not $p.Exe) {
            $argomenti = @($pr.installa_runtime)
            Write-Info "Installo Python $($pr.versione): py $($argomenti -join ' ')"
            Write-Info 'Se chiede di abilitare i percorsi lunghi puoi rispondere di no: servirebbero i diritti di amministratore.'
            & $p.Py @argomenti | Out-Host
            $p = Find-Python314
        }
    }
    if ($p.Exe) { $Script:Python = $p }
    return $p
}

function Install-UvDiRiserva {
    $u = $Manifesto.prerequisiti.uv
    $s = [pscustomobject]@{ nome = "uv $($u.versione)"; download = $u.download; radice_zip = ''; file_installati = $u.file_installati }
    [void](Install-Strumento $s (Join-Relativo $Lab $u.cartella_di_riserva) (Join-Path (Join-Path $Lab 'downloads') 'uv'))
}

function Get-Uv([switch]$Installa) {
    if ($null -ne $Script:Uv) { return $Script:Uv }
    $u = Find-Uv
    if ($null -eq $u -and $Installa) {
        $pr = $Manifesto.prerequisiti.uv
        Write-Info "uv manca: lo installo con winget (versione $($pr.versione))..."
        [void](Install-ConWinget $pr.winget @('--version', $pr.versione))
        $u = Find-Uv
        if ($null -eq $u) {
            Write-Info "Con winget non è andata: scarico uv $($pr.versione) ufficiale nel laboratorio..."
            Install-UvDiRiserva
            $u = Find-Uv
        }
    }
    if ($null -ne $u) { $Script:Uv = $u }
    return $u
}

function Get-PythonPronto {
    $p = Get-Python
    if (-not $p.Exe) {
        Stop-Errore 'Python 3.14 non è installato (comando py -3.14).' @(
            "Installa il Python install manager:  winget install --id $($Manifesto.prerequisiti.python.winget) -e",
            'poi Python 3.14:  py install 3.14',
            'oppure rilancia questo script con -InstallaMancanti.')
    }
    return $p
}

function Get-UvPronto {
    $u = Get-Uv
    if ($null -eq $u) {
        Stop-Errore 'uv non è installato.' @(
            "Installalo con:  winget install --id $($Manifesto.prerequisiti.uv.winget) -e",
            'oppure rilancia questo script con -InstallaMancanti.')
    }
    return $u
}

function Invoke-Prerequisiti {
    $pr = $Manifesto.prerequisiti
    $mancano = @()

    $git = Find-Git
    if ($null -eq $git -and $InstallaMancanti) {
        Write-Info 'git manca: lo installo con winget, solo per questo utente...'
        [void](Install-ConWinget $pr.git.winget @($pr.git.winget_argomenti))
        $git = Find-Git
    }
    if ($null -ne $git) {
        Write-Ok "git $($git.Versione): $($git.Percorso)"
        if ($git.Versione -and ([version]$git.Versione -lt [version]$pr.git.versione_minima)) {
            Write-Avviso "git è vecchio (serve almeno la $($pr.git.versione_minima)): aggiornalo con  winget upgrade --id $($pr.git.winget) -e"
        }
    } else {
        $mancano += "git e Git Bash (Git for Windows):  winget install --id $($pr.git.winget) -e $(@($pr.git.winget_argomenti) -join ' ')"
    }
    $bash = Find-GitBash $git
    if ($bash) {
        Write-Ok "Git Bash: $bash"
    } elseif ($null -ne $git) {
        $mancano += "Git Bash (fa parte di Git for Windows): reinstallalo con  winget install --id $($pr.git.winget) -e"
    }

    $py = Get-Python -Installa:$InstallaMancanti
    if ($py.Exe) {
        Write-Ok "Python $($py.Versione): $($py.Exe)"
        if ($py.Versione -ne $pr.python.versione_di_riferimento) {
            Write-Info "(sul PC di lavoro c'è la $($pr.python.versione_di_riferimento): va bene qualsiasi 3.14)"
        }
    } elseif ($py.Py) {
        $mancano += 'Python 3.14:  py install 3.14'
    } else {
        $mancano += "Python 3.14 con il comando py:  winget install --id $($pr.python.winget) -e   e poi   py install 3.14"
    }

    $uv = Get-Uv -Installa:$InstallaMancanti
    if ($null -ne $uv) {
        Write-Ok "uv $($uv.Versione): $($uv.Percorso)"
        if ($uv.Versione -ne $pr.uv.versione) { Write-Info "(il manifesto indica la $($pr.uv.versione): va bene anche questa)" }
    } else {
        $mancano += "uv:  winget install --id $($pr.uv.winget) -e"
    }

    if ($mancano.Count -gt 0) {
        $rimedio = @('Installa quello che manca con questi comandi (non servono i diritti di amministratore):') +
            @($mancano | ForEach-Object { "- $_" }) +
            @('poi chiudi e riapri PowerShell e rilancia lo script.', 'Oppure rilancia lo script con -InstallaMancanti: li installa lui con winget.')
        Stop-Errore "Mancano dei prerequisiti: $($mancano.Count)." $rimedio
    }
    return 'ok'
}

# ------------------------------------------------------------------ ambienti Python (venv e PyMusicLooper)

function Get-StatoVenv([string]$Cartella) {
    if (-not [System.IO.Directory]::Exists($Cartella)) { return 'assente' }
    $cfg = Join-Path $Cartella 'pyvenv.cfg'
    $exe = Join-Path $Cartella 'Scripts\python.exe'
    if (-not [System.IO.File]::Exists($cfg) -or -not [System.IO.File]::Exists($exe)) { return 'rovinato (mancano pyvenv.cfg o python.exe)' }
    $testo = [System.IO.File]::ReadAllText($cfg)
    if ($testo -notmatch '(?m)^\s*version_info\s*=\s*3\.14\.') { return 'fatto con un Python diverso dal 3.14' }
    if ($testo -match '(?m)^\s*home\s*=\s*(.+?)\s*$') {
        $base = $Matches[1]
        if (-not [System.IO.File]::Exists((Join-Path $base 'python.exe'))) { return "rovinato (il Python di base $base non c'è più)" }
    }
    return 'ok'
}

# Pacchetti del manifesto che non risultano installati alla versione giusta (cartelle *.dist-info).
function Get-PacchettiMancanti([string]$SitePackages, $Pacchetti) {
    $mancanti = @()
    foreach ($p in @($Pacchetti)) {
        $nome = ([string]$p.nome) -replace '[-_.]+', '_'
        $di = Join-Path $SitePackages ('{0}-{1}.dist-info' -f $nome, $p.versione)
        if (-not [System.IO.Directory]::Exists($di)) { $mancanti += "$($p.nome)==$($p.versione)" }
    }
    return $mancanti
}

function Invoke-Uv([string[]]$Argomenti) {
    $uv = Get-UvPronto
    $ambiente = @{ UV_PYTHON_DOWNLOADS = 'never'; UV_CACHE_DIR = (Join-Path (Join-Path $Lab 'downloads') 'uv-cache') }
    $vecchi = @{}
    foreach ($k in $ambiente.Keys) {
        $vecchi[$k] = [Environment]::GetEnvironmentVariable($k)
        [Environment]::SetEnvironmentVariable($k, $ambiente[$k])
    }
    try {
        $a = @($Argomenti) + @('--no-config')
        & $uv.Percorso @a | Out-Host
        $codice = $LASTEXITCODE
    } finally {
        foreach ($k in $vecchi.Keys) { [Environment]::SetEnvironmentVariable($k, $vecchi[$k]) }
    }
    if ($codice -ne 0) {
        Stop-Errore "uv $($Argomenti[0]) $($Argomenti[1]) non è riuscito (codice $codice)." @(
            'Leggi i messaggi di uv qui sopra.',
            'Se dice che un hash non corrisponde, non forzare: avvisa Claude (il manifesto va ricontrollato).',
            'Se è un problema di rete, rilancia lo script: riparte da qui.')
    }
}

# Prima di ricreare un ambiente Python ne salva in logs\ l'elenco dei pacchetti (cartelle *.dist-info):
# uv venv --clear lo svuota, e così si sa cosa c'era, anche i pacchetti aggiunti a mano.
function Save-ElencoPacchetti([string]$Cartella) {
    $site = Join-Path $Cartella 'Lib\site-packages'
    if (-not [System.IO.Directory]::Exists($site)) { return $null }
    $voci = @(Get-ChildItem -LiteralPath $site -Directory -Filter '*.dist-info' -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Name -replace '\.dist-info$', '' } | Sort-Object)
    if ($voci.Count -eq 0) { return $null }
    $nome = $Cartella
    if (Test-Dentro $Cartella $Lab) { $nome = $Cartella.Substring($Lab.TrimEnd('\').Length).TrimStart('\') }
    $nome = ($nome -replace '[\\/:]+', '-').Trim('-')
    $dir = Join-Path $Lab 'logs'
    New-Cartella $dir
    $file = Join-Path $dir ('{0}-{1}-pacchetti-prima.txt' -f $nome, (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $righe = @("# Pacchetti che c'erano in $Cartella prima di ricrearlo (nome-versione).") + $voci
    Write-Testo $file (($righe -join "`n") + "`n")
    return $file
}

function Install-AmbientePython([string]$Nome, [string]$Cartella, $Pacchetti, [string]$FileRequisiti) {
    $pacchetti = @($Pacchetti)
    $site = Join-Path $Cartella 'Lib\site-packages'
    $stato = Get-StatoVenv $Cartella
    if (-not $Forza -and $stato -eq 'ok') {
        $mancanti = @(Get-PacchettiMancanti $site $pacchetti)
        if ($mancanti.Count -eq 0) {
            Write-Ok "$Nome è già a posto: Python 3.14 e $($pacchetti.Count) pacchetti alle versioni fissate."
            return 'già a posto'
        }
        Write-Info "Da installare o aggiornare: $($mancanti -join ', ')."
    }
    $py = Get-PythonPronto
    [void](Get-UvPronto)
    if ($Forza -or $stato -ne 'ok') {
        if ($stato -ne 'assente') {
            $motivo = $stato
            if ($stato -eq 'ok') { $motivo = '-Forza' }
            Write-Info "Ricreo da capo $Nome ($motivo) in $Cartella con Python $($py.Versione)."
            $elenco = Save-ElencoPacchetti $Cartella
            if ($elenco) { Write-Info "I pacchetti aggiunti a mano si perdono: l'elenco di quelli che c'erano è in $elenco" }
        } else {
            Write-Info "Creo $Nome in $Cartella con Python $($py.Versione)..."
        }
        Invoke-Uv @('venv', $Cartella, '--python', $py.Exe, '--clear', '--no-python-downloads')
    }
    New-Cartella (Split-Path $FileRequisiti -Parent)
    $righe = @('# Scritto da tools/setup/prepara_laboratorio.ps1 da laboratorio.json: non modificarlo a mano.')
    foreach ($p in $pacchetti) { $righe += ('{0}=={1} --hash=sha256:{2}' -f $p.nome, $p.versione, $p.sha256) }
    Write-Testo $FileRequisiti (($righe -join "`n") + "`n")
    Write-Info "Installo $($pacchetti.Count) pacchetti con l'hash di PyPI (solo wheel, niente compilazioni)..."
    Invoke-Uv @('pip', 'install', '--python', (Join-Path $Cartella 'Scripts\python.exe'), '--require-hashes', '--only-binary', ':all:', '-r', $FileRequisiti)
    $mancanti = @(Get-PacchettiMancanti $site $pacchetti)
    if ($mancanti.Count -gt 0) {
        Stop-Errore "Dopo l'installazione mancano ancora: $($mancanti -join ', ')." @('Rilancia lo script con -Forza; se si ripete, avvisa Claude.')
    }
    Write-Ok "$Nome è pronto: $($pacchetti.Count) pacchetti verificati."
    return 'installato'
}

function Invoke-Venv {
    $cfg = $Manifesto.python.venv
    return (Install-AmbientePython 'il venv del laboratorio' (Join-Relativo $Lab $cfg.cartella) $cfg.pacchetti (Join-Path $Lab 'downloads\python\venv-requisiti.txt'))
}

function Invoke-PyMusicLooper {
    $cfg = $Manifesto.python.pymusiclooper
    $base = Join-Relativo $Lab $cfg.cartella
    $exe = Join-Relativo $base $cfg.eseguibile
    $ambiente = Join-Relativo $base $cfg.ambiente
    $pacchetti = @($cfg.pacchetti)
    if (-not $Forza -and [System.IO.File]::Exists($exe)) {
        foreach ($c in @($ambiente, (Join-Relativo $base $cfg.ambiente_vecchio))) {
            if ((Get-StatoVenv $c) -eq 'ok' -and @(Get-PacchettiMancanti (Join-Path $c 'Lib\site-packages') $pacchetti).Count -eq 0) {
                Write-Ok "PyMusicLooper $($cfg.versione) già installato ($c), $($pacchetti.Count) pacchetti alle versioni fissate."
                return 'già a posto'
            }
        }
    }
    $esito = Install-AmbientePython "l'ambiente di PyMusicLooper" $ambiente $pacchetti (Join-Path $Lab 'downloads\python\pymusiclooper-requisiti.txt')
    $src = Join-Relativo $ambiente $cfg.eseguibile_nell_ambiente
    if (-not [System.IO.File]::Exists($src)) { Stop-Errore "Nell'ambiente di PyMusicLooper manca $src." @('Rilancia lo script con -Forza.') }
    New-Cartella (Split-Path $exe -Parent)
    Copy-Item -LiteralPath $src -Destination $exe -Force
    Write-Ok "PyMusicLooper $($cfg.versione): $exe"
    if ($esito -eq 'già a posto') { return 'sistemato' }
    return $esito
}

# ------------------------------------------------------------------ cartella condivisa e skill

# Ferma lo script se la cartella condivisa non c'è (serve ai passi 7 e 8).
function Assert-Condiviso {
    if (-not [System.IO.Directory]::Exists($Cond)) {
        Stop-Errore "Non trovo la cartella condivisa $Cond." @(
            'Sul PC di lavoro la riempie tools\setup\aggiorna_condiviso.ps1.',
            'Qui deve arrivare con OneDrive: controlla che OneDrive sia acceso e che la cartella ClaudeCode sia sincronizzata.',
            'Se sta altrove, indica il percorso con -Condiviso o con la variabile CAR_CONDIVISO.',
            'Per installare intanto solo i programmi: -Solo prerequisiti,godot,blender,ffmpeg,venv,pymusiclooper')
    }
}

# Confronta la cartella condivisa con il suo inventario: se ha meno file, OneDrive non ha finito di scaricarla.
# Con -SoloAvviso (controllo in anticipo, prima di scaricare i programmi) avvisa e basta.
function Test-CondivisoCompleto([switch]$SoloAvviso) {
    $nomeInv = $Manifesto.condiviso.inventario
    $f = Join-Path $Cond $nomeInv
    if (-not [System.IO.File]::Exists($f)) {
        Write-Avviso "Nella cartella condivisa manca ${nomeInv}: non posso controllare che OneDrive l'abbia scaricata tutta."
        return
    }
    $inv = Read-Json $f
    if (-not $Script:InfoCondivisoMostrata) {
        Write-Info "Cartella condivisa aggiornata il $($inv.aggiornato) da $($inv.pc)."
        $Script:InfoCondivisoMostrata = $true
    }
    # Bloccano solo le cartelle che servono al laboratorio e le skill; per le altre basta un avviso.
    $servono = @($Manifesto.condiviso.nel_laboratorio | ForEach-Object { [string]$_.cartella }) + @([string]$Manifesto.condiviso.skill.cartella)
    $incomplete = @()
    foreach ($p in @($inv.cartelle.PSObject.Properties)) {
        $qui = Get-Inventario (Join-Path $Cond $p.Name)
        if ($qui.file -ge [int]$p.Value.file) { continue }
        $testo = '{0} ({1} file su {2})' -f $p.Name, $qui.file, $p.Value.file
        if ($servono -contains $p.Name) { $incomplete += $testo }
        elseif (-not $SoloAvviso) { Write-Avviso "OneDrive non ha ancora scaricato tutto $testo; al laboratorio non serve, vado avanti." }
    }
    if ($incomplete.Count -eq 0) { return }
    if ($SoloAvviso) {
        Write-Avviso "OneDrive non ha ancora scaricato tutta la cartella condivisa: $($incomplete -join ', '). Intanto installo i programmi; la ricontrollo al passo 7."
        return
    }
    Stop-Errore "La cartella condivisa non è ancora completa su questo PC: $($incomplete -join ', ')." @(
        'OneDrive la sta ancora scaricando: aspetta che l''icona di OneDrive dica che è tutto aggiornato, poi rilancia.',
        'Per farla scaricare tutta subito: in Esplora file, tasto destro su ctrlaltrevenge-lab-condiviso > "Mantieni sempre su questo dispositivo".')
}

# Regole di music\: si copiano solo music.json, FONTI.md e gli OGG segnaposto del manifesto, e solo se la cartella
# condivisa contiene esattamente la musica segnaposto nota e quella del laboratorio non ha brani veri.
# Restituisce $true se si può copiare.
function Test-MusicaCopiabile($Voce, [string]$Da, [string]$A, [string[]]$EscludiCartelle) {
    $nome = [string]$Voce.cartella
    $ignora = @($Manifesto.condiviso.escludi_file)
    $qui = Get-StatoMusica $A $Voce $EscludiCartelle $ignora
    if ($qui.Stato -eq 'privata' -or $qui.Stato -eq 'illeggibile') {
        Write-Info "${nome}: nel laboratorio non c'è solo la musica segnaposto ($($qui.Motivo)): non la tocco."
        return $false
    }
    $la = Get-StatoMusica $Da $Voce $EscludiCartelle $ignora
    if ($la.Stato -eq 'vuota') {
        Write-Avviso "${nome}: nella cartella condivisa non c'è la musica segnaposto ($($la.Motivo)): la salto."
        return $false
    }
    if ($la.Stato -ne 'segnaposto') {
        Write-Avviso "${nome}: nella cartella condivisa non c'è solo la musica segnaposto nota ($($la.Motivo)): non la copio. Avvisa Claude: lì non devono esserci brani veri."
        return $false
    }
    Write-Info "${nome}: copio solo $((Get-FileMusica $Voce) -join ', ')."
    return $true
}

function Invoke-Condivisi {
    $c = $Manifesto.condiviso
    Assert-Condiviso
    Test-CondivisoCompleto
    if ($Forza) { Write-Info '-Forza qui non vale: copio solo i file più nuovi e non sostituisco mai un file del laboratorio con uno più vecchio.' }
    $backup = Join-Path (Join-Path $Lab 'backup') (Get-Date -Format 'yyyyMMdd-HHmmss')
    $copiate = 0
    foreach ($v in @($c.nel_laboratorio)) {
        $nome = [string]$v.cartella
        $da = Join-Path $Cond $nome
        $a = Join-Path $Lab $nome
        if (-not [System.IO.Directory]::Exists($da)) { Write-Avviso "Nella cartella condivisa manca $nome`: la salto."; continue }
        $escludiCartelle = @($c.escludi_cartelle) + @(Get-Campo $v 'escludi_cartelle' @())
        $escludiFile = @($c.escludi_file) + @(Get-Campo $v 'escludi_file' @())
        $soloFile = @(Get-Campo $v 'solo_file' @())
        $senzaSottocartelle = $false
        if ((Get-Campo $v 'regola' '') -eq 'musica') {
            if (-not (Test-MusicaCopiabile $v $da $a $escludiCartelle)) { continue }
            $soloFile = @(Get-FileMusica $v)
            $senzaSottocartelle = $true
        }
        $inv = Get-Inventario $da
        $nota = ''
        if ($inv.solo_online -gt 0) { $nota = "; $($inv.solo_online) sono ancora solo online e OneDrive li scarica adesso, può volerci un po'" }
        Write-Info ('{0}: {1} file, {2}{3}...' -f $nome, $inv.file, (Format-Dimensione $inv.byte), $nota)
        $codice = Invoke-Copia -Da $da -A $a -SoloFile $soloFile -EscludiCartelle $escludiCartelle -EscludiFile $escludiFile -Backup (Join-Path $backup $nome) -SenzaSottocartelle:$senzaSottocartelle
        if (Test-Copiato $codice) { Write-Ok "$nome copiata (file nuovi o più recenti)."; $copiate++ } else { Write-Ok "$nome è già aggiornata." }
    }
    if ($copiate -gt 0) { return 'copiato' }
    return 'già a posto'
}

function Invoke-Skill {
    $s = $Manifesto.condiviso.skill
    Assert-Condiviso
    $sorgente = Join-Path $Cond $s.cartella
    if (-not [System.IO.Directory]::Exists($sorgente)) {
        Stop-Errore "Nella cartella condivisa manca la cartella $($s.cartella) con le skill ($sorgente)." @(
            'Sul PC di lavoro rilancia tools\setup\aggiorna_condiviso.ps1, poi aspetta che OneDrive sincronizzi.')
    }
    New-Cartella $Skill
    $installate = 0
    foreach ($nome in @($s.nomi)) {
        $da = Join-Path $sorgente $nome
        $a = Join-Path $Skill $nome
        foreach ($f in @($s.file_obbligatori)) {
            if (-not [System.IO.File]::Exists((Join-Path $da $f))) {
                Stop-Errore "La skill $nome nella cartella condivisa è incompleta: manca $f." @('Sul PC di lavoro rilancia tools\setup\aggiorna_condiviso.ps1.')
            }
        }
        if ([System.IO.Directory]::Exists($a) -and -not $Forza) {
            Write-Info "${nome}: c'è già, non la tocco."
            continue
        }
        [void](Invoke-Copia -Da $da -A $a -Forza)
        foreach ($f in @($s.file_obbligatori)) {
            if (-not [System.IO.File]::Exists((Join-Path $a $f))) { Stop-Errore "Dopo la copia, nella skill $nome manca $f." @('Rilancia lo script con -Forza.') }
        }
        Write-Ok "$nome installata."
        $installate++
    }
    Write-Info "Fonte: $($s.fonte), commit $($s.commit.Substring(0, 8)), licenza $($s.licenza)."
    if ($installate -gt 0) {
        Write-Info 'Riavvia Claude Code perché veda le skill nuove.'
        return "installate $installate"
    }
    return 'già a posto'
}

# ------------------------------------------------------------------ Gioca.bat

function Invoke-Gioca {
    $g = Get-StrumentoDaId 'godot'
    $dirGodot = Join-Relativo $Lab $g.cartella
    $console = Join-Path $dirGodot $g.eseguibile_console
    $gui = Join-Path $dirGodot $g.eseguibile
    $gioco = Join-Path $Radice 'game'
    $righe = @(
        '@echo off',
        'rem CTRL+ALT REVENGE - avvio dello slice "Sotto la Linea".',
        'rem Scritto da tools\setup\prepara_laboratorio.ps1 con i percorsi di questo PC:',
        'rem se sposti il repo o il laboratorio, rilancia lo script.',
        'rem 1. importa gli asset del progetto in modalità headless (Godot con la console);',
        'rem 2. avvia il gioco in una finestra (Godot senza console).',
        'rem Gli argomenti passati a questo file arrivano a Godot, per esempio:',
        'rem   Gioca.bat -- --autostart                              (salta il titolo)',
        'rem   Gioca.bat -- --replay res://tests/replays/demo.json   (dimostrazione)',
        'chcp 65001 > nul',
        'setlocal',
        "set `"GODOT_CONSOLE=$console`"",
        "set `"GODOT=$gui`"",
        "set `"GAME=$gioco`"",
        '',
        'if not exist "%GODOT%" (',
        '  echo Godot non trovato: "%GODOT%"',
        '  echo Rilancia tools\setup\prepara_laboratorio.ps1 dal repo.',
        '  pause',
        '  exit /b 1',
        ')',
        'if not exist "%GAME%\project.godot" (',
        '  echo Progetto non trovato: "%GAME%"',
        '  pause',
        '  exit /b 1',
        ')',
        '',
        'echo Importazione degli asset in corso...',
        '"%GODOT_CONSOLE%" --headless --path "%GAME%" --import',
        'if errorlevel 1 (',
        '  echo Importazione non riuscita: controlla i messaggi qui sopra.',
        '  pause',
        '  exit /b 1',
        ')',
        '',
        'echo Avvio di CTRL+ALT REVENGE...',
        'start "CTRL+ALT REVENGE" "%GODOT%" --path "%GAME%" %*',
        'endlocal'
    )
    $testo = ($righe -join "`r`n") + "`r`n"
    $file = Join-Path $Lab 'Gioca.bat'
    if ([System.IO.File]::Exists($file) -and -not $Forza) {
        $attuale = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8) -replace "`r`n", "`n"
        if ($attuale -eq ($testo -replace "`r`n", "`n")) {
            Write-Ok "Gioca.bat è già aggiornato: $file"
            return 'già a posto'
        }
        Write-Info 'Gioca.bat ha percorsi o testo diversi: lo riscrivo.'
    }
    if (-not [System.IO.Directory]::Exists($gioco)) { Write-Avviso "Non trovo la cartella del gioco ${gioco}: Gioca.bat la cercherà lì." }
    Write-Testo $file $testo -Crlf
    Write-Ok "scritto $file (gioco: $gioco)."
    return 'scritto'
}

# ------------------------------------------------------------------ verifica finale

# $DatiUtente diventa APPDATA per Godot: lì finisce user:// (log, cache) del progetto, invece che in
# %APPDATA%\Godot\app_userdata, dove stanno i dati del gioco vero. Le impostazioni dell'editor non cambiano
# posto: con il file _sc_ stanno comunque in editor_data accanto a Godot.
function Invoke-Godot([string]$Exe, [string[]]$Argomenti, [int]$Timeout, [string]$Log, [string]$DatiUtente) {
    $t0 = Get-Date
    $tutti = @('--path', $Progetto) + $Argomenti
    $r = Invoke-Programma $Exe $tutti -TimeoutSec $Timeout -Cartella $Progetto -Ambiente @{ APPDATA = $DatiUtente }
    $secondi = [int]((Get-Date) - $t0).TotalSeconds
    $intestazione = "# $Exe $($tutti -join ' ')`n# APPDATA=$DatiUtente`n# codice d'uscita: $($r.Codice), secondi: $secondi`n"
    Write-Testo $Log ($intestazione + "--- stdout ---`n" + [string]$r.Uscita + "`n--- stderr ---`n" + [string]$r.Errori)
    Add-Member -InputObject $r -NotePropertyName Log -NotePropertyValue $Log
    Add-Member -InputObject $r -NotePropertyName Secondi -NotePropertyValue $secondi
    return $r
}

function Test-UscitaGodot($R, [string]$Cosa, [string]$UltimaRiga) {
    $righe = @(([string]$R.Uscita + "`n" + [string]$R.Errori) -split "`r?`n")
    $errori = @($righe | Where-Object { $_ -match $Manifesto.verifica_finale.errori })
    $problemi = @()
    if ($R.Scaduto) { $problemi += "Godot non ha finito entro $($R.Secondi) secondi" }
    elseif ($R.Codice -ne 0) { $problemi += "Godot è uscito con il codice $($R.Codice)" }
    if ($errori.Count -gt 0) { $problemi += "nell'output ci sono $($errori.Count) righe di errore" }
    if ($UltimaRiga) {
        $ultima = @(([string]$R.Uscita -split "`r?`n") | Where-Object { $_.Trim() } | Select-Object -Last 1)
        $testoUltima = ''
        if ($ultima.Count -gt 0) { $testoUltima = ([string]$ultima[0]).Trim() }
        if ($testoUltima -ne $UltimaRiga) { $problemi += "l'ultima riga è '$testoUltima' invece di '$UltimaRiga'" }
    }
    if ($problemi.Count -gt 0) {
        if ($errori.Count -gt 0) {
            Write-Host '  --- righe di errore ---' -ForegroundColor DarkGray
            foreach ($e in @($errori | Select-Object -First 15)) { Write-Host "  $e" -ForegroundColor DarkGray }
        }
        Write-Host '  --- ultime righe ---' -ForegroundColor DarkGray
        foreach ($riga in @($righe | Where-Object { $_.Trim() } | Select-Object -Last 20)) { Write-Host "  $riga" -ForegroundColor DarkGray }
        Stop-Errore "Verifica finale ($Cosa) non riuscita: $($problemi -join '; ')." @(
            "Log completo: $($R.Log)",
            'Se nel progetto c''è un lavoro in corso (per esempio di un''altra sessione di Claude), può essere normale: chiedi a Claude di guardare il log.')
    }
}

function Invoke-Verifica {
    $v = $Manifesto.verifica_finale
    $g = Get-StrumentoDaId 'godot'
    $godot = Join-Path (Join-Relativo $Lab $g.cartella) $g.eseguibile_console
    if (-not [System.IO.File]::Exists($godot)) {
        Stop-Errore "Godot non è installato nel laboratorio ($godot)." @('Rilancia lo script senza -Solo, oppure con -Solo godot,verifica.')
    }
    if (-not [System.IO.File]::Exists((Join-Path $Progetto 'project.godot'))) {
        Stop-Errore "Non trovo project.godot in $Progetto." @(
            'Se è la cartella game del repo, aspetta che OneDrive finisca di sincronizzare il repo.',
            'Per provare un altro progetto usa -ProgettoGodot <cartella>.')
    }
    $logDir = Join-Path $Lab 'logs'
    New-Cartella $logDir
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $datiUtente = Join-Path $logDir "verifica-$stamp-appdata"
    New-Cartella $datiUtente
    Write-Info "Progetto: $Progetto"
    Write-Info "I dati utente del progetto (user://) di questa verifica vanno in $datiUtente"
    Write-Info 'Importo gli asset (Godot headless): la prima volta può volerci qualche minuto...'
    $tentativi = [math]::Max(1, [int](Get-Campo $v.importazione 'tentativi' 1))
    for ($t = 1; $t -le $tentativi; $t++) {
        $nomeLog = "verifica-$stamp-importazione.log"
        if ($t -gt 1) { $nomeLog = "verifica-$stamp-importazione-$t.log" }
        $r = Invoke-Godot $godot @($v.importazione.argomenti) ([int]$v.importazione.timeout_s) (Join-Path $logDir $nomeLog) $datiUtente
        $testo = [string]$r.Uscita + "`n" + [string]$r.Errori
        # Crash: codice d'uscita fuori da 0-255 (per esempio 0xC0000005) o il messaggio del gestore dei crash di Godot.
        $crash = (-not $r.Scaduto) -and ($r.Codice -lt 0 -or $r.Codice -gt 255 -or $testo -match 'CrashHandlerException|Program crashed')
        if (-not $crash -or $t -eq $tentativi) { break }
        Write-Avviso "Godot è andato in crash durante l'importazione (codice $($r.Codice), log in $($r.Log)): con Godot 4.7.2 succede, soprattutto la prima volta. Riprovo ($($t + 1) di $tentativi)..."
    }
    Test-UscitaGodot $r 'importazione' ''
    Write-Ok "importazione riuscita in $($r.Secondi) s."
    Write-Info 'Lancio i test del gioco (res://tests/run_tests.gd)...'
    $r = Invoke-Godot $godot @($v.test.argomenti) ([int]$v.test.timeout_s) (Join-Path $logDir "verifica-$stamp-test.log") $datiUtente
    Test-UscitaGodot $r 'test' ([string]$v.test.ultima_riga)
    $passati = @(([string]$r.Uscita -split "`r?`n") | Where-Object { $_ -like 'Test passati*' } | Select-Object -Last 1)
    $dettaglio = ''
    if ($passati.Count -gt 0) { $dettaglio = " ($($passati[0].Trim()))" }
    Write-Ok "test riusciti in $($r.Secondi) s$dettaglio; l'ultima riga è $($v.test.ultima_riga). Log in $logDir"
    return 'ok, DONE'
}

# ------------------------------------------------------------------ preliminari

function Show-Configurazione {
    Write-Titolo 'CTRL+ALT REVENGE: preparazione del laboratorio'
    Write-Info "PC:                  $env:COMPUTERNAME (utente $env:USERNAME), PowerShell $($PSVersionTable.PSVersion)"
    Write-Info "Repo:                $Radice"
    Write-Info "Laboratorio:         $Lab"
    Write-Info "Cartella condivisa:  $Cond"
    Write-Info "Skill di Claude:     $Skill"
    Write-Info "Progetto da provare: $Progetto"
    $opzioni = @()
    if ($Forza) { $opzioni += '-Forza' }
    if ($InstallaMancanti) { $opzioni += '-InstallaMancanti' }
    if ($SaltaVerifica) { $opzioni += '-SaltaVerifica' }
    if ($Solo.Count -gt 0) { $opzioni += "-Solo $($Solo -join ',')" }
    if ($opzioni.Count -eq 0) { $opzioni = @('nessuna') }
    Write-Info "Opzioni:             $($opzioni -join ' ')"
}

function Test-Preliminari {
    foreach ($od in @(Get-CartelleOneDrive)) {
        if (Test-Dentro $Lab $od) {
            Stop-Errore "Il laboratorio ($Lab) è dentro OneDrive ($od)." @(
                'Il laboratorio deve stare fuori da OneDrive: contiene programmi e file grandi.',
                "Usa la cartella predefinita $(Join-Path $HOME $Manifesto.laboratorio.predefinito) o un'altra fuori da OneDrive.")
        }
    }
    if (Test-Dentro $Lab $Radice) { Stop-Errore "Il laboratorio ($Lab) è dentro il repo." @('Il laboratorio deve stare fuori dal repo: usa la cartella predefinita.') }
    if (Test-Dentro $Cond $Radice) { Stop-Errore "La cartella condivisa ($Cond) è dentro il repo: finirebbe su GitHub." @('Spostala accanto al repo, non dentro.') }
    $predefinito = Join-Path $HOME $Manifesto.laboratorio.predefinito
    if ($Lab -ne $predefinito) {
        Write-Avviso ("Il laboratorio non è nella cartella predefinita ($predefinito). Il gioco cerca la musica solo lì, e lì cercano il laboratorio anche tools/env e tools/fxui; " +
            "tools/run_godot.sh, tools/audio, tools/sprites e tools/site trovano questo laboratorio solo se la variabile CAR_LAB vale $Lab.")
    }
    # La cartella condivisa serve ai passi 7 e 8: meglio saperlo subito che dopo aver scaricato i programmi.
    if ((Test-Passo 'condivisi') -or (Test-Passo 'skill')) {
        Assert-Condiviso
        Test-CondivisoCompleto -SoloAvviso
    }
    New-Cartella $Lab
    $disco = New-Object System.IO.DriveInfo -ArgumentList ([System.IO.Path]::GetPathRoot($Lab))
    $liberiGb = [math]::Round($disco.AvailableFreeSpace / 1GB, 1)
    $minimo = [double]$Manifesto.laboratorio.spazio_libero_minimo_gb
    if ($liberiGb -lt 2) {
        Stop-Errore "Sul disco $($disco.Name) restano solo $liberiGb GB liberi." @("Per un laboratorio nuovo servono circa $minimo GB: libera spazio e rilancia.")
    } elseif ($liberiGb -lt $minimo) {
        Write-Avviso "Sul disco $($disco.Name) restano $liberiGb GB: per un laboratorio nuovo ne servono circa $minimo."
    }
}

# ------------------------------------------------------------------ programma principale

try {
    $Radice = Resolve-Percorso (Join-Path $PSScriptRoot '..\..')
    $Manifesto = Read-Manifesto (Join-Path $PSScriptRoot 'laboratorio.json')
    $Lab = Get-CartellaLaboratorio $Laboratorio $Manifesto
    $Cond = Get-CartellaCondivisa $Condiviso $Manifesto $Radice
    $Skill = Get-CartellaSkill $CartellaSkill $Manifesto
    if ($ProgettoGodot) { $Progetto = Resolve-Percorso $ProgettoGodot }
    else { $Progetto = Join-Relativo $Radice $Manifesto.verifica_finale.progetto_predefinito }

    Show-Configurazione
    Test-Preliminari

    $titoloCondivisi = 'File dalla cartella condivisa ({0})' -f (@($Manifesto.condiviso.nel_laboratorio | ForEach-Object { [string]$_.cartella }) -join ', ')
    $passi = @(
        @{ Nome = 'prerequisiti'; Titolo = 'Prerequisiti: git, Git Bash, Python 3.14, uv'; Azione = { Invoke-Prerequisiti } },
        @{ Nome = 'godot'; Titolo = 'Godot 4.7.2'; Azione = { Invoke-Strumento 'godot' } },
        @{ Nome = 'blender'; Titolo = 'Blender 4.5.15'; Azione = { Invoke-Strumento 'blender' } },
        @{ Nome = 'ffmpeg'; Titolo = 'FFmpeg 9.0.2'; Azione = { Invoke-Strumento 'ffmpeg' } },
        @{ Nome = 'venv'; Titolo = 'venv di Python (NumPy, Pillow, SciPy)'; Azione = { Invoke-Venv } },
        @{ Nome = 'pymusiclooper'; Titolo = 'PyMusicLooper 3.6.0'; Azione = { Invoke-PyMusicLooper } },
        @{ Nome = 'condivisi'; Titolo = $titoloCondivisi; Azione = { Invoke-Condivisi } },
        @{ Nome = 'skill'; Titolo = 'Skill di Godot per Claude Code'; Azione = { Invoke-Skill } },
        @{ Nome = 'gioca'; Titolo = 'Gioca.bat con i percorsi di questo PC'; Azione = { Invoke-Gioca } },
        @{ Nome = 'verifica'; Titolo = 'Verifica finale: importazione e test del gioco'; Azione = { Invoke-Verifica } }
    )
    $totale = $passi.Count
    for ($i = 0; $i -lt $totale; $i++) {
        $p = $passi[$i]
        $etichetta = '{0,2}. {1}' -f ($i + 1), $p.Titolo
        if (-not (Test-Passo $p.Nome)) {
            Add-Esito $etichetta 'saltato'
            continue
        }
        Write-Passo ($i + 1) $totale $p.Titolo
        try {
            $esito = @(& $p.Azione) | Select-Object -Last 1
            if (-not $esito) { $esito = 'ok' }
            Add-Esito $etichetta ([string]$esito)
        } catch {
            Add-Esito $etichetta 'ERRORE'
            # Nel riepilogo compaiono anche i passi che dopo l'errore non sono stati fatti.
            for ($j = $i + 1; $j -lt $totale; $j++) {
                $q = $passi[$j]
                $etichettaDopo = '{0,2}. {1}' -f ($j + 1), $q.Titolo
                if (Test-Passo $q.Nome) { Add-Esito $etichettaDopo 'non fatto' } else { Add-Esito $etichettaDopo 'saltato' }
            }
            throw
        }
    }
} catch {
    Write-Errore $_
    Show-Riepilogo
    Write-Host ''
    Write-Host 'Il laboratorio non è completo: correggi il problema e rilancia lo script (riparte saltando ciò che è già a posto).' -ForegroundColor Red
    exit 1
}

Show-Riepilogo
Write-Host ''
Write-Host "Fatto. Laboratorio: $Lab" -ForegroundColor Green
if (Test-Passo 'gioca') { Write-Host "Per giocare: doppio clic su $(Join-Path $Lab 'Gioca.bat')" -ForegroundColor Green }
exit 0
