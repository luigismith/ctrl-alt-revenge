# Accensione di Ctrl-Alt-Revenge

I passi che restano a Luigi, una volta sola, per accendere i social e il sito del gioco. Tutto il resto (pubblicazione, verifiche, sito, rinnovo dei token, sentinella) gira da solo su GitHub, anche con il PC spento.

**Le regole di questa pagina:**
- I login, le password e i clic di consenso sono di Luigi. La sessione social prepara e verifica, ma non entra negli account.
- Ogni token, chiave o segreto va in due posti soltanto: nei secret di GitHub, incollato da Luigi con `gh secret set`, e in Vaultwarden, nella cartella «Claude - infrastruttura». Mai in un file, in una chat o in uno screenshot: questo repository è pubblico, e lo sono anche i suoi log.
- Si va in ordine. Alla fine di ogni passo Luigi dice «fatto» alla regia: la sessione social fa la sua verifica (colonna «Come si verifica») e solo dopo si passa al successivo.
- Niente esce sui social finché la regia non dà il via al primo post e al primo Short.

| # | Passo | Tempo | Come si verifica (lo fa la sessione social) |
|---|---|---|---|
| 1 | L'account Instagram del gioco | 10 min | — |
| 2 | L'app Meta e il token di Instagram | 20 min | «Rinnova token Instagram» poi «Sentinella»: il log dice `risponde, account @…` |
| 3 | Il canale YouTube del gioco | 5 min | — |
| 4 | Google Cloud e il token di YouTube | 20 min | «Sentinella»: il log dice `il refresh token risponde` |
| 5 | cron-job.org | 15 min | un lavoro lanciato a mano fa partire una run, che si ferma da sola fuori orario |
| 6 | Pages e lo scambio dei nomi (con la regia) | 10 min | il sito risponde al suo indirizzo, `en/` compreso |
| 7 | L'app Meta in modalità Live | 5 min | i commenti si leggono (serve alla fase 2) |

---

## 1. L'account Instagram del gioco

Dal telefono, nell'app Instagram:

1. Dal proprio profilo: nome utente in alto → **Aggiungi account Instagram** → **Crea un nuovo account**.
   - Nome utente: il più vicino possibile al titolo (per esempio `ctrlaltrevenge` o `ctrl.alt.revenge`, quello libero).
   - Nome visualizzato: `Ctrl-Alt-Revenge`.
   - Password: generata da Vaultwarden e salvata lì subito.
2. **Impostazioni → Tipo di account e strumenti → Passa a un account professionale → Creator**. Categoria: *Videogioco* (o *Creator digitale*, se non c'è). Non serve collegare una Pagina Facebook.
3. Bio, da copiare così (onesta, senza date e senza promesse):

   ```
   Platform d'azione in 2,5D · Taranto, 2087
   Fatto in Unreal Engine 5: set di cartone, personaggi come pupazzi da stop motion
   Progetto personale, in sviluppo
   ```
   Il link del sito si mette al passo 6, quando l'indirizzo è quello definitivo.
4. Attivare l'autenticazione a due fattori (**Centro gestione account → Password e sicurezza**) e salvare i codici di recupero in Vaultwarden.

## 2. L'app Meta e il token di Instagram

È un'app nuova, separata da quella di Elettrofoni: un problema su una non ferma l'altra.

1. Su [developers.facebook.com/apps](https://developers.facebook.com/apps), con l'account Facebook sviluppatore di sempre: **Crea app**.
   - Nome: `Ctrl-Alt-Revenge publisher`.
   - Caso d'uso: **Gestisci messaggi e contenuti su Instagram** (in inglese *Manage messaging & content on Instagram*).
   - Portfolio aziendale: nessuno.
2. Nell'app, **Ruoli dell'app → Ruoli → Aggiungi persone → Tester di Instagram**: il nome utente dell'account del passo 1.
   Poi, su Instagram con l'account del gioco (dal browser è più comodo: instagram.com → **Impostazioni → App e siti web → Inviti come tester**): **Accetta**.
3. Nell'app: **Casi d'uso → Personalizza → Configurazione API con login di Instagram**.
   - Al punto «Genera token d'accesso»: **Aggiungi account**, si entra con l'account del gioco e si accettano i permessi. Devono esserci almeno `instagram_business_basic` e `instagram_business_content_publish`; `instagram_business_manage_comments` serve per la fase 2 dei commenti.
   - **Genera token** e copiarlo subito in Vaultwarden (voce «Ctrl-Alt-Revenge – token Instagram»). Dura 60 giorni: da lì in poi lo rinnova GitHub da solo.
4. La chiave che cifra il token nel repository: in Vaultwarden, **Generatore → password di 40 caratteri**, salvata come «Ctrl-Alt-Revenge – STATE_KEY».
5. Nel terminale, dalla cartella `%USERPROFILE%\ctrlaltrevenge-lab\social\`, due comandi. Ognuno chiede di incollare il valore e non lo mostra:

   ```
   gh secret set IG_ACCESS_TOKEN
   gh secret set STATE_KEY
   ```

**Lasciare l'app in modalità Sviluppo** per ora: pubblicare funziona già, perché l'account è tester. La si passa a Live al passo 7, quando l'indirizzo del sito è definitivo.

> Se un giorno il token si revoca (password di Instagram cambiata, app tolta dalle autorizzazioni), la sentinella apre una issue. Si ripetono i punti 3 e 5 solo per `IG_ACCESS_TOKEN`, e la sessione social cancella `token.enc`.

## 3. Il canale YouTube del gioco

Dal computer, con l'account Google personale:

1. [youtube.com](https://www.youtube.com) → foto profilo → **Impostazioni → Aggiungi o gestisci i tuoi canali → Crea un canale**.
2. Nome: `Ctrl-Alt-Revenge`. Così nasce un account brand, separato dal canale personale.
3. Nella descrizione del canale, lo stesso testo della bio di Instagram.

## 4. Google Cloud e il token di YouTube

1. Su [console.cloud.google.com](https://console.cloud.google.com): selettore dei progetti → **Nuovo progetto**, nome `ctrl-alt-revenge`.
2. **API e servizi → Libreria → YouTube Data API v3 → Abilita**.
3. **Google Auth Platform** (la vecchia «Schermata consenso OAuth») → **Inizia**:
   - nome dell'app `Ctrl-Alt-Revenge publisher`, email di assistenza quella di Luigi;
   - pubblico **Esterno**;
   - poi in **Pubblico → Pubblica app**, così lo stato diventa **In produzione**. Questo passo è importante: in «Test» il token muore dopo 7 giorni.
4. **Client → Crea client → Tipo di applicazione: App desktop**, nome `pubblicatore`. Copiare l'**ID client** e il **Client secret** in Vaultwarden («Ctrl-Alt-Revenge – OAuth Google»).
5. Nel terminale, dalla cartella `%USERPROFILE%\ctrlaltrevenge-lab\social\`:

   ```
   python -I strumenti/ottieni_token_youtube.py
   ```
   - Lo script chiede l'ID client e il secret: si incollano e non si vedono.
   - Si apre il browser: scegliere il **canale Ctrl-Alt-Revenge**, non quello personale.
   - Google avvisa che l'app non è verificata: **Avanzate → Vai a Ctrl-Alt-Revenge publisher**. Per un'app usata da una persona sola la verifica non serve.
   - Lo script controlla che il canale sia quello giusto e mette da solo i tre secret `YT_*` su GitHub. Il refresh token non serve salvarlo: se si perde, si rilancia lo script.

## 5. cron-job.org

Il cron di GitHub a volte ritarda o salta. cron-job.org è un secondo innesco indipendente: chiama GitHub negli orari di uscita. Se le due cose partono insieme, i doppioni li ferma `stato.json`.

1. Su GitHub: **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
   - Nome `cron-job ctrl-alt-revenge`, scadenza la più lunga che GitHub propone. La data di scadenza va annotata in Vaultwarden, insieme al token.
   - **Repository access → Only select repositories →** solo il repository del sito nuovo.
   - **Permissions → Repository → Actions: Read and write**. Nient'altro.
2. Su [cron-job.org](https://cron-job.org): un account (password da Vaultwarden), poi **Settings → fuso orario Europe/Rome**. Con il fuso di Roma il cambio dell'ora non sposta niente.
3. Due lavori, entrambi così:
   - metodo **POST**, URL `https://api.github.com/repos/luigismith/<repository>/actions/workflows/<file>/dispatches`;
   - intestazioni `Authorization: Bearer <il token del punto 1>` e `Accept: application/vnd.github+json`;
   - corpo `{"ref":"main"}`.

   | Lavoro | `<file>` | Quando (ora di Roma) |
   |---|---|---|
   | Instagram | `pubblica-ig.yml` | martedì, venerdì e domenica, 18:15 |
   | YouTube | `pubblica-yt.yml` | domenica, 20:15 |

   `<repository>` è `ctrl-alt-revenge` (lo scambio dei nomi è fatto: passo 6).

## 6. Pages e lo scambio dei nomi (fatto il 16/11/2026)

Luigi ha detto «Sostituisci subito il vecchio» il 16/11/2026; i comandi li ha lanciati la regia.

1. Il vecchio repository del gioco 2D ora si chiama `ctrl-alt-revenge-2d` ed è un archivio. Il suo sito in pixel art resta acceso su `/ctrl-alt-revenge-2d/`.
2. `ctrl-alt-revenge-nuovo` ora si chiama `ctrl-alt-revenge`.
3. Pages è acceso (Source: GitHub Actions) e la variabile `PAGES_ATTIVE` vale `si`: il sito si aggiorna da solo a ogni push su `docs/`.
4. Il sito risponde su `https://luigismith.github.io/ctrl-alt-revenge/` (e `/en/`). Questo indirizzo va:
   - nella bio di Instagram (**Modifica profilo → Link**) e nella descrizione del canale YouTube;
   - negli URL dei due lavori di cron-job.org (passo 5).

Per qualche minuto, fra il primo e il terzo punto, il sito non risponde: va fatto in un momento senza uscite (non martedì, venerdì o domenica sera).

## 7. L'app Meta in modalità Live

Serve per leggere i commenti (fase 2): in modalità Sviluppo l'API risponde con un elenco vuoto, senza errori. Elettrofoni l'ha scoperto così, il 16/10/2026.

1. Nell'app Meta, **Impostazioni app → Di base**:
   - URL della normativa sulla privacy: `https://luigismith.github.io/ctrl-alt-revenge/privacy.html`;
   - URL per l'eliminazione dei dati: `https://luigismith.github.io/ctrl-alt-revenge/cancellazione-dati.html`;
   - categoria *Intrattenimento* e un'icona (la regia ne fornisce una).
2. In alto, **Modalità app: Live** (Pubblica).

Va fatto dopo il passo 6: se l'indirizzo della privacy smette di rispondere, Meta può bloccare l'app, e con lei le pubblicazioni.

---

## Dopo l'accensione

- **Le issue del repository arrivano per email**, ed è lì che il sistema chiede aiuto:
  - «In coda: …» è il veto: chiuderla ferma quel contenuto, riaprirla lo fa ripartire;
  - «Sentinella: …» sono i problemi trovati ogni sera;
  - quelle con l'etichetta «pubblicazione» sono gli errori dei pubblicatori, che si fermano al primo errore e non riprovano.
- **Le risposte ai commenti** partono solo dopo il via di Luigi.
- **Gli abbonamenti:** nessuno. GitHub Actions, Pages e cron-job.org sono gratuiti, e le API di Meta e di YouTube non costano.
