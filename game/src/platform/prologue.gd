class_name Prologue
extends TestRoom
## Il prologo in grigio (tappa 2 del piano; scaletta della decisione 64): dalla tomba di Mimmo al
## cancello di San Brunone, il pignoramento, la fuga per i Tamburi, il garage col riavvio del braccio
## e l'uscita dal lucernario. Gira sul motore della stanza di prova, con la mappa e i contenuti suoi.
##
## Prima del riavvio GIG ha il braccio bloccato (decisione 34; scelta di Luigi del 5 novembre 2026,
## «base + appeso»): corsa, salto semplice, accovacciarsi, scivolata e sporgenze con la sola destra.
## Col riavvio arrivano la Spinta e il resto delle acrobazie.
##
## Le vignette a fumetto qui sono riquadri provvisori con una didascalia: le tavole vere sono i
## murales di Totò, che arrivano con la grafica. Nessuna battuta della sceneggiatura sta in questo
## file, che è pubblico.

## Il prologo è finito e GIG è sul tetto: dopo END_HOLD tick (o ATTACCO dopo END_SKIP) la partita passa
## alla fine della demo. `result`: {"ticks": il tick dell'arrivo, "prologue": true}.
signal prologue_finished(result: Dictionary)

## I livelli si disegnano in LDtk (docs/ldtk.md), con le celle, i cartelli e le loro scritte. Il prologo
## nuovo ha due livelli nello stesso file: A, il cimitero fino alla torre, e B, la fuga per i Tamburi
## fino al garage. Il prologo di prima, in un livello solo, resta per i test e per la grafica
## (prologo.txt si rifà da lì con tools/ldtk/livelli_ldtk.py e serve agli script della grafica).
const PROLOGUE_MAP := "res://data/platform/prologo_v2.ldtk"
const PROLOGUE_V1 := "res://data/platform/prologo.ldtk"
## La grafica: per ora il cimitero (tools/ambienti/componi_prologo.py); la fuga e il garage in grigio.
## Nel prologo nuovo la prima schermata di A è quella di prima, col pavimento ART_SHIFT_Y px più giù:
## lì si usa la grafica di prima fino ad ART_CROP_X, il resto è greybox.
const PROLOGUE_ART := "res://assets/env/prologo/layers.json"
const ART_SHIFT_Y := 220
const ART_CROP_X := 520
## Le tavole vestite di car-grafica, livello per livello, nell'ordine in cui si disegnano (la dopo sta
## sopra la prima dove si toccano).
## - A1-A3, il cimitero dall'ingresso alla galleria (colonne 0-145 di A, x 0-2920): le aiuole e la
##   fontanella, le trincee della condotta con le transenne, le cappelle e il ricovero sotto il cipresso.
##   A1 riusa le colonne 0-25 della scena di prima, che nel prologo nuovo non si disegna più.
## - A4, la galleria del cimitero (colonne 144-229 di A): la scena, le colonne davanti e i pezzi a stati
##   (la porticina intera o rotta, il cancello del deposito chiuso o aperto).
## - A6, il cantiere davanti al muro di San Brunone (colonne 274-347): i lampeggianti, il quadro con la
##   leva, i fari, il cancelletto, i LED dei pannelli ETERNA e le scintille sulla pozza.
## - B1, la strada fuori dal cimitero (colonne 0-35 di B): il fioraio, il purificatore, la pensilina e
##   il fianco della chiesa; le luci menta dell'ologramma, del purificatore e dello schermo.
## - B2, le palazzine dei Tamburi (colonne 36-140 di B): il piano medio dietro, la bici del
##   fruttivendolo col sigillo o libera, la serranda della cantina chiusa o aperta.
## - B3, il forno e lo scavo (colonne 128-171 di B, sopra terra dalla 134): il sacchetto dei taralli, il
##   fumo della canna fumaria e la porta della 168 chiusa dietro GIG.
## - B4, il garage (colonne 172-227 di B, dalla cima alla terra): il lucernario, il banco e la stanza
##   chiusa; lo scaffale del registro è vuoto, il registro sarà uno sprite a parte.
const A1_ART := "res://assets/env/prologo/v2/a1/a1.json"
const A2_ART := "res://assets/env/prologo/v2/a2/a2.json"
const A3_ART := "res://assets/env/prologo/v2/a3/a3.json"
const GALLERY_ART := "res://assets/env/prologo/v2/a4/a4.json"
const A5_ART := "res://assets/env/prologo/v2/a5/a5.json"
const A6_ART := "res://assets/env/prologo/v2/a6/a6.json"
## La soglia del cantiere ETERNA fra A5 e A6: solo pezzi, senza scena, sopra quella di A6.
const CANTIERE_ART := "res://assets/env/prologo/v2/cantiere/cantiere.json"
const B1_ART := "res://assets/env/prologo/v2/b1/b1.json"
const B2_ART := "res://assets/env/prologo/v2/b2/b2.json"
const B3_ART := "res://assets/env/prologo/v2/b3/b3.json"
const B4_ART := "res://assets/env/prologo/v2/b4/b4.json"
const CANTINE_B_ART := "res://assets/env/prologo/v2/cantine/cantine.json"
const CORTILE_B_ART := "res://assets/env/prologo/v2/cortile/cortile.json"
const S1_ART := "res://assets/env/prologo/v2/s1/s1.json"
const LEVEL_ART: Array = [[A1_ART, A2_ART, A3_ART, S1_ART, GALLERY_ART, A5_ART, A6_ART, CANTIERE_ART],
	[B1_ART, B2_ART, B3_ART, CORTILE_B_ART, CANTINE_B_ART, B4_ART]]
## I fondi larghi del livello (cielo, lontano, medio e vicino), disegnati allo zoom della vista: in A
## tutto il cimitero coi tre veli, rosa, scirocco e pioggia; in B la sera dei Tamburi, col vicino che è
## l'isolato dietro le palazzine della scena.
const WIDE_ART: Array = ["res://assets/env/prologo/v2/a/a_larghi.json",
	"res://assets/env/prologo/v2/b/b_larghi.json"]
## I tempi degli stati che si muovono da soli, in tick: il lampeggio del cantiere, il respiro dei LED,
## le scintille (a raffiche: SPARK_ON tick su SPARK_CYCLE, un fotogramma ogni SPARK_STEP) e il fumo.
const BLINK_TICKS := 30
const BREATH_TICKS := 240
const SPARK_CYCLE := 100
const SPARK_ON := 36
const SPARK_STEP := 4
const SMOKE_TICKS := 15
## Il sigillo SIDERA sulla catena del cancello di A5: le due scritte si alternano ogni SEAL_TICKS (1,2 s);
## quando GIG gli passa davanti ronza e tremola SEAL_FLICKERS volte, un fotogramma ogni SEAL_STEP.
const SEAL_TICKS := 72
const SEAL_FLICKERS := 3
const SEAL_STEP := 4
## Gli stati che stanno sopra una leva del livello (il quadro di cantiere di A6, il chiavistello di A5):
## lì la leva è disegnata dalla tavola, e lo stato cambia quando la si tira.
const LEVER_STATES := ["quadro_giu", "chiavistello_chiuso"]
## La telecamera tiene il pavimento a CAM_GROUND px dall'alto finché GIG non scende sotto (come la mappa
## di prima, alta 500 px): così l'introduzione si scioglie nel gioco senza scatti.
const CAM_GROUND := 230
## Il passaggio da un livello all'altro: il nero entra, il livello cambia a metà, il nero esce.
const SWITCH_TICKS := 40
## Il garage del prologo di prima, rispetto alla porta (colonna 300, righe 18-22): il pilota lo usa
## spostato dove sta la porta del livello.
const V1_DOOR := Vector2i(300, 18)

## Le vignette: titolo e didascalia provvisoria (le tavole vere sono i murales).
const VIGNETTES := {
	"mimmo": ["LA NOTTE DEI MORTI, 2086", "vignetta: il ricordo di Mimmo"],
	"riavvio": ["IL GARAGE", "vignetta: il ricordo del primo braccio, costruito qui"],
	"naso": ["CTRL + ALT + CANC", "vignetta: il terzo tasto, col naso"],
}
## Tick minimi di una vignetta prima che SALTO o ATTACCO la chiudano, e massimi.
const VIGNETTE_MIN := 30
const VIGNETTE_MAX := 600

## I tre tasti del riavvio, in ordine: CTRL, ALT e CANC.
const REBOOT_KEYS: Array[int] = [InputFrame.ATTACK, InputFrame.JUMP, InputFrame.DASH]
const REBOOT_LABELS: Array[String] = ["CTRL", "ALT", "CANC"]
## Entro questa distanza orizzontale SU funziona alla lapide e al banco (e compare il suggerimento).
const USE_REACH := 40
## Dopo il riavvio, i tick prima che gli Esattori sfondino la porta, e ogni quanto bussano.
const DOOR_BREAK := 540
const DOOR_BANG := 60

## Le ripartenze: i cartelli superati coi piedi a terra. Quelle dopo l'arena non rifanno lo scontro.
const CHECKPOINT_SIGNS: Array[String] = ["e", "f", "i", "j"]
## La scena nel motore del pignoramento (decisione 68): game/data/scene/pignoramento.json.
const PIGNORAMENTO := "pignoramento"
## I rinforzi al muro: la scena parte quando GIG sta in piedi sulla cima del muro del cimitero, che
## rispetto al cartello h va da dx +70 a +130, a dy -120 (sceneggiatura, «I rinforzi al muro»).
const RINFORZI := "rinforzi"
const RINFORZI_TOP := Vector3i(70, 130, -120)
## I murales di Totò nel prologo (docs/lore, i copioni dei murales): l'introduzione da «Nuova partita»,
## il ricordo di Mimmo alla lapide, il ricordo del primo braccio dopo il terzo tasto e il passaggio al
## capitolo 1, prima del cartello della fine.
const INTRO := "introduzione"
const MIMMO := "ricordo_mimmo"
const RICORDO_2064 := "ricordo_2064"
const PASSAGGIO := "passaggio_1"
## La fine: la scritta resta END_HOLD tick (4 s), ATTACCO o SALTO la chiudono dopo END_SKIP.
const END_HOLD := 240
const END_SKIP := 60

## La musica di ogni tratto e di ogni stato del prologo nuovo (tabella di car-musica, `musica-nel-gioco.md`).
## Cambiare un brano è cambiare un valore: `brano` è l'id di music.json ("" = silenzio), `fade` i secondi della
## dissolvenza (entrando nel tratto), `db` il volume in più o in meno. Se il brano manca, resta il silenzio.
## Sul cimitero (A1-A5) continua `lumini` piano, -6 dB (Luigi, 11 novembre: «Lumini continua piano»).
const MUSIC := {
	"vecchio": {"brano": "stage1", "fade": 0.5},                # il prologo di prima, un livello solo
	"A1": {"brano": "lumini", "fade": 2.0, "db": -6.0},         # la tomba di Mimmo
	"A2_A5": {"brano": "lumini", "fade": 2.0, "db": -6.0},      # viale, trincee, Colombe
	"S1": {"brano": "", "fade": 1.5},                           # il ricovero del custode
	"arena": {"brano": "pignoramento", "fade": 0.8},            # gli Esattori: continua il brano del messo
	"A6": {"brano": "", "fade": 4.0},                           # il cantiere sotto la pioggia
	"B1": {"brano": "stage1", "fade": 2.0, "db": -3.0},         # la fuga
	"B2": {"brano": "stage1", "fade": 1.5, "db": -3.0},
	"B2_cantine": {"brano": "", "fade": 1.0},                   # sotto la strada: solo le gocce
	"B3": {"brano": "stage1", "fade": 1.5, "db": -3.0},
	"B4": {"brano": "stage1", "fade": 1.5, "db": -3.0},         # verso il garage, a porta aperta
	"B4_porta": {"brano": "", "fade": 1.5},                     # dentro, con la porta chiusa: la pioggia
	"naso": {"brano": "", "fade": 1.0},                         # il terzo tasto
	"riavvio": {"brano": "riavvio", "fade": 0.0},               # Tere e l'occhio cyan
	"porta": {"brano": "porta", "fade": 1.0},                   # i colpi alla porta, fino all'uscita
	"passaggio": {"brano": "", "fade": 2.0},                    # il passaggio al capitolo 1 (niente jingle)
}
## Dove cominciano i tratti, in px (livello A: 20 px per cella nel piano di docs/lore/livelli/prologo.md).
const MUSIC_A2_X := 720
const MUSIC_A6_X := 5520
const MUSIC_B2_X := 720
const MUSIC_B3_X := 2640
const MUSIC_B4_X := 3360
## `riavvio` suona da quando si accende l'occhio cyan (la scarica del riavvio) per tanti tick, poi il
## brano dei colpi alla porta (`porta`) prende il suo posto: i colpi cominciano subito, ma il risveglio
## ha il suo momento.
const MUSIC_RIAVVIO_TICKS := 300

const C_VIGNETTE := Color8(18, 16, 24)
const C_INK := Color8(240, 232, 210)
## La vecchia tastiera beige del padre, sul banco.
const C_KEYBOARD := Color8(200, 190, 160)
const C_KEYBOARD_LO := Color8(120, 112, 96)
## Il dentro del garage, rispetto alla prima cella della porta (41 × 13 celle): lì non piove.
const GARAGE_SIZE := Vector2i(41, 13)
const C_GATE_ORANGE := Color8(196, 104, 40)

## Il file dei livelli (i test usano quello di prima), i nomi dei suoi livelli e quello che si gioca.
var map_file: String = PROLOGUE_MAP
var level: int = 0
var _levels: PackedStringArray = []
## Tick che restano del passaggio al livello dopo (0 = nessun passaggio).
var switch_t: int = 0
## Ripartenza attuale: indice nelle ripartenze del livello (-1 = la partenza del livello).
var checkpoint: int = -1
var rebooted: bool = false
var finished: bool = false
## L'uscita sul tetto: passato il segno Z, GIG corre da solo per OUTRO_RUN tick e salta; poco prima
## dell'apice, quando lo sprite passa al fotogramma OUTRO_ARC di jump_arc, il gioco si ferma e parte il
## passaggio (MP13): la figura del murale è quella posa, così sprite e figura si sovrappongono esatti.
## -1 = non ancora; outro_jump: ha già saltato. OUTRO_MAX è il limite, se il salto non arrivasse mai.
const OUTRO_ARC := 3
const OUTRO_RUN := 30
const OUTRO_MAX := 120
var outro_t: int = -1
var outro_jump: bool = false
## Cosa viene dopo, scritto sotto «FINE DEL PROLOGO», una riga per voce: lo dà main.gd in NUOVA PARTITA,
## che prosegue nello slice. Vuoto: la riga di sempre, quando il prologo si gioca da solo dai CAPITOLI.
var next_title: PackedStringArray = []
## Tick passati dalla fine, e il tick dell'arrivo sul tetto. Non entrano nell'hash: sono il passaggio
## alla schermata di fine, non la simulazione.
var end_t: int = 0
var end_tick: int = 0
## Vignetta aperta ("" = nessuna) e tick da quando è aperta.
var vignette: String = ""
var vignette_t: int = 0
var _after_vignette: String = ""
var seen_mimmo: bool = false
## L'introduzione al primo tick (da «Nuova partita» e dai capitoli; non dalla riga di comando né nei
## test). Solo regia: non entra nell'hash.
var play_intro: bool = false
## La scena dei rinforzi è già passata. È solo disegno: non entra nell'hash, come la scena stessa.
var seen_rinforzi: bool = false
## Il riavvio: 0 = non cominciato, 1-3 = tasti già premuti, 4 = fatto.
var reboot_step: int = 0
var door_closed: bool = false
## Il tratto di cui la musica suona adesso (MUSIC); "" = da applicare.
var _music_key: String = ""
## Tick che restano del brano del risveglio (MUSIC_RIAVVIO_TICKS dalla scarica del riavvio).
var _music_riavvio: int = 0
## Tick che mancano prima che gli Esattori sfondino la porta (-1 = non bussano).
var door_t: int = -1
## Piove da quando arrivano gli Esattori (decisione 54).
var raining: bool = false
var _door_cells: Array[Vector2i] = []
## I cancelli delle entità Cancello ({iid, cells, rect, colore, open}) e le leve ({iid, px, apre}).
## Le leve tirate restano tirate nelle ripartenze dello stesso livello.
var _gates2: Array[Dictionary] = []
var _levers: Array[Dictionary] = []
var pulled: PackedStringArray = []
## Il tempo (solo disegno): il cielo che si chiude, la pioggia, la luce sugli attori.
var weather: Weather
## La luce cyan del riavvio: un lampo breve sul GIG del gioco, che si spegne in REBOOT_LIGHT tick.
## Solo disegno: non entra nell'hash.
const REBOOT_LIGHT := 34
## La scarica del riavvio aspetta la fine del ricordo del 2064 (solo disegno).
var _reboot_fx_pending: bool = false
var _reboot_light: PointLight2D
var _reboot_light_t: int = 0
## I riflessi sul pavimento bagnato dell'arena (solo disegno).
var _wet: WetFloor
## Le tavole vestite del livello: i loro piani (un Backdrop per tavola, col suo cam_ref_y), i pezzi a
## stati di tutte, per nome (porta_intera, cancello_chiuso, quadro_su, fumo_2...), e dove stanno i
## cancelli disegnati (lì non si disegna la grata). Solo disegno.
var _galleries: Array[Backdrop] = []
## I fondi larghi del livello (WIDE_ART), se ci sono. Solo disegno.
var _wide_art: Backdrop
var _gallery_states: Dictionary = {}
var _gallery_gates: Array[Rect2] = []
## Il pavimento dell'arena dipinto in prospettiva (chiave "pavimento_arena"): {"tex", "x", "y"}; dove
## copre la vista prende il posto di quello disegnato. Solo disegno.
var _arena_floor: Dictionary = {}
## Il tremolio del sigillo: il tick in cui è cominciato, e se GIG gli era già davanti. Solo disegno.
var _seal_from: int = -100000
var _seal_near: bool = false
## Le luci vive delle tavole (chiave "luci" dei json): PointLight2D sugli attori, come nel resto del
## gioco; la luce sulla scena è già dipinta. Si spengono con le altre (F5, --no-lights).
var _gallery_lights: Array[PointLight2D] = []
var _gallery_light_base: Array = []
var _light_tex: GradientTexture2D
var _halo_tex: Dictionary = {}
var _pool_tex: GradientTexture2D
## La scena delle tavole prende anche gli aloni delle luci vive (gli attori no: hanno le loro).
const LIGHT_MASK_SCENE := 4

# ------------------------------------------------------------------ interni (solo disegno)
## Gli interni del livello (entità Interno di LDtk): {"nome", "rect", "stacco", "stacco_alto", "cam":
## [sinistra, destra, alto, basso]}. Dentro = i piedi di GIG nel rettangolo (bordo alto escluso, fondo
## compreso). Fuori dall'hash: cambiano solo quello che si vede.
var _interiors: Array[Dictionary] = []
## I limiti della telecamera di fuori (Telecamera di LDtk coi campi cam_*): {"rect", "cam"}.
var _cam_zones: Array[Dictionary] = []
## Lo stacco (Luigi: «soglia + luce, stacco solo dentro»): 0,3 s di nero a gradini, come la caduta; a
## metà cambia quello che si vede.
const CUT_TICKS := 18
const ZONE_HOLD := 8.0
## L'interno dove stanno i piedi (-1 fuori) e quello che si vede adesso (cambia a metà dello stacco).
var _zone_raw: int = -1
var _zone_shown: int = -1
var _cut_t: int = 0
var _prev_feet := Vector2.ZERO
## La copertura delle tavole (la facciata che nasconde l'interno): 1 piena, 0 sparita quando GIG è dentro.
var _cover_k: float = 1.0
## I nodi della copertura (sopra la scena, sotto GIG) e degli stipiti (sopra GIG), figli della stanza
## così si schiacciano con lei; le copertine, coi loro rettangoli, e i piani che si vedono solo dentro.
var _cover_nodes: Array[Node2D] = []
var _covers: Array[Sprite2D] = []
var _cover_front: Array[Rect2] = []
var _inside_layers: Array[Backdrop.Layer] = []
## Quello che si vede solo fuori, con la copertura (la sua emissione, gli stipiti di fuori), e solo dentro
## (il muro di dentro attorno alla porta, gli stipiti di dentro, la porta chiusa vista da dentro); la luce
## della porta aperta (il garage di B4).
var _cover_glow: Array[Sprite2D] = []
var _inside_art: Array[Sprite2D] = []
var _door_light: Sprite2D = null
## Le luci che si vedono solo dentro (le lampadine delle cantine), con la loro energia piena.
var _inside_lights: Array = []
## I segreti senza stacco (il ricovero di S1): la facciata, la sua emissione e le sue luci sfumano da
## sole quando i piedi di GIG sono in un interno che la facciata copre, con un k loro (1 piena, 0 sparita):
## {"arte": [Sprite2D], "luci": [[PointLight2D, energia]], "rect": Rect2, "k": float}.
var _secrets: Array[Dictionary] = []
## Le aperture nel tetto degli interni (il lucernario del garage, la grata delle cantine): colonne senza
## Pieno né cancelli sopra il bordo alto. Lì piove anche dentro. In quelle senza stacco dall'alto
## (_roof_fades, il lucernario) la copertura sfuma coi piedi di GIG mentre passa.
var _roof_holes: Array[Rect2] = []
var _roof_fades: Array[Rect2] = []
## L'interno di cui il meteo ha la fascia asciutta sopra il soffitto (-1: nessuno). Dentro le cantine
## la telecamera mostra anche la terra sopra il soffitto, dove non deve piovere; fuori lì c'è la strada.
var _dry_zone := -1
const ROOF_FADE := 40.0
## Quanto sopra il bordo alto di un buco del tetto conta la testa di GIG, da dentro.
const ROOF_HEAD := 120.0
## I limiti della vista: lo spostamento dal centro libero, e il passaggio morbido quando cambiano.
const LIMIT_BLEND := 24
var _view_push := Vector2.ZERO
var _view_snap: bool = true
var _limit_key: String = ""
var _blend_t: int = 0
var _blend_from := Vector2.ZERO


func _setup_stage() -> void:
	_levels = LdtkMap.level_names(map_file) if map_file.ends_with(".ldtk") else PackedStringArray()
	level = maxi(_levels.find(Game.options.level_name), 0) if Game.options.level_name != "" else 0
	map_path = _level_path(level)
	_stage_art()
	# Il pavimento dell'arena è la ghiaia del viale davanti al cancello, col cordolo e la terra rossa.
	floor_colors = {"floor": Color8(124, 116, 109), "line": Color8(104, 97, 92), "top": Color8(150, 141, 132),
		"kerb": Color8(96, 48, 38), "speck": Color8(158, 148, 138)}
	panels = {}
	arena_id = PIGNORAMENTO
	hud_title = "PROLOGO"
	use_lives = true
	arena_spawns = _pignoramento_spawns()


## I due Esattori del pignoramento, il messo e un rider, compaiono dove li lascia la scena (l'esito
## del copione). Senza copione entrano da sinistra, dal viale.
static func _pignoramento_spawns() -> Array:
	var sd := SceneData.load_scene(PIGNORAMENTO)
	var out: Array = []
	for who: String in ["messo", "rider"]:
		var e := sd.end_of(who)
		var s := {"type": str((sd.actors.get(who, {}) as Dictionary).get("tipo", who)), "delay": 0, "side": -1,
			"y": float(e.get("y", 200.0 if who == "messo" else 236.0))}
		if not e.is_empty():
			s["x"] = float(e["x"])
			s["verso"] = int(e.get("verso", 1))
		out.append(s)
	return out


## Il percorso del livello `i` del file (il file stesso, se ha un livello solo).
func _level_path(i: int) -> String:
	if _levels.size() <= 1:
		return map_file
	return map_file + "#" + _levels[clampi(i, 0, _levels.size() - 1)]


## Il prologo nuovo ha più livelli nello stesso file; quello di prima uno solo.
func _multi_level() -> bool:
	return _levels.size() > 1


## La grafica del livello: tutta nel prologo di prima, la prima schermata in A, niente in B.
func _stage_art() -> void:
	art_offset_y = 0
	art_crop_x = 0
	art_skip = []
	art_scenes = true
	env_path = PROLOGUE_ART
	if _multi_level():
		if level == 0:
			art_offset_y = ART_SHIFT_Y
			art_crop_x = ART_CROP_X
			# Della grafica di prima resta solo la prima schermata col suo primo piano: cielo, medio e
			# vicino sono i fondi larghi (WIDE_ART), che guardano a ovest per tutto il cimitero, e le
			# palazzine, le auto e i panni stesi della fuga di prima non ci sono.
			art_skip = ["cielo", "medio", "vicino", "cielo_fuga", "medio_fuga", "vicino_fuga", "davanti_fuga"]
			# La scena di prima no: la prima schermata ora è A1, che ne riusa le colonne 0-25 così com'erano.
			art_scenes = false
		else:
			env_path = ""


## La grafica del livello e la vestizione nuova: in A la galleria, in B le palazzine.
func _build_art() -> void:
	for n in _art_extra + _art_view:
		n.queue_free()
	_art_extra.clear()
	_art_view.clear()
	_wide_art = null
	for l in _gallery_lights:
		l.queue_free()
	_gallery_lights.clear()
	_gallery_light_base.clear()
	_galleries.clear()
	_gallery_states.clear()
	_gallery_gates.clear()
	for n in _cover_nodes:
		n.queue_free()
	_cover_nodes.clear()
	_covers.clear()
	_cover_front.clear()
	_inside_layers.clear()
	_cover_glow.clear()
	_inside_art.clear()
	_door_light = null
	_inside_lights.clear()
	_secrets.clear()
	_arena_floor = {}
	_seal_from = -100000
	_seal_near = false
	art_holes.clear()
	art_open_from = -1
	super._build_art()
	if _multi_level() and level < WIDE_ART.size():
		_build_wide_art(WIDE_ART[level])
	if _multi_level() and level < LEVEL_ART.size():
		for path: String in LEVEL_ART[level]:
			_build_gallery(path)
	_update_gallery()


## I fondi larghi del livello: un Backdrop coi suoi veli, in un nodo dietro a tutto che segue lo zoom
## della vista (_art_view).
func _build_wide_art(path: String) -> void:
	if path == "" or not FileAccess.file_exists(path):
		return
	var bd := Backdrop.new()
	if not bd.load_json(path):
		push_warning("Fondi larghi non validi (%s)" % "; ".join(bd.errors))
		return
	var node := Node2D.new()
	node.name = "SfondoLargo"
	add_child(node)
	move_child(node, 0)
	bd.build(node, node, 1)
	_art_view.append(node)
	_wide_art = bd


## Un tratto vestito (la galleria del cimitero, le palazzine dei Tamburi): la scena e i pezzi a stati
## nella stanza, dietro a quello che la stanza disegna (come la scena di prima); il piano medio dietro
## e le colonne davanti in nodi loro, che non sfumano col taglio.
func _build_gallery(path: String) -> void:
	if not FileAccess.file_exists(path):
		return
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (data is Dictionary):
		push_warning("Vestizione non leggibile: %s" % path)
		return
	var d: Dictionary = data
	var dir := path.get_base_dir()
	# Una tavola senza scena (la soglia del cantiere) ha solo pezzi, stati e luci.
	var sc: Variant = d.get("scena")
	if not (sc is Dictionary) and not (d.get("pezzi") is Dictionary) and not (d.get("segreto") is Dictionary):
		return
	var has_scene := sc is Dictionary
	# --b-grigio: in B niente scena né pezzi a stati, solo i piani; i blocchi restano grigi.
	var grey := Game.options.grey_b and level >= 1
	var scene_pos := Vector2(int(sc.get("x", 0)), int(sc.get("y", 0))) if has_scene else Vector2.ZERO
	var scene_w := 0.0
	if grey:
		var tex := SpriteSheet.load_texture(dir.path_join(str(sc.get("image", "")))) if has_scene else null
		scene_w = tex.get_width() if tex != null else 0.0
	else:
		if has_scene:
			var scene := _gallery_sprite(dir, sc)
			if scene == null:
				return
			var hole := Rect2(scene.position, scene.texture.get_size())
			art_holes.append(hole)
			scene_w = hole.size.x
		# Le luci dipinte della tavola (maxischermo, led, lampioni): sopra la scena, in additivo e fuori
		# dalla tinta del tempo, così restano accese anche quando la scena si scurisce.
		var em := _gallery_sprite(dir, d.get("emissione"))
		if em != null:
			_scene_art.erase(em)
			var m := CanvasItemMaterial.new()
			m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
			m.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
			em.material = m
		# Il muro di dentro attorno alla porta (sopra la scena accanto) e la luce della porta aperta:
		# solo dentro.
		var inners: Variant = d.get("dentro")
		for spec: Variant in (inners if inners is Array else [inners]):
			var inner := _gallery_sprite(dir, spec)
			if inner != null:
				_inside_art.append(inner)
		var inner_em := _gallery_sprite(dir, d.get("emissione_dentro"))
		if inner_em != null:
			_scene_art.erase(inner_em)
			inner_em.material = _additive()
			_inside_art.append(inner_em)
		var dl := _gallery_sprite(dir, d.get("luce_porta"))
		if dl != null:
			_scene_art.erase(dl)
			dl.material = _additive()
			_door_light = dl
	var lights: Variant = d.get("luci", [])
	if lights is Array and not grey:
		for lv: Variant in lights:
			_gallery_light(lv)
	var inner_lights: Variant = d.get("luci_dentro", [])
	if inner_lights is Array and not grey:
		for lv: Variant in inner_lights:
			var from := _gallery_lights.size()
			_gallery_light(lv)
			for i in range(from, _gallery_lights.size()):
				_inside_lights.append([_gallery_lights[i], _gallery_light_base[i][0]])
	var open_from := int(d.get("fondo_aperto_da", -1))
	if open_from >= 0:
		art_open_from = open_from if art_open_from < 0 else mini(art_open_from, open_from)
	var cover: Node2D = null if grey else _build_cover(dir, d)
	if not grey and d.get("segreto") is Dictionary:
		_build_secret(dir, d["segreto"])
	var states: Variant = d.get("stati", {})
	if states is Dictionary and not grey:
		for k: String in (states as Dictionary):
			if _gallery_states.has(k):
				push_warning("Vestizione: lo stato %s c'è già in un'altra tavola (%s)" % [k, path])
				continue
			var gate := k.begins_with("cancell") or k.begins_with("serranda")
			# Con la copertura, le ante del cancello stanno sopra di lei (e GIG sopra le ante).
			var s := _gallery_sprite(dir, states[k], cover if gate else null)
			if s != null:
				_gallery_states[k] = s
				if k == "porta_dentro":
					_inside_art.append(s)
				if gate:
					_gallery_gates.append(_sprite_rect(s))
					if cover != null:
						_cover_front.append(_sprite_rect(s))
	# I pezzi fermi alla scala di gioco (la moto del rider, il cartellone ETERNA): come la scena, sempre
	# accesi.
	# Quelli che si chiamano "davanti..." stanno sopra GIG, con gli stipiti (_build_cover).
	var pieces: Variant = d.get("pezzi", {})
	if pieces is Dictionary and not grey:
		for k: String in (pieces as Dictionary):
			if not k.begins_with("davanti"):
				var pc := _gallery_sprite(dir, pieces[k])
				# "copre": un pezzo pieno che fa da tavola (la terra sotto il pavimento di A4): la stanza
				# non ci disegna sopra le sue celle grigie (art_holes).
				if pc != null and bool((pieces[k] as Dictionary).get("copre", false)):
					art_holes.append(_sprite_rect(pc))
				# "sotto": sotto gli stati di un'altra tavola (il telaio della botola, sotto le serrande).
				var under: Variant = (pieces[k] as Dictionary).get("sotto", [])
				if pc != null and under is Array:
					var at := -1
					for st: Variant in under:
						var o: Sprite2D = _gallery_states.get(str(st))
						if o != null and o.get_parent() == pc.get_parent():
							at = o.get_index() if at < 0 else mini(at, o.get_index())
					if at >= 0:
						pc.get_parent().move_child(pc, at)
	# Il pavimento dell'arena dipinto e i suoi colori (per dove il dipinto non arriva).
	var af: Variant = d.get("pavimento_arena")
	if af is Dictionary and not grey:
		var tex := SpriteSheet.load_texture(dir.path_join(str(af.get("image", ""))))
		if tex != null:
			_arena_floor = {"tex": tex, "x": float(af.get("x", 0)), "y": float(af.get("y", 0))}
	var fc: Variant = d.get("floor_colors")
	if fc is Dictionary and not grey:
		for k: String in (fc as Dictionary):
			var c: Variant = fc[k]
			if floor_colors.has(k) and c is Array and (c as Array).size() >= 3:
				floor_colors[k] = Color8(int(c[0]), int(c[1]), int(c[2]))
	# I piani della grafica di prima che qui cambiano tratto o velocità (per esempio il cielo rosa che
	# sfuma più a lungo): campi del json dei piani, per nome.
	var fix: Variant = d.get("piani_di_prima", {})
	if fix is Dictionary and backdrop != null:
		for l: Backdrop.Layer in backdrop.layers:
			if (fix as Dictionary).has(l.name):
				_fix_layer(l, fix[l.name])
	var bd := Backdrop.new()
	bd.cam_ref_y = float(d.get("cam_ref_y", 450))
	var specs: Array = []
	for key: String in ["medio", "davanti"]:
		specs.append([key, d.get(key)])
	# Altri piani, così come sono scritti (senza i conti del medio).
	var more: Variant = d.get("piani", [])
	if more is Array:
		for lv: Variant in more:
			specs.append(["piano", lv])
	for spec: Array in specs:
		var key: String = spec[0]
		var lv: Variant = spec[1]
		if not (lv is Dictionary):
			continue
		var l := Backdrop.parse_layer(lv, dir)
		if l.texture == null:
			push_warning("Vestizione: manca %s" % lv.get("image", ""))
			continue
		if key == "medio":
			# Il piano medio parte dall'inizio della scena; se è più stretto di quanto la telecamera ne
			# scorre lungo la scena, si ripete.
			if not (lv as Dictionary).has("origin_x"):
				l.origin_x = int(scene_pos.x)
			var need := View.W + ceili(scene_w * l.scroll)
			if l.repeat_x <= 0 and l.texture.get_width() < need:
				l.repeat_x = l.texture.get_width()
		# Il primo piano di dentro (le colonne della galleria): si vede solo quando la copertura non c'è.
		if bool((lv as Dictionary).get("solo_dentro", false)):
			_inside_layers.append(l)
		bd.layers.append(l)
	if not bd.layers.is_empty():
		_galleries.append(bd)
		var back := Node2D.new()
		back.name = "SfondoVestizione"
		add_child(back)
		move_child(back, 0)
		var front := Node2D.new()
		front.name = "PrimoPianoVestizione"
		add_child(front)
		_art_extra.append_array([back, front])
		bd.build(back, front, 1)


## Una luce viva della tavola, alla sua posizione del mondo: colore, energia, raggio e altezza (per
## le normal map) dal json. Accende GIG e i droni. Con "alone" e "pozza" accende anche la scena, ma
## solo intorno alla luce dipinta: l'alone è un anello attorno alla fonte, la pozza un anello schiacciato
## sulla strada (alla y "y" della pozza); il centro resta quasi spento, così la luce già dipinta non
## raddoppia. "ritmo": "tremola" (il forno), "pulsa" (il maxischermo) o "lampeggia" (il led SIDERA), solo
## disegno.
func _gallery_light(spec: Variant) -> void:
	if not (spec is Dictionary):
		return
	var d: Dictionary = spec
	if _light_tex == null:
		_light_tex = _radial_tex(128, 128, -1.0)
		_pool_tex = _radial_tex(256, 48, 0.15)
	var nm := str(d.get("nome", _gallery_lights.size()))
	var col := Color.html(str(d.get("colore", "#ffffff")))
	var pos := Vector2(float(d.get("x", 0)), float(d.get("y", 0)))
	var rhythm := str(d.get("ritmo", ""))
	var l := _gallery_point(nm, _light_tex, col, float(d.get("energia", 0.5)),
			float(d.get("raggio", 100)) / 64.0, pos, Fighter.LIGHT_MASK_ACTORS, rhythm)
	l.height = float(d.get("altezza", 30))
	var halo: Variant = d.get("alone")
	if halo is Dictionary:
		var hole := snappedf(float(halo.get("vuoto", 0.15)), 0.05)
		if not _halo_tex.has(hole):
			_halo_tex[hole] = _radial_tex(128, 128, hole)
		_gallery_point(nm + "_alone", _halo_tex[hole], col, float(halo.get("energia", 0.15)),
				float(halo.get("raggio", 120)) / 64.0, pos, LIGHT_MASK_SCENE, rhythm)
	var pool: Variant = d.get("pozza")
	if pool is Dictionary:
		_gallery_point(nm + "_pozza", _pool_tex, col, float(pool.get("energia", 0.15)),
				float(pool.get("larghezza", 200)) / 128.0,
				Vector2(float(pool.get("x", pos.x)), float(pool.get("y", pos.y))), LIGHT_MASK_SCENE, rhythm)


func _gallery_point(nm: String, tex: Texture2D, col: Color, energy: float, sc: float, pos: Vector2,
		mask: int, rhythm: String) -> PointLight2D:
	var l := PointLight2D.new()
	l.name = "Luce_" + nm
	l.texture = tex
	l.color = col
	l.energy = energy
	l.texture_scale = sc
	l.range_item_cull_mask = mask
	l.blend_mode = Light2D.BLEND_MODE_ADD
	l.position = pos
	l.enabled = lights_on and not Game.options.no_lights
	_room_node.add_child(l)
	_gallery_lights.append(l)
	_gallery_light_base.append([energy, rhythm, float(_gallery_lights.size()) * 1.3])
	return l


## Il gradiente delle luci: pieno al centro (`hole` < 0), oppure ad anello: quasi spento fino alla
## frazione `hole` del raggio (dove la luce è già dipinta), pieno poco più in là, poi a sfumare.
static func _radial_tex(w: int, h: int, hole: float) -> GradientTexture2D:
	var t := GradientTexture2D.new()
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = w
	t.height = h
	var g := Gradient.new()
	if hole >= 0.0:
		g.offsets = PackedFloat32Array([0.0, hole, minf(hole + 0.22, 0.9), 1.0])
		g.colors = PackedColorArray([Color(1, 1, 1, 0.08), Color(1, 1, 1, 0.3), Color(1, 1, 1, 1),
				Color(1, 1, 1, 0)])
	else:
		g.set_color(0, Color.WHITE)
		g.set_color(1, Color(1, 1, 1, 0))
	t.gradient = g
	return t


## Il led che lampeggia piano (la telecamera SIDERA del cortile): 1 s acceso ogni 3.
const LED_TICKS := 180


## Il respiro delle luci vive al tick `t` (solo disegno): il forno tremola, il maxischermo pulsa, il led
## della telecamera lampeggia.
static func light_rhythm(rhythm: String, t: int, phase: float) -> float:
	match rhythm:
		"tremola":
			return 0.82 + 0.1 * sin(t * 0.31 + phase) + 0.08 * sin(t * 1.07 + phase * 2.0)
		"pulsa":
			return 0.8 + 0.2 * sin(t * TAU / 150.0 + phase)
		"lampeggia":
			return 1.0 if posmod(t, LED_TICKS) < LED_TICKS / 3 else 0.0
	return 1.0


func _tick_gallery_lights() -> void:
	for i in _gallery_lights.size():
		var b: Array = _gallery_light_base[i]
		if b[1] != "":
			_gallery_lights[i].energy = b[0] * light_rhythm(b[1], tick, b[2])


## Cambia i campi di un piano della grafica di prima (solo tratto, dissolvenze, origine e velocità).
static func _fix_layer(l: Backdrop.Layer, f: Variant) -> void:
	if not (f is Dictionary):
		return
	var fd: Dictionary = f
	l.scroll = float(fd.get("scroll", l.scroll))
	l.x_from = int(fd.get("x_from", l.x_from))
	l.x_to = int(fd.get("x_to", l.x_to))
	l.fade_in = maxi(0, int(fd.get("fade_in", l.fade_in)))
	l.fade_out = maxi(0, int(fd.get("fade_out", l.fade_out)))
	l.origin_x = int(fd.get("origin_x", l.origin_x))


## Un pezzo della galleria nella stanza, alla sua posizione del mondo (null se manca l'immagine); con
## `parent`, in quel nodo della stanza (la copertura, gli stipiti) invece che dietro alla stanza.
func _gallery_sprite(dir: String, spec: Variant, parent: Node2D = null) -> Sprite2D:
	if not (spec is Dictionary):
		return null
	var tex := SpriteSheet.load_texture(dir.path_join(str(spec.get("image", ""))))
	if tex == null:
		push_warning("Galleria: manca %s" % spec.get("image", ""))
		return null
	var s := Sprite2D.new()
	s.name = "Galleria_" + str(spec["image"]).get_basename()
	s.centered = false
	s.texture = tex
	s.position = Vector2(int(spec.get("x", 0)), int(spec.get("y", 0)))
	# "alfa": quanto si vede il pezzo (l'ombra del cortile si può alleggerire).
	s.modulate.a = float(spec.get("alfa", 1.0))
	s.show_behind_parent = parent == null
	s.light_mask = 1 | LIGHT_MASK_SCENE
	(parent if parent != null else _room_node).add_child(s)
	_scene_art.append(s)
	return s


## La copertura della tavola (chiave "copertura": la facciata davanti all'interno, che sfuma quando GIG
## entra) e gli stipiti (chiave "stipiti", sopra GIG). La copertura sta in un nodo della stanza sopra
## la scena, le persone e i droni (z 6), dove vanno anche le ante dei cancelli; gli stipiti in uno sopra
## GIG (z 8). Ritorna il nodo della copertura (null se la tavola non ce l'ha).
func _build_cover(dir: String, d: Dictionary) -> Node2D:
	var node: Node2D = null
	if d.get("copertura") is Dictionary:
		node = Node2D.new()
		node.name = "Copertura"
		node.z_index = 6
		_room_node.add_child(node)
		_cover_nodes.append(node)
		var s := _gallery_sprite(dir, d["copertura"], node)
		if s != null:
			# La facciata non prende gli aloni delle luci di dentro.
			s.light_mask = 1
			_covers.append(s)
			_cover_front.append(_sprite_rect(s))
			var glow := _gallery_sprite(dir, d.get("copertura_emis"), node)
			if glow != null:
				_scene_art.erase(glow)
				glow.material = _additive()
				_cover_glow.append(glow)
		# Quello che si vede sopra il soffitto da dentro (la terra sopra le cantine): sta con la copertura,
		# sopra la strada, le persone e i droni, e si vede solo dentro.
		var above_in := _gallery_sprite(dir, d.get("sopra_dentro"), node)
		if above_in != null:
			_inside_art.append(above_in)
	var jambs: Array = []
	# Gli stipiti di fuori e di dentro (il garage): si scambiano con lo stacco.
	var jamb_sides: Dictionary = {}
	if d.get("stipiti") is Array:
		jambs.append_array(d["stipiti"])
	elif d.get("stipiti") is Dictionary:
		for side: String in ["fuori", "dentro"]:
			if d["stipiti"].get(side) is Dictionary:
				jambs.append(d["stipiti"][side])
				jamb_sides[jambs.size() - 1] = side
	# I pezzi "davanti..." (il palo e l'anta del varco del cantiere) stanno sopra GIG come gli stipiti.
	var pieces: Variant = d.get("pezzi", {})
	if pieces is Dictionary:
		for k: String in (pieces as Dictionary):
			if k.begins_with("davanti"):
				jambs.append(pieces[k])
	if not jambs.is_empty():
		var front := Node2D.new()
		front.name = "Stipiti"
		front.z_index = 8
		_room_node.add_child(front)
		_cover_nodes.append(front)
		for i in jambs.size():
			var j := _gallery_sprite(dir, jambs[i], front)
			if j != null and jamb_sides.has(i):
				(_cover_glow if jamb_sides[i] == "fuori" else _inside_art).append(j)
	return node


## Un segreto senza stacco (chiave "segreto": "facciata", "emissione" in additivo, "luci"): sta in un
## nodo della stanza sopra GIG, le persone e i droni (z 6), come la copertura, ma sfuma con un k suo.
func _build_secret(dir: String, d: Dictionary) -> void:
	var node := Node2D.new()
	node.name = "Segreto"
	node.z_index = 6
	_room_node.add_child(node)
	_cover_nodes.append(node)
	var face := _gallery_sprite(dir, d.get("facciata"), node)
	if face == null:
		return
	face.light_mask = 1
	var sc: Dictionary = {"arte": [face], "luci": [], "rect": _sprite_rect(face), "k": 1.0}
	var glow := _gallery_sprite(dir, d.get("emissione"), node)
	if glow != null:
		_scene_art.erase(glow)
		glow.material = _additive()
		sc["arte"].append(glow)
	var lights: Variant = d.get("luci", [])
	if lights is Array:
		for lv: Variant in lights:
			var from := _gallery_lights.size()
			_gallery_light(lv)
			for i in range(from, _gallery_lights.size()):
				sc["luci"].append([_gallery_lights[i], _gallery_light_base[i][0]])
	_secrets.append(sc)


static func _additive() -> CanvasItemMaterial:
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	m.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
	return m


## Quello che prende la tinta del tempo: la scena (e la galleria), e le colonne davanti.
func _graded_art() -> Array:
	var out: Array = []
	out.append_array(_scene_art)
	for bd in _galleries:
		for l in bd.layers:
			out.append_array(l.sprites)
	return out


static func _sprite_rect(s: Sprite2D) -> Rect2:
	return Rect2(s.position, s.texture.get_size())


func _update_art() -> void:
	super._update_art()
	_update_gallery()


## I piani seguono la telecamera. Gli stati (solo disegno, dalla logica che c'è già):
## - la porticina è rotta quando al suo posto la mappa non è più piena;
## - cancello, serranda e cancelletto sono aperti quando lo è il cancello del livello che gli sta sotto;
## - la bici è libera quando il fruttivendolo che le sta accanto ha ringraziato;
## - il quadro di cantiere va su quando la sua leva è tirata, e con lui si accendono i fari;
## - i lampeggianti lampeggiano, i LED ETERNA respirano, le scintille crepitano a raffiche e il fumo
##   gira, sempre;
## - il sacchetto sparisce quando GIG prende i taralli che gli stanno sotto;
## - la porta della 168 è chiusa quando si è chiusa dietro GIG.
func _update_gallery() -> void:
	var c := (_view_c - View.SIZE / 2.0).round()
	for bd in _galleries:
		bd.update(int(c.x), tick, c.y - bd.cam_ref_y)
	# Dentro: la copertura sparisce e compare il primo piano di dentro.
	for l in _inside_layers:
		if l.node != null:
			l.node.modulate.a *= 1.0 - _cover_k
			l.node.visible = l.node.modulate.a > 0.0
	for s in _covers + _cover_glow:
		s.modulate.a = _cover_k
		s.visible = _cover_k > 0.0
	for s in _inside_art:
		s.modulate.a = 1.0 - _cover_k
		s.visible = _cover_k < 1.0
	for pair: Array in _inside_lights:
		(pair[0] as PointLight2D).visible = _cover_k < 1.0
		(pair[0] as PointLight2D).energy = float(pair[1]) * (1.0 - _cover_k)
	for sc: Dictionary in _secrets:
		var k: float = sc["k"]
		for a: Sprite2D in sc["arte"]:
			a.modulate.a = k
			a.visible = k > 0.0
		for pair: Array in sc["luci"]:
			(pair[0] as PointLight2D).visible = k > 0.0
			(pair[0] as PointLight2D).energy = float(pair[1]) * k
	if _door_light != null:
		_door_light.modulate.a = 1.0 - _cover_k
		_door_light.visible = _cover_k < 1.0 and not door_closed
	# I fondi larghi contano la parallasse dall'angolo di quello che si vede del mondo.
	if _wide_art != null:
		var v := _visible_rect().position.round()
		_wide_art.update(int(v.x), tick, v.y - _wide_art.cam_ref_y)
	_tick_gallery_lights()
	if _gallery_states.is_empty():
		return
	var broken := false
	if _gallery_states.has("porta_intera"):
		var p: Sprite2D = _gallery_states["porta_intera"]
		var mid := Vector2i((p.position + p.texture.get_size() / 2.0) / SolidGrid.TILE)
		broken = grid.cell(mid.x, mid.y) != SolidGrid.Cell.SOLID
	var freed := false
	if _gallery_states.has("bici_libera"):
		var near := _sprite_rect(_gallery_states["bici_libera"]).grow(40)
		for q in favors.persone:
			if q.thanked and near.has_point(Vector2(q.px)):
				freed = true
	var lever_up := _lever_pulled_under("quadro_giu")
	var latch_up := _lever_pulled_under("chiavistello_chiuso")
	var seal := _tick_seal()
	var bag_taken := false
	if _gallery_states.has("sacchetto"):
		var near := _sprite_rect(_gallery_states["sacchetto"]).grow(40)
		for it in favors.ristori:
			if it.taken and near.has_point(Vector2(it.home)):
				bag_taken = true
	var blink := (tick / BLINK_TICKS) % 2 == 0
	var spark := tick % SPARK_CYCLE < SPARK_ON
	var spark_f := (tick / SPARK_STEP) % 2
	for k: String in _gallery_states:
		var s: Sprite2D = _gallery_states[k]
		var on := true
		match k:
			"porta_intera":
				on = not broken
			"porta_rotta":
				on = broken
			"cancello_chiuso", "cancelletto_chiuso":
				on = not _gate_open_under(s)
			"cancello_aperto", "cancelletto_aperto":
				on = _gate_open_under(s)
			# La botola della cantina la alza il fruttivendolo: aperta da quando l'anta è su.
			"serranda_chiusa":
				on = not _gate_open_under(s, true)
			"serranda_aperta":
				on = _gate_open_under(s, true)
			"bici_sigillo":
				on = not freed
			"bici_libera":
				on = freed
			"quadro_giu", "fari_spenti":
				on = not lever_up
			"quadro_su", "fari_accesi":
				on = lever_up
			"chiavistello_chiuso":
				on = not latch_up
			"chiavistello_tirato":
				on = latch_up
			"sigillo_1":
				on = seal == 1
			"sigillo_2":
				on = seal == 2
			"lampeggianti_accesi", "varco_lampeggiante_acceso":
				on = blink
			"lampeggianti_spenti", "varco_lampeggiante_spento":
				on = not blink
			"led_eterna":
				s.modulate.a = 0.78 + 0.22 * (0.5 + 0.5 * sin(tick * TAU / BREATH_TICKS))
			"scintille_1":
				on = spark and spark_f == 0
			"scintille_2":
				on = spark and spark_f == 1
			"fumo_1", "fumo_2", "fumo_3":
				on = (tick / SMOKE_TICKS) % 3 == int(k.right(1)) - 1
			"sacchetto":
				on = not bag_taken
			"porta_chiusa":
				on = door_closed
			"porta_dentro":
				on = door_closed and _cover_k < 1.0
		s.visible = on


## Il cancello del livello sotto un cancello disegnato è aperto. `by_hand`: e chi lo apre a mano (la
## Persona del premio) l'ha già alzato.
func _gate_open_under(s: Sprite2D, by_hand: bool = false) -> bool:
	var r := _sprite_rect(s)
	for g in _gates2:
		if (g["rect"] as Rect2).intersects(r):
			return g["open"] and (not by_hand or favors.lifted(String(g["iid"])))
	return false


## Una leva del livello dentro uno stato che la disegna (il quadro di cantiere, il chiavistello).
func _lever_drawn(at: Vector2i) -> bool:
	for k: String in LEVER_STATES:
		if _gallery_states.has(k) and _sprite_rect(_gallery_states[k]).grow(8).has_point(Vector2(at)):
			return true
	return false


## La leva sotto lo stato `key` è già tirata.
func _lever_pulled_under(key: String) -> bool:
	if not _gallery_states.has(key):
		return false
	var near := _sprite_rect(_gallery_states[key]).grow(8)
	for l in _levers:
		if String(l["iid"]) in pulled and near.has_point(Vector2(l["px"])):
			return true
	return false


## Il sigillo SIDERA adesso: 1 o 2 (la scritta accesa), 0 spento (nel tremolio). Quando GIG gli arriva
## davanti, sotto lo schermo fino al pavimento, ronza e tremola; la sua luce segue lo schermo.
func _tick_seal() -> int:
	if not _gallery_states.has("sigillo_1"):
		return 0
	var r := _sprite_rect(_gallery_states["sigillo_1"])
	var front := Rect2(r.position.x - 6.0, r.position.y, r.size.x + 12.0, float(_floor_y) + 4.0 - r.position.y)
	var near := player != null and front.has_point(Vector2(player.px, player.py))
	if near and not _seal_near and tick - _seal_from > SEAL_FLICKERS * 2 * SEAL_STEP:
		_seal_from = tick
		if sound:
			Sfx.play_at(&"zap", player.px, 0.1, -12.0)
	_seal_near = near
	var t := tick - _seal_from
	var out := 1 + (tick / SEAL_TICKS) % 2
	if t >= 0 and t < SEAL_FLICKERS * 2 * SEAL_STEP and (t / SEAL_STEP) % 2 == 0:
		out = 0
	for i in _gallery_lights.size():
		if _gallery_lights[i].name == "Luce_sigillo":
			_gallery_lights[i].energy = _gallery_light_base[i][0] * [0.0, 1.0, 0.7][out]
	return out


## Un cancello del livello che ha un cancello disegnato sopra (lì niente grata).
func _gate_drawn(r: Rect2) -> bool:
	for q in _gallery_gates:
		if q.intersects(r):
			return true
	return false


## Lo stato disegnato della galleria (per i test): porta rotta, cancello aperto.
func gallery_state() -> Dictionary:
	var out := {}
	for k: String in _gallery_states:
		out[k] = (_gallery_states[k] as Sprite2D).visible
	return out


func _ready() -> void:
	super._ready()
	_read_level_things()
	# Il tempo: la pioggia a strati (quello alla profondità di GIG dietro gli attori, subito dopo la
	# stanza dei blocchi), il cielo e i piani del cimitero che si chiudono; nel garage non piove.
	weather = Weather.new()
	weather.setup(grid, _dry_rects(), 1)
	weather.attach(self, _view, _room_node)
	weather.grade_backdrop(backdrop, _graded_art())
	# Sopra il pavimento in profondità (z 1), sotto le ombre (60) e gli attori.
	_wet = WetFloor.new()
	_wet.z_index = 2
	_view.add_child(_wet)
	_reset()


## La porta, i cancelli e le leve del livello, dalle sue entità.
func _read_level_things() -> void:
	_door_cells.clear()
	for p: Vector2i in grid.marks.get("/", []):
		_door_cells.append(Vector2i(p.x / SolidGrid.TILE, p.y / SolidGrid.TILE - 1))
	_gates2.clear()
	_levers.clear()
	pulled.clear()
	_interiors.clear()
	_cam_zones.clear()
	for e: Dictionary in grid.entities:
		match String(e["tipo"]):
			"Interno":
				var r := Rect2(e["pos"], e["size"])
				var c: Dictionary = e["campi"]
				var cam := _cam_fields(c)
				# Senza nessun limite scritto (il ricovero) la telecamera resta libera; con almeno uno,
				# i vuoti sono i bordi del rettangolo (legenda-ldtk §5).
				if cam.any(func(v: float) -> bool: return is_finite(v)):
					var edge := [r.position.x, r.end.x, r.position.y, r.end.y]
					for i in 4:
						if not is_finite(cam[i]):
							cam[i] = edge[i]
				_interiors.append({"nome": str(c.get("nome", "")), "rect": r, "stacco": c.get("stacco", true) == true,
					"stacco_alto": c.get("stacco_alto", true) == true, "cam": cam})
			"Telecamera":
				var cam := _cam_fields(e["campi"])
				if cam.any(func(v: float) -> bool: return is_finite(v)):
					_cam_zones.append({"rect": Rect2(e["pos"], e["size"]), "cam": cam})
			"Cancello":
				var pos: Vector2i = e["pos"]
				var size: Vector2i = e["size"]
				var cells: Array[Vector2i] = []
				for y in range(pos.y / SolidGrid.TILE, (pos.y + size.y) / SolidGrid.TILE):
					for x in range(pos.x / SolidGrid.TILE, (pos.x + size.x) / SolidGrid.TILE):
						cells.append(Vector2i(x, y))
						_gate_cells[Vector2i(x, y)] = true
				_gates2.append({"iid": e["iid"], "cells": cells, "rect": Rect2(pos, size),
					"colore": str(e["campi"].get("colore", "grigio")), "open": false})
			"Leva":
				var apre: Array = e["campi"]["apre"] if e["campi"].get("apre") is Array else []
				_levers.append({"iid": e["iid"], "px": e["px"], "apre": apre})
	_apply_gates()


## I limiti cam_sinistra, cam_destra, cam_alto, cam_basso di una zona (INF dove sono vuoti).
static func _cam_fields(c: Dictionary) -> Array[float]:
	var out: Array[float] = []
	for k: String in ["cam_sinistra", "cam_destra", "cam_alto", "cam_basso"]:
		var v: Variant = c.get(k)
		out.append(float(v) if v != null else INF)
	return out


## I cancelli chiusi sono pieni; si aprono quando una leva che li apre è tirata, o col premio di una Persona.
func _apply_gates() -> void:
	for g in _gates2:
		g["open"] = false
		for l in _levers:
			if String(l["iid"]) in pulled and g["iid"] in l["apre"]:
				g["open"] = true
		# O una Persona che ringrazia (il fruttivendolo apre la serranda).
		if favors.is_open(String(g["iid"])):
			g["open"] = true
		for c: Vector2i in g["cells"]:
			grid.set_cell(c.x, c.y, SolidGrid.Cell.EMPTY if g["open"] else SolidGrid.Cell.SOLID)


func _on_favor_opened() -> void:
	_apply_gates()


## Dove non piove: negli interni del livello, e dentro il garage se il livello ha la porta; non sotto le
## aperture del tetto (il lucernario), dove la pioggia entra.
func _dry_rects(shown: int = -1) -> Array:
	var out: Array = []
	for z in _interiors:
		out.append(z["rect"])
	var band := Rect2()
	if shown >= 0 and shown < _interiors.size():
		var zr: Rect2 = _interiors[shown]["rect"]
		var cam_top: float = _interiors[shown]["cam"][2]
		if is_finite(cam_top) and cam_top < zr.position.y:
			band = Rect2(zr.position.x, cam_top, zr.size.x, zr.position.y - cam_top)
	if not _door_cells.is_empty():
		var d := _door_cells[0]
		out.append(Rect2(d.x * SolidGrid.TILE, (d.y - 8) * SolidGrid.TILE, GARAGE_SIZE.x * SolidGrid.TILE,
			GARAGE_SIZE.y * SolidGrid.TILE))
	_find_roof_holes()
	for h in _roof_holes:
		var cut: Array = []
		for r: Rect2 in out:
			if r.position.x < h.end.x and r.end.x > h.position.x and r.position.y < h.end.y and r.end.y > h.position.y:
				if h.position.x > r.position.x:
					cut.append(Rect2(r.position.x, r.position.y, h.position.x - r.position.x, r.size.y))
				if h.end.x < r.end.x:
					cut.append(Rect2(h.end.x, r.position.y, r.end.x - h.end.x, r.size.y))
			else:
				cut.append(r)
		out = cut
	if band.has_area():
		# La fascia, tagliata in x dai buchi del suo tetto (dalla grata piove fino in fondo).
		var parts: Array = [band]
		for h in _roof_holes:
			if h.position.y != band.end.y:
				continue
			var next: Array = []
			for r: Rect2 in parts:
				if r.position.x < h.end.x and r.end.x > h.position.x:
					if h.position.x > r.position.x:
						next.append(Rect2(r.position.x, r.position.y, h.position.x - r.position.x, r.size.y))
					if h.end.x < r.end.x:
						next.append(Rect2(h.end.x, r.position.y, r.end.x - h.end.x, r.size.y))
				else:
					next.append(r)
			parts = next
		out.append_array(parts)
	return out


## Il meteo segue l'interno inquadrato: la fascia asciutta sopra il soffitto cambia nel nero dello stacco.
func _sync_dry() -> void:
	if _zone_shown == _dry_zone or weather == null:
		return
	_dry_zone = _zone_shown
	weather.dry.clear()
	for r: Variant in _dry_rects(_dry_zone):
		weather.dry.append(r as Rect2)


## Le aperture nel tetto degli interni con lo stacco (il lucernario del garage, la grata delle cantine):
## le colonne senza Pieno né cancelli nella riga sopra il bordo alto; dove si entra dall'alto, solo
## quelle con una grata (celle sottili). Ognuna è alta quanto l'interno.
func _find_roof_holes() -> void:
	_roof_holes.clear()
	_roof_fades.clear()
	for z in _interiors:
		if not z["stacco"]:
			continue
		var r: Rect2 = z["rect"]
		# La cella subito sopra il bordo alto, anche quando il bordo cade a metà cella (la galleria di A4).
		var row := (int(r.position.y) - 1) / SolidGrid.TILE
		# Dove si entra dall'alto con lo stacco, le aperture libere sono entrate: piove solo dalle grate.
		var grate_only: bool = z["stacco_alto"]
		var from := -1
		var c0 := int(r.position.x) / SolidGrid.TILE
		var c1 := ceili(r.end.x / SolidGrid.TILE)
		for c in range(c0, c1 + 1):
			var open := c < c1 and grid.cell(c, row) != SolidGrid.Cell.SOLID and not _gate_cells.has(Vector2i(c, row))
			if open and grate_only:
				open = grid.cell(c, row) == SolidGrid.Cell.THIN or grid.cell(c, row - 1) == SolidGrid.Cell.THIN
			if open and from < 0:
				from = c
			elif not open and from >= 0:
				var h := Rect2(from * SolidGrid.TILE, r.position.y, (c - from) * SolidGrid.TILE, r.size.y)
				_roof_holes.append(h)
				if z["stacco"] and not z["stacco_alto"]:
					_roof_fades.append(h)
				from = -1


## Il passaggio al livello `i` dello stesso file: la mappa, la grafica, la porta, i cancelli e il tempo
## nuovi, e GIG alla partenza. Quello che si è fatto (Mimmo, il riavvio) resta.
func _enter_level(i: int) -> void:
	level = i
	map_path = _level_path(i)
	_stage_art()
	_load_map()
	_read_level_things()
	weather.grid = grid
	weather.dry.clear()
	for r: Variant in _dry_rects():
		weather.dry.append(r as Rect2)
	_dry_zone = -1
	weather.refresh_surfaces()
	for n: Node in [_art_back, _art_front]:
		if n != null:
			n.queue_free()
	_art_back = null
	_art_front = null
	for sp in _scene_art:
		sp.queue_free()
	_scene_art.clear()
	backdrop = null
	art_until_x = 0
	tilt_squash = TILT_SQUASH
	_build_art()
	weather.grade_backdrop(backdrop, _graded_art())
	checkpoint = -1
	_reset()


## Le ripartenze del livello, da sinistra: i cartelli LDtk con «ripartenza» (CHECKPOINT_SIGNS per una
## mappa senza).
func _cps() -> Array[String]:
	return grid.checkpoints if not grid.checkpoints.is_empty() else CHECKPOINT_SIGNS


## L'indice della ripartenza dell'arena: da lì in poi lo scontro è fatto e piove.
func _arena_cp() -> int:
	var cps := _cps()
	var id := "f"
	if not grid.arenas.is_empty() and str(grid.arenas[0].get("ripartenza", "")) != "":
		id = str(grid.arenas[0]["ripartenza"])
	var i := cps.find(id)
	return i if i >= 0 else 1 << 30


## La pioggia delle zone Meteo nel punto `p` (i piedi): -1 senza zone, 0 asciutto, 1 piove («inizia» come
## «forte»). Dove due zone si sovrappongono vale la più piccola (un interno asciutto dentro la pioggia
## del livello).
func _meteo_at(p: Vector2i) -> int:
	var out := -1
	var best := 1 << 62
	for e: Dictionary in grid.entities:
		if e["tipo"] != "Meteo":
			continue
		var r := Rect2i(e["pos"], e["size"])
		# I piedi sul fondo della zona contano dentro.
		if r.has_point(p - Vector2i(0, 1)) and r.get_area() < best:
			best = r.get_area()
			out = 0 if str(e["campi"].get("pioggia", "no")) == "no" else 1
	return out


func _reset() -> void:
	# Alla ripartenza la musica si decide da capo dal tratto in cui si riparte.
	_music_key = ""
	_music_riavvio = 0
	if grid == null or _door_cells.is_empty() and grid.marks.has("/"):
		super._reset()
		return
	var cp := checkpoint
	super._reset()
	var at := _checkpoint_pos(cp)
	# Il cartello dell'arena si supera solo a scontro finito (l'arena si apre 40 px prima).
	arena_done = cp >= _arena_cp()
	raining = cp >= _arena_cp() or _meteo_at(at) == 1
	switch_t = 0
	if weather != null:
		weather.set_rain(raining, true)
	_reboot_fx_pending = false
	vignette = ""
	finished = false
	outro_t = -1
	outro_jump = false
	squeeze_on = false
	_squeeze_k = 0.0
	end_t = 0
	player.arm_locked = not rebooted
	player.boosts_left = player.boosts_max()
	# La porta è chiusa dopo il riavvio e per chi riparte già dentro il garage.
	_set_door(rebooted or not _door_cells.is_empty() and cp >= 0 and at.x > (_door_cells[0].x + 2) * SolidGrid.TILE
		or not _multi_level() and cp >= CHECKPOINT_SIGNS.find("j"))
	door_t = DOOR_BREAK if rebooted else -1
	if rebooted:
		reboot_step = 4
	elif reboot_step < 4:
		reboot_step = 0
	player.place(at.x, at.y)
	player.facing = 1
	_reset_interiors()
	_cam = _cam_target()


## Alla ripartenza gli interni sono già com'è giusto: niente stacco, copertura e limiti a scatto.
func _reset_interiors() -> void:
	_prev_feet = Vector2(player.px, player.py)
	_zone_raw = -1
	_zone_raw = _interior_at(_prev_feet)
	_zone_shown = _zone_raw
	_cut_t = 0
	_view_snap = true
	_tick_interiors(true)


## Le spie: una per cartello di ripartenza, dove GIG riparte; accese quelle già superate. Dopo il
## riavvio si riparte dal banco del garage e le spie del cimitero non servono più.
func _checkpoint_lamps() -> Array:
	var out: Array = []
	if rebooted:
		return out
	var cps := _cps()
	for i in cps.size():
		if grid.marks.has(cps[i]):
			out.append([_checkpoint_pos(i), i <= checkpoint])
	return out


func _checkpoint_pos(cp: int) -> Vector2i:
	if rebooted and grid.marks.has("X"):
		return grid.marks["X"][0]
	var cps := _cps()
	if cp < 0 or cp >= cps.size() or not grid.marks.has(cps[cp]):
		return _start
	var p: Vector2i = grid.marks[cps[cp]][0]
	return Vector2i(p.x - 30, p.y)


func _set_door(closed: bool) -> void:
	door_closed = closed
	for c in _door_cells:
		grid.set_cell(c.x, c.y, SolidGrid.Cell.SOLID if closed else SolidGrid.Cell.EMPTY)


# ------------------------------------------------------------------ tick

func _stage_tick(frame: InputFrame) -> InputFrame:
	if switch_t > 0:
		switch_t -= 1
		if switch_t == SWITCH_TICKS / 2:
			_enter_level(level + 1)
			switch_t = SWITCH_TICKS / 2
		return InputFrame.new()
	if finished:
		end_t += 1
		if end_t == END_HOLD or end_t > END_SKIP and end_t < END_HOLD and (
				frame.was_pressed(InputFrame.ATTACK) or frame.was_pressed(InputFrame.JUMP)):
			end_t = END_HOLD + 1
			prologue_finished.emit({"ticks": end_tick, "prologue": true})
		return InputFrame.new()
	# L'uscita sul tetto: avanti tutta, poi il salto, tenuto fino all'apice.
	if outro_t >= 0:
		outro_t += 1
		if not outro_jump and outro_t > OUTRO_RUN and player.state == PlatformPlayer.State.GROUND:
			outro_jump = true
			return InputFrame.new(InputFrame.RIGHT | InputFrame.JUMP, InputFrame.JUMP)
		return InputFrame.new(InputFrame.RIGHT | (InputFrame.JUMP if outro_jump else 0), 0)
	if vignette != "":
		vignette_t += 1
		var close := vignette_t >= VIGNETTE_MAX or vignette_t >= VIGNETTE_MIN and (
			frame.was_pressed(InputFrame.JUMP) or frame.was_pressed(InputFrame.ATTACK))
		if close:
			vignette = ""
			if _after_vignette != "":
				var next := _after_vignette
				_after_vignette = ""
				_open_vignette(next)
			elif reboot_step == 3:
				if SceneData.load_scene(RICORDO_2064).errors.is_empty():
					request_scene(RICORDO_2064, {"gig": scene_pose_player("X")})
				_finish_reboot()
		return InputFrame.new()
	# Da «Nuova partita»: l'introduzione, coi murales di Totò, si scioglie nel cimitero.
	if play_intro:
		play_intro = false
		request_scene(INTRO, {"gig": scene_pose_player("")})
		return InputFrame.new()
	var on_ground := player.state == PlatformPlayer.State.GROUND
	# Le leve: SU accanto, coi piedi a terra, apre i cancelli che comanda.
	var lv := _near_lever()
	if lv >= 0 and frame.was_pressed(InputFrame.UP):
		pulled.append(String(_levers[lv]["iid"]))
		_apply_gates()
		_on_event("lever")
		return InputFrame.new()
	# La lapide di Mimmo: SU davanti apre il ricordo (il murale; la vignetta, se il copione non c'è).
	if not seen_mimmo and on_ground and _near("M", USE_REACH) and frame.was_pressed(InputFrame.UP):
		seen_mimmo = true
		if SceneData.load_scene(MIMMO).errors.is_empty():
			request_scene(MIMMO, {"gig": scene_pose_player("M")})
		else:
			_open_vignette("mimmo")
		return InputFrame.new()
	# Il riavvio: SU accanto al banco attacca la tastiera, poi i tre tasti in ordine.
	if not rebooted and on_ground and _near("X", USE_REACH):
		if reboot_step == 0 and frame.was_pressed(InputFrame.UP):
			reboot_step = 1
			_on_event("keyboard")
			return InputFrame.new()
		if reboot_step >= 1:
			if frame.was_pressed(REBOOT_KEYS[reboot_step - 1]):
				reboot_step += 1
				_on_event("reboot_key")
				if reboot_step == 4:
					reboot_step = 3
					# Col copione il naso viene prima e il ricordo del 2064 dopo; senza, le due vignette.
					if SceneData.load_scene(RICORDO_2064).errors.is_empty():
						_open_vignette("naso")
					else:
						_open_vignette("riavvio")
						_after_vignette = "naso"
			return InputFrame.new()
	elif reboot_step in [1, 2]:
		reboot_step = 0
	return frame


func _stage_after_step() -> void:
	_music_update()
	if finished or switch_t > 0:
		return
	if outro_t >= 0:
		var up := player.vy > PlatformPlayer.to_sub(PlatformPlayer.ARC_VY[OUTRO_ARC - 1])
		if outro_jump and player.state == PlatformPlayer.State.AIR and up or outro_t >= OUTRO_MAX:
			_end_prologue()
		return
	var on_ground := player.state == PlatformPlayer.State.GROUND
	# Ripartenze: il cartello superato coi piedi a terra.
	var nxt := checkpoint + 1
	var cps := _cps()
	if on_ground and nxt < cps.size() and grid.marks.has(cps[nxt]):
		var p: Vector2i = grid.marks[cps[nxt]][0]
		if player.px >= p.x and player.py == p.y:
			checkpoint = nxt
			_on_checkpoint()
	# Entrato nel garage, la porta si chiude dietro GIG.
	if not door_closed and not _door_cells.is_empty() and player.left() > (_door_cells[0].x + 2) * SolidGrid.TILE \
			and player.py > (_door_cells[0].y - 6) * SolidGrid.TILE:
		_set_door(true)
		_on_event("door_close")
	# Dopo il riavvio gli Esattori bussano, poi sfondano: chi è ancora dentro riparte dal banco.
	if door_t > 0:
		door_t -= 1
		if door_t % DOOR_BANG == 0:
			_on_event("door_bang")
		if door_t == 0:
			_on_event("door_break")
			if _inside_garage():
				_reset()
	# Le zone Meteo: dove piove comincia a piovere.
	if not raining and _meteo_at(Vector2i(player.px, player.py)) == 1:
		raining = true
	# I rinforzi al muro, nel prologo di prima (in quello nuovo la scena è da rifare sulla torre).
	if not seen_rinforzi and on_ground and not _multi_level() and _on_wall_top():
		seen_rinforzi = true
		var poses := {"gig": scene_pose_player("h")}
		player.facing = 1
		request_scene(RINFORZI, poses)
	if grid.marks.has("Z") and player.py <= grid.marks["Z"][0].y and player.px >= grid.marks["Z"][0].x - 40:
		# L'uscita porta a un altro livello dello stesso file: il nero, poi il livello dopo.
		if LdtkMap.next_path(map_path, grid) != "" and level + 1 < _levels.size():
			switch_t = SWITCH_TICKS
			_on_event("level_exit")
			return
		# L'ultimo livello: i comandi passano all'uscita (un secondo, fino all'apice del salto), e la
		# telecamera si stringe su GIG verso l'aggancio a MP13.
		outro_t = 0
		squeeze_on = true


## La fine del prologo, all'apice del salto dell'uscita.
func _end_prologue() -> void:
	finished = true
	end_t = 0
	end_tick = tick
	_on_event("prologue_end")
	_music_update()
	# Il passaggio al capitolo 1: il gioco fermo a metà salto, MP13 a spray, poi il cartello.
	request_scene(PASSAGGIO, {"gig": scene_pose_player("")})


## GIG è in piedi sulla cima del muro del cimitero, accanto al cancello chiuso.
func _on_wall_top() -> bool:
	if not grid.marks.has("h"):
		return false
	var h: Vector2i = grid.marks["h"][0]
	return player.py == h.y + RINFORZI_TOP.z and player.px >= h.x + RINFORZI_TOP.x and player.px <= h.x + RINFORZI_TOP.y


func _finish_reboot() -> void:
	reboot_step = 4
	rebooted = true
	player.arm_locked = false
	player.boosts_left = player.boosts_max()
	door_t = DOOR_BREAK
	# Con il ricordo del 2064 la scarica si vede quando il murale si chiude.
	if _scene_request.is_empty():
		_on_event("reboot")
	else:
		_reboot_fx_pending = true


func scene_end(sp: ScenePlayer) -> void:
	super.scene_end(sp)
	if _reboot_fx_pending:
		_reboot_fx_pending = false
		_on_event("reboot")


## GIG è entrato nell'arena del cancello: parte la scena del pignoramento (decisione 68; Luigi: «La
## presentazione del messo è un filmato»). La simulazione ne applica subito l'esito, nello stesso tick:
## GIG davanti al cancello chiuso, girato verso il viale, col segno del laser sul braccio; il messo e
## il rider al loro posto; comincia a piovere (decisione 54). La scena è solo disegno: nei test, che
## non la recitano, lo scontro comincia uguale.
func _on_arena_fight() -> void:
	var g := arena.player
	var poses := {"gig": scene_pose_fighter(g)}
	var e := SceneData.load_scene(PIGNORAMENTO).end_of("gig")
	if not e.is_empty():
		g.px = _arena_cam_x + float(e["x"])
		g.py = float(e["y"])
		g.facing = 1 if int(e.get("verso", g.facing)) >= 0 else -1
	g.mark()
	raining = true
	arena.start_next_wave()
	request_scene(PIGNORAMENTO, poses)


## Il gioco riparte dopo la scena del pignoramento: lo scontro ha la sua musica.
func _on_scene_handoff(_id: String) -> void:
	# Lo scontro non ha strati: continua il brano del pignoramento (MUSIC["arena"]).
	pass


# ------------------------------------------------------------------ musica

## Il prologo nuovo decide la musica da sé, dal tratto (MUSIC). All'ingresso dall'introduzione resta il
## tema del titolo, che la scena spegne sul murale del cimitero.
## TestRoom._ready la chiama prima di creare GIG (con --start-x, senza introduzione): allora il brano lo
## sceglie il primo tick, che sa dov'è GIG.
func _start_music() -> void:
	if not play_intro and player != null:
		_music_update()


## Il tratto o lo stato del prologo, a cui MUSIC dà il brano. Legge solo lo stato: la musica non entra
## nella simulazione.
func _music_tratto() -> String:
	if not _multi_level():
		return "vecchio"
	if finished:
		return "passaggio"
	if vignette == "riavvio" or vignette == "naso":
		return vignette
	if rebooted:
		return "riavvio" if _music_riavvio > 0 else "porta"
	var feet := Vector2(player.px, player.py)
	var inside := ""
	var zi := _interior_at(feet)
	if zi >= 0:
		inside = str(_interiors[zi]["nome"])
	if level == 0:
		if arena_phase == ArenaPhase.FIGHT:
			return "arena"
		if arena_done or arena_phase == ArenaPhase.LEAVE or player.px >= MUSIC_A6_X:
			return "A6"
		if inside == "ricovero":
			return "S1"
		return "A1" if player.px < MUSIC_A2_X else "A2_A5"
	if inside == "cantine":
		return "B2_cantine"
	if door_closed:
		return "B4_porta"
	if player.px < MUSIC_B2_X:
		return "B1"
	if player.px < MUSIC_B3_X:
		return "B2"
	return "B3" if player.px < MUSIC_B4_X else "B4"


## La riga di MUSIC del tratto: {"brano": StringName ("" = silenzio), "fade": s, "db": dB}.
func _music_for(tratto: String) -> Dictionary:
	var row: Dictionary = MUSIC.get(tratto, {})
	return {"brano": StringName(str(row.get("brano", ""))), "fade": float(row.get("fade", 0.5)),
		"db": float(row.get("db", 0.0))}


## Un tick: se il tratto è cambiato, la musica cambia. Durante una scena la musica è della scena.
func _music_update() -> void:
	if (not sound and music == Music) or scene != null or not _scene_request.is_empty():
		return
	_music_riavvio = maxi(_music_riavvio - 1, 0)
	_music_apply()


## Suona il brano del tratto di adesso, se non è già quello.
func _music_apply() -> void:
	var key := _music_tratto()
	if key == _music_key:
		return
	_music_key = key
	var row := _music_for(key)
	var track: StringName = row["brano"]
	if track != &"" and music.has_track(track):
		music.play(track, row["fade"], row["db"])
		# Lo stesso brano che già suona (lumini dopo il ricordo di Mimmo) non riparte: cambia solo il volume.
		music.set_trim(row["db"], row["fade"])
	else:
		music.stop(row["fade"])


## Fine di una scena: il brano del tratto in cui si torna (E1: se la scena era partita dal silenzio, il
## suo brano si ferma invece di restare acceso sul gioco).
func scene_music_end(_prev: StringName) -> void:
	_music_key = ""
	# La scena del ricordo del 2064 finisce sulla scarica del riavvio: da lì suona `riavvio`.
	if _reboot_fx_pending:
		_music_riavvio = MUSIC_RIAVVIO_TICKS
	_music_apply()


## La pioggia si vede: fuori dalle scene sempre, quando piove; in una scena da quando il cielo si
## chiude (l'evento "pioggia" della regia).
func _rain_shown() -> bool:
	return raining and (scene == null or not scene.holds_sim() or bool(scene_flags.get("pioggia", false)))


func _open_vignette(id: String) -> void:
	vignette = id
	vignette_t = 0


func _near(mark: String, reach: int) -> bool:
	if not grid.marks.has(mark):
		return false
	var m: Vector2i = grid.marks[mark][0]
	return absi(player.px - m.x) <= reach and player.py == m.y


## La leva a portata di SU (coi piedi alla sua altezza) non ancora tirata, o -1.
func _near_lever() -> int:
	if player.state != PlatformPlayer.State.GROUND:
		return -1
	for i in _levers.size():
		var p: Vector2i = _levers[i]["px"]
		if String(_levers[i]["iid"]) not in pulled and absi(player.px - p.x) <= USE_REACH and player.py == p.y:
			return i
	return -1


func _inside_garage() -> bool:
	if _door_cells.is_empty():
		return false
	var x0 := (_door_cells[0].x + 2) * SolidGrid.TILE
	return player.px > x0 and player.py > (_door_cells[0].y - 8) * SolidGrid.TILE


## Prima del riavvio il braccio è morto: niente Vista e niente copie.
func _arm_alive() -> bool:
	return rebooted


func _stage_hash() -> Array:
	return [checkpoint, rebooted, finished, vignette, vignette_t, seen_mimmo, reboot_step, door_closed, door_t, raining,
		level, switch_t, ",".join(pulled), outro_t, outro_jump]


## I suoni del prologo, poi quelli della stanza.
const PROLOGUE_SFX := {
	"keyboard": [&"ui_confirm", -2.0], "reboot_key": [&"ui_move", 0.0], "reboot": [&"zap", 0.0],
	"door_close": [&"bin_hit", -4.0], "door_bang": [&"body_thud", -3.0], "door_break": [&"bin_break", 0.0],
	"prologue_end": [&"go_arrow", 0.0], "lever": [&"ui_confirm", -2.0], "level_exit": [&"go_arrow", -2.0],
}


func _event_sound(e: String) -> void:
	if sound and PROLOGUE_SFX.has(e):
		var s: Array = PROLOGUE_SFX[e]
		Sfx.play_at(s[0], player.px, 0.05, s[1])
		return
	super._event_sound(e)


func _on_event(e: String) -> void:
	super._on_event(e)
	if e == "reboot":
		_music_riavvio = MUSIC_RIAVVIO_TICKS
		# Il braccio riparte: una scarica intorno a GIG, che va dal bianco al cyan al verde acqua e lascia
		# la scia, e un lampo di luce cyan su di lui.
		for i in 34:
			var a := _spark_rng.randf_range(0.0, TAU)
			var s := _spark_rng.randf_range(1.2, 3.6) if i < 26 else _spark_rng.randf_range(4.0, 5.5)
			_spark(player.px, player.py - 60, cos(a) * s, sin(a) * s - 0.5, _spark_rng.randi_range(14, 30), C_CYAN, true)
		_flash_reboot_light()


## Il lampo cyan del riavvio: una PointLight2D sugli attori, accanto al braccio, che si spegne da sola.
func _flash_reboot_light() -> void:
	if _reboot_light == null:
		var g := GradientTexture2D.new()
		g.fill = GradientTexture2D.FILL_RADIAL
		g.fill_from = Vector2(0.5, 0.5)
		g.fill_to = Vector2(1.0, 0.5)
		g.width = 128
		g.height = 128
		var grad := Gradient.new()
		grad.set_color(0, Color.WHITE)
		grad.set_color(1, Color(1, 1, 1, 0))
		g.gradient = grad
		_reboot_light = PointLight2D.new()
		_reboot_light.name = "LuceDelRiavvio"
		_reboot_light.texture = g
		_reboot_light.texture_scale = 1.5
		_reboot_light.height = 24.0
		_reboot_light.color = C_CYAN
		_reboot_light.blend_mode = Light2D.BLEND_MODE_ADD
		_reboot_light.range_item_cull_mask = Fighter.LIGHT_MASK_ACTORS
		_view.add_child(_reboot_light)
	_reboot_light_t = REBOOT_LIGHT
	_update_reboot_light()


func _update_reboot_light() -> void:
	if _reboot_light == null:
		return
	var k := float(_reboot_light_t) / REBOOT_LIGHT
	_reboot_light.position = Vector2(player.px + 10 * player.facing, player.py - 56)
	_reboot_light.energy = 2.2 * k * k
	_reboot_light.enabled = lights_on and _reboot_light_t > 0


func _set_lights(on: bool) -> void:
	super._set_lights(on)
	for l in _gallery_lights:
		l.enabled = on
	if weather != null:
		weather.set_lights(on)
	_update_reboot_light()


## La telecamera: con GIG sul pavimento del livello o più in alto, il pavimento resta a CAM_GROUND px
## dall'alto (non si guarda sotto terra); nelle fosse segue GIG come sempre.
func _cam_target() -> Vector2:
	var t := super._cam_target()
	var gy := _ground_y()
	if gy > 0 and player.py <= gy:
		t.y = minf(t.y, float(gy - CAM_GROUND))
	return t


## L'interno dove stanno i piedi di GIG (-1 fuori): bordo alto escluso (sul tetto si è fuori), fondo compreso.
## Da quello in cui si è già si esce solo oltre ZONE_HOLD pixel: un salto che sfiora il soffitto, o due
## passi avanti e indietro sulla soglia, non fanno lampeggiare lo stacco. Sul tetto (12 px sopra la
## galleria) si è fuori.
func _interior_at(feet: Vector2) -> int:
	if _zone_raw >= 0 and _zone_raw < _interiors.size() \
			and _in_zone((_interiors[_zone_raw]["rect"] as Rect2).grow(ZONE_HOLD), feet):
		return _zone_raw
	for i in _interiors.size():
		if _in_zone(_interiors[i]["rect"], feet):
			return i
	return -1


static func _in_zone(r: Rect2, feet: Vector2) -> bool:
	return feet.x >= r.position.x and feet.x < r.end.x and feet.y > r.position.y and feet.y <= r.end.y


## Due interni che si vedono allo stesso modo (la galleria e il deposito, coi limiti uguali): fra loro
## niente stacco.
func _same_look(a: int, b: int) -> bool:
	return a >= 0 and b >= 0 and _interiors[a]["cam"] == _interiors[b]["cam"]


## Un tick degli interni (solo disegno, prima della telecamera): quando i piedi passano il bordo di un
## interno con lo stacco, 0,3 s di nero e a metà la vista nuova (la telecamera dentro i limiti, la
## copertura via); senza stacco la copertura sfuma. Tornando indietro nella prima metà lo stacco si
## riavvolge.
func _tick_interiors(force_snap: bool = false) -> void:
	var feet := Vector2(player.px, player.py)
	var raw := _interior_at(feet)
	if raw != _zone_raw:
		var cut := false
		if not _same_look(raw, _zone_raw):
			# Lo stacco dell'interno da cui si esce o in cui si entra, dal bordo che si passa.
			for i: int in [_zone_raw, raw]:
				if i < 0:
					continue
				var top: float = (_interiors[i]["rect"] as Rect2).position.y
				var over := feet.y <= top or _prev_feet.y <= top
				cut = cut or bool(_interiors[i]["stacco_alto" if over else "stacco"])
		_zone_raw = raw
		if _cut_t > CUT_TICKS / 2:
			# Nella prima metà: se si torna di là lo stacco si riavvolge, altrimenti a metà si prende
			# l'interno di adesso.
			if raw == _zone_shown:
				_cut_t = CUT_TICKS - _cut_t
		elif not cut:
			_zone_shown = raw
		else:
			# Uno stacco nuovo, o un altro dopo la metà di quello di prima (dal nero di adesso).
			_cut_t = CUT_TICKS - _cut_t + (1 if _cut_t > 0 else 0)
	_prev_feet = feet
	var snap := force_snap
	if _cut_t > 0:
		_cut_t -= 1
		if _cut_t == CUT_TICKS / 2:
			_zone_shown = _zone_raw
			snap = true
			_cam = _cam_target()
			_view_snap = true
	# Lo zoom della vista larga cambia dentro il nero (o subito, alla ripartenza).
	if snap and wide_cam:
		_wide_k = _wide_target()
	var target := 1.0
	if _zone_shown >= 0:
		var r: Rect2 = _interiors[_zone_shown]["rect"]
		for s in _covers:
			if _sprite_rect(s).intersects(r):
				target = 0.0
	_cover_k = target if snap else move_toward(_cover_k, target, 1.0 / CUT_TICKS)
	_sync_dry()
	# I segreti senza stacco: la facciata sfuma in 0,3 s quando i piedi sono nell'interno che copre.
	for sc: Dictionary in _secrets:
		var in_secret := raw >= 0 and (_interiors[raw]["rect"] as Rect2).intersects(sc["rect"])
		var to := 0.0 if in_secret else 1.0
		sc["k"] = to if snap else move_toward(sc["k"], to, 1.0 / CUT_TICKS)
	# Dal lucernario non c'è stacco: la copertura segue i piedi, piena 40 px sopra il bordo alto, sparita
	# sul bordo.
	if _cut_t == 0:
		for h in _roof_fades:
			if feet.x >= h.position.x and feet.x < h.end.x and feet.y > h.position.y - ROOF_FADE \
					and feet.y <= h.position.y:
				_cover_k = (h.position.y - feet.y) / ROOF_FADE
	# GIG sopra la copertura e le ante quando le tocca (fuori, davanti alla facciata); altrimenti con gli
	# altri attori, sotto le persone e i droni.
	var me := Rect2(feet.x - 16.0, feet.y - 100.0, 32.0, 100.0)
	var over := false
	for i in _cover_front.size():
		if me.intersects(_cover_front[i]) and (i >= _covers.size() or _cover_k > 0.0):
			over = true
	# Da dentro, con la testa in un buco del tetto (sotto la grata), GIG sta sopra la terra di sopra.
	if _cover_k < 1.0:
		for h in _roof_holes:
			if me.intersects(Rect2(h.position.x, h.position.y - ROOF_HEAD, h.size.x, ROOF_HEAD)):
				over = true
	_body.z_index = 7 if over else 0


## I limiti della vista adesso: [sinistra, destra, alto, basso] (INF dove non ce ne sono). Quelli
## dell'interno che si vede, o quelli delle Telecamera dove stanno i piedi.
func _cam_limits() -> Array[float]:
	if _zone_shown >= 0 and _zone_shown < _interiors.size():
		return _interiors[_zone_shown]["cam"]
	var out: Array[float] = [INF, INF, INF, INF]
	var feet := Vector2(player.px, player.py)
	for z in _cam_zones:
		if _in_zone(z["rect"], feet):
			for i in 4:
				if is_finite(z["cam"][i]):
					out[i] = z["cam"][i]
	return out


func _follow_camera() -> void:
	_tick_interiors()
	super._follow_camera()


## Negli interni chiusi sopra e sotto la vista larga torna stretta: sono disegnati per l'altezza di uno
## schermo (270 px), e a 2/3 sotto il pavimento resterebbe il vuoto.
func _wide_target() -> float:
	if _zone_shown >= 0 and _zone_shown < _interiors.size():
		var lim: Array = _interiors[_zone_shown]["cam"]
		if is_finite(lim[2]) and is_finite(lim[3]):
			return 0.0
	return super._wide_target()


## Il pavimento dell'arena: dove la tavola lo ha dipinto in prospettiva (il piazzale di A5) si apre
## quello, schiacciato col tilt dal filo del pavimento; ai lati resta quello disegnato, coi colori della
## tavola.
func _draw_floor() -> void:
	super._draw_floor()
	if tilt <= 0.0 or _arena_floor.is_empty():
		return
	var tex: Texture2D = _arena_floor["tex"]
	var h := roundf(tex.get_height() * tilt)
	if h >= 1.0:
		_floor_node.draw_texture_rect(tex, Rect2(_arena_floor["x"], _arena_floor["y"], tex.get_width(), h), false)


## I limiti degli interni e delle Telecamera sulla vista disegnata. Se la vista è più larga del tratto
## sta nel mezzo; in verticale vince il bordo alto (la trave del soffitto). Quando i limiti cambiano
## (si sale sul tetto, si scende in strada) la vista ci arriva piano; allo stacco subito.
func _view_limits(c: Vector2, z: float) -> Vector2:
	var lim := _cam_limits()
	var h := View.SIZE / (2.0 * z)
	var want := c
	var l := lim[0]
	var r := lim[1]
	if is_finite(l) and is_finite(r) and r - l <= 2.0 * h.x:
		want.x = (l + r) / 2.0
	else:
		if is_finite(r):
			want.x = minf(want.x, r - h.x)
		if is_finite(l):
			want.x = maxf(want.x, l + h.x)
	if is_finite(lim[3]):
		want.y = minf(want.y, lim[3] - h.y)
	if is_finite(lim[2]):
		want.y = maxf(want.y, lim[2] + h.y)
	var d := (want - c).round()
	var key := str(lim)
	if _view_snap:
		_view_snap = false
		_blend_t = 0
		_view_push = d
	else:
		if key != _limit_key:
			_blend_t = LIMIT_BLEND
			_blend_from = _view_push
		if _blend_t > 0:
			_blend_t -= 1
			_view_push = _blend_from.lerp(d, _ease(1.0 - float(_blend_t) / LIMIT_BLEND)).round()
		else:
			_view_push = d
	_limit_key = key
	return c + _view_push


## Il nero dello stacco degli interni (a gradini, come la caduta).
func _cut_alpha() -> float:
	if _cut_t <= 0:
		return 0.0
	var k := 1.0 - absf(float(_cut_t) - CUT_TICKS / 2.0) / (CUT_TICKS / 2.0)
	return ceilf(k * 4.0) / 4.0


## Il pavimento del livello: il più basso fra i piedi dei cartelli (0 se non ce ne sono).
func _ground_y() -> int:
	var y := 0
	for id: String in grid.signs:
		if grid.marks.has(id):
			y = maxi(y, grid.marks[id][0].y)
	return y


# ------------------------------------------------------------------ pilota automatico

## La regia del pilota: chiude le vignette, fa il riavvio e la salita nel garage fino al tetto.
## Fuori dal garage guida il pilota della stanza.
var _pilot_seq: int = -1


func pilot_keys(t: int) -> int:
	if finished or switch_t > 0 or outro_t >= 0:
		return 0
	if vignette != "":
		return InputFrame.JUMP if t % 2 == 0 else 0
	if _near_lever() >= 0:
		return InputFrame.UP if t % 2 == 0 else 0
	if not seen_mimmo and _near("M", USE_REACH):
		return InputFrame.UP if t % 2 == 0 else 0
	if not seen_mimmo and grid.marks.has("M") and player.state == PlatformPlayer.State.GROUND and player.px > grid.marks["M"][0].x \
			and checkpoint < 0 and player.px < grid.marks["M"][0].x + 80:
		return InputFrame.LEFT
	if not door_closed:
		return -1
	if not rebooted:
		if reboot_step >= 1:
			return REBOOT_KEYS[reboot_step - 1] if t % 2 == 0 else 0
		var dx: int = grid.marks["X"][0].x - player.px
		if player.state != PlatformPlayer.State.GROUND:
			return -1
		if absi(dx) <= 8:
			return InputFrame.UP if t % 2 == 0 else 0
		return -1 if dx > 0 and dx > 40 else (InputFrame.RIGHT if dx > 0 else InputFrame.LEFT)
	var rk := _pilot_registro(t)
	return rk if rk >= 0 else _pilot_garage()


## Sullo scaffale, con una base ancora da leggere vicina: con la Vista accesa fino alla base, SU, e
## fermo finché la copia finisce. -1 = niente da fare.
func _pilot_registro(t: int) -> int:
	if registri.busy():
		return InputFrame.VISTA
	var p := player
	if p.state != PlatformPlayer.State.GROUND:
		return -1
	for b: Registri.Base in registri.basi:
		if b.read or p.py != b.px.y or absi(b.px.x - p.px) > 160:
			continue
		var dx := b.px.x - p.px
		if absi(dx) <= 10:
			return InputFrame.VISTA | (InputFrame.UP if t % 2 == 0 else 0)
		return InputFrame.VISTA | (InputFrame.RIGHT if dx > 0 else InputFrame.LEFT)
	return -1


## Nel garage dopo il riavvio: sullo scaffale con la Spinta, poi su per il lucernario con la Spinta,
## aggrappato al bordo, e sul tetto verso destra.
var _pilot_boost: bool = false
var _pilot_air_x: int = 0


func _pilot_garage() -> int:
	var T := SolidGrid.TILE
	var p := player
	# Le misure sono quelle del garage di prima, spostate dove sta la porta.
	var o := _door_cells[0] - V1_DOOR if not _door_cells.is_empty() else Vector2i.ZERO
	if p.state == PlatformPlayer.State.LEDGE_HANG or p.state == PlatformPlayer.State.LEDGE_CLIMB:
		return -1
	if p.py <= (9 + o.y) * T and p.state != PlatformPlayer.State.AIR:
		return InputFrame.RIGHT
	if p.state == PlatformPlayer.State.AIR or _pilot_seq >= 0:
		_pilot_seq += 1
		var keys := 0
		# SALTO tenuto; per la Spinta un tick lasciato e poi SALTO di nuovo.
		if _pilot_seq < 18 or (_pilot_boost and _pilot_seq >= 20 and _pilot_seq < 38):
			keys |= InputFrame.JUMP
		if p.state != PlatformPlayer.State.AIR and _pilot_seq > 3:
			_pilot_seq = -1
		# Con la testa nel lucernario: verso destra, al bordo, per aggrapparsi.
		var tx := (400 + o.x) * T if p.py < (15 + o.y) * T else _pilot_air_x
		if absi(tx - p.px) > 6:
			keys |= InputFrame.RIGHT if tx > p.px else InputFrame.LEFT
		return keys
	# Da terra e dallo scaffale si salta sotto il lucernario, con la Spinta.
	var from := (320 + o.x) * T
	_pilot_boost = true
	_pilot_air_x = from
	var d := from - p.px
	if absi(d) > 6:
		return InputFrame.RIGHT if d > 0 else InputFrame.LEFT
	_pilot_seq = 0
	return InputFrame.JUMP


# ------------------------------------------------------------------ disegno

func _draw_stage(v: Node2D) -> void:
	# La lapide di Mimmo e la tastiera sul banco: un segno cyan che pulsa finché servono, e SU
	# quando si è abbastanza vicini.
	if grid.marks.has("X"):
		_draw_keyboard(v, grid.marks["X"][0])
	if vignette == "" and not finished:
		if not seen_mimmo and grid.marks.has("M"):
			_draw_use_spot(v, grid.marks["M"][0], _near("M", USE_REACH))
		if door_closed and not rebooted and reboot_step == 0 and grid.marks.has("X"):
			_draw_use_spot(v, grid.marks["X"][0], _near("X", USE_REACH))
	# I cancelli chiusi, una grata del loro colore, e le leve ancora da tirare.
	for g in _gates2:
		if not g["open"] and not _gate_drawn(g["rect"]):
			_draw_grate(v, g["rect"], C_GATE_ORANGE if g["colore"] == "arancio" else C_SOLID_TOP)
	if vignette == "" and not finished:
		var near := _near_lever()
		for i in _levers.size():
			var lp: Vector2i = _levers[i]["px"]
			var done := String(_levers[i]["iid"]) in pulled
			# Dove la tavola ha il quadro di cantiere, la leva è la sua: niente leva grigia.
			if not _lever_drawn(lp):
				v.draw_rect(Rect2(lp.x - 3, lp.y - 18, 6, 18), C_GATE_DARK)
				v.draw_rect(Rect2(lp.x - (8 if done else -2), lp.y - 26, 6, 10), C_OK if done else C_LED_RED)
			if not done:
				_draw_use_spot(v, lp, near == i)
	# La porta del garage, e gli Esattori che bussano.
	if door_closed and not _door_cells.is_empty():
		var c := _door_cells[0]
		var r := Rect2(c.x * SolidGrid.TILE, c.y * SolidGrid.TILE, 2 * SolidGrid.TILE, _door_cells.size() / 2 * SolidGrid.TILE)
		# La porta grigia, dove la tavola non ha la sua (B3, porta_chiusa).
		if not _gallery_states.has("porta_chiusa"):
			v.draw_rect(r, C_GATE_DARK)
			for k in range(int(r.position.y) + 4, int(r.end.y), 8):
				v.draw_rect(Rect2(r.position.x, k, r.size.x, 1), C_GATE)
		if door_t > 0 and door_t % DOOR_BANG > DOOR_BANG - 14:
			UiFont.draw_text(v, Vector2(r.position.x - 24, r.position.y - 16), "BUM!", C_LED_RED, 1, 1)


## Un cancello chiuso: il fondo scuro e le sbarre verticali del suo colore.
func _draw_grate(v: Node2D, r: Rect2, c: Color) -> void:
	v.draw_rect(r, C_GATE_DARK)
	for k in range(int(r.position.x) + 3, int(r.end.x), 6):
		v.draw_rect(Rect2(k, r.position.y, 2, r.size.y), c)
	v.draw_rect(Rect2(r.position.x, r.position.y, r.size.x, 2), c)
	v.draw_rect(Rect2(r.position.x, r.end.y - 2, r.size.x, 2), c)


## Il segno di un punto dove premere SU: un triangolo cyan che pulsa e ondeggia sopra la testa di
## GIG, con SU sopra quando si è vicini (solo disegno; niente, con --senza-hud).
func _draw_use_spot(v: Node2D, at: Vector2i, near: bool) -> void:
	if Game.options.no_hud:
		return
	var f := Engine.get_physics_frames()
	var bob := roundf(sin(f * 0.12) * 2.0)
	var c := C_CYAN
	c.a = 1.0 if near else 0.55 + 0.45 * absf(sin(f * 0.08))
	var y := at.y - 112.0 + bob
	v.draw_colored_polygon(PackedVector2Array([Vector2(at.x - 6, y), Vector2(at.x + 6, y), Vector2(at.x, y + 7)]), c)
	if near:
		UiFont.draw_text(v, Vector2(at.x, y - 16), "SU", C_CYAN, 1, 1)


## La vecchia tastiera del padre sul banco, accanto al punto del riavvio; dopo, il cavo al braccio.
func _draw_keyboard(v: Node2D, at: Vector2i) -> void:
	var top := at.y - 2 * SolidGrid.TILE
	var r := Rect2(at.x - 62, top - 5, 28, 5)
	v.draw_rect(r, C_KEYBOARD)
	for i in 6:
		v.draw_rect(Rect2(r.position.x + 2 + i * 4, top - 4, 3, 1), C_KEYBOARD_LO)
		v.draw_rect(Rect2(r.position.x + 2 + i * 4, top - 2, 3, 1), C_KEYBOARD_LO)
	if not rebooted and door_closed:
		var f := Engine.get_physics_frames()
		if (f / 20) % 2 == 0:
			v.draw_rect(Rect2(r.end.x - 3, top - 4, 2, 1), C_CYAN)


## Ogni fotogramma, dopo la telecamera e anche durante le scene: il tempo segue quello che si vede.
## Il cielo comincia a chiudersi quando la pioggia si vede (nella scena del pignoramento all'evento
## "pioggia"), e la sua luce tinge gli attori e il pavimento (solo disegno).
func _tick_extras() -> void:
	super._tick_extras()
	if _reboot_light_t > 0:
		_reboot_light_t -= 1
		_update_reboot_light()
	if weather == null:
		return
	if _rain_shown() and not weather.raining:
		weather.set_rain(true)
	elif not raining and weather.raining:
		weather.set_rain(false)
	var vr := _visible_rect()
	var band := Rect2()
	if tilt > 0.0:
		band = Rect2(vr.position.x - 8.0, _floor_y, vr.size.x + 16.0, roundf((ARENA_BAND.y - ARENA_BAND.x) * tilt))
	weather.tick(vr, zoom, band)
	if arena != null and tilt > 0.0 and weather.raining:
		var depth := roundf((View.H - ARENA_BAND.x + 8.0) * tilt)
		_wet.update(Rect2(vr.position.x - 8.0, _floor_y, vr.size.x + 16.0, depth), weather.density() * tilt,
				arena.fighters, arena.position, tick)
	else:
		_wet.update(Rect2(), 0.0, [], Vector2.ZERO, tick)
	var tint := weather.actor_tint()
	_body.modulate = tint
	_floor_node.modulate = weather.ground_tint()
	if arena != null:
		for f in arena.fighters:
			f.body.modulate = tint
	if scene != null:
		for p: ScenePuppet in scene.puppets.values():
			if is_instance_valid(p):
				p.body.modulate = tint
	for p in _extras:
		if is_instance_valid(p):
			p.body.modulate = tint


func _draw_stage_hud(h: Control) -> void:
	if arena_phase == ArenaPhase.NONE:
		# L'ora, sotto il titolo (cronologia: il cimitero dalle 15.15, la fuga e il garage verso le 16).
		var tardi := _cps().find("i")
		var ora := "GIOVEDÌ SANTO · ORE 16.00" if tardi >= 0 and checkpoint >= tardi else "GIOVEDÌ SANTO · ORE 15.15"
		UiFont.draw_text(h, Vector2(View.CX, 2), ora, C_DIM, 1, 1)
	if reboot_step >= 1 and reboot_step <= 3 and vignette == "":
		_draw_reboot_prompt(h)
	if door_t > 0:
		UiFont.draw_text(h, Vector2(View.CX, 20), "GLI ESATTORI SFONDANO LA PORTA: ESCI DAL LUCERNARIO", C_LED_RED, 1, 1)
	_draw_prologue_fades(h)


## Mentre gli Esattori sfondano la porta, la scritta rossa sta sotto l'ora: i fumetti (Tere nel garage)
## scendono sotto di lei invece di coprirla.
func _bubble_top() -> float:
	return maxf(super(), 34.0 / zoom) if door_t > 0 else super()


## Con --senza-hud resta solo questo: il buio della caduta, le vignette, i neri e il cartello finale.
func _draw_stage_fades(h: Control) -> void:
	super(h)
	_draw_prologue_fades(h)


func _draw_prologue_fades(h: Control) -> void:
	if vignette != "":
		_draw_vignette(h)
	# Il nero del passaggio fra i livelli.
	if switch_t > 0:
		var k := 1.0 - absf(float(switch_t) - SWITCH_TICKS / 2.0) / (SWITCH_TICKS / 2.0)
		h.draw_rect(Rect2(0, 0, View.W, View.H), Color(0, 0, 0, clampf(k * 1.4, 0.0, 1.0)))
	# Lo stacco degli interni.
	var cut := _cut_alpha()
	if cut > 0.0:
		h.draw_rect(Rect2(0, 0, View.W, View.H), Color(0, 0, 0, cut))
	# Il cartello dopo il murale del passaggio (compare mentre la scena esce e l'interfaccia torna).
	if finished and (scene == null or not scene.holds_sim()):
		h.draw_rect(Rect2(0, 0, View.W, View.H), Color(0, 0, 0, 0.6))
		UiFont.draw_text(h, Vector2(View.CX, View.H / 2.0 - 16), "FINE DEL PROLOGO", C_CYAN, 2, 1)
		var dopo: PackedStringArray = next_title if not next_title.is_empty() else PackedStringArray(["poi il capitolo 1, I tetti dei Tamburi"])
		for i in dopo.size():
			UiFont.draw_text(h, Vector2(View.CX, View.H / 2.0 + 14 + 12 * i), dopo[i], C_DIM, 1, 1)
		if end_t > END_SKIP and (end_t / 20) % 2 == 0:
			UiFont.draw_text(h, Vector2(View.CX, View.H / 2.0 + 40), "ATTACCO per continuare", C_CYAN, 1, 1)


func _draw_reboot_prompt(h: Control) -> void:
	var y := View.H - 60.0
	h.draw_rect(Rect2(View.CX - 120, y - 6, 240, 40), Color(0, 0, 0, 0.7))
	for i in 3:
		var x := View.CX - 80 + i * 80
		var done := reboot_step - 1 > i
		var now := reboot_step - 1 == i
		h.draw_rect(Rect2(x - 26, y, 52, 16), C_CYAN if done else (C_TEXT if now else C_CASE_LO))
		UiFont.draw_text(h, Vector2(x, y + 3), REBOOT_LABELS[i], C_SCREEN if done or now else C_DIM, 1, 1)
	var hint: String = ["ATTACCO", "SALTO", "SCATTO"][clampi(reboot_step - 1, 0, 2)]
	UiFont.draw_text(h, Vector2(View.CX, y + 21), "premi " + hint, C_DIM, 1, 1)


func _draw_vignette(h: Control) -> void:
	var v: Array = VIGNETTES[vignette]
	var r := Rect2(48, 40, View.W - 96, View.H - 80)
	h.draw_rect(Rect2(0, 0, View.W, View.H), Color(0, 0, 0, 0.5))
	h.draw_rect(r.grow(3), C_INK)
	h.draw_rect(r, C_VIGNETTE)
	UiFont.draw_text(h, Vector2(r.get_center().x, r.position.y + 20), str(v[0]), C_INK, 2, 1)
	UiFont.draw_text(h, Vector2(r.get_center().x, r.get_center().y), str(v[1]), C_DIM, 1, 1)
	if vignette_t >= VIGNETTE_MIN:
		UiFont.draw_text(h, Vector2(r.get_center().x, r.end.y - 16), "SALTO per continuare", C_CYAN, 1, 1)
