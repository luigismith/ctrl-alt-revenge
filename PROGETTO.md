# Ctrl-Alt-Revenge: il sito e i social che vanno da soli

Progetto del 15 novembre 2026, sessione `caru-social`. Da approvare dalla regia prima di costruire.

Il modello è Elettrofoni (`luigismith/DIVULGA`): pubblica GitHub Actions, Claude prepara soltanto. Da Elettrofoni si riusano il codice provato e le sue lezioni (cron che salta, finestra oraria, stato salvato subito, niente retry, verifica sul permalink). Qui cambia una cosa: le reti di sicurezza sono script, non routine Claude.

## 1. Architettura

```
GitHub (repo pubblico)                                 fuori da GitHub
┌──────────────────────────────────────────────┐
│ inbox/      ← la regia lascia i materiali     │
│ contenuti/  ← la coda (scritta dalla routine) │      Routine Claude (Sonnet)
│ sito/       ← testi IT/EN e modello del sito  │ ◄──  una volta a settimana:
│ docs/       ← il sito pubblicato (Pages)      │      inbox → coda, niente segreti
│ stato.json  ← cosa è uscito, con permalink    │
│ token.enc   ← token Instagram cifrato         │      cron-job.org
│                                               │ ◄──  rete per il cron di GitHub
│ Actions: pubblica-ig, pubblica-yt, pages,     │      (lancia un dispatch)
│          sentinella, rinnova-token, controlli │
└──────────────────────────────────────────────┘
         │ immagini e video serviti da Pages
         ▼
  Instagram (API con Instagram Login)    YouTube (Data API v3, OAuth)
```

- **Dove vive:** tutto su GitHub. Il PC di Luigi può restare spento per settimane.
- **Chi pubblica:** solo le Actions, con script Python. Claude non vede mai un token.
- **I media:** l'API di Instagram scarica le immagini e i video da un indirizzo pubblico, quindi stanno sotto `docs/social/<id>/` e vanno online con Pages prima della chiamata (come in Elettrofoni). YouTube invece riceve il file direttamente dal runner.
- **L'indirizzo del sito** non è scritto nel codice: si ricava dal nome del repository in esecuzione (`https://luigismith.github.io/<nome>/`). Così lo scambio dei nomi (`-nuovo` → `ctrl-alt-revenge`) non rompe i link dei media in coda.

### Le cartelle

| Cartella o file | Cosa contiene | Chi la scrive |
|---|---|---|
| `inbox/<data>-<slug>/` | il materiale grezzo e la sua `nota.md` | la regia |
| `contenuti/<data>-<slug>.yml` | la coda: un file per ogni uscita | la routine, la regia |
| `docs/` | il sito pubblicato e i media social (Pages) | gli script |
| `sito/` | modello HTML, CSS, testi `it.json` e `en.json` | la sessione social |
| `strumenti/` | gli script Python | la sessione social |
| `stato.json` | ogni uscita con data, id e permalink: l'idempotenza vive qui | gli script |
| `token.enc` | token Instagram cifrato (AES-GCM, chiave nel secret `STATE_KEY`) | gli script |

## 2. Le cadenze

- **Instagram, post:** 2 a settimana, **martedì e venerdì**, nella finestra 18-21 italiane. Carosello di tavole o immagine singola.
- **Instagram, reel:** uno quando la regia manda un video nuovo, mai riempitivi. Esce in un giorno senza post (di norma la domenica, 18-21).
- **YouTube Shorts:** lo stesso video del reel, lo stesso giorno, un'ora dopo. Stesso file, titolo e descrizione propri.
- **Instagram, storie:** una per ogni post e reel, con la tavola verticale (l'API non permette adesivi o link). Facoltativa: se fallisce, il post resta valido.
- **Mai riempitivi.** Se la coda è vuota non esce niente: non si ricicla e non si inventa. Se la coda copre meno di 14 giorni, la sentinella apre una issue per la regia (al massimo una a settimana).

Guardie negli script (da Elettrofoni):
- al massimo 1 uscita nel feed al giorno, e almeno 20 ore fra due uscite;
- si pubblica solo nella finestra 17-22 italiane, salvo `forza: true` messo a mano;
- tre passate di cron a minuti «storti» più cron-job.org; i doppioni li ferma `stato.json`;
- lo stato si salva e si spinge subito dopo la pubblicazione, prima di ogni altro passo.

## 3. Il formato della coda

### `inbox/`: cosa lascia la regia

Una cartella per consegna, per esempio `inbox/2026-11-18-cancello/`:

```
inbox/2026-11-18-cancello/
  nota.md
  cancello_davanti.png
  cancello_giro.mp4
  musica.mp3          (se il video non ha già l'audio)
```

`nota.md`, con poche righe fisse in cima e il resto libero:

```markdown
---
approvato: si                # senza questa riga la routine non la usa
mostra: prologo              # cosa si vede (prologo = cimitero, cancello)
uso: [post, reel, short, sito]
battute: []                  # solo battute approvate, testo esatto
musica: "Titolo del brano Suno di Luigi"   # o: nessuna
ai: no                       # sì se c'è un'immagine generata che sembra vera
---
Cosa mostra e cosa vuole dire. Dettagli da non dire. Eventuali crediti.
```

**Attenzione:** il repository è pubblico, quindi anche `inbox/` è pubblica appena la regia la spinge. In `inbox/` entra solo materiale già approvato per uscire, mai provini né scarti. Il limite per file è 50 MB (i video si comprimono prima).

### `contenuti/`: la coda

Un file YAML per uscita, per esempio `contenuti/2026-11-20-cancello.yml`:

```yaml
id: 2026-11-20-cancello
tipo: carosello            # carosello | immagine | reel   (reel => anche Short)
uscita: 2026-11-20         # il giorno previsto; slitta se salta
fonte: inbox/2026-11-18-cancello
media: [cancello_davanti.png, ...]
tavole: cartone            # modello delle tavole (vedi §6)
didascalia: |
  Testo italiano, poi una riga in inglese.
hashtag: [ctrlaltrevenge, indiegame, unrealengine5, stopmotion, taranto]   # max 5
youtube:                   # solo per i reel
  titolo: "..."            # max 100 caratteri
  descrizione: |
    ...
ai: false
stato: pronto              # bozza | pronto
```

- Gli script generano le tavole e il video finale in `docs/social/<id>/`: Claude scrive solo testi e scelte, il resto è codice deterministico.
- `strumenti/controlli.py` gira a ogni push e prima di ogni pubblicazione: lunghezze (didascalia 2200, titolo YouTube 100), al massimo 5 hashtag, al massimo 10 slide, i file esistono, video verticale 1080×1920 fra 3 e 90 secondi con audio AAC, nessuna parola della lista nera degli spoiler.
- **La lista nera degli spoiler non sta nel repository:** anche solo come elenco di nomi, in un repository pubblico sarebbe un indice della trama. La scrive la regia.
  - Nelle Actions, `controlli.py` la legge dal secret `CARU_PAROLE_VIETATE`, una parola o frase per riga.
  - In locale la legge da `C:\Users\Admin\ctrlaltrevenge-lab\social-privato\spoiler.txt`, fuori dal repository e mai committato.
  - Se la lista manca, i controlli **falliscono**: non si pubblica alla cieca.
  - Quando trova una parola vietata, il log dice solo il file e la riga, mai la parola (i log sono pubblici). GitHub maschera comunque i valori dei secret nei log, ma una parola comune scritta da noi non deve dipendere da quella maschera.
- **Finestra di veto:** un contenuto entra in coda almeno 48 ore prima dell'uscita. Quando la routine lo mette in coda, uno script apre una issue «In coda: <id>, esce il <data>», con l'anteprima delle tavole e della didascalia.
  - **Per fermarlo basta chiudere la issue**, anche dall'app GitHub sul telefono. Il pubblicatore lo salta finché la issue resta chiusa.
  - Per farlo ripartire si riapre la issue.
  - Dopo l'uscita la issue la chiude il bot, con il permalink.

## 4. La routine settimanale

- **Quando:** lunedì alle 8:30, una volta a settimana. Modello Sonnet.
- **Cosa fa:**
  1. lancia `python strumenti/inbox.py`: se non c'è niente di nuovo lo scrive in una riga e **si ferma subito** (giro da pochi centesimi di token);
  2. per ogni consegna nuova e approvata legge solo la `nota.md` e guarda i media (le immagini le apre, dei video legge i dati con `ffprobe`);
  3. scrive i file in `contenuti/`: didascalie in italiano e in inglese, hashtag, titolo e descrizione per YouTube, la data secondo le cadenze;
  4. aggiorna i testi del sito solo se la nota lo chiede (`uso: [sito]`);
  5. lancia `controlli.py`, fa il commit e il push;
  6. lascia un commento di quattro righe nella issue fissa «Diario della routine»: cosa ha messo in coda, per quando, cosa manca.
- **Cosa non fa:** non pubblica, non tocca i segreti, non risponde ai commenti, non inventa materiale.
- **Tetto:** 15 minuti e circa 30 passi. Se un controllo fallisce due volte, lascia il contenuto in `bozza` e lo scrive nel diario.
- **Le risposte ai commenti** (fase 2): uno script delle Actions raccoglie i commenti nuovi in `commenti/da-leggere.md`; la routine scrive le bozze di risposta; partono solo dopo il via di Luigi (come in Elettrofoni), con il workflow `rispondi.yml` lanciato a mano.
- La routine la crea la regia (o io, con il suo via), quando il sistema ha superato la prova a secco.

## 5. YouTube: l'audit e il token

- **Video privati:** la regia temeva il blocco dei progetti non verificati nati dopo il 28 luglio 2020. La documentazione di oggi dice il contrario. Nella pagina `videos.insert`, alla voce `status.privacyStatus`, si legge: «Videos uploaded from unverified API projects are not restricted to private viewing mode» (controllato il 15/11/2026 su developers.google.com/youtube/v3/docs/videos/insert).
  - Come lo gestiamo: lo script chiede `public`, poi rilegge il video con `videos.list`. Se YouTube lo ha lasciato privato o bloccato, lo script si ferma, apre una issue e non riprova. In quel caso si chiede l'audit con il modulo ufficiale (support.google.com/youtube/contact/yt_api_form), e intanto lo Short si rende pubblico a mano da YouTube Studio.
  - Il primo Short esce comunque solo con il via della regia.
- **Quota:** `videos.insert` ha un suo contatore da 100 caricamenti al giorno. A noi ne serve uno a settimana, quindi l'audit per la quota non serve.
- **Il refresh token scade dopo 7 giorni** se la schermata di consenso è in stato «Testing». Va messa «In production» prima di generare il token. Con gli ambiti `youtube.upload` e `youtube.readonly` Google mostrerà a Luigi l'avviso «app non verificata»: per un solo utente si prosegue senza verifica. Il token muore anche dopo 6 mesi senza uso: la sentinella lo usa una volta a settimana, così resta vivo.
- **Shorts:** l'API non ha un campo «Short». Un video verticale di al massimo 3 minuti diventa Short da solo. Teniamo i video sotto i 90 secondi, così valgono anche come reel.
- **Etichetta «contenuto alterato o sintetico»:** si imposta con `status.containsSyntheticMedia` solo se la nota dice `ai: sì`, cioè per immagini realistiche generate. Il gioco animato e i pupazzi non la richiedono. Su Instagram si segue la stessa regola (al passo 4 controllo se l'API espone l'etichetta; se non la espone, una riga nella didascalia).

## 6. Il sito

- **Pagine:** `docs/index.html` (italiano) e `docs/en/index.html` (inglese), generate da `strumenti/genera_sito.py` con `sito/modello.html` e i testi `sito/testi/it.json` e `en.json`. Poi `privacy.html` e `cancellazione-dati.html`, che servono all'app Meta, e la pagina 404.
- **Sezioni:**
  - l'apertura con la tavola del cancello o il video;
  - il gioco (platform d'azione in 2,5D, arene, hacking);
  - il mondo (Taranto 2087, da `docs/mondo.md` del vecchio sito, senza spoiler);
  - i personaggi del prologo;
  - «Dal laboratorio», l'elenco delle uscite social con i permalink, aggiornato dagli script dopo ogni pubblicazione;
  - come è fatto, con onestà: Unreal Engine 5, personaggi che sembrano pupazzi da stop motion e set di cartone, gli strumenti usati, nessuna data di uscita, progetto personale non in vendita.
- **Aspetto:** il diorama di carU, con cartone ondulato, nastro, carta strappata, stencil e titoli decisi anni '90. Niente pixel art. Le tavole social escono dagli stessi modelli HTML (Playwright → JPEG 1080×1350 e 1080×1920), così sito e post sembrano dello stesso mondo.
- **Leggero:** HTML e CSS fatti a mano, poco JavaScript, immagini WebP con il loro JPEG di riserva, video solo dove serve.

## 7. Le Actions

| Workflow | Quando | Cosa fa |
|---|---|---|
| `controlli.yml` | a ogni push | valida la coda e il sito |
| `pubblica-ig.yml` | mar/ven/dom, tre passate, più cron-job.org | prossima uscita IG: tavole, deploy Pages, pubblica, salva lo stato, storia, verifica sul permalink, aggiorna «Dal laboratorio» |
| `pubblica-yt.yml` | dopo il reel (si accoda) e con una passata propria | carica lo Short, verifica sul permalink e con oEmbed (risponde solo se il video è pubblico) |
| `pages.yml` | a ogni modifica di `docs/` | deploy del sito |
| `sentinella.yml` | ogni sera alle 23:25 | vedi sotto |
| `rinnova-token.yml` | domenica notte | rinnova il token IG se mancano meno di 25 giorni |

**La sentinella** è uno script, senza Claude. Apre una issue (una sola per problema, non la ripete se è già aperta) quando:
- un'uscita prevista nell'ultima giornata chiusa non c'è;
- la coda copre meno di 14 giorni;
- il token IG scade entro 10 giorni o non risponde, o il refresh token di YouTube non risponde;
- il sito non risponde con 200.

Le issue arrivano per email a Luigi e la regia le vede con `gh issue list`.

**La verifica è vera:**
- dopo Instagram si apre il `permalink` restituito dall'API e si controlla che la pagina esista e sia il post giusto;
- dopo YouTube si apre `https://www.youtube.com/shorts/<id>` e si interroga oEmbed;
- un «200» della chiamata di pubblicazione non basta. Su un errore ci si ferma e si apre una issue, senza tentativi in loop: il budget dei video di Instagram si consuma anche con i tentativi falliti.

**Prova a secco:** ogni pubblicatore ha `--prova`, che fa tutto (tavole, Pages, controlli, URL raggiungibili) tranne la chiamata che pubblica, e lo dice nei log. Lo si lancia dal workflow con l'input `prova: true`.

**I log sono pubblici.** I token non si stampano mai (redazione come in `token_ig.py`), e le risposte dell'API si filtrano prima di scriverle.

## 8. Cosa è automatico e cosa resta a Luigi

**Automatico:**
- pubblicazione di post, storie, reel e Short;
- verifica e permalink;
- aggiornamento del sito dopo ogni uscita;
- rinnovo del token Instagram;
- la sentinella e le sue issue;
- il rifornimento della coda (la routine, dal materiale della regia).

**Resta a Luigi, una volta sola** (la lista passo per passo è in [`ACCENSIONE.md`](ACCENSIONE.md)):
1. creare dal telefono l'account Instagram del gioco e passarlo a professionale (creator);
2. creare un'app Meta nuova, con «Instagram API with Instagram Login», aggiungere l'account come tester e generare il token. L'app è nuova e non si riusa quella di Elettrofoni, così un problema su una non ferma l'altra e non si toccano le impostazioni di Elettrofoni;
3. creare il canale YouTube del gioco (account brand con il nome Ctrl-Alt-Revenge);
4. su Google Cloud:
   - un progetto nuovo con YouTube Data API v3 attiva;
   - la schermata di consenso esterna, in produzione;
   - un client OAuth «app desktop»;
   - poi lanciare una volta `strumenti/ottieni_token_youtube.py` sul PC, che apre il browser per il consenso;
5. mettere i secret nel repository con `gh secret set`, incollandoli lui: `IG_ACCESS_TOKEN`, `STATE_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`. Una copia va in Vaultwarden;
6. cron-job.org: un account, un token GitHub a grana fine (solo questo repository, permesso Actions in scrittura) e due lavori;
7. dopo lo scambio dei nomi, aggiornare l'indirizzo nei lavori di cron-job.org.

**Resta a Luigi, nel tempo:**
- il via alle risposte ai commenti;
- le decisioni che la regia gli porta.

## 9. Lo scambio dei nomi (alla fine, con il via della regia)

1. Rinominare `ctrl-alt-revenge` in `ctrl-alt-revenge-2d`. Il suo sito si sposta da solo su `/ctrl-alt-revenge-2d/`: da decidere se tenerlo acceso come archivio o spegnerne le Pages.
2. Rinominare `ctrl-alt-revenge-nuovo` in `ctrl-alt-revenge`.
3. Rilanciare `pages.yml` e controllare che `luigismith.github.io/ctrl-alt-revenge/` mostri il sito nuovo.
4. Aggiornare l'indirizzo in cron-job.org e i remote dei cloni locali.

Rischio: fra il passo 1 e il passo 3 il sito è spento per qualche minuto, e i link di GitHub al vecchio nome restano senza redirect, perché il nome viene ripreso dal repository nuovo.

## 10. Costi

Zero: le Actions sono gratuite sui repository pubblici, Pages e cron-job.org sono gratuiti, le API di Meta e di YouTube non costano. I token di Claude si spendono solo nella routine settimanale, che si ferma subito quando `inbox/` è vuota, e nei giri chiesti dalla regia.

## 11. L'ordine dei lavori

1. ✅ Il repository e questo progetto.
2. Il prototipo della home in italiano, con le catture a 1440 px e da telefono, poi lo stop per Luigi.
3. Il pubblicatore Instagram e la sua prova a secco.
4. Il pubblicatore di YouTube Shorts e la sua prova a secco.
5. ✅ La sentinella e la sua prova (`strumenti/sentinella.py`, `prove/prova_sentinella.py`).
6. Il workflow delle Pages.
7. ✅ La pagina «Accensione di Ctrl-Alt-Revenge» con i passi di Luigi: [`ACCENSIONE.md`](ACCENSIONE.md).
8. Con il via della regia: la routine, poi il primo post e il primo Short, poi lo scambio dei nomi.
