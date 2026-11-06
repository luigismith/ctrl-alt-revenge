#Requires -Version 5.1
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
    Aggiorna la cartella privata condivisa in OneDrive con il laboratorio di questo PC.

.DESCRIPTION
    La cartella condivisa è ctrlaltrevenge-lab-condiviso, accanto al repo (oppure $env:CAR_CONDIVISO).
    Lo script ci copia:
      - dal laboratorio ($env:CAR_LAB o %USERPROFILE%\ctrlaltrevenge-lab): sources, note-private,
        suno (solo i testi, mai i brani), ricerca-2026-11-03;
      - le sei skill di Godot da %USERPROFILE%\.claude\skills (oppure $env:CAR_SKILLS_DIR);
      - le due locandine di riferimento da docs\riferimenti-estetica del repo, finché ci sono.
    La musica non ci va mai: quella segnaposto la ricrea prepara_laboratorio.ps1 in ogni laboratorio, i brani di Suno
    stanno solo nel laboratorio di ogni PC.
    Copia solo i file nuovi o più recenti: non cancella mai niente e non sostituisce mai un file della cartella
    condivisa con uno più vecchio. Alla fine scrive LEGGIMI.md e inventario.json.
    La cartella è privata: mai nel repo, mai condivisa con altri, niente brani di Suno.

.PARAMETER Forza
    Ricopia anche i file che sembrano uguali (stessa data e stessa dimensione). Non sostituisce comunque mai un
    file della cartella condivisa con uno più vecchio.

.PARAMETER Prova
    Mostra cosa copierebbe, senza copiare né scrivere niente.

.PARAMETER Laboratorio
    Cartella del laboratorio. Vince su $env:CAR_LAB.

.PARAMETER Condiviso
    Cartella condivisa. Vince su $env:CAR_CONDIVISO.

.PARAMETER CartellaSkill
    Cartella delle skill di Claude Code. Vince su $env:CAR_SKILLS_DIR.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\setup\aggiorna_condiviso.ps1"
#>
[CmdletBinding()]
param(
    [switch]$Forza,
    [switch]$Prova,
    [string]$Laboratorio = '',
    [string]$Condiviso = '',
    [string]$CartellaSkill = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comune.ps1')

$Script:Righe = New-Object System.Collections.Generic.List[object]

# Una riga del riepilogo e della tabella di LEGGIMI.md.
function Add-Riga([string]$Cartella, [string]$Descrizione, [string]$Destinazione, [string]$Esito) {
    $Script:Righe.Add([pscustomobject]@{ Cartella = $Cartella; Descrizione = $Descrizione; Destinazione = $Destinazione; Esito = $Esito })
}

function Show-Configurazione {
    Write-Titolo 'CTRL+ALT REVENGE: aggiornamento della cartella privata condivisa'
    Write-Info "PC:                 $env:COMPUTERNAME (utente $env:USERNAME), PowerShell $($PSVersionTable.PSVersion)"
    Write-Info "Repo:               $Radice"
    Write-Info "Laboratorio:        $Lab"
    Write-Info "Skill di Claude:    $Skill"
    Write-Info "Cartella condivisa: $Cond"
    if ($Forza) { Write-Info 'Opzione -Forza: ricopio anche i file che sembrano uguali, ma mai sopra file più nuovi.' }
    if ($Prova) { Write-Info 'Opzione -Prova: mostro solo cosa copierei, senza copiare.' }
}

function Test-Preliminari {
    if (-not [System.IO.Directory]::Exists($Lab)) {
        Stop-Errore "Non trovo il laboratorio $Lab." @('Indica la cartella giusta con -Laboratorio o con la variabile CAR_LAB.')
    }
    if (Test-Dentro $Cond $Radice) {
        Stop-Errore "La cartella condivisa ($Cond) è dentro il repo: finirebbe su GitHub." @('Deve stare accanto al repo, non dentro.')
    }
    if ((Test-Dentro $Cond $Lab) -or (Test-Dentro $Lab $Cond)) {
        Stop-Errore 'Il laboratorio e la cartella condivisa non possono stare uno dentro l''altra.' @('Controlla -Laboratorio, -Condiviso, CAR_LAB e CAR_CONDIVISO.')
    }
    $inOneDrive = $false
    foreach ($od in @(Get-CartelleOneDrive)) { if (Test-Dentro $Cond $od) { $inOneDrive = $true } }
    if (-not $inOneDrive) {
        Write-Avviso "La cartella condivisa non è dentro OneDrive: non arriverà sull'altro PC da sola."
    }
    if (-not [System.IO.Directory]::Exists($Cond)) {
        if ($Prova) {
            Write-Info 'La cartella condivisa non c''è ancora: la creerei.'
        } else {
            New-Cartella $Cond
            Write-Ok "creata la cartella condivisa $Cond"
        }
    }
}

# Copia una cartella del laboratorio (o del repo) nella cartella condivisa, con le regole del manifesto.
function Copy-Voce($Voce, [string]$Destinazione, [switch]$SoloCondiviso) {
    $c = $Manifesto.condiviso
    $nome = [string]$Voce.cartella
    $descrizione = [string]$Voce.descrizione
    $dalRepo = [string](Get-Campo $Voce 'dal_repo' '')
    if ($dalRepo) { $da = Join-Relativo $Radice $dalRepo } else { $da = Join-Path $Lab $nome }
    $a = Join-Path $Cond $nome
    Write-Titolo "$nome  ($da)"
    if (-not [System.IO.Directory]::Exists($da)) {
        if ($dalRepo) {
            Write-Info "Nel repo non c'è più $dalRepo`: restano le copie già nella cartella condivisa."
            Add-Riga $nome $descrizione $Destinazione 'non più nel repo'
        } elseif ($SoloCondiviso) {
            Write-Info "$nome non è nel laboratorio di questo PC: resta la copia già nella cartella condivisa."
            Add-Riga $nome $descrizione $Destinazione 'solo qui'
        } else {
            Write-Avviso "Nel laboratorio manca $nome`: la salto."
            Add-Riga $nome $descrizione $Destinazione 'manca nel laboratorio'
        }
        return
    }
    $escludiCartelle = @($c.escludi_cartelle) + @(Get-Campo $Voce 'escludi_cartelle' @())
    $escludiFile = @($c.escludi_file) + @(Get-Campo $Voce 'escludi_file' @())
    $soloFile = @(Get-Campo $Voce 'solo_file' @())
    if ($soloFile.Count -gt 0) { Write-Info "Copio solo: $($soloFile -join ' ')" }
    $codice = Invoke-Copia -Da $da -A $a -SoloFile $soloFile -EscludiCartelle $escludiCartelle -EscludiFile $escludiFile -Forza:$Forza -Prova:$Prova
    $esito = 'già aggiornata'
    if (Test-Copiato $codice) { $esito = 'aggiornata' }
    if ($Prova) { $esito = 'prova' }
    Write-Ok "$nome`: $esito."
    Add-Riga $nome $descrizione $Destinazione $esito
}

function Copy-Skill {
    $s = $Manifesto.condiviso.skill
    $base = Join-Path $Cond $s.cartella
    Write-Titolo "$($s.cartella)  ($Skill)"
    $copiate = 0
    foreach ($nome in @($s.nomi)) {
        $da = Join-Path $Skill $nome
        if (-not [System.IO.Directory]::Exists($da)) {
            Stop-Errore "Non trovo la skill $nome in $Skill." @(
                'Le sei skill di Godot devono essere installate su questo PC prima di aggiornare la cartella condivisa.',
                'Se stanno altrove, indica la cartella con -CartellaSkill o con la variabile CAR_SKILLS_DIR.')
        }
        foreach ($f in @($s.file_obbligatori)) {
            if (-not [System.IO.File]::Exists((Join-Path $da $f))) {
                Stop-Errore "Nella skill $nome manca $f." @('Ogni skill copiata deve avere SKILL.md, FONTE.md (da dove viene) e LICENSE.')
            }
        }
        $codice = Invoke-Copia -Da $da -A (Join-Path $base $nome) -EscludiCartelle @($Manifesto.condiviso.escludi_cartelle) -EscludiFile @($Manifesto.condiviso.escludi_file) -Forza:$Forza -Prova:$Prova
        if (Test-Copiato $codice) { $copiate++ }
    }
    $esito = 'già aggiornate'
    if ($copiate -gt 0) { $esito = "aggiornate $copiate" }
    if ($Prova) { $esito = 'prova' }
    Write-Ok "$(@($s.nomi).Count) skill: $esito (fonte $($s.fonte), commit $($s.commit.Substring(0, 8)), $($s.licenza))."
    Add-Riga $s.cartella "le sei skill di Godot per Claude Code ($($s.licenza), con FONTE.md e LICENSE)" '%USERPROFILE%\.claude\skills' $esito
}

function Write-Inventario {
    $cartelle = [ordered]@{}
    [int64]$totByte = 0
    $totFile = 0
    foreach ($r in $Script:Righe) {
        $inv = Get-Inventario (Join-Path $Cond $r.Cartella)
        $cartelle[$r.Cartella] = [ordered]@{ file = $inv.file; byte = $inv.byte }
        Add-Member -InputObject $r -NotePropertyName File -NotePropertyValue $inv.file
        Add-Member -InputObject $r -NotePropertyName Byte -NotePropertyValue $inv.byte
        $totFile += $inv.file
        $totByte += $inv.byte
    }
    $data = Get-Date -Format 'yyyy-MM-dd HH:mm'
    # JSON scritto a mano, una cartella per riga: ConvertTo-Json di PowerShell 5.1 lo renderebbe illeggibile.
    $j = @('{')
    $j += '  "nota": ' + ('Scritto da tools/setup/aggiorna_condiviso.ps1. prepara_laboratorio.ps1 lo usa per capire se OneDrive ha finito di scaricare la cartella.' | ConvertTo-Json -Compress) + ','
    $j += '  "aggiornato": ' + ($data | ConvertTo-Json -Compress) + ','
    $j += '  "pc": ' + ([string]$env:COMPUTERNAME | ConvertTo-Json -Compress) + ','
    $j += '  "cartelle": {'
    $nomi = @($cartelle.Keys)
    for ($i = 0; $i -lt $nomi.Count; $i++) {
        $v = $cartelle[$nomi[$i]]
        $virgola = ','
        if ($i -eq $nomi.Count - 1) { $virgola = '' }
        $j += ('    {0}: {{"file": {1}, "byte": {2}}}{3}' -f ([string]$nomi[$i] | ConvertTo-Json -Compress), $v.file, $v.byte, $virgola)
    }
    $j += '  },'
    $j += ('  "totale": {{"file": {0}, "byte": {1}}}' -f $totFile, $totByte)
    $j += '}'
    $testo = ($j -join "`n") + "`n"
    [void]($testo | ConvertFrom-Json)
    Write-Testo (Join-Path $Cond $Manifesto.condiviso.inventario) $testo
    return [pscustomobject]@{ File = $totFile; Byte = $totByte; Data = $data }
}

function Write-Leggimi($Totale) {
    $t = @()
    $t += '# Cartella privata del laboratorio di CTRL+ALT REVENGE'
    $t += ''
    $t += '> **Questa cartella è PRIVATA.** Non va mai nel repository pubblico su GitHub e non si condivide con nessuno:'
    $t += '> niente link di condivisione di OneDrive, niente copie su chiavette o su altri servizi.'
    $t += ''
    $t += 'Serve a portare da un PC all''altro (quello di lavoro e quello di casa) le cose del laboratorio che uno script'
    $t += 'non può riscaricare in modo affidabile (i pacchetti di Quaternius e OpenGameArt) o che sono solo nostre.'
    $t += ''
    $t += '- La riempie `tools\setup\aggiorna_condiviso.ps1` del repo, con il laboratorio del PC su cui si lancia (di solito quello di lavoro).'
    $t += '- `tools\setup\prepara_laboratorio.ps1` la copia nel laboratorio di ogni PC (`%USERPROFILE%\ctrlaltrevenge-lab`).'
    $t += '- Tutti e due copiano solo i file nuovi o più recenti: non cancellano niente e non sostituiscono mai un file con uno più vecchio.'
    $t += '  `prepara_laboratorio.ps1` mette prima da parte in `ctrlaltrevenge-lab\backup\` i file del laboratorio che sostituisce.'
    $t += '- La guida completa è `docs\lavorare-da-casa.md`, nel repo.'
    $t += ''
    $t += "Ultimo aggiornamento: $($Totale.Data), da $env:COMPUTERNAME."
    $t += ''
    $t += '## Cosa contiene'
    $t += ''
    $t += '| Cartella | Cosa c''è | Dove va | File | Dimensione |'
    $t += '|---|---|---|---:|---:|'
    foreach ($r in $Script:Righe) {
        $t += ('| `{0}\` | {1} | {2} | {3} | {4} |' -f $r.Cartella, $r.Descrizione, $r.Destinazione, $r.File, (Format-Dimensione $r.Byte))
    }
    $t += ('| **Totale** | | | **{0}** | **{1}** |' -f $Totale.File, (Format-Dimensione $Totale.Byte))
    $t += ''
    $t += '`inventario.json` riassume gli stessi numeri: `prepara_laboratorio.ps1` lo usa per capire se OneDrive ha finito di scaricare la cartella.'
    $t += ''
    $t += '## Cosa NON contiene, mai'
    $t += ''
    $t += '- **La musica**: né i brani di Suno (WAV scaricati e OGG preparati per il gioco) né quella segnaposto. I brani di Suno su ogni'
    $t += '  PC si riscaricano dall''account Suno (in `%USERPROFILE%\ctrlaltrevenge-lab\suno\`), oppure li genera Claude direttamente nel'
    $t += '  browser, con Claude in Chrome; poi si preparano nel laboratorio con `tools\audio\prepare_music.py`. La musica segnaposto CC0'
    $t += '  la ricrea `prepara_laboratorio.ps1` nel laboratorio, con `tools\audio\make_placeholder_music.py`, sempre uguale (sha256'
    $t += '  fissati in `tools\setup\laboratorio.json`). Da `suno\` gli script copiano solo i testi (`*.md`, `*.txt`).'
    $t += '- **Gli strumenti** (Godot, Blender, FFmpeg, PyMusicLooper, Python): li scarica e li verifica `prepara_laboratorio.ps1`, dagli'
    $t += '  indirizzi ufficiali e con gli hash scritti in `tools\setup\laboratorio.json`.'
    $t += '- **Password, token, chiavi API**: mai, né qui né nel repo.'
    $t += ''
    $t += '## Regole'
    $t += ''
    $t += '- Non modificare i file qui a mano: si cambiano nel laboratorio e poi si rilancia `aggiorna_condiviso.ps1`, che copia i file nuovi'
    $t += '  o più recenti e non cancella niente.'
    $t += '- Prima di cambiare PC aspetta che OneDrive abbia finito di sincronizzare (icona di OneDrive senza frecce).'
    $t += '- Le licenze dei modelli CC0 sono verificate in `tools\sprites\FONTI.md` e `tools\env\FONTI.md` del repo; quelle delle skill'
    $t += '  in `skills\<nome>\FONTE.md` e `LICENSE` (LGPL-3.0).'
    $t += '- Le due immagini in `riferimenti-estetica\` sono state generate con ChatGPT: servono solo come riferimento per lo stile e non'
    $t += '  vanno né nel gioco né nel repo.'
    Write-Testo (Join-Path $Cond 'LEGGIMI.md') (($t -join "`n") + "`n")
}

# ------------------------------------------------------------------ programma principale

try {
    $Radice = Resolve-Percorso (Join-Path $PSScriptRoot '..\..')
    $Manifesto = Read-Manifesto (Join-Path $PSScriptRoot 'laboratorio.json')
    $Lab = Get-CartellaLaboratorio $Laboratorio $Manifesto
    $Cond = Get-CartellaCondivisa $Condiviso $Manifesto $Radice
    $Skill = Get-CartellaSkill $CartellaSkill $Manifesto

    Show-Configurazione
    Test-Preliminari

    $c = $Manifesto.condiviso
    foreach ($v in @($c.nel_laboratorio)) { Copy-Voce $v ("laboratorio (``$($v.cartella)\``)") }
    foreach ($v in @($c.solo_condiviso)) { Copy-Voce $v 'resta qui' -SoloCondiviso }
    Copy-Skill

    if ($Prova) {
        Write-Host ''
        Write-Host 'Prova finita: non ho copiato né scritto niente.' -ForegroundColor Green
        exit 0
    }

    $totale = Write-Inventario
    Write-Leggimi $totale
    Write-Titolo 'Riepilogo della cartella condivisa'
    foreach ($r in $Script:Righe) {
        Write-Host ('  {0,-22} {1,6} file {2,10}   {3}' -f $r.Cartella, $r.File, (Format-Dimensione $r.Byte), $r.Esito)
    }
    Write-Host ('  {0,-22} {1,6} file {2,10}' -f 'Totale', $totale.File, (Format-Dimensione $totale.Byte)) -ForegroundColor Green
    Write-Host ''
    Write-Host "Scritti LEGGIMI.md e $($c.inventario) in $Cond" -ForegroundColor Green
    Write-Host 'Prima di passare all''altro PC aspetta che OneDrive abbia caricato tutto (icona di OneDrive senza frecce).' -ForegroundColor Yellow
} catch {
    Write-Errore $_
    exit 1
}
exit 0
