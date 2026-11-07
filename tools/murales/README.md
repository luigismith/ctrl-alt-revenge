# I murales di Totò

Le vignette dei filmati (l'introduzione, i ricordi, i passaggi fra i capitoli) sono murales dipinti a spray, in
pixel art. Lo stile è quello dei primi piani (`game/assets/ui/closeups/`): contorni spessi viola-nero, campiture
piatte a due o tre toni, sfumature a spray, qualche colatura, colori saturi e un filo di neon rosa.

## Formato

| | |
|---|---|
| Vignetta | 512×288, in 16:9 come lo schermo (480×270) più 32×18 px di margine per scorrerci sopra |
| Panoramica | fino a 960×288, per le carrellate |
| Dettaglio | zoom intero 2x della telecamera delle scene, così i pixel restano quadrati |
| Colori | 48 per vignetta, niente retinatura, contorno `#1e1028` |

Per ogni vignetta escono in `game/assets/murales/<capitolo>/<id>/`:

- `murale.png`: la vignetta, opaca;
- `murale_emis.png`: le luci da sommare (neon, lampade, schermi), per farle pulsare;
- `murale_rivela.png`: l'ordine dello spray in grigio (0 compare subito, 255 per ultimo), per far dipingere la
  vignetta davanti a noi e passare in modo morbido dal gioco al murale;
- `murale.json`: misure, scorrimento consigliato e fonte per i crediti.

## Come si fa una vignetta

1. **Le pose.** I personaggi vengono dal nostro 3D: `posa.py --chi gig --azione Idle_Loop --yaw 55` fa il render a
   colori nella cartella privata `ctrlaltrevenge-lab-condiviso/murales/<capitolo>/pose/`.
2. **La base.** A ChatGPT si caricano solo i nostri render, i nostri schizzi e le nostre basi, mai foto con diritti.
   Il prompt è in inglese e chiede niente scritte: le scritte le fa il nostro codice. La base, il prompt e la data
   vanno nel `registro.md` della cartella privata del capitolo.
3. **La riduzione.** Si scrive la configurazione accanto alla base (`<id>.json`, il formato è nella testa di
   `murale.py`) e si lancia `python -I tools/murales/murale.py <id>.json`. L'anteprima a 2x, con i riquadri dello
   schermo, esce in `tools/out/murales/`.
4. **Le scritte.** Tag, insegne e cartelli si aggiungono nella configurazione: li disegna `tools/env/pixfont.py`,
   con il contorno e le colature.

Le basi, i prompt e i render restano nella cartella privata: nel repo vanno solo la pixel art e gli script.
