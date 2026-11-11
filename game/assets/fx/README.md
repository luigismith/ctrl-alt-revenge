# Effetti visivi

Tutto è generato da `tools/fxui/make_fx.py`: disegno procedurale con semi fissi, senza antialiasing, con le dissolvenze a retinatura come sulle console a 16 bit. Gli effetti seguono il formato del §7 della specifica, in `fx.json`:

```json
{"hit_spark_light": {"image": "hit_spark_light.png", "frame": [24, 24], "count": 4, "ticks": 2, "anchor": [12, 12]}}
```

Ogni PNG è una striscia orizzontale di `count` fotogrammi grandi `frame`; ogni fotogramma dura `ticks` tick a 60 Hz. `anchor` è il punto del fotogramma che va sulla posizione dell'effetto. I campi in più sono facoltativi:
- `loop`;
- `mode`: `"anim"` si anima, `"variants"` sono fotogrammi da scegliere;
- `flip`: va specchiato per chi guarda a sinistra;
- `variants`, `tile`, `note`.

## Elenco

| Effetto | Fotogramma | N × tick | Ancora | Uso |
|---|---|---|---|---|
| `hit_spark_light` | 24×24 | 4 × 2 | centro | jab, ginocchiata: stella bianca, gialla, arancio |
| `hit_spark_heavy` | 40×40 | 5 × 2 | centro | calcio finale, proiezione, haymaker: stella grande e anello d'urto |
| `cyber_spark` | 40×40 | 5 × 2 | centro | gancio cyber: archi cyan; più lunghi verso +x (`flip`) |
| `glint` | 25×25 | 6 × 2 | centro | lampo che annuncia l'haymaker (12 tick, dal tick 20 dell'avvio) |
| `dust_land` | 64×24 | 6 × 3 | punto a terra | atterraggio e corpo che cade: due nuvole ai lati |
| `dust_skid` | 32×20 | 5 × 3 | il piede | sbuffo che va verso −x per chi guarda a destra (`flip`) |
| `ombra` | 60×15 | 3 varianti | centro | 0 grande 58×12, 1 media 44×10, 2 piccola 30×8; semitrasparente |
| `rain_streak` | 6×16 | 4 varianti | testa | gocce di 7, 10, 13, 16 px; cadono 4 px in giù per 1 px a sinistra |
| `rain_splash` | 12×8 | 4 × 3 | impatto | schizzo a terra |
| `rain_sheet` | 128×128 | 1 | — | facoltativo: tessera di pioggia ripetibile da far scorrere |
| `ko_flash` | 64×64 | 6 × 3 | centro | facoltativo: lampo del KO finale dell'ondata |

**Ombre.** Il fotogramma 0 (grande) riempie il fotogramma, quindi si può anche stirare a una larghezza qualsiasi. Per restare perfetti al pixel conviene però scegliere una delle tre varianti e disegnarla a 1x.

## Verifica

- Tavole a 4x in `tools/fxui/out/check/fx_<nome>_4x.png`: fotogrammi su fondo scuro e su un viola medio, con riquadri e tacche dell'ancora.
- In scena: `tools/fxui/out/check/hud_mockup_*.png`.
- In Godot: `tools/fxui/out/check/godot_fx_3x.png`, prodotto da `godot_check.py hud`.

Licenza: asset originali, `LicenseRef-CAR-Assets`.
