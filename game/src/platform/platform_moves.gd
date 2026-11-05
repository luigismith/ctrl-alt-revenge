class_name PlatformMoves
extends Resource
## I valori di taratura del movimento platform di GIG: si cambiano qui (o in
## data/platform/gig_moves.tres), non nel codice. Sono valori di partenza, da tarare con Luigi
## e il pad nella stanza di prova. Unità: pixel e tick (60 al secondo); 60 px sono un metro.
## Il 5 novembre 2026 la risoluzione è passata da 384×216 a 480×270: tutte le misure in pixel
## sono cresciute del 25%, quindi il movimento è lo stesso di prima, in metri e in tick.
##
## La simulazione li converte in sottopixel interi (PlatformPlayer.SUB), così resta
## deterministica e i replay tornano uguali.

@export_group("Corsa")
## Velocità massima di corsa: 3,125 px/tick = 187,5 px/s, circa 3 m/s. GIG ha cinquant'anni.
@export var run_speed: float = 3.125
@export var ground_accel: float = 0.3125
@export var ground_decel: float = 0.5
## Girarsi di colpo frena più forte che lasciare il tasto.
@export var ground_turn: float = 0.6875
@export var air_accel: float = 0.225
@export var air_decel: float = 0.1

@export_group("Salto")
## Velocità iniziale del salto: tenendo il tasto arriva a circa 87 px (1,45 m), cioè sopra un
## muro di 4 blocchi (80 px). Regola per i livelli: 4 blocchi col salto, di più con la Spinta o le mani.
## Il 5 novembre 2026 Luigi l'ha trovato "troppo lunare": stessa altezza, il 13% di tempo in meno in
## aria (velocità per 1/0,87, gravità per 1/0,87²).
@export var jump_speed: float = 8.1875
@export var gravity: float = 0.3625
## Gravità in discesa, più forte: il salto è più deciso e meno "lunare".
@export var fall_gravity: float = 0.5
## Vicino alla cima del salto, con il tasto tenuto, la gravità cala: un attimo di sospensione.
@export var apex_gravity: float = 0.23125
@export var apex_band: float = 1.15
@export var max_fall: float = 8.625
## Lasciando SALTO mentre sale, la velocità verso l'alto si moltiplica per questo: salto variabile.
@export var jump_cut: float = 0.45
## Tick dopo il bordo in cui il salto vale ancora da terra (coyote time).
@export var coyote_ticks: int = 6
## Tick in cui una pressione di SALTO resta in attesa (atterraggio, sporgenza): come il buffer
## degli attacchi.
@export var jump_buffer: int = 8

@export_group("Spinta (doppio salto)")
## La scarica del braccio verso il basso: circa 60 px in più (un metro).
@export var boost_speed: float = 6.6125
## Quante Spinte per ogni volta in aria.
@export var boosts: int = 1

@export_group("Accovacciarsi e scivolare")
## Sotto questa velocità GIÙ accovaccia; sopra, fa scivolare.
@export var slide_min_speed: float = 2.25
@export var slide_speed: float = 4.5
@export var slide_friction: float = 0.1125
@export var slide_ticks: int = 26
## Tick da accovacciato prima che una nuova scivolata sia possibile.
@export var slide_cooldown: int = 10
@export var crouch_speed: float = 1.0
## Tick in cui le celle sottili non reggono, dopo GIÙ + SALTO.
@export var drop_ticks: int = 10

@export_group("Sporgenze")
## Le mani arrivano a una sporgenza se lo spigolo è fra la cima del corpo e questi pixel più giù
## (fino al petto). Se lo spigolo è basso e sotto non c'è posto per stare appesi, GIG scavalca.
@export var ledge_reach: int = 30
## Tick in cui, appena lasciata una sporgenza, non ci si riaggrappa.
@export var ledge_regrab: int = 14

@export_group("Muri: freno col braccio e salto a muro")
## In caduta, spingendo contro un muro, GIG pianta il braccio e scivola giù a questa velocità al
## massimo (Luigi, 5 novembre 2026: "Frena col braccio", come Mega Man X).
@export var wall_slide_speed: float = 1.625
## Quanto in fretta frena: la caduta si avvicina a wall_slide_speed di tanto per tick.
@export var wall_slide_brake: float = 0.5625
## Tick in cui, spingendo via dal muro, il braccio resta piantato: c'è tempo per premere SALTO.
@export var wall_stick: int = 8
## Tick dopo il distacco in cui SALTO vale ancora come salto a muro (il coyote time del muro).
@export var wall_coyote: int = 5
## Il salto a muro: verso l'alto e via dal muro.
@export var wall_jump_speed: float = 7.5
@export var wall_jump_push: float = 3.75
## Tick dopo il salto a muro in cui il controllo in aria è più debole: non si torna subito al muro.
@export var wall_jump_lock: int = 9

@export_group("Scatto in aria")
## Lo scatto è orizzontale, uno per salto, con un tasto suo (Luigi, 5 novembre 2026): 7,5 px/tick
## per 8 tick, cioè 3 blocchi, sospeso. Si ricarica a terra, su un muro o su una sporgenza.
@export var dash_speed: float = 7.5
@export var dash_ticks: int = 8
## Velocità che resta alla fine dello scatto.
@export var dash_exit_speed: float = 3.125

@export_group("Corsa sul muro")
## Arrivando di corsa contro un muro e premendo SALTO, GIG fa qualche passo in verticale (Luigi,
## 5 novembre 2026, come Prince of Persia): i piedi salgono fino a wallrun_height px sopra il punto
## di partenza, due blocchi sopra il salto, comunque la si prenda (da terra o già in salto),
## rallentando di wallrun_decel per tick. Una volta sola prima di toccare terra.
@export var wallrun_height: int = 125
@export var wallrun_decel: float = 0.1375
## Velocità di corsa che serve: da fermi non si fa.
@export var wallrun_min_speed: float = 2.5
## Tick in cui lo slancio della corsa vale ancora (contro il muro la corsa si ferma subito).
@export var wallrun_momentum: int = 10

@export_group("Corpo")
## Il rettangolo di collisione, con i piedi in basso al centro. Più stretto dello sprite (circa 60 px
## con le braccia): nei platform conta il busto.
@export var body_width: int = 25
@export var body_height: int = 100
@export var crouch_height: int = 58
