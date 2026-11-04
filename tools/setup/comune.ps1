# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
#
# Funzioni comuni a prepara_laboratorio.ps1 e aggiorna_condiviso.ps1.
# Non si lancia da solo: gli altri script lo includono con  . (Join-Path $PSScriptRoot 'comune.ps1')
# Funziona in Windows PowerShell 5.1 e in PowerShell 7, anche con percorsi che contengono spazi.

Set-StrictMode -Version 2.0

# ------------------------------------------------------------------ messaggi

function Write-Titolo([string]$Testo) {
    Write-Host ''
    Write-Host $Testo -ForegroundColor Cyan
}

function Write-Passo([int]$Numero, [int]$Totale, [string]$Testo) {
    Write-Host ''
    Write-Host ('[{0}/{1}] {2}' -f $Numero, $Totale, $Testo) -ForegroundColor Cyan
}

function Write-Info([string]$Testo) { Write-Host "  $Testo" }

function Write-Ok([string]$Testo) { Write-Host "  OK: $Testo" -ForegroundColor Green }

function Write-Avviso([string]$Testo) { Write-Host "  ATTENZIONE: $Testo" -ForegroundColor Yellow }

# Ferma lo script con un messaggio e, se c'è, il rimedio (una riga per elemento).
function Stop-Errore {
    param([Parameter(Mandatory = $true)][string]$Messaggio, [string[]]$Rimedio = @())
    $ex = New-Object System.Exception -ArgumentList $Messaggio
    $ex.Data['rimedio'] = ($Rimedio -join "`n")
    throw $ex
}

# Stampa un errore catturato da try/catch, con il rimedio se c'è.
function Write-Errore($Record) {
    $ex = $Record.Exception
    Write-Host ''
    Write-Host "ERRORE: $($ex.Message)" -ForegroundColor Red
    $rimedio = ''
    if ($null -ne $ex.Data -and $ex.Data.Contains('rimedio')) { $rimedio = [string]$ex.Data['rimedio'] }
    if ($rimedio) {
        Write-Host 'Cosa fare:' -ForegroundColor Yellow
        foreach ($riga in ($rimedio -split "`n")) { Write-Host "  $riga" -ForegroundColor Yellow }
    } elseif ($null -ne $Record.InvocationInfo -and $Record.InvocationInfo.ScriptName) {
        Write-Host ('(errore imprevisto alla riga {0} di {1})' -f $Record.InvocationInfo.ScriptLineNumber,
            (Split-Path -Leaf $Record.InvocationInfo.ScriptName)) -ForegroundColor DarkGray
    }
}

# ------------------------------------------------------------------ dati e percorsi

# Valore di un campo del manifesto, o il predefinito se manca (con StrictMode un campo assente darebbe errore).
function Get-Campo($Oggetto, [string]$Nome, $Predefinito = $null) {
    if ($null -eq $Oggetto) { return $Predefinito }
    $p = $Oggetto.PSObject.Properties[$Nome]
    if ($null -eq $p -or $null -eq $p.Value) { return $Predefinito }
    return $p.Value
}

function Read-Json([string]$Percorso) {
    $testo = [System.IO.File]::ReadAllText($Percorso, [System.Text.Encoding]::UTF8)
    return ($testo | ConvertFrom-Json)
}

# Legge tools/setup/laboratorio.json e controlla le parti che servono.
function Read-Manifesto([string]$Percorso) {
    if (-not [System.IO.File]::Exists($Percorso)) {
        Stop-Errore "Non trovo il manifesto $Percorso." @('Lo script deve restare in tools\setup del repo, accanto a laboratorio.json.')
    }
    try {
        $m = Read-Json $Percorso
    } catch {
        Stop-Errore "Il manifesto $Percorso non è un JSON valido: $($_.Exception.Message)" @('Ripristinalo con: git checkout -- tools/setup/laboratorio.json')
    }
    foreach ($campo in @('formato', 'laboratorio', 'prerequisiti', 'strumenti', 'python', 'condiviso', 'verifica_finale')) {
        if ($null -eq (Get-Campo $m $campo)) { Stop-Errore "Nel manifesto manca il campo '$campo'." @('Ripristinalo con: git checkout -- tools/setup/laboratorio.json') }
    }
    if ($m.formato -ne 1) { Stop-Errore "Il manifesto ha il formato $($m.formato), questo script conosce solo il formato 1." @('Aggiorna il repo (git pull) e rilancia.') }
    return $m
}

# Percorso assoluto, anche se relativo alla cartella corrente di PowerShell; senza barra finale.
function Resolve-Percorso([string]$Percorso) {
    $p = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Percorso)
    $p = [System.IO.Path]::GetFullPath($p)
    if ($p.Length -gt 3) { $p = $p.TrimEnd('\') }
    return $p
}

# Unisce un percorso base e uno relativo scritto con le barre "/" (come nel manifesto).
function Join-Relativo([string]$Base, [string]$Relativo) {
    return (Join-Path $Base ($Relativo -replace '/', '\'))
}

function Get-CartellaLaboratorio([string]$Parametro, $Manifesto) {
    if ($Parametro) { return (Resolve-Percorso $Parametro) }
    $variabile = $Manifesto.laboratorio.variabile
    $valore = [Environment]::GetEnvironmentVariable($variabile)
    if ($valore) { return (Resolve-Percorso $valore) }
    return (Join-Path $HOME $Manifesto.laboratorio.predefinito)
}

function Get-CartellaCondivisa([string]$Parametro, $Manifesto, [string]$Radice) {
    if ($Parametro) { return (Resolve-Percorso $Parametro) }
    $valore = [Environment]::GetEnvironmentVariable($Manifesto.condiviso.variabile)
    if ($valore) { return (Resolve-Percorso $valore) }
    return (Join-Path (Split-Path $Radice -Parent) $Manifesto.condiviso.nome_cartella)
}

function Get-CartellaSkill([string]$Parametro, $Manifesto) {
    if ($Parametro) { return (Resolve-Percorso $Parametro) }
    $skill = $Manifesto.condiviso.skill
    $valore = [Environment]::GetEnvironmentVariable($skill.variabile)
    if ($valore) { return (Resolve-Percorso $valore) }
    return (Join-Relativo $HOME $skill.predefinito)
}

# Vero se $Percorso è $Base o sta dentro $Base.
function Test-Dentro([string]$Percorso, [string]$Base) {
    if (-not $Percorso -or -not $Base) { return $false }
    $p = $Percorso.TrimEnd('\') + '\'
    $b = $Base.TrimEnd('\') + '\'
    return $p.StartsWith($b, [System.StringComparison]::OrdinalIgnoreCase)
}

# Cartelle di OneDrive di questo utente (personale e di lavoro).
function Get-CartelleOneDrive {
    $r = @()
    foreach ($n in @('OneDrive', 'OneDriveCommercial', 'OneDriveConsumer')) {
        $v = [Environment]::GetEnvironmentVariable($n)
        if ($v -and ($r -notcontains $v)) { $r += $v }
    }
    return $r
}

# ------------------------------------------------------------------ file

function Get-Hash([string]$Percorso, [string]$Algoritmo = 'SHA256') {
    return (Get-FileHash -LiteralPath $Percorso -Algorithm $Algoritmo).Hash.ToLowerInvariant()
}

# Scrive un file di testo in UTF-8 senza BOM (con -Crlf, fine riga di Windows).
function Write-Testo([string]$Percorso, [string]$Testo, [switch]$Crlf) {
    $t = $Testo -replace "`r`n", "`n"
    if ($Crlf) { $t = $t -replace "`n", "`r`n" }
    [System.IO.File]::WriteAllText($Percorso, $t, (New-Object System.Text.UTF8Encoding -ArgumentList $false))
}

function New-Cartella([string]$Percorso) {
    [void][System.IO.Directory]::CreateDirectory($Percorso)
}

function Format-Dimensione([double]$Byte) {
    $it = [System.Globalization.CultureInfo]::GetCultureInfo('it-IT')
    if ($Byte -ge 1GB) { return ($Byte / 1GB).ToString('0.0', $it) + ' GB' }
    if ($Byte -ge 1MB) { return ($Byte / 1MB).ToString('0.0', $it) + ' MB' }
    if ($Byte -ge 1KB) { return ($Byte / 1KB).ToString('0', $it) + ' KB' }
    return ('{0} byte' -f [int64]$Byte)
}

# Numero di file, byte e file "solo online" di OneDrive (non ancora scaricati) di una cartella.
function Get-Inventario([string]$Cartella) {
    $n = 0
    [int64]$byte = 0
    $online = 0
    if ([System.IO.Directory]::Exists($Cartella)) {
        foreach ($f in @(Get-ChildItem -LiteralPath $Cartella -Recurse -File -Force -ErrorAction SilentlyContinue)) {
            $n++
            $byte += $f.Length
            $attr = [int64]$f.Attributes
            # 0x1000 = Offline, 0x40000 = RecallOnOpen, 0x400000 = RecallOnDataAccess (file di OneDrive solo online)
            if (($attr -band 0x1000) -or ($attr -band 0x40000) -or ($attr -band 0x400000)) { $online++ }
        }
    }
    return [pscustomobject]@{ file = $n; byte = $byte; solo_online = $online }
}

# ------------------------------------------------------------------ programmi esterni

# Mette tra virgolette un argomento secondo le regole di Windows (CommandLineToArgvW).
function ConvertTo-ArgomentoWin([string]$Argomento) {
    if ($Argomento.Length -gt 0 -and $Argomento -notmatch '[\s"]') { return $Argomento }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    $barre = 0
    foreach ($c in $Argomento.ToCharArray()) {
        if ($c -eq [char]'\') { $barre++; continue }
        if ($c -eq [char]'"') {
            [void]$sb.Append('\' * (2 * $barre + 1))
            [void]$sb.Append('"')
            $barre = 0
            continue
        }
        if ($barre -gt 0) { [void]$sb.Append('\' * $barre); $barre = 0 }
        [void]$sb.Append($c)
    }
    if ($barre -gt 0) { [void]$sb.Append('\' * (2 * $barre)) }
    [void]$sb.Append('"')
    return $sb.ToString()
}

# Chiude un processo e tutti i suoi figli.
function Stop-Albero([int]$Id) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot 'System32\taskkill.exe'
    $psi.Arguments = "/T /F /PID $Id"
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $k = [System.Diagnostics.Process]::Start($psi)
    [void]$k.StandardOutput.ReadToEnd()
    [void]$k.StandardError.ReadToEnd()
    [void]$k.WaitForExit(30000)
}

# Lancia un programma e ne cattura l'output, con un tempo massimo.
# Restituisce Codice (-1 se il tempo è scaduto), Uscita (stdout), Errori (stderr), Scaduto.
function Invoke-Programma {
    param(
        [Parameter(Mandatory = $true)][string]$Eseguibile,
        [string[]]$Argomenti = @(),
        [int]$TimeoutSec = 0,
        [string]$Cartella = '',
        [hashtable]$Ambiente = @{}
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Eseguibile
    $psi.Arguments = (@($Argomenti | ForEach-Object { ConvertTo-ArgomentoWin $_ }) -join ' ')
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    if ($Cartella) { $psi.WorkingDirectory = $Cartella }
    foreach ($k in $Ambiente.Keys) { $psi.EnvironmentVariables[$k] = [string]$Ambiente[$k] }
    try {
        $p = [System.Diagnostics.Process]::Start($psi)
    } catch {
        Stop-Errore "Non riesco ad avviare $Eseguibile`: $($_.Exception.Message)"
    }
    $p.StandardInput.Close()
    $uscita = $p.StandardOutput.ReadToEndAsync()
    $errori = $p.StandardError.ReadToEndAsync()
    $scaduto = $false
    if ($TimeoutSec -gt 0) {
        if (-not $p.WaitForExit($TimeoutSec * 1000)) {
            $scaduto = $true
            Stop-Albero $p.Id
        }
    }
    $p.WaitForExit()
    $codice = -1
    if (-not $scaduto) { $codice = $p.ExitCode }
    $r = [pscustomobject]@{ Codice = $codice; Uscita = $uscita.Result; Errori = $errori.Result; Scaduto = $scaduto }
    $p.Dispose()
    return $r
}

function Get-Robocopy { return (Join-Path $env:SystemRoot 'System32\robocopy.exe') }

# Opzioni di robocopy per copiare anche i file che sembrano uguali: /IS (stessa data e dimensione) e /IT
# (attributi diversi). Dove c'è, cioè nei Windows 10 e 11 recenti, anche /IM: un file con la stessa data e la
# stessa dimensione ma un contenuto cambiato (ora di modifica NTFS diversa) per robocopy è "modificato" e senza
# /IM lo salta anche con /IS. Il controllo si fa una volta sola, con robocopy /?.
$Script:OpzioniUguali = $null
function Get-OpzioniUguali {
    if ($null -eq $Script:OpzioniUguali) {
        $opzioni = @('/IS', '/IT')
        # Niente 2>$null: in Windows PowerShell 5.1, con ErrorActionPreference = Stop, fermerebbe lo script.
        $aiuto = @(& (Get-Robocopy) '/?') -join "`n"
        if ($aiuto -match '(?m)^\s*/IM\s*::') { $opzioni += '/IM' }
        $Script:OpzioniUguali = $opzioni
    }
    return $Script:OpzioniUguali
}

function Stop-ErroreRobocopy([string]$Da, [string]$A, [int]$Codice) {
    Stop-Errore "robocopy non è riuscito a copiare `"$Da`" in `"$A`" (codice $Codice)." @(
        'Controlla che nessun programma tenga aperti quei file e che ci sia spazio sul disco, poi rilancia.',
        'Se la cartella di partenza è in OneDrive, controlla che OneDrive sia acceso e collegato.')
}

# Prima di una copia: chiede a robocopy (/L, solo elenco) quali file della destinazione verrebbero sostituiti
# e li copia in $Backup, con gli stessi percorsi relativi. Restituisce quanti ne ha messi da parte.
function Backup-Sostituiti([string[]]$Filtri, [string]$Da, [string]$A, [string]$Backup) {
    $log = Join-Path ([System.IO.Path]::GetTempPath()) ('car-copia-{0}.log' -f [guid]::NewGuid().ToString('N'))
    try {
        # /XX: niente righe per i file che ci sono solo nella destinazione; /UNILOG: elenco in UTF-16, così i nomi
        # con lettere accentate arrivano giusti.
        $argomenti = @($Filtri) + @('/L', '/XX', '/FP', '/NS', '/NC', '/NDL', '/NJH', '/NJS', '/R:0', '/W:0', "/UNILOG:$log")
        & (Get-Robocopy) @argomenti | Out-Null
        if ($LASTEXITCODE -ge 8) { Stop-ErroreRobocopy $Da $A $LASTEXITCODE }
        $n = 0
        if (-not [System.IO.File]::Exists($log)) { return 0 }
        foreach ($riga in [System.IO.File]::ReadAllLines($log, [System.Text.Encoding]::Unicode)) {
            $sorgente = $riga.Trim()
            if (-not $sorgente.StartsWith($Da + '\', [System.StringComparison]::OrdinalIgnoreCase)) { continue }
            $relativo = $sorgente.Substring($Da.Length + 1)
            $vecchio = Join-Path $A $relativo
            if (-not [System.IO.File]::Exists($vecchio)) { continue }
            $copia = Join-Path $Backup $relativo
            New-Cartella (Split-Path $copia -Parent)
            Copy-Item -LiteralPath $vecchio -Destination $copia -Force
            $n++
        }
        return $n
    } finally {
        if ([System.IO.File]::Exists($log)) { Remove-Item -LiteralPath $log -Force }
    }
}

# Copia con robocopy i file nuovi e quelli più recenti. Non cancella mai niente nella destinazione e non sostituisce
# mai un file con uno più vecchio (/XO, anche con -Forza). Con -Forza ricopia anche i file che sembrano uguali
# (stessa data e dimensione). Con -Backup mette prima da parte, nella cartella indicata, i file che sta per sostituire.
# Con -SenzaSottocartelle copia solo i file della cartella di partenza, non quelli delle sottocartelle.
# Restituisce il codice di robocopy, che è una somma di bit: 1 = ha copiato dei file, 2 = nella destinazione ci sono
# file in più (restano), 4 = file non corrispondenti. Da 8 in su ferma lo script. Per sapere se ha copiato: Test-Copiato.
function Invoke-Copia {
    param(
        [Parameter(Mandatory = $true)][string]$Da,
        [Parameter(Mandatory = $true)][string]$A,
        [string[]]$SoloFile = @(),
        [string[]]$EscludiCartelle = @(),
        [string[]]$EscludiFile = @(),
        [string]$Backup = '',
        [switch]$SenzaSottocartelle,
        [switch]$Forza,
        [switch]$Prova
    )
    $da = $Da.TrimEnd('\')
    $a = $A.TrimEnd('\')
    $filtri = @($da, $a) + @($SoloFile)
    if (-not $SenzaSottocartelle) { $filtri += '/E' }
    $filtri += '/XO'
    if ($Forza) { $filtri += @(Get-OpzioniUguali) }
    if (@($EscludiCartelle).Count -gt 0) { $filtri += '/XD'; $filtri += $EscludiCartelle }
    if (@($EscludiFile).Count -gt 0) { $filtri += '/XF'; $filtri += $EscludiFile }
    if ($Backup -and -not $Prova -and [System.IO.Directory]::Exists($a)) {
        $n = Backup-Sostituiti $filtri $da $a $Backup
        if ($n -gt 0) { Write-Info "Prima di sostituirli ho messo da parte $n file in $Backup" }
    }
    $argomenti = $filtri + @('/COPY:DT', '/DCOPY:T', '/R:2', '/W:5', '/XJ', '/MT:8', '/NP', '/NFL', '/NDL', '/NJH')
    # Con -Prova robocopy elenca soltanto (/L) e stampa il riepilogo di cosa copierebbe.
    if ($Prova) { $argomenti += '/L' } else { $argomenti += '/NJS' }
    & (Get-Robocopy) @argomenti | Where-Object { $_.Trim() } | Out-Host
    $codice = $LASTEXITCODE
    if ($codice -ge 8) { Stop-ErroreRobocopy $Da $A $codice }
    return $codice
}

# Vero se il codice di robocopy dice che sono stati copiati dei file (bit 1).
function Test-Copiato([int]$Codice) { return (($Codice -band 1) -ne 0) }

# ------------------------------------------------------------------ musica

# I primi elementi di un elenco, per i messaggi.
function Format-Elenco([string[]]$Voci, [int]$Massimo = 3) {
    $v = @($Voci)
    if ($v.Count -le $Massimo) { return ($v -join ', ') }
    return ('{0} e altri {1}' -f (($v[0..($Massimo - 1)]) -join ', '), ($v.Count - $Massimo))
}

# I soli file di music\ che gli script copiano: music.json, FONTI.md e gli OGG segnaposto del manifesto.
function Get-FileMusica($Voce) {
    $nomi = @(Get-Campo $Voce 'file_di_testo' @())
    $nomi += @((Get-Campo $Voce 'segnaposto_sha256').PSObject.Properties | ForEach-Object { $_.Name })
    return $nomi
}

# Stato di una cartella music\ (del laboratorio o della cartella condivisa), con le regole della voce "music" del manifesto.
# Restituisce Stato e Motivo. Stato vale:
#   'vuota'       niente music.json e nessun file che non sia un segnaposto noto;
#   'segnaposto'  music.json elenca solo brani segnaposto che usano gli OGG del manifesto, ogni OGG ha lo sha256
#                 fissato lì e non c'è nessun altro file;
#   'privata'     c'è almeno un file che non è un segnaposto noto: un brano vero (per esempio di Suno), un OGG
#                 diverso da quello fissato, un file di lavoro di prepare_music.py rimasto a metà;
#   'illeggibile' music.json è rovinato.
# Le sottocartelle in $EscludiCartelle (come _work di prepare_music.py) non contano: gli script non le copiano mai.
# I file in $Ignora (desktop.ini, Thumbs.db...) non contano.
function Get-StatoMusica {
    param([string]$Cartella, $Voce, [string[]]$EscludiCartelle = @(), [string[]]$Ignora = @())
    $r = [pscustomobject]@{ Stato = 'vuota'; Motivo = '' }
    $noti = @{}
    foreach ($p in @((Get-Campo $Voce 'segnaposto_sha256').PSObject.Properties)) {
        $noti[$p.Name.ToLowerInvariant()] = ([string]$p.Value).ToLowerInvariant()
    }
    $testi = @(Get-Campo $Voce 'file_di_testo' @() | ForEach-Object { ([string]$_).ToLowerInvariant() })
    if (-not [System.IO.Directory]::Exists($Cartella)) { $r.Motivo = 'la cartella non c''è'; return $r }
    $base = (Resolve-Percorso $Cartella) + '\'
    $estranei = @()
    $diversi = @()
    foreach ($f in @(Get-ChildItem -LiteralPath $base -Recurse -File -Force -ErrorAction SilentlyContinue)) {
        $relativo = $f.FullName
        if ($relativo.StartsWith($base, [System.StringComparison]::OrdinalIgnoreCase)) { $relativo = $relativo.Substring($base.Length) }
        $parti = @($relativo -split '\\')
        $escluso = $false
        for ($i = 0; $i -lt $parti.Count - 1; $i++) {
            foreach ($x in @($EscludiCartelle)) { if ($parti[$i] -like $x) { $escluso = $true } }
        }
        if ($escluso) { continue }
        $ignorato = $false
        foreach ($x in @($Ignora)) { if ($f.Name -like $x) { $ignorato = $true } }
        if ($ignorato) { continue }
        $nome = $f.Name.ToLowerInvariant()
        if ($parti.Count -eq 1 -and $testi -contains $nome) { continue }
        if ($parti.Count -eq 1 -and $noti.ContainsKey($nome)) {
            if ((Get-Hash $f.FullName) -ne $noti[$nome]) { $diversi += $f.Name }
            continue
        }
        $estranei += $relativo
    }
    $mj = Join-Path $base 'music.json'
    if (-not [System.IO.File]::Exists($mj)) {
        if ($diversi.Count -gt 0 -or $estranei.Count -gt 0) {
            $r.Stato = 'privata'
            $r.Motivo = "manca music.json, ma ci sono file che non sono i segnaposto noti: $(Format-Elenco ($diversi + $estranei))"
        } else {
            $r.Motivo = 'manca music.json'
        }
        return $r
    }
    try { $j = Read-Json $mj } catch {
        $r.Stato = 'illeggibile'
        $r.Motivo = "music.json non si legge: $($_.Exception.Message)"
        return $r
    }
    $r.Stato = 'privata'
    foreach ($t in @(Get-Campo $j 'tracks' @())) {
        $id = [string](Get-Campo $t 'id' '?')
        $testo = '{0} {1} {2}' -f (Get-Campo $t 'source' ''), (Get-Campo $t 'license' ''), (Get-Campo $t 'title' '')
        if ((Get-Campo $t 'placeholder' $false) -ne $true -or $testo -match '(?i)suno') {
            $r.Motivo = "in music.json il brano '$id' non è un segnaposto"
            return $r
        }
        $usati = @([string](Get-Campo $t 'file' '')) + @(@(Get-Campo $t 'layers' @()) | ForEach-Object { [string](Get-Campo $_ 'file' '') })
        foreach ($u in $usati) {
            if (-not $noti.ContainsKey($u.ToLowerInvariant())) {
                $r.Motivo = "in music.json il brano '$id' usa '$u', che non è un segnaposto del manifesto"
                return $r
            }
        }
    }
    if ($diversi.Count -gt 0) {
        $r.Motivo = "$(Format-Elenco $diversi): non è il segnaposto fissato nel manifesto (sha256 diverso)"
        return $r
    }
    if ($estranei.Count -gt 0) {
        $r.Motivo = "ci sono file che non sono segnaposto noti: $(Format-Elenco $estranei)"
        return $r
    }
    $r.Stato = 'segnaposto'
    $r.Motivo = 'solo i brani segnaposto noti'
    return $r
}
