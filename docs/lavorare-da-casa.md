# Lavorare da casa (e su due PC)

CTRL+ALT REVENGE si sviluppa su due PC: quello di **lavoro** e quello di **casa**. Questa guida spiega dove sta ogni cosa, cosa fare la prima volta a casa e le poche regole da rispettare ogni giorno.

## 1. Dove sta cosa

| Cosa | Dove | Come arriva sull'altro PC |
|---|---|---|
| **Repo**: codice, grafica ed effetti sonori del gioco, documenti, script | `Documenti\ClaudeCode\ctrlaltrevenge`, nel OneDrive di lavoro | da solo, con OneDrive. GitHub ne tiene una copia di sicurezza |
| **Laboratorio**: Godot, Blender, FFmpeg, Python, modelli 3D, musica segnaposto, ricerca | `%USERPROFILE%\ctrlaltrevenge-lab`, su ogni PC, **fuori** da OneDrive | lo crea lo script `prepara_laboratorio.ps1` (vedi sotto) |
| **Cartella privata condivisa**: modelli CC0, note private, ricerca, locandine, skill di Claude | `Documenti\ClaudeCode\ctrlaltrevenge-lab-condiviso`, nel OneDrive di lavoro, accanto al repo | da sola, con OneDrive. La riempie lo script `aggiorna_condiviso.ps1` |
| **Storia e gameplay**: `docs\lore\` (con `gameplay.md`) | nella cartella del repo, ma fuori dal repo pubblico | da sola, con OneDrive. La copia di sicurezza è un repo privato su GitHub |
| **Brani di Suno** | solo nel laboratorio di ogni PC (`suno\` e `music\`) | non viaggiano: vedi la sezione 4 |

Il **OneDrive di lavoro** è quello con l'account dell'azienda: in Esplora file la sua cartella si chiama "OneDrive -" seguito dal nome dell'azienda, in PowerShell è `$env:OneDriveCommercial`.

`%USERPROFILE%` è la cartella del tuo utente Windows, per esempio `C:\Users\Admin`: sui due PC può essere diversa. Gli script la trovano da soli.

La cartella condivisa è **privata**: non va mai nel repo e non si condivide con nessuno (niente link di OneDrive). Dentro c'è un `LEGGIMI.md` con l'elenco di cosa contiene.

### Cosa c'è su GitHub e cosa no

Il repo `ctrl-alt-revenge` su GitHub è pubblico.

| Nel repo pubblico | Mai nel repo pubblico |
|---|---|
| il codice del gioco e degli strumenti | la musica, sia quella segnaposto sia quella di Suno |
| la grafica e gli effetti sonori fatti da noi | i modelli 3D e le animazioni CC0 di partenza (`sources`) |
| i documenti pubblici: la specifica e questa guida | la storia completa e il gameplay: `docs\lore\` |
| `tools/setup`: l'elenco degli strumenti e gli script del laboratorio | le note private, la ricerca, le locandine fatte con ChatGPT, i programmi (Godot, Blender...), password e chiavi |

La storia completa resta nella cartella del repo, ma il repo pubblico la ignora (è nel `.gitignore`). La copia di sicurezza di `docs\lore\`, con la cronologia e il gameplay (`docs\lore\gameplay.md`, dal 6 novembre 2026), è il repo **privato** `ctrl-alt-revenge-storia`: come si aggiorna è nella sezione 3.

## 2. La prima volta sul PC di casa

**Prima di cominciare:**
- sul PC devono esserci il OneDrive di lavoro (con il tuo account dell'azienda) e Claude Code;
- OneDrive deve aver finito di scaricare la cartella `ClaudeCode` (icona della nuvola senza frecce blu);
- consigliato: in Esplora file, tasto destro su `ctrlaltrevenge` e poi su `ctrlaltrevenge-lab-condiviso` > **Mantieni sempre su questo dispositivo**. Così i file sono davvero sul disco, non solo online.

**Strada facile: chiedi a Claude.**
1. In Esplora file apri la cartella del repo: `Documenti\ClaudeCode\ctrlaltrevenge`, nel OneDrive di lavoro.
2. Clicca sulla barra degli indirizzi, scrivi `powershell` e premi Invio: si apre PowerShell già nella cartella giusta.
3. Scrivi `claude` e premi Invio.
4. Scrivi a Claude: **prepara il laboratorio**. Lancia lui lo script, legge i messaggi e ti dice se devi fare qualcosa.

**Strada a mano.** Dalla stessa finestra di PowerShell (passi 1 e 2 qui sopra):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\prepara_laboratorio.ps1
```

- Se manca qualcosa (git, Python 3.14 o uv), lo script si ferma e scrive i comandi per installarlo. Puoi anche lasciarlo fare a lui aggiungendo `-InstallaMancanti` in fondo al comando. Non servono i diritti di amministratore.
- Se non trova la cartella condivisa si ferma subito, prima di scaricare qualsiasi cosa.
- La prima volta ci vogliono da pochi minuti a un quarto d'ora, secondo la connessione: scarica circa 0,7 GB di programmi e copia circa 1,3 GB dalla cartella condivisa. Il laboratorio finito occupa circa 4 GB.
- **Non tocca i tuoi file.** Dalla cartella condivisa prende solo i file più nuovi: non sostituisce mai un file del laboratorio con uno più vecchio, e quelli che sostituisce li mette prima da parte in `ctrlaltrevenge-lab\backup\<data>\`. Se in `music\` ci sono brani veri, non la tocca.
- **Rifà da capo solo ciò che si può ricreare**, quando serve o con `-Forza`: i programmi, i due ambienti Python e Gioca.bat. Quando ricrea un ambiente Python, i pacchetti aggiunti a mano si perdono: l'elenco di quelli che c'erano finisce in `ctrlaltrevenge-lab\logs\`.
- Alla fine scrive **Fatto** e un riepilogo. Se un passo non riesce, il riepilogo mostra anche i passi rimasti "non fatto". Per giocare: doppio clic su `%USERPROFILE%\ctrlaltrevenge-lab\Gioca.bat`.
- Riavvia Claude Code, così vede le sei skill di Godot appena installate.

**Cosa fa lo script**, in dieci passi:

| Passo | Cosa fa |
|---|---|
| 1. Prerequisiti | controlla git con Git Bash, Python 3.14 (comando `py`) e uv |
| 2-4. Godot, Blender, FFmpeg | li scarica dai siti ufficiali e controlla che siano identici agli originali (hash) |
| 5-6. Python | crea il venv del laboratorio e installa PyMusicLooper, con le versioni fissate |
| 7. Cartella condivisa | copia nel laboratorio `sources`, `music` (solo la musica segnaposto), `note-private`, `suno` (solo i testi) e `ricerca-2026-11-03` |
| 8. Skill | installa le sei skill di Godot in `%USERPROFILE%\.claude\skills` |
| 9. Gioca.bat | lo scrive con i percorsi di questo PC |
| 10. Verifica | importa il gioco e lancia i test automatici: devono finire con `DONE` |

Si può rilanciare quando si vuole: salta ciò che è già a posto. Opzioni utili:

| Opzione | A cosa serve |
|---|---|
| `-InstallaMancanti` | installa con winget git, Python 3.14 e uv, se mancano |
| `-Forza` | quando qualcosa sembra rotto: reinstalla i programmi, ricrea i due ambienti Python, ricopia le skill e riscrive Gioca.bat. Non vale per il passo 7: dalla cartella condivisa arrivano sempre e solo i file più nuovi |
| `-Solo godot,verifica` | fa solo i passi indicati (nomi: prerequisiti, godot, blender, ffmpeg, venv, pymusiclooper, condivisi, skill, gioca, verifica) |
| `-SaltaVerifica` | non lancia i test alla fine |

Se preferisci installare tu i prerequisiti, questi sono i comandi (poi chiudi e riapri PowerShell):

```powershell
winget install --id Git.Git -e --scope user
winget install --id Python.PythonInstallManager -e
py install 3.14
winget install --id astral-sh.uv -e
```

## 3. Le regole di ogni giorno

1. **Un PC alla volta.** Non lavorare, e non far lavorare Claude, sui due PC nello stesso momento: OneDrive mescolerebbe i file e il repo si può rovinare.
2. **Prima di cambiare PC, aspetta OneDrive.**
   - Sul PC che lasci: chiudi Godot, Blender e Claude Code, poi aspetta che l'icona di OneDrive non mostri più frecce blu.
   - Sul PC dove arrivi: aspetta la stessa cosa prima di aprire il progetto.
3. **A fine giornata, copia di sicurezza su GitHub.**
   - Il modo semplice: chiedi a Claude "fai il commit e il push su GitHub, anche della storia".
   - **Il repo pubblico.** Il ramo di lavoro è `master` (il vecchio prototipo Pygame è nel ramo `legacy-pygame`). A mano, nella cartella del repo:

     | Comando | A cosa serve |
     |---|---|
     | `git status` | mostra cosa è cambiato |
     | `git push origin master` | manda su GitHub i commit fatti |
     | `git pull --ff-only origin master` | prende da GitHub le novità fatte altrove (per esempio da Claude sul web) |
     
   - **La storia.** `docs\lore\` è un repo git a parte, collegato al repo privato `ctrl-alt-revenge-storia`. A mano, sempre dalla cartella del repo, ma prima un controllo: `git -C docs\lore rev-parse --show-toplevel` deve finire con `docs/lore`. Se finisce con `ctrlaltrevenge`, il repo della storia su questo PC non c'è: non andare avanti, perché i comandi qui sotto agirebbero sul repo pubblico, e chiedi a Claude.

     | Comando | A cosa serve |
     |---|---|
     | `git -C docs\lore status` | mostra cosa è cambiato nella storia |
     | `git -C docs\lore add -A` | prepara tutte le modifiche |
     | `git -C docs\lore commit -m "Cosa è cambiato"` | le salva con un messaggio |
     | `git -C docs\lore push` | le manda sul repo privato |

   - Passando da un PC all'altro non serve il pull: il repo, comprese le cartelle `.git`, arriva con OneDrive. GitHub serve da copia di sicurezza e per ripartire se qualcosa si rompe.
   - La prima volta che fai il push dal PC di casa, git apre il browser per farti accedere a GitHub: è normale.
4. **Hai cambiato cose nel laboratorio?** Per esempio modelli nuovi in `sources` o note in `note-private`.
   - Su quel PC, prima di cambiare PC, lancia:
     ```powershell
     powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\aggiorna_condiviso.ps1
     ```
     Copia nella cartella condivisa solo i file nuovi o più recenti e non cancella niente. Con `-Prova` mostra cosa copierebbe, senza copiare. Con `-Forza` ricopia anche i file che sembrano uguali, ma non sostituisce mai un file della cartella condivisa con uno più vecchio.
   - Sull'altro PC rilancia `prepara_laboratorio.ps1`: copia solo le novità.
   - Se cambi la stessa nota sui due PC senza passare dalla cartella condivisa, al giro dopo vince la versione più recente; l'altra, nel laboratorio, finisce in `backup\`.
5. **Nel repo non vanno mai** musica, brani di Suno, modelli CC0 di partenza, note private, la storia completa o immagini fatte con l'AI. Prima di ogni commit un controllo automatico (`tools/guard_assets.py`) blocca l'audio e i file grandi, ma non può riconoscere tutto.

## 4. La musica (Suno)

- **Oggi** il gioco usa musica segnaposto CC0 (Free VGMs di Safety Stoat Studios). Arriva con la cartella condivisa e sta in `%USERPROFILE%\ctrlaltrevenge-lab\music\`.
- **I brani veri** si faranno con Suno, con il tuo abbonamento Pro. Quando sarà il momento, Claude si collega e usa Suno direttamente nel tuo browser (Claude in Chrome), sul PC dove stai lavorando:
  1. genera le varianti con i prompt di `%USERPROFILE%\ctrlaltrevenge-lab\suno\PROMPT.md`;
  2. tu ascolti e scegli;
  3. Claude scarica il WAV (Chrome lo mette in Download) e lo sposta in `ctrlaltrevenge-lab\suno\`;
  4. lo prepara per il gioco con `tools\audio\prepare_music.py` (loop, volume, OGG in `ctrlaltrevenge-lab\music\`).
- **I brani di Suno non vanno né nel repo né nella cartella condivisa.** Sull'altro PC si riscaricano dalla tua libreria di Suno, oppure lo fa Claude nel browser; poi si ripete il passo 4. Ricorda che ogni download conta nel limite del mese (vedi `PROMPT.md`).
- **Come ti proteggono gli script.**
  - `aggiorna_condiviso.ps1` copia da `music\` solo `music.json`, `FONTI.md` e i quattro OGG segnaposto, e solo se ognuno è identico (sha256) a quello fissato in `tools\setup\laboratorio.json`. Se trova un brano vero, un OGG diverso o un file che non conosce, non copia niente di `music\`.
  - La cartella di lavoro `music\_work\` di `prepare_music.py` non viaggia mai. Da `suno\` si copiano solo i testi (`*.md`, `*.txt`).
  - `prepara_laboratorio.ps1` fa gli stessi controlli: non tocca `music\` se ci sono brani veri, e non copia una `music\` condivisa che contiene file sconosciuti.
  - Gli script non possono riconoscere un brano salvato altrove: i brani tienili solo in `suno\` e in `music\`.
- Durante lo sviluppo il gioco cerca la musica solo in `%USERPROFILE%\ctrlaltrevenge-lab\music\`: lascia il laboratorio nella sua cartella predefinita, altrimenti il gioco resta muto.

## 5. Problemi probabili

| Cosa vedi | Perché | Cosa fare |
|---|---|---|
| "l'esecuzione di script è disabilitata nel sistema" | Windows blocca gli script di PowerShell | lancia sempre con `powershell -NoProfile -ExecutionPolicy Bypass -File ...`, come nei comandi qui sopra |
| "La cartella condivisa non è ancora completa su questo PC" | OneDrive la sta ancora scaricando | aspetta, oppure tasto destro sulla cartella > Mantieni sempre su questo dispositivo; poi rilancia. Se lo dice all'inizio, intanto lo script installa i programmi |
| "Non trovo la cartella condivisa" | OneDrive non ha ancora sincronizzato `ClaudeCode` | controlla che il OneDrive di lavoro sia acceso e collegato; se manca anche al lavoro, lancia lì `aggiorna_condiviso.ps1` |
| "Mancano dei prerequisiti" | manca git, Python 3.14 o uv | usa i comandi che lo script stampa, oppure rilancia con `-InstallaMancanti`; poi chiudi e riapri PowerShell |
| "l'hash non torna" o "checksum ufficiale diverso" | download rovinato, oppure il file sul sito è cambiato | rilancia lo script, che riscarica. Se si ripete, non usare il file e chiedi a Claude |
| Download lento o interrotto | la rete | rilancia: salta ciò che è già a posto e riparte da lì |
| "music: nel laboratorio non c'è solo la musica segnaposto" | in `music\` ci sono brani veri, per esempio di Suno, o un brano preparato a metà | se hai preparato dei brani è normale: lo script non tocca la cartella. Altrimenti fai leggere il messaggio a Claude |
| "music: nella cartella condivisa non c'è solo la musica segnaposto nota" | nella cartella condivisa è finito un file che non dovrebbe esserci | non copiarlo a mano: chiedi a Claude di controllare |
| "Prima di sostituirli ho messo da parte N file" | dalla cartella condivisa sono arrivate versioni più nuove di file del laboratorio | i file di prima sono in `ctrlaltrevenge-lab\backup\<data>\`: se ti servivano, recuperali da lì |
| Il gioco parte ma è muto | manca `ctrlaltrevenge-lab\music\`, oppure il laboratorio non è nella cartella predefinita | rilancia `prepara_laboratorio.ps1` e lascia il laboratorio in `%USERPROFILE%\ctrlaltrevenge-lab` |
| Gioca.bat dice "Godot non trovato" | il laboratorio non è pronto o è stato spostato | rilancia `prepara_laboratorio.ps1`: riscrive Gioca.bat con i percorsi giusti |
| Compaiono file con il nome del PC in fondo (per esempio `level-NOMEPC.gd`) | OneDrive ha visto lo stesso file cambiato sui due PC | tieni la versione giusta e cancella l'altra. Se il file è dentro `game\.godot`, cancella pure tutta la cartella `.godot`: è una cache e Godot la rifà. Se è dentro una cartella `.git`, non toccarlo: chiedi a Claude |
| git dice "bad object", "index file corrupt" o simili | OneDrive ha sincronizzato `.git` a metà | non fare altri commit, aspetta OneDrive e chiedi a Claude: il repo si ripristina da GitHub |
| "Godot è andato in crash durante l'importazione" | Godot 4.7.2 ogni tanto va in crash alla prima importazione | lo script riprova da solo, fino a tre volte. Se non basta, rilancia |
| La verifica finale (passo 10) fallisce | c'è un lavoro in corso nel gioco, oppure mancano dei file | il resto del laboratorio è pronto. Il log è in `ctrlaltrevenge-lab\logs\`: fallo leggere a Claude |
| Con `-Forza`: "Non riesco a sostituire i file" | Godot o Blender sono aperti | chiudili e rilancia |
| Claude Code non vede le skill di Godot | va riavviato dopo l'installazione | chiudi e riapri Claude Code |
| Poco spazio sul disco | il laboratorio occupa circa 4 GB | si può svuotare `ctrlaltrevenge-lab\downloads\`: ci sono gli archivi già installati (circa 0,6 GB) e la cache dei pacchetti Python. I venv restano a posto, ma la cache libera poco, perché i venv usano gli stessi file. Anche `ctrlaltrevenge-lab\backup\` si può svuotare, dopo averci guardato dentro |

## 6. Dettagli per Claude

- `tools/setup/laboratorio.json`: versioni, URL ufficiali e hash di tutto ciò che si scarica, più l'elenco delle cartelle che arrivano dalla cartella condivisa e le regole per `music` (gli sha256 dei quattro OGG segnaposto). Se si rifà la musica segnaposto, quegli hash vanno aggiornati, altrimenti gli script trattano `music` come privata e non la copiano più.
- `tools/setup/prepara_laboratorio.ps1` e `tools/setup/aggiorna_condiviso.ps1`, con le funzioni comuni in `tools/setup/comune.ps1`. Funzionano in Windows PowerShell 5.1 e in PowerShell 7.
- Le copie usano sempre robocopy `/XO`, anche con `-Forza`. `prepara_laboratorio.ps1`, prima di copiare, chiede a robocopy (`/L`) quali file sostituirebbe e li mette in `<laboratorio>\backup\<data>\`.
- Variabili d'ambiente, tutte facoltative: `CAR_LAB` (laboratorio), `CAR_CONDIVISO` (cartella condivisa), `CAR_SKILLS_DIR` (skill). Gli stessi percorsi si possono dare agli script con `-Laboratorio`, `-Condiviso` e `-CartellaSkill`. `tools/env` e `tools/fxui` ignorano `CAR_LAB` e cercano solo `%USERPROFILE%\ctrlaltrevenge-lab`.
- Il primo giro di `prepara_laboratorio.ps1` dura qualche minuto e stampa le barre di avanzamento di curl: lancialo in background o con un timeout lungo (10 minuti).
- Nella verifica finale Godot gira con `APPDATA` spostata in `<laboratorio>\logs\verifica-<data>-appdata`: lì finisce `user://` del progetto (log, cache), non in `%APPDATA%\Godot\app_userdata`, dove stanno i dati del gioco. I log dell'importazione e dei test stanno in `<laboratorio>\logs\`.
- Per provare gli script senza toccare il laboratorio vero: `-Laboratorio` (o `CAR_LAB`) e `-CartellaSkill` verso cartelle di prova, `-ProgettoGodot` verso una copia di `game` con accanto `THIRD-PARTY-NOTICES.md` (durante lo sviluppo i crediti lo cercano nella cartella sopra il progetto), `-Condiviso` verso una copia se si vuole provare anche la cartella condivisa.
- Gli strumenti si verificano con i checksum ufficiali (SHA512-SUMS.txt di Godot, `.sha256` di Blender e di gyan.dev); i pacchetti Python si installano con `uv pip install --require-hashes --only-binary :all:` e gli sha256 di PyPI.
- `downloads\free_vgms\` sta solo nel laboratorio del PC di lavoro: serve a `tools/audio/make_placeholder_music.py` per rifare la musica segnaposto, e si riscarica con `--download`.
