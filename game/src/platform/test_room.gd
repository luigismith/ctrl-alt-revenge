class_name TestRoom
extends Node2D
## La stanza di prova in grigio (tappa 1 del piano): niente grafica, solo blocchi, GIG e i
## numeri che servono a tarare il movimento con il pad. Le misure che vanno bene diventano le
## regole per disegnare i livelli.
##
## La simulazione (PlatformPlayer) gira a tick fissi come il resto del gioco; la telecamera e
## le scintille sono solo disegno, quindi possono essere morbide.

signal quit_to_title
## Esce dal gioco a replay finito (--quit-at-end), dopo aver stampato l'hash.
signal replay_done

## Nelle build di debug ogni partita giocata dal vivo si salva qui, un file per sessione: si
## rigioca con --stanza --replay <file>, per vedere i problemi senza doverli spiegare.
const SESSION_DIR := "user://stanza_sessioni"

const MAP := "res://data/platform/stanza_prova.txt"
const MOVES := "res://data/platform/gig_moves.tres"

## Testi dei cartelli, per le lettere minuscole della mappa.
const SIGNS := {
	"a": ["CORRI E SALTA", "tieni SALTO per saltare più in alto"],
	"b": ["FOSSI DA 3, 5, 7 E 9 BLOCCHI", "il 9 si passa solo con la Spinta"],
	"c": ["PIATTAFORME SOTTILI", "si sale da sotto · GIÙ + SALTO per scendere"],
	"d": ["SPORGENZE", "in caduta verso il muro ti aggrappi · SU o SALTO per salire"],
	"e": ["CUNICOLO BASSO", "GIÙ mentre corri: scivolata"],
	"f": ["ARENA", "entra: la telecamera si inclina e arrivano gli Esattori · poi VAI"],
	"h": ["SALTO A MURO", "in caduta spingi contro il muro: il braccio frena · SALTO per staccarti"],
	"i": ["SCATTO", "in aria L, C o un dorsale: 3 blocchi in avanti, uno per salto"],
	"j": ["CORSA SUL MURO", "di corsa contro il muro, SALTO: qualche passo in su"],
	"k": ["HACKING", "tieni SU sotto la centralina, poi corri"],
	"l": ["DUE PANNELLI", "tempi diversi: conta l'ordine"],
	"m": ["POLVERE A RAFFICHE", "sta' in alto, o passa svelto: fa male dopo 1 s"],
	"n": ["MASCHERINA", "20 s senza polvere"],
	"o": ["ABBONAMENTO", "una vita in più, al massimo 3"],
	"g": ["FINE DELLA STANZA", "R o SELECT per ricominciare"],
}

## L'hacking "Collega e corri" (decisione del 5 novembre 2026, in docs/lore/gameplay.md): GIG tiene SU
## sotto una centralina e appoggia il pugno cyber alla presa; dopo HACK_TICKS il cancello del
## pannello si apre per `open` tick, poi si richiude. Il puzzle è il percorso: arrivarci in tempo e,
## con più pannelli, scegliere l'ordine giusto.
const HACK_TICKS := 30
## Distanza orizzontale massima fra GIG e il suo posto sotto la centralina per collegarsi, in px.
## Collegato, GIG fa i passi che mancano (1 px per tick) per avere il pugno sotto la presa.
const HACK_REACH := 14
## Il pugno cyber nella posa dell'hacking, rispetto ai piedi: davanti di 13 px (lo sprite "hack").
const HACK_FIST_X := 13
## Pannello (lettera maiuscola della mappa) → simbolo delle celle del suo cancello e tick di apertura.
## Nella prova dei due pannelli Q, a terra accanto al cancello vicino, apre quello lontano per poco;
## R, sul ballatoio che si incontra prima, apre quello vicino per molto. Chi forza subito Q deve
## tornare indietro fino al ballatoio, e il cancello lontano si richiude: prima R, poi Q, e via.
const PANELS := {
	"P": {"gate": "|", "open": 150},
	"Q": {"gate": ";", "open": 180},
	"R": {"gate": ":", "open": 360},
}
## La centralina sul muro: larga, alta, e col fondo (la presa) all'altezza del pugno alzato.
const PANEL_W := 44
const PANEL_H := 46
const PANEL_BOTTOM := 124
## Tick dell'animazione del cancello che sale o scende (solo disegno).
const GATE_ANIM := 8
const C_GATE := Color8(214, 160, 58)
const C_GATE_DARK := Color8(120, 84, 30)
const C_PANEL := Color8(24, 26, 34)
const C_CASE := Color8(58, 62, 78)
const C_CASE_HI := Color8(108, 114, 134)
const C_CASE_LO := Color8(30, 32, 42)
const C_SCREEN := Color8(8, 20, 26)
const C_HAZARD := Color8(232, 184, 48)
const C_LED_RED := Color8(255, 64, 72)
const C_OK := Color8(110, 230, 120)

const C_BG := Color8(38, 38, 46)
const C_GRID := Color8(46, 46, 56)
const C_SOLID := Color8(92, 92, 106)
const C_SOLID_TOP := Color8(140, 140, 156)
const C_THIN := Color8(120, 120, 136)
## L'acqua delle buche senza fondo, nel grigio.
const C_WATER := Color8(28, 46, 70)
const C_WATER_TOP := Color8(84, 128, 160)
const C_TEXT := Color8(232, 228, 214)
const C_DIM := Color8(160, 156, 150)
const C_CYAN := Color8(64, 232, 255)
## Il verde acqua dove sbiadiscono le scintille del riavvio (bianco, poi cyan, poi verde acqua).
const C_TEAL := Color8(52, 196, 168)
const C_BOX := Color8(255, 80, 80)
const C_FLOOR := Color8(66, 66, 80)
const C_FLOOR_LINE := Color8(84, 84, 100)
const C_KERB := Color8(30, 30, 38)
## Dove c'è la grafica i cartelli sono didascalie a fumetto, con il fondo e il bordo delle vignette.
const C_CAPTION := Color8(18, 16, 24)
const C_CAPTION_INK := Color8(240, 232, 210)
## Da quanti px prima a quanti px dopo il suo segno (rispetto a GIG) si vede una didascalia.
const CAPTION_FROM := -260
const CAPTION_TO := 140

## L'arena della stanza (decisione del 4 novembre 2026, in docs/lore/gameplay.md): quando GIG entra la
## telecamera si blocca e si inclina un po' dall'alto, il pavimento si allarga in profondità e si
## combatte con il sistema dello slice (un Level ospitato, a corsie); a scontro finito compare VAI,
## la telecamera torna laterale e si riprende a saltare.
enum ArenaPhase { NONE, ENTER, FIGHT, LEAVE }

## Le vite (Luigi, 8 novembre 2026: cadere in una fossa costa una vita, e anche il KO nell'arena).
## Solo nei tratti che le accendono con use_lives (il prologo): la stanza di prova riparte e basta.
## La caduta: GIG esce dal fondo per FALL_OUT px, lo schermo si scurisce in FALL_FADE tick e resta
## nero fino a FALL_TICKS; poi riparte dall'ultima ripartenza e lampeggia per RESPAWN_BLINK tick.
const FALL_OUT := 24
const FALL_FADE := 30
const FALL_TICKS := 50
const RESPAWN_BLINK := 60
const RESPAWN_FADE := 15
## Senza vite: CONTINUA? da 9 a 0, una cifra ogni CONTINUE_TICKS; i primi CONTINUE_GRACE tick non
## si risponde (il tasto ancora premuto). Poi GAME OVER per GAME_OVER_TICKS e il titolo.
const CONTINUE_TICKS := 60
const CONTINUE_GRACE := 20
const GAME_OVER_TICKS := 150
## Quanto resta la scritta RIPARTENZA dopo un cartello di ripartenza superato.
const CHECKPOINT_TAG := 90
## La fascia calpestabile dell'arena in coordinate dello schermo, come nello slice: il bordo dietro
## coincide con la linea del pavimento del platform.
const ARENA_BAND := Vector2(188, 260)
## Tick dell'inclinazione all'entrata e all'uscita.
const TILT_IN := 40
const TILT_OUT := 32
## Quanto si schiaccia in verticale la stanza dietro il pavimento, a telecamera inclinata.
const TILT_SQUASH := 0.12
## Quanto GIG scende nella fascia mentre la telecamera si inclina.
const ENTRY_DEPTH := 26.0
## Distanza del punto di fuga delle linee del pavimento, in px sopra la linea del pavimento.
const PERSP := 240.0
## Posizione dell'arena rispetto al suo cartello ("f"): telecamera bloccata e punto d'ingresso.
const ARENA_CAM_FROM_SIGN := -170
const ARENA_TRIGGER_FROM_SIGN := -40
## Nei livelli LDtk l'arena è una zona: la telecamera si ferma sul suo lato sinistro e lo scontro
## parte quando GIG arriva a questa distanza da lì (come col cartello: 170 - 40).
const ARENA_TRIGGER_IN := ARENA_TRIGGER_FROM_SIGN - ARENA_CAM_FROM_SIGN
## Gli Esattori dell'arena (decisione 63): due rider, che arrivano in gruppo, e poi l'esattore di
## professione, che para e carica.
const ARENA_SPAWNS := [
	{"type": "rider", "delay": 30, "side": 1, "y": 205},
	{"type": "rider", "delay": 55, "side": -1, "y": 240},
	{"type": "esattore", "delay": 320, "side": 1, "y": 243},
]

## Il tratto che si gioca: la stanza di prova usa le costanti qui sopra, il prologo (e i livelli
## che verranno) le sue, impostate in _setup_stage().
var map_path: String = MAP
var signs: Dictionary = SIGNS
var panels: Dictionary = PANELS
var arena_spawns: Array = ARENA_SPAWNS
## Nome dell'ondata dell'arena (per i conteggi e i replay) e scritta in alto a sinistra.
var arena_id: String = "arena_prova"
## Le zone tossiche e i power-up dei segni della mappa di testo (quelli LDtk hanno i loro campi).
var hazard_marks: Dictionary = {"~": {"tipo": "polvere"}, "%": {"tipo": "polvere", "ciclo_s": 6.0, "attiva_s": 6.0}}
var powerup_marks: Dictionary = {"1": "mascherina", "2": "abbonamento"}
var hazards := Hazards.new()
## I droni fuori dalle arene (Colomba, Vedetta, Segugio), dalle entità Nemico del livello LDtk.
var drones := Drones.new()
## Persone, oggetti, ristori e battute in gioco.
var favors := Favors.new()
## Le processioni: muri morbidi che avanzano piano e che il faro della Vedetta non tocca.
var processions := Processions.new()
var hud_title: String = "STANZA DI PROVA"
## Le vite contano (le accende il prologo); il numero sta in Game.lives, per tutta la partita.
var use_lives: bool = false
## La caduta in corso: tick dall'uscita dal fondo (-1 = nessuna).
var fall_t: int = -1
## CONTINUA?: tick da quando è comparso (-1 = nascosto) e la cifra che resta.
var continue_t: int = -1
var continue_left: int = -1
## GAME OVER: tick da quando è comparso (-1 = no).
var over_t: int = -1
## Il lampeggio dopo una ripartenza, e la scritta RIPARTENZA (tick che restano).
var respawn_blink: int = 0
var checkpoint_tag: int = 0
## La grafica del tratto (un layers.json, vedi Backdrop): i piani dello sfondo con la parallasse e la
## scena disegnata sui blocchi. Vuota nella stanza di prova, che resta in grigio.
var env_path: String = ""
## Fin dove arriva la grafica, in px del mondo: lì non si disegnano i blocchi grigi né il fondo grigio.
var art_until_x: int = 0
## La grafica di una mappa vecchia su una nuova: quanto scende (in px del mondo) e, se non è 0, fin
## dove si usa (la scena si taglia lì, e da lì in poi la stanza resta in grigio).
var art_offset_y: int = 0
var art_crop_x: int = 0
## I piani della grafica di prima da lasciare fuori (per nome), quando su una mappa nuova non c'entrano.
var art_skip: PackedStringArray = []
## False: della grafica di prima solo i piani, senza le scene (quando le tavole nuove le sostituiscono).
var art_scenes: bool = true
## I tratti disegnati più avanti nella mappa (per esempio le tavole del prologo), in px del mondo:
## lì niente blocchi grigi né righe, e il fondo grigio solo sotto (sopra si vede il cielo).
var art_holes: Array[Rect2] = []
## Da questa x del mondo in poi il fondo grigio non si dipinge (-1: dappertutto): i blocchi grigi
## restano, e dietro si vedono i piani della vestizione (nel prologo, A5 e A6 non ancora vestiti).
var art_open_from: int = -1
## Quanto si schiaccia la stanza a telecamera inclinata. Con la grafica niente: la pixel art schiacciata
## perderebbe righe.
var tilt_squash: float = TILT_SQUASH
var backdrop: Backdrop
## I pezzi della scena disegnata, uno dopo l'altro (il prologo: il cimitero, poi i Tamburi).
var _scene_art: Array[Sprite2D] = []
## Quanto si vede ogni didascalia (0-1): solo disegno, fuori dalla simulazione.
var _caption_alpha: Dictionary = {}
## I colori del pavimento in profondità dell'arena (il prologo ci mette la ghiaia del viale) e, se non
## è trasparente, il colore dei sassolini sparsi.
var floor_colors: Dictionary = {"floor": C_FLOOR, "line": C_FLOOR_LINE, "top": C_SOLID_TOP, "kerb": C_KERB,
	"speck": Color(0, 0, 0, 0)}

var grid: SolidGrid
var player: PlatformPlayer
var input: PlayerInput
var pilot: RoomPilot
var moves: PlatformMoves
var tick: int = 0
var show_boxes: bool = false
## Musica ed effetti sonori (spenti nei test).
var sound: bool = true

var _start: Vector2i = Vector2i(100, 380)
## Tick in cui si è premuto R (ricomincia): fanno parte della sessione registrata.
var _resets: Array = []
var _replay_resets: Array = []
var _record_path: String = ""
var _view: Node2D
var _room_node: Node2D
var _floor_node: Node2D
var _body: Sprite2D
var _hud: Control
var _overlay: LevelOverlay

## L'arena: il Level ospitato esiste solo mentre si combatte.
var arena: Level
var arena_phase: ArenaPhase = ArenaPhase.NONE
var arena_done: bool = false
var _arena_t: int = 0
## Inclinazione della telecamera, da 0 (laterale) a 1 (arena). Solo disegno, ma segue i tick.
var tilt: float = 0.0
var _floor_y: int = 460
var _arena_cam_x: int = -1
var _arena_trigger_x: int = -1
var _cam_from: Vector2 = Vector2.ZERO
var _leave_from_py: float = 0.0
var _cam: Vector2 = Vector2.ZERO
## I cancelli, per simbolo della mappa: {"cells": celle, "rect": Rect2i in pixel, "timer": tick di
## apertura che restano (0 = chiuso), "lift": quanto è alzato nel disegno, da 0 a 1}.
var gates: Dictionary = {}
var _gate_cells: Dictionary = {}
## Il pannello a cui GIG è collegato ("" se nessuno) e da quanti tick.
var hack_panel: String = ""
var hack_t: int = 0
## Quante volte è stato forzato ogni pannello, in questo giro.
var hacks_done: Dictionary = {}
var last_hacked: String = ""
## Scintille della Spinta e degli atterraggi: [x, y, vx, vy, vita, vita iniziale, colore, scarica].
## Le scintille di una scarica (il riavvio) cambiano colore mentre vivono e lasciano la scia. Solo disegno.
var _sparks: Array = []
## Gli aloni additivi degli effetti (Glow): scintille, braccio cyan, contatto. Solo disegno.
var _fx_glow: Glow
## Le luci accese o spente (F5 nelle build di debug, --no-lights): il tempo, l'arena, i lampi.
var lights_on: bool = true
var _spark_rng := RandomNumberGenerator.new()
## L'ultimo tick in cui ha suonato il faro rosso di una Vedetta.
var _faro_t: int = -1000
## Chi suona le voci delle battute in gioco (favors.voices).
var _line_voice: AudioStreamPlayer
const FARO_GAP := 45

## La scena nel motore in corso (decisione 68), o null. La chiede il tratto con request_scene() nel
## tick in cui parte, dopo averne applicato l'esito alla simulazione; parte nello stesso fotogramma.
var scene: ScenePlayer
## Le scene si recitano solo dove c'è chi guarda: i test chiamano _sim_tick() e non le vedono.
var scenes_enabled: bool = true
## Quello che le scene hanno già fatto vedere (per esempio "pioggia"): solo disegno.
var scene_flags: Dictionary = {}
var _scene_request: Dictionary = {}
## Le comparse rimaste nel mondo a scena finita: solo disegno.
var _extras: Array[ScenePuppet] = []
## Lo zoom del disegno (1 nel gioco; durante le scene lo decide il lettore).
var zoom: float = 1.0
## La telecamera larga (normale dall'8 novembre 2026; --camera-stretta la spegne). Il disegno passa alla
## risoluzione della finestra (S pixel dello schermo per pixel del gioco); nel platform la vista si allarga
## a (S-1)/S, cioè un pixel dello schermo in meno per pixel del gioco, così i pixel restano quadrati e
## tutti uguali (a 1440 × 810 si vede 720 × 405, a 1080p 640 × 360). All'arrivo degli Esattori stringe a 1
## mentre l'arena si apre, e si riallarga all'uscita. Sotto i 3 pixel per pixel (finestre più piccole di
## 1440 × 810, come spesso la demo web) resta la vista di sempre, 480 × 270; se la finestra cambia misura
## si passa dall'una all'altra. È solo disegno: `_cam`, la telecamera della logica, e tutto quello che
## decide il gioco restano uguali a ogni misura della finestra.
var wide_cam: bool = false
## La telecamera che si stringe su GIG (solo disegno: `_cam`, quella della logica, non cambia). Da
## quando `squeeze_on` è vero lo zoom va in SQUEEZE_TICKS da quello del gioco a SQUEEZE_ZOOM, e il centro
## passa sopra GIG (SQUEEZE_UP pixel del mondo sopra i piedi), seguendolo morbido. Nel prologo è la corsa
## da sola dell'uscita sul tetto: all'apice del salto l'inquadratura è già quasi quella dell'aggancio a
## MP13.
var squeeze_on: bool = false
var _squeeze_k: float = 0.0
var _squeeze_c: Vector2 = Vector2.ZERO
const SQUEEZE_TICKS := 45
const SQUEEZE_ZOOM := 2.0
const SQUEEZE_UP := 40.0
## Pixel dello schermo per pixel del gioco a zoom 1 (1 senza la prova: il disegno a 480×270).
var _px_s: int = 1
## 0 = stretta, 1 = larga; si muove di 1/WIDE_TICKS a tick, con l'ease.
var _wide_k: float = 1.0
const WIDE_TICKS := 60
## La telecamera larga è accesa (anche quando la finestra è troppo piccola e la vista è quella di
## sempre), e lo stiramento della finestra da rimettere all'uscita.
var _wide_on: bool = false
var _scale_mode_before: Window.ContentScaleMode = Window.CONTENT_SCALE_MODE_VIEWPORT
var _view_c: Vector2 = Vector2.ZERO
var _art_back: Node2D
var _art_front: Node2D
## Altri piani davanti, che seguono lo zoom ma non sfumano col taglio della grafica.
var _art_extra: Array[Node2D] = []
## I piani disegnati allo zoom della vista, come il piano di gioco (i fondi larghi): il nodo ha l'origine
## nell'angolo in alto a sinistra dello schermo, cioè di quello che si vede del mondo, e chi lo riempie
## conta la parallasse da lì (vedi _visible_rect).
var _art_view: Array[Node2D] = []
var _signs_node: Node2D
## Le basi dei registri (vedi Registri), dalle entità Registro della mappa.
var registri := Registri.new()
## La Vista, l'occhio destro di GIG: accesa finché il tasto è tenuto (Luigi, 9 novembre 2026). Non cambia
## la simulazione, solo quello che si vede; entra nell'impronta dove ci sono basi.
var vista: bool = false
## Quanto è accesa sullo schermo, da 0 a 1 (si accende e si spegne in VISTA_FADE tick): solo disegno.
var _vista_k: float = 0.0
const VISTA_FADE := 6
## Il velo della Vista: verde acqua scuro, sopra a tutto il mondo e sotto ai cartelli.
const C_VISTA_VEIL := Color(0.02, 0.20, 0.26, 0.36)
## L'occhio rispetto al punto `head` del fotogramma (verso la faccia, un po' sopra).
const VISTA_EYE := Vector2i(4, -3)


func configure(opts: Dictionary) -> void:
	input = opts.get("input", null)
	pilot = opts.get("pilot", null)
	_record_path = str(opts.get("record", ""))
	sound = bool(opts.get("sound", true))
	if input != null and input.mode == PlayerInput.Mode.REPLAY:
		_replay_resets = input.replay.start.get("resets", [])


func _ready() -> void:
	if input == null:
		input = PlayerInput.live()
	_setup_stage()
	moves = load(MOVES) as PlatformMoves
	if moves == null:
		moves = PlatformMoves.new()
	_load_map()
	if Game.options.start_x >= 0.0:
		_start.x = roundi(Game.options.start_x)
		if Game.options.start_y >= 0.0:
			_start.y = roundi(Game.options.start_y)
	_spark_rng.seed = 7
	# La musica del livello, se il laboratorio ha i brani (non tocca la simulazione).
	if sound:
		Music.duck(false)
		Music.play(&"stage1")
	_view = Node2D.new()
	_view.draw.connect(_draw_back)
	add_child(_view)
	_room_node = Node2D.new()
	_room_node.draw.connect(_draw_room)
	_view.add_child(_room_node)
	_floor_node = Node2D.new()
	_floor_node.z_index = 1
	_floor_node.draw.connect(_draw_floor)
	_view.add_child(_floor_node)
	_build_art()
	# Le firme di Totò sul muro: sopra la grafica del livello, dietro a GIG.
	var tags := Node2D.new()
	tags.draw.connect(func() -> void:
		if arena == null:
			favors.draw_tags(tags, tick, _visible_rect()))
	_view.add_child(tags)
	# Le basi dei registri: oggetti del mondo, dietro a GIG.
	var reg := Node2D.new()
	reg.draw.connect(func() -> void:
		if arena == null:
			registri.draw_bodies(reg, _visible_rect()))
	_view.add_child(reg)
	var sheet := SpriteSheet.get_sheet(&"gig")
	player = PlatformPlayer.new(moves, grid, sheet)
	# prima del riavvio (prologo) GIG ha il braccio morto: luci spente e il braccio che pende
	player.sheet_locked = SpriteSheet.get_sheet(&"gig_spento")
	if pilot != null:
		pilot.player = player
		pilot.room = self
	_body = Sprite2D.new()
	_body.centered = false
	_body.region_enabled = true
	_body.texture = sheet.texture
	# Come i combattenti: lo shader con la luce a gradini, e le luci degli attori (il sole e il cielo
	# del tempo, i lampi) solo se il foglio ha la normal map.
	var mat := ShaderMaterial.new()
	mat.shader = Fighter._get_flash_shader()
	_body.material = mat
	_body.light_mask = Fighter.LIGHT_MASK_ACTORS if sheet.has_normals else 1
	_view.add_child(_body)
	# I perdoni, le Persone e i droni con lo sprite vero (Segugio, Vedetta), sotto gli effetti: come GIG, con la normal map e la
	# luce a gradini. Coni, aloni e scritte restano nel nodo degli effetti.
	var drone_bodies := Node2D.new()
	drone_bodies.z_index = 5
	var dmat := ShaderMaterial.new()
	dmat.shader = Fighter._get_flash_shader()
	drone_bodies.material = dmat
	drone_bodies.light_mask = Fighter.LIGHT_MASK_ACTORS
	drone_bodies.draw.connect(func() -> void:
		if arena == null:
			processions.draw_bodies(drone_bodies, tick, _visible_rect())
			favors.draw_bodies(drone_bodies, tick, _visible_rect(), player)
			drones.draw_bodies(drone_bodies, tick, _visible_rect()))
	_view.add_child(drone_bodies)
	var fx := Node2D.new()
	fx.z_index = 5
	fx.draw.connect(func() -> void: _draw_fx(fx))
	_view.add_child(fx)
	_fx_glow = Glow.new(fx)
	lights_on = not Game.options.no_lights
	if Game.options.wide_camera:
		_setup_wide_cam()
	# La Vista: il velo sopra a tutto il mondo e al primo piano (z 1000), e sopra al velo quello che
	# rivela (il contorno e le onde delle basi, anche dietro i muri finti) e l'occhio di GIG; la copia
	# di un registro e la sua scritta si vedono anche senza.
	var veil := Node2D.new()
	veil.z_index = 1050
	veil.draw.connect(func() -> void: _draw_vista_veil(veil))
	_view.add_child(veil)
	var revealed := Node2D.new()
	revealed.z_index = 1060
	revealed.draw.connect(func() -> void:
		if arena == null:
			registri.draw_overlay(revealed, _visible_rect(), _vista_k, tick, _cyber_fist())
			_draw_vista_eye(revealed))
	_view.add_child(revealed)
	# I cartelli sopra tutto il mondo, anche sopra il primo piano della grafica (z 1000).
	var signs_node := Node2D.new()
	signs_node.z_index = 1100
	signs_node.draw.connect(func() -> void: _draw_signs(signs_node))
	_view.add_child(signs_node)
	_signs_node = signs_node
	var layer := CanvasLayer.new()
	layer.layer = 10
	add_child(layer)
	_hud = Control.new()
	_hud.size = View.SIZE
	_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hud.draw.connect(_draw_hud)
	layer.add_child(_hud)
	_overlay = LevelOverlay.new()
	layer.add_child(_overlay)
	show_boxes = Game.options.debug_boxes
	if input.mode == PlayerInput.Mode.REPLAY and input.replay.start.has("x"):
		_start.x = int(input.replay.start["x"])
	if _record_path != "":
		input.recorder = Replay.new()
		input.recorder.note = "Stanza di prova, sessione dal vivo"
	_reset()
	# --skip-to <tick>: un replay corre senza disegnare fino a quel tick (per guardare un momento).
	if input.mode == PlayerInput.Mode.REPLAY and Game.options.skip_to > 0:
		while tick < Game.options.skip_to and not input.replay_finished(tick):
			_sim_tick()
		_cam = _cam_target()
	_update_art()


## Legge la mappa di `map_path`: la griglia, i cartelli, la partenza, l'arena e i cancelli. La chiama
## _ready, e il prologo quando passa da un livello all'altro dello stesso file (poi tocca a lui
## rimettere GIG sulla griglia nuova).
func _load_map() -> void:
	grid = SolidGrid.load_file(map_path)
	if not grid.signs.is_empty():
		signs = grid.signs  # i testi dei cartelli stanno nel livello LDtk
	if grid.marks.has("G"):
		_start = grid.marks["G"][0]
	_floor_y = 460
	_arena_cam_x = -1
	_arena_trigger_x = -1
	if not grid.arenas.is_empty():
		var r: Rect2i = grid.arenas[0]["rect"]
		_floor_y = r.end.y
		_arena_cam_x = clampi(r.position.x, 0, grid.pixel_width() - View.W)
		_arena_trigger_x = r.position.x + ARENA_TRIGGER_IN
	elif grid.marks.has("f"):
		var f: Vector2i = grid.marks["f"][0]
		_floor_y = f.y
		_arena_cam_x = clampi(f.x + ARENA_CAM_FROM_SIGN, 0, grid.pixel_width() - View.W)
		_arena_trigger_x = f.x + ARENA_TRIGGER_FROM_SIGN
	if player != null:
		player.grid = grid
	_build_gates()
	hazards.build(grid, hazard_marks, powerup_marks)
	drones.build(grid)
	if not Game.options.solo_drones.is_empty():
		for i in range(drones.drones.size() - 1, -1, -1):
			if drones.drones[i].tipo not in Game.options.solo_drones:
				drones.drones.remove_at(i)
	favors.build(grid)
	processions.build(grid)
	registri.setup(grid.entities)


## Da ridefinire nei tratti che non sono la stanza di prova: mappa, cartelli, pannelli, arena.
func _setup_stage() -> void:
	pass


## La grafica del tratto, se c'è: i piani dello sfondo in un nodo prima del mondo, la scena dentro la
## stanza (dietro a quello che la stanza disegna, come i segni di SU e la pioggia).
func _build_art() -> void:
	if env_path == "" or not FileAccess.file_exists(env_path):
		return
	var bd := Backdrop.new()
	if not bd.load_json(env_path):
		push_warning("Grafica del tratto non valida (%s): resta il grigio" % "; ".join(bd.errors))
		return
	if not art_skip.is_empty():
		bd.layers.assign(bd.layers.filter(func(l: Backdrop.Layer) -> bool: return not art_skip.has(l.name)))
	backdrop = bd
	art_until_x = bd.level_width if art_crop_x <= 0 else mini(art_crop_x, bd.level_width)
	tilt_squash = 0.0
	var back := Node2D.new()
	back.name = "Sfondo"
	add_child(back)
	move_child(back, 0)
	var front := Node2D.new()
	front.name = "PrimoPiano"
	add_child(front)
	_art_back = back
	_art_front = front
	bd.build(back, front, 1)
	for sc: Dictionary in (bd.scenes if art_scenes else []):
		var tex := SpriteSheet.load_texture(bd.dir.path_join(str(sc["image"])))
		if tex == null:
			push_warning("Scena mancante: %s" % sc["image"])
			continue
		var sx := int(sc.get("x", 0))
		if art_crop_x > 0 and sx >= art_until_x:
			continue
		var s := Sprite2D.new()
		s.name = "Scena_%d" % _scene_art.size()
		s.centered = false
		s.texture = tex
		s.position = Vector2(sx, int(sc.get("y", 0)) + art_offset_y)
		if art_crop_x > 0 and sx + tex.get_width() > art_until_x:
			s.region_enabled = true
			s.region_rect = Rect2(0, 0, art_until_x - sx, tex.get_height())
		s.show_behind_parent = true
		_room_node.add_child(s)
		_scene_art.append(s)


## I piani dello sfondo seguono la telecamera (posizioni intere, come il mondo).
func _update_art() -> void:
	if backdrop == null:
		return
	var c := (_view_c - View.SIZE / 2.0).round()
	backdrop.update(int(c.x), tick, c.y - backdrop.cam_ref_y - art_offset_y)
	# Con la grafica tagliata il primo piano (più veloce della stanza) sfuma mentre il taglio entra
	# nello schermo.
	if art_crop_x > 0 and _art_front != null:
		_art_front.modulate.a = clampf((art_until_x + 40 - _vis_x1()) / 80.0, 0.0, 1.0)


## Il tick del tratto, prima di GIG: può cambiare l'ingresso (per esempio vuoto durante una vignetta).
func _stage_tick(frame: InputFrame) -> InputFrame:
	return frame


## Il tick del tratto, dopo GIG.
func _stage_after_step() -> void:
	pass


## I tasti del pilota automatico per i momenti con una regia (vignette, riavvio...); -1 = decide lui.
func pilot_keys(_t: int) -> int:
	return -1


## Lo stato del tratto per l'impronta dei test.
func _stage_hash() -> Array:
	return []


## Il braccio è vivo: la Vista si accende e le basi dei registri si copiano. Il prologo lo vuole dopo il
## riavvio.
func _arm_alive() -> bool:
	return true


## Disegno del tratto: nel mondo (sopra i blocchi) e sull'interfaccia.
func _draw_stage(_v: Node2D) -> void:
	pass


func _draw_stage_hud(_h: Control) -> void:
	pass


func _reset() -> void:
	_close_arena()
	_clear_extras()
	arena_done = false
	_reset_hacking()
	_reset_hazards()
	player.place(_start.x, _start.y)
	player.facing = 1
	_sparks.clear()
	_cam = _cam_target()


func _physics_process(_delta: float) -> void:
	# Durante una scena la simulazione è ferma: recita il lettore (START la salta).
	if scene != null and scene.holds_sim():
		_scene_frame()
		return
	if input.mode == PlayerInput.Mode.LIVE:
		if Input.is_action_just_pressed(&"pause"):
			quit_to_title.emit()
			return
		if Input.is_action_just_pressed(&"room_reset"):
			_resets.append(tick)
			_reset()
		if Input.is_action_just_pressed(&"debug_boxes"):
			show_boxes = not show_boxes
		if OS.is_debug_build() and Input.is_action_just_pressed(&"debug_lights"):
			lights_on = not lights_on
			_set_lights(lights_on)
	if input.mode == PlayerInput.Mode.REPLAY and input.replay_finished(tick):
		replay_done.emit()
		return
	_sim_tick()
	# Una scena chiesta in questo tick parte subito, nello stesso fotogramma: niente salti.
	if not _scene_request.is_empty():
		_start_scene()
		if scene != null and scene.holds_sim():
			_scene_frame()
			return
	_tick_sparks()
	_follow_camera()
	if scene != null:
		# L'uscita della scena: il gioco è già ripartito, la telecamera torna morbida a quella del gioco.
		scene.tick()
	_update_art()
	_sync_visual()
	_overlay.tick()
	_tick_extras()
	_redraw_all()


func _redraw_all() -> void:
	_view.queue_redraw()
	_hud.queue_redraw()
	for c in _view.get_children():
		if c is Node2D and c != _body and not (c is ScenePuppet):
			(c as Node2D).queue_redraw()


## Un tick della simulazione: ingressi, GIG, eventi. Il disegno resta fuori.
func _sim_tick() -> void:
	_scene_request = {}
	if input.mode == PlayerInput.Mode.REPLAY and (_replay_resets.has(float(tick)) or _replay_resets.has(tick)):
		_reset()
	var frame := input.next_frame(tick)
	tick += 1
	if respawn_blink > 0:
		respawn_blink -= 1
	if checkpoint_tag > 0:
		checkpoint_tag -= 1
	if use_lives and _lives_tick(frame):
		return
	if arena_phase != ArenaPhase.NONE:
		_arena_tick(frame)
		return
	frame = _stage_tick(frame)
	vista = frame.is_held(InputFrame.VISTA) and _arm_alive()
	# La copia di un registro: GIG si china col polso nella culla, fermo finché finisce.
	if not registri.is_empty():
		if registri.step(frame, player, _arm_alive()):
			frame = InputFrame.new()
		for e in registri.events:
			_on_event(e)
	var hack_events := PackedStringArray()
	frame = _hack_tick(frame, hack_events)
	# Collegato al pannello, GIG alza il braccio cyber verso la cassetta.
	player.pose_override = &"hack" if hack_panel != "" else &""
	if registri.busy():
		player.pose_override = &"crouch"
	player.step(frame)
	for e in player.events:
		_on_event(e)
	for e in hack_events:
		_on_event(e)
	_stage_after_step()
	if not processions.is_empty():
		processions.step(player, frame.was_pressed(InputFrame.DASH))
		drones.shields = processions.shields()
		for e: Array in processions.events:
			var s: Array = PROC_SFX.get(String(e[0]), [])
			if not s.is_empty():
				Sfx.play_at(s[0], e[1], 0.05, s[1])
		if processions.pushed:
			drones.alert_pending = true
	if not hazards.is_empty() and _hazards_tick():
		return
	if not drones.is_empty() and _drones_tick():
		return
	if not favors.is_empty():
		_favors_tick(frame)
	if use_lives and player.py > grid.pixel_height() + FALL_OUT:
		_start_fall()
	elif player.py > grid.pixel_height() + 80:
		_reset()
	elif _arena_starts():
		_open_arena()


# ------------------------------------------------------------------ zone tossiche e power-up

## Alla ripartenza: energia piena, power-up perso, corsa e caduta normali.
func _reset_hazards() -> void:
	hazards.reset()
	drones.reset()
	favors.reset()
	if _line_voice != null:
		_line_voice.stop()
	processions.reset()
	drones.shields = processions.shields()
	registri.reset()
	vista = false
	player.jab_block = false
	Game.energy = Game.ENERGY_MAX
	player.glide_fall = 0.0
	player.speed_pct = 100
	player.boost_pct = 100
	# Il colpo solo c'è dove ci sono droni: altrove ATTACCO resta libero.
	player.can_jab = not drones.is_empty()


## Zone e power-up, dopo il passo di GIG: true se GIG è rimasto senza energia (la simulazione si ferma).
func _hazards_tick() -> bool:
	var dmg := hazards.step(tick, player, Game.energy)
	for e in hazards.events:
		_on_event(e)
	return dmg > 0 and hurt(dmg)


## Persone, oggetti e ristori, dopo il passo di GIG e dei droni (che possono servire a una Persona).
func _favors_tick(frame: InputFrame) -> void:
	favors.arena_done = arena_done
	Game.energy = favors.step(player, frame.was_pressed(InputFrame.UP), drones, Game.energy)
	for e: Array in favors.events:
		if e[0] == "scarica":
			Game.scarica = Game.SCARICA_MAX
		elif e[0] == "firma":
			Game.add_score(Favors.FIRMA_POINTS)
			Game.stats[&"firme"] = Game.stats.get(&"firme", 0) + 1
			# Schegge di vernice: rosa e arancio, come la tag.
			for i in 10:
				var a := TAU * i / 10.0 + _spark_rng.randf_range(-0.2, 0.2)
				var sp := _spark_rng.randf_range(0.8, 1.8)
				_spark(e[1], e[2], cos(a) * sp, sin(a) * sp - 0.6, _spark_rng.randi_range(12, 22),
					C_TAG_PINK if i % 2 == 0 else C_TAG_ORANGE)
		var s: Array = FAVOR_SFX.get(String(e[0]), [])
		if not s.is_empty():
			Sfx.play_at(s[0], e[1], 0.05, s[1])
	for v: AudioStream in favors.voices:
		_play_line_voice(v)
	if favors.changed:
		_on_favor_opened()


## La voce di una battuta in gioco: una alla volta, la nuova ferma quella prima.
func _play_line_voice(v: AudioStream) -> void:
	if _line_voice == null:
		_line_voice = AudioStreamPlayer.new()
		_line_voice.bus = Sfx.BUS
		add_child(_line_voice)
	_line_voice.stream = v
	_line_voice.play()


## Una battuta in gioco detta da fuori dai favori (Tere alla base del registro): il fumetto, se i favori
## girano in questo tratto, e la voce.
func _say_in_game(id: String, tag: String) -> void:
	var before := favors.voices.size()
	favors._say(id, Vector2.ZERO, true, tag)
	if favors.is_empty():
		# Senza favori nessuno farebbe scorrere il fumetto: resta solo la voce.
		favors.bubbles.clear()
	for i in range(before, favors.voices.size()):
		_play_line_voice(favors.voices[i])
	favors.voices.resize(before)


## Una Persona ha aperto i suoi premi: chi ha i cancelli li riapplica (il prologo).
func _on_favor_opened() -> void:
	pass


## I suoni dei favori (segnaposto, dagli effetti che ci sono).
const FAVOR_SFX := {
	"ristoro": [&"ui_confirm", -2.0], "preso": [&"grab", -2.0], "posato": [&"ui_confirm", -4.0],
	"chiede": [&"ui_move", -6.0], "grazie": [&"glint", -2.0], "battuta": [&"ui_move", -8.0],
	"firma": [&"glint", 0.0],
}
## I colori delle schegge delle firme (dallo sprite della tag).
const C_TAG_PINK := Color8(244, 110, 160)
const C_TAG_ORANGE := Color8(250, 160, 50)


## I droni, dopo il passo di GIG: true se GIG è rimasto senza energia. Le spinte, i rimbalzi e i
## sigilli li dà il drone a GIG, che ne scrive gli eventi: si suonano qui.
func _drones_tick() -> bool:
	var n := player.events.size()
	var dmg := drones.step(player)
	for i in range(n, player.events.size()):
		_on_event(player.events[i])
	for e: Array in drones.events:
		_on_drone_event(e)
	return dmg > 0 and hurt(dmg)


## Gli eventi dei droni hanno il punto dove succedono: lì il suono e le scintille.
func _on_drone_event(e: Array) -> void:
	var name: String = e[0]
	# Il faro che si accende e si spegne sul bordo della luce suona una volta sola ogni tanto.
	if name == "faro_rosso":
		if tick - _faro_t < FARO_GAP:
			return
		_faro_t = tick
	var x: float = e[1]
	var y: float = e[2]
	if sound and DRONE_SFX.has(name):
		var s: Array = DRONE_SFX[name]
		Sfx.play_at(s[0], x, 0.05, s[1])
	match name:
		"drone_rotto":
			for i in 16:
				var a := _spark_rng.randf_range(0.0, TAU)
				var sp := _spark_rng.randf_range(1.0, 3.0)
				_spark(x, y, cos(a) * sp, sin(a) * sp - 1.0, _spark_rng.randi_range(10, 22), C_LED_RED if i % 3 == 0 else C_TEXT)
		"corazza", "sigillo_muro":
			for i in 5:
				_spark(x, y, _spark_rng.randf_range(-1.5, 1.5), -_spark_rng.randf_range(0.5, 1.5), 8, C_DIM)
		"pignorato", "morso":
			for i in 8:
				var a := _spark_rng.randf_range(0.0, TAU)
				_spark(x, y, cos(a) * 2.0, sin(a) * 2.0, 12, C_LED_RED)


## GIG perde energia: a zero, con le vite si perde una vita (decisione B di Luigi, 8 novembre 2026);
## nella stanza si ricomincia. True se è finita così.
func hurt(dmg: int) -> bool:
	Game.energy = maxi(Game.energy - dmg, 0)
	if Game.energy > 0:
		return false
	_on_event("ko_energia")
	if use_lives:
		fall_t = 0
		Game.lose_life()
		Game.count(&"ko_energia")
	else:
		_reset()
	return true


## La barra dell'energia sull'HUD, da `x`: restituisce dove finisce.
func _draw_energy(h: Control, x: float) -> float:
	var w := 60.0
	var f := roundf(w * float(mini(Game.energy, Game.ENERGY_MAX)) / Game.ENERGY_MAX)
	h.draw_rect(Rect2(x - 1, 4, w + 2, 7), Color(0, 0, 0, 0.7))
	var c := C_OK if Game.energy > Game.ENERGY_MAX / 3 else (C_HAZARD if Game.energy > Game.ENERGY_MAX / 6 else C_LED_RED)
	h.draw_rect(Rect2(x, 5, f, 5), c)
	h.draw_rect(Rect2(x, 5, f, 1), c.lightened(0.35))
	# Oltre il massimo (la scarcella): una seconda fascia chiara sopra la barra piena.
	if Game.energy > Game.ENERGY_MAX:
		h.draw_rect(Rect2(x, 5, roundf(w * float(Game.energy - Game.ENERGY_MAX) / Game.ENERGY_MAX), 2), C_TEXT)
	return x + w


# ------------------------------------------------------------------ vite

## La parte del tick che riguarda le vite: true se la simulazione resta ferma (caduta, CONTINUA?,
## GAME OVER). A CONTINUA? si risponde coi tasti del fotogramma registrato, così i replay tornano.
func _lives_tick(frame: InputFrame) -> bool:
	# Sotto CONTINUA? e ABBONAMENTO SCADUTO, fuori dall'arena, GIG sta fermo alla ripartenza (senza
	# questo passo resterebbe disegnato nella posa della caduta).
	if (over_t >= 0 or continue_t >= 0) and arena == null:
		player.step(InputFrame.new())
	if over_t >= 0:
		over_t += 1
		if over_t == GAME_OVER_TICKS:
			quit_to_title.emit()
		return true
	if continue_t >= 0:
		continue_t += 1
		if continue_t > CONTINUE_GRACE and (frame.was_pressed(InputFrame.ATTACK) or frame.was_pressed(InputFrame.JUMP)):
			_continue_run()
		elif continue_t % CONTINUE_TICKS == 0:
			continue_left -= 1
			if continue_left < 0:
				continue_t = -1
				over_t = 0
				if _overlay != null:
					_overlay.game_over_ticks = 0
				if sound:
					Music.stop(1.0)
			if _overlay != null:
				_overlay.continue_count = continue_left
		return true
	if fall_t >= 0:
		fall_t += 1
		# GIG continua a cadere, fuori dallo schermo, mentre si fa buio.
		player.step(InputFrame.new())
		if fall_t >= FALL_TICKS:
			fall_t = -1
			_reset()
			respawn_blink = RESPAWN_BLINK
			if Game.lives <= 0:
				_open_continue()
		return true
	if arena != null and arena.wants_continue:
		_open_continue()
		return true
	return false


func _start_fall() -> void:
	fall_t = 0
	Game.lose_life()
	Game.count(&"cadute")
	if sound:
		Sfx.play_at(&"body_fall", player.px)


func _open_continue() -> void:
	continue_t = 0
	continue_left = 9
	if _overlay != null:
		_overlay.continue_count = continue_left
	if sound:
		Music.duck(true)


func _continue_run() -> void:
	continue_t = -1
	continue_left = -1
	if _overlay != null:
		_overlay.continue_count = -1
	Game.continue_run()
	if arena != null and arena.wants_continue:
		# Nell'arena GIG rientra dall'alto, come nello slice.
		arena.wants_continue = false
		arena.player.respawn()
	else:
		respawn_blink = RESPAWN_BLINK
	if sound:
		Sfx.play_at(&"ui_confirm", player.px)
		Music.duck(false)


## Superata una ripartenza (la chiama il tratto): la spia si accende e compare RIPARTENZA.
func _on_checkpoint() -> void:
	checkpoint_tag = CHECKPOINT_TAG
	if sound:
		Sfx.play_at(&"ui_confirm", player.px)


## Da ridefinire nei tratti con le ripartenze: [posizione dei piedi, accesa] per ogni spia.
func _checkpoint_lamps() -> Array:
	return []


## Le spie delle ripartenze, a terra dove GIG riparte: spente in grigio, accese in cyan col bagliore.
func _draw_checkpoint_lamps(n: Node2D) -> void:
	for l: Array in _checkpoint_lamps():
		var at := Vector2(l[0])
		if at.x < _vis_x0() - 40 or at.x > _vis_x1() + 40:
			continue
		var lit: bool = l[1]
		var dark := Color8(40, 44, 52)
		n.draw_rect(Rect2(at + Vector2(-1, -11), Vector2(3, 11)), dark)
		n.draw_rect(Rect2(at + Vector2(-3, -1), Vector2(7, 1)), dark)
		var top := at + Vector2(-2, -15)
		n.draw_rect(Rect2(top, Vector2(5, 4)), C_CYAN if lit else Color8(84, 88, 96))
		if lit:
			n.draw_rect(Rect2(top + Vector2(1, 1), Vector2(3, 2)), C_TEXT)
			var pulse := 1.0 + 0.6 * float(checkpoint_tag) / CHECKPOINT_TAG
			_fx_glow.halo(top + Vector2(2, 2), roundi(6.0 * pulse), Color(C_CYAN, 0.45))


func _draw_lives_hud(h: Control) -> void:
	# Il buio della caduta, a gradini come le altre dissolvenze, e la luce che torna alla ripartenza.
	var dark := 0.0
	if fall_t >= 0:
		dark = clampf(float(fall_t) / FALL_FADE, 0.0, 1.0)
	elif respawn_blink > RESPAWN_BLINK - RESPAWN_FADE:
		dark = float(respawn_blink - (RESPAWN_BLINK - RESPAWN_FADE)) / RESPAWN_FADE
	if dark > 0.0:
		h.draw_rect(Rect2(Vector2.ZERO, View.SIZE), Color(0, 0, 0, ceilf(dark * 4.0) / 4.0))
	if checkpoint_tag > CHECKPOINT_TAG - 30 or (checkpoint_tag > 0 and (checkpoint_tag / 10) % 2 == 0):
		UiFont.draw_text(h, Vector2(View.CX, 18), "RIPARTENZA", C_CYAN, 1, 1)


func _exit_tree() -> void:
	_save_recording()
	_drop_wide_cam()


func _save_recording() -> void:
	if input == null or input.recorder == null or _record_path == "" or input.recorder.length == 0:
		return
	input.recorder.start = {"x": _start.x, "resets": _resets}
	DirAccess.make_dir_recursive_absolute(_record_path.get_base_dir())
	if input.recorder.save_file(_record_path) == OK:
		print("Sessione salvata: %s (%d tick)" % [ProjectSettings.globalize_path(_record_path), input.recorder.length])
	input.recorder = null


# ------------------------------------------------------------------ telecamera

## I tick che restano del tremito della vista (solo grafica, fuori dall'impronta).
var _shake_t: int = 0
const SHAKE_TICKS := 8


func _cam_target() -> Vector2:
	# Un po' avanti nella direzione dello sguardo, con GIG nel terzo basso dello schermo.
	return Vector2(player.px + player.facing * 45 - View.CX, player.py - 188)


## La telecamera larga: il disegno alla risoluzione della finestra, a multipli interi, finché la finestra
## ne regge almeno 3; segue i cambi di misura della finestra.
func _setup_wide_cam() -> void:
	# Senza schermo (i test, i replay) niente: la logica non cambia e il disegno resta quello di sempre.
	if DisplayServer.get_name() == "headless":
		return
	var win := get_tree().root
	_scale_mode_before = win.content_scale_mode
	_wide_on = true
	if not win.size_changed.is_connected(_fit_wide_cam):
		win.size_changed.connect(_fit_wide_cam)
	_fit_wide_cam()


## Larga o stretta secondo la finestra adesso: sotto i 3 pixel per pixel la vista larga non avrebbe pixel
## interi abbastanza fitti, e resta quella di sempre.
func _fit_wide_cam() -> void:
	if not _wide_on or not is_inside_tree():
		return
	var win := get_tree().root
	var s := maxi(1, mini(win.size.x / View.W, win.size.y / View.H))
	wide_cam = s >= 3
	_px_s = s if wide_cam else 1
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS if wide_cam else _scale_mode_before


## All'uscita dalla stanza (verso le scene, il titolo, lo slice) il disegno torna come l'ha trovato.
func _drop_wide_cam() -> void:
	if not _wide_on:
		return
	_wide_on = false
	var win := get_tree().root
	if win.size_changed.is_connected(_fit_wide_cam):
		win.size_changed.disconnect(_fit_wide_cam)
	win.content_scale_mode = _scale_mode_before
	wide_cam = false
	_px_s = 1


## Lo zoom del gioco adesso: 1, o con la prova fra 1 e (S-1)/S.
func _game_zoom() -> float:
	if not wide_cam:
		return 1.0
	var wide := float(_px_s - 1) / _px_s
	return lerpf(1.0, wide, _ease(_wide_k))


## Un tick della prova: larga nel platform e quando GIG esce dall'arena, stretta quando arrivano gli
## Esattori.
func _wide_tick() -> void:
	if wide_cam:
		var target := 1.0 if arena_phase in [ArenaPhase.NONE, ArenaPhase.LEAVE] else 0.0
		_wide_k = move_toward(_wide_k, target, 1.0 / WIDE_TICKS)


## Il centro della vista del gioco: quello della telecamera, tenuto dentro la stanza se la vista è larga.
func _game_view_center(z: float) -> Vector2:
	var c := _cam.round() + View.SIZE / 2.0
	if z >= 1.0:
		return c
	var h := (View.SIZE / (2.0 * z)).round()
	c.x = clampf(c.x, h.x, maxf(h.x, float(grid.pixel_width()) - h.x))
	c.y = minf(c.y, float(grid.pixel_height()) - h.y)
	return c


func _follow_camera() -> void:
	_wide_tick()
	if arena_phase != ArenaPhase.NONE:
		_arena_camera()
		return
	var t := _cam_target()
	_cam.x += (t.x - _cam.x) * 0.12
	# In verticale segue piano mentre GIG salta, deciso quando atterra o cade a lungo.
	var k := 0.18 if player.state != PlatformPlayer.State.AIR or player.vy > PlatformPlayer.to_sub(5.0) else 0.04
	_cam.y += (t.y - _cam.y) * k
	_cam.x = clampf(_cam.x, 0.0, float(grid.pixel_width() - View.W))
	_cam.y = clampf(_cam.y, float(-80), float(grid.pixel_height() - View.H))
	# Il colpo di un Rompibile: la vista trema pochi tick, di lato (solo grafica).
	var shake := Vector2.ZERO
	if _shake_t > 0:
		shake.x = (1 - 2 * (_shake_t % 2)) * ceilf(2.0 * _shake_t / SHAKE_TICKS)
		_shake_t -= 1
	var z := _game_zoom()
	var c := _game_view_center(z)
	if squeeze_on or _squeeze_k > 0.0:
		var feet := Vector2(player.px, player.py - SQUEEZE_UP)
		_squeeze_c = feet if _squeeze_k == 0.0 else _squeeze_c.lerp(feet, 0.5)
		_squeeze_k = move_toward(_squeeze_k, 1.0 if squeeze_on else 0.0, 1.0 / SQUEEZE_TICKS)
		var e := _ease(_squeeze_k)
		var zs := exp(lerpf(log(z), log(SQUEEZE_ZOOM), e))
		c = c.lerp(_squeeze_c, e)
		c.y = minf(c.y, float(grid.pixel_height()) - View.H / (2.0 * zs))
		z = zs
	_place_view(c, z, shake)


## Mette la vista: il punto `center` del mondo al centro dello schermo, ingrandito `z` volte intorno al
## centro (lo zoom delle scene). A zoom 1 è la telecamera di sempre, a posizioni intere; i piani dello
## sfondo si ingrandiscono allo stesso modo. Con zoom intero i pixel restano quadrati e netti.
func _place_view(center: Vector2, z: float, shake: Vector2 = Vector2.ZERO) -> void:
	zoom = z
	_view_c = center
	var half := View.SIZE / 2.0
	# Posizioni a pixel interi dello schermo (con la prova della telecamera larga, più fitti di quelli
	# del gioco).
	var s := float(_px_s)
	_view.scale = Vector2(z, z)
	_view.position = half - (center * z * s).round() / s + shake
	# Con la telecamera larga i piani dello sfondo non si rimpiccioliscono: la telecamera arretra, il
	# piano di gioco si allarga e lo sfondo lontano resta com'è (e copre lo schermo con le sue immagini,
	# fatte per la vista a 480).
	var zb := maxf(z, 1.0) if wide_cam else z
	for n: Node2D in [_art_back, _art_front] + _art_extra:
		if n != null:
			n.scale = Vector2(zb, zb)
			n.position = (half * (1.0 - zb) * s).round() / s + shake
	for n: Node2D in _art_view:
		if n != null:
			n.scale = Vector2(z, z)
			n.position = shake


## I bordi sinistro e destro di quello che si vede del mondo (per non disegnare quello che sta fuori).
func _vis_x0() -> float:
	return _visible_rect().position.x


func _vis_x1() -> float:
	return _visible_rect().end.x


## Quello che si vede del mondo adesso (con lo zoom delle scene è più piccolo dello schermo).
func _visible_rect() -> Rect2:
	var size := View.SIZE / zoom
	return Rect2(_view_c - size / 2.0, size)


# ------------------------------------------------------------------ disegno

func _sync_visual() -> void:
	_vista_k = move_toward(_vista_k, 1.0 if vista and arena == null else 0.0, 1.0 / VISTA_FADE)
	# A telecamera inclinata la stanza dietro il pavimento si schiaccia verso la linea del pavimento.
	var s := 1.0 - tilt_squash * tilt
	_room_node.scale = Vector2(1, s)
	_room_node.position = Vector2(0, _floor_y * (1.0 - s))
	_body.visible = arena == null and (respawn_blink == 0 or (respawn_blink / 4) % 2 == 0)
	# Dopo un colpo dei droni GIG lampeggia finché è intoccabile; col sigillo addosso no.
	if player.inv_t > 0 and player.hurt_t == 0 and player.stuck_left == 0 and (player.inv_t / 3) % 2 == 1:
		_body.visible = false
	if arena != null:
		arena.player.sync_visual()
		# Mentre la telecamera si inclina il livello non fa step(), che di solito ridisegna le ombre.
		arena.shadows.queue_redraw()
		return
	for gs: String in gates:
		var gt: Dictionary = gates[gs]
		gt["lift"] = move_toward(gt["lift"], 1.0 if gt["timer"] > 0 else 0.0, 1.0 / GATE_ANIM)
	if hack_panel != "" and tick % 3 == 0:
		# Le scintille sul pannello mentre il braccio lo forza.
		var fist := _cyber_fist()
		_spark(fist.x + _spark_rng.randf_range(-4, 4), fist.y - 6, _spark_rng.randf_range(-1.2, 1.2), -_spark_rng.randf_range(0.4, 1.6), _spark_rng.randi_range(8, 14), C_CYAN)
	var f := player.anim.frame()
	if _body.texture != player.anim.sheet.texture:
		_body.texture = player.anim.sheet.texture
		_body.light_mask = Fighter.LIGHT_MASK_ACTORS if player.anim.sheet.has_normals else 1
	_body.region_rect = Rect2(f.rect)
	_body.offset = Vector2(-f.anchor)
	_body.scale = Vector2(player.facing, 1)
	_body.position = Vector2(player.sprite_anchor())


func _draw_back() -> void:
	var r := _visible_rect()
	var x0 := maxf(r.position.x - 8, float(art_until_x))
	var x1 := r.end.x + 8
	if art_open_from >= 0:
		x1 = minf(x1, float(art_open_from))
	if x1 > x0:
		var skies: Array[Rect2] = []
		for h in art_holes:
			skies.append(Rect2(h.position.x, -100000, h.size.x, h.end.y + 100000))
		for q in _outside_all(Rect2(x0, r.position.y - 8, x1 - x0, r.size.y + 16), skies):
			_view.draw_rect(q, C_BG)


## I pezzi di `r` fuori da `hole` (r stesso se non si toccano).
static func _outside(r: Rect2, hole: Rect2) -> Array[Rect2]:
	var h := r.intersection(hole)
	if not h.has_area():
		return [r]
	var out: Array[Rect2] = []
	if h.position.y > r.position.y:
		out.append(Rect2(r.position.x, r.position.y, r.size.x, h.position.y - r.position.y))
	if h.end.y < r.end.y:
		out.append(Rect2(r.position.x, h.end.y, r.size.x, r.end.y - h.end.y))
	if h.position.x > r.position.x:
		out.append(Rect2(r.position.x, h.position.y, h.position.x - r.position.x, h.size.y))
	if h.end.x < r.end.x:
		out.append(Rect2(h.end.x, h.position.y, r.end.x - h.end.x, h.size.y))
	return out


## I pezzi di `r` fuori da tutti gli `holes`.
static func _outside_all(r: Rect2, holes: Array[Rect2]) -> Array[Rect2]:
	var out: Array[Rect2] = [r]
	for h in holes:
		var next: Array[Rect2] = []
		for q in out:
			next.append_array(_outside(q, h))
		out = next
	return out


## La cella `r` sta tutta dentro un tratto disegnato.
func _in_art(r: Rect2) -> bool:
	for h in art_holes:
		if h.encloses(r):
			return true
	return false


func _draw_room() -> void:
	var v := _room_node
	var vr := _visible_rect()
	var x0 := maxi(int(vr.position.x) / SolidGrid.TILE - 1, art_until_x / SolidGrid.TILE)
	var x1 := mini(int(vr.end.x) / SolidGrid.TILE + 1, grid.width - 1)
	# Con la stanza schiacciata dall'inclinazione si vedono un paio di file in più in alto.
	var y0 := maxi(int(vr.position.y) / SolidGrid.TILE - 3, 0)
	var y1 := mini(int(vr.end.y) / SolidGrid.TILE + 1, grid.height - 1)
	# Una riga ogni metro (3 blocchi), per leggere le misure a occhio; non dove il fondo è aperto.
	var t := SolidGrid.TILE
	var gx1 := x1 if art_open_from < 0 else mini(x1, art_open_from / t - 1)
	for cx in range(x0, gx1 + 1):
		if cx % 3 == 0:
			for q in _outside_all(Rect2(cx * t, y0 * t, 1, (y1 - y0 + 1) * t), art_holes):
				v.draw_rect(q, C_GRID)
	for cy in range(y0, y1 + 1):
		if cy % 3 == 1 and gx1 >= x0:
			for q in _outside_all(Rect2(x0 * t, cy * t, (gx1 - x0 + 1) * t, 1), art_holes):
				v.draw_rect(q, C_GRID)
	_draw_water(v, x0, x1)
	for cy in range(y0, y1 + 1):
		for cx in range(x0, x1 + 1):
			if _gate_cells.has(Vector2i(cx, cy)):
				continue
			if _in_art(Rect2(cx * t, cy * t, t, t)):
				continue
			match grid.cell(cx, cy):
				SolidGrid.Cell.SOLID:
					v.draw_rect(Rect2(cx * t, cy * t, t, t), C_SOLID)
					if grid.cell(cx, cy - 1) != SolidGrid.Cell.SOLID:
						v.draw_rect(Rect2(cx * t, cy * t, t, 2), C_SOLID_TOP)
				SolidGrid.Cell.THIN:
					v.draw_rect(Rect2(cx * t, cy * t, t, 4), C_THIN)
					v.draw_rect(Rect2(cx * t, cy * t, t, 1), C_SOLID_TOP)
	hazards.draw_zones(v, tick, vr)
	_draw_hacking(v)
	_draw_stage(v)
	if show_boxes and arena == null:
		var r := Rect2(player.left(), player.top(), moves.body_width, player.height)
		v.draw_rect(Rect2(r.position, Vector2(r.size.x, 1)), C_BOX)
		v.draw_rect(Rect2(r.position + Vector2(0, r.size.y - 1), Vector2(r.size.x, 1)), C_BOX)
		v.draw_rect(Rect2(r.position, Vector2(1, r.size.y)), C_BOX)
		v.draw_rect(Rect2(r.position + Vector2(r.size.x - 1, 0), Vector2(1, r.size.y)), C_BOX)


## Nel grigio, l'acqua nelle buche senza fondo (le colonne vuote fino all'ultima riga della mappa),
## perché si legga che lì si cade e si perde la vita: il pelo sta una cella sotto il bordo più basso
## dei due lati, e si muove piano con le onde. È solo disegno.
func _draw_water(v: Node2D, x0: int, x1: int) -> void:
	var t := SolidGrid.TILE
	var bottom := grid.height - 1
	var cx := maxi(x0, 0)
	while cx <= x1:
		if grid.cell(cx, bottom) != SolidGrid.Cell.EMPTY:
			cx += 1
			continue
		# la buca intera, anche fuori dalla vista
		var a := cx
		while a > 0 and grid.cell(a - 1, bottom) == SolidGrid.Cell.EMPTY:
			a -= 1
		var b := cx
		while b < grid.width - 1 and grid.cell(b + 1, bottom) == SolidGrid.Cell.EMPTY:
			b += 1
		var lip := -1
		for wx: int in [a - 1, b + 1]:
			if wx < 0 or wx >= grid.width:
				continue
			var r := bottom
			while r > 0 and grid.cell(wx, r - 1) == SolidGrid.Cell.SOLID:
				r -= 1
			lip = maxi(lip, r)
		if lip >= 0 and lip < bottom:
			var top := (lip + 1) * t
			var w := Rect2(a * t, top, (b - a + 1) * t, (grid.height - lip - 1) * t)
			v.draw_rect(w, C_WATER)
			v.draw_rect(Rect2(w.position.x, top, w.size.x, 2), C_WATER_TOP)
			# le creste: trattini chiari che scorrono piano sotto la pioggia
			var ph := (tick / 6) % 16
			var x := int(w.position.x) - 16 + ph
			while x < int(w.end.x):
				var x_a := maxi(x, int(w.position.x))
				var x_b := mini(x + 6, int(w.end.x))
				if x_b > x_a:
					v.draw_rect(Rect2(x_a, top + 5, x_b - x_a, 1), C_WATER_TOP)
				x += 16
		cx = b + 1


## I cartelli non si schiacciano con la stanza (il testo in pixel verrebbe storto): si sposta
## solo la loro altezza, come i blocchi. In grigio stanno sempre sopra il loro segno; dove c'è la
## grafica sono didascalie a fumetto che compaiono quando GIG si avvicina.
func _draw_signs(v: Node2D) -> void:
	var s := 1.0 - tilt_squash * tilt
	for k: String in signs:
		if not grid.marks.has(k):
			continue
		var p: Vector2i = grid.marks[k][0]
		if p.x < _vis_x0() - 250 or p.x > _vis_x1() + 250:
			_caption_alpha.erase(k)
			continue
		var lines: Array = signs[k]
		var y := roundf(_floor_y - (_floor_y - (p.y - 150)) * s)
		if backdrop != null:
			_draw_caption(v, k, p, y, lines)
			continue
		UiFont.draw_text(v, Vector2(p.x, y), str(lines[0]), C_TEXT, 1, 1)
		UiFont.draw_text(v, Vector2(p.x, y + 12), str(lines[1]), C_DIM, 1, 1, Color(0, 0, 0, 0), UiFont.SHADOW, true)


## Una didascalia: il riquadro con il titolo e il consiglio, una punta verso il segno, e una
## dissolvenza breve in entrata e in uscita. Resta dentro lo schermo anche col segno vicino al bordo.
func _draw_caption(v: Node2D, k: String, p: Vector2i, y: float, lines: Array) -> void:
	var dx := player.px - p.x
	var want := 1.0 if dx > CAPTION_FROM and dx < CAPTION_TO else 0.0
	var a := move_toward(float(_caption_alpha.get(k, 0.0)), want, 0.08)
	_caption_alpha[k] = a
	if a <= 0.0:
		return
	var t0 := str(lines[0])
	var t1 := str(lines[1])
	var w := float(maxi(UiFont.text_width(t0), UiFont.text_width(t1, 1, true)) + 14)
	var x := clampf(roundf(p.x - w / 2.0), _vis_x0() + 4.0, _vis_x1() - 4.0 - w)
	# Entrando sale di qualche px, come un fumetto che si posa.
	var r := Rect2(x, y - 5.0 + roundf((1.0 - a) * 4.0), w, 29.0)
	var ink := Color(C_CAPTION_INK, a)
	v.draw_rect(r.grow(1.0), ink)
	v.draw_rect(r, Color(C_CAPTION, 0.9 * a))
	var tip := clampf(float(p.x), r.position.x + 7.0, r.end.x - 7.0)
	v.draw_colored_polygon(PackedVector2Array([Vector2(tip - 4.0, r.end.y + 1.0), Vector2(tip + 4.0, r.end.y + 1.0),
		Vector2(tip, r.end.y + 6.0)]), ink)
	var cx := roundf(r.get_center().x)
	UiFont.draw_text(v, Vector2(cx, r.position.y + 3.0), t0, Color(C_TEXT, a), 1, 1, Color(0, 0, 0, 0), Color(UiFont.SHADOW, a))
	UiFont.draw_text(v, Vector2(cx, r.position.y + 15.0), t1, Color(C_DIM, a), 1, 1, Color(0, 0, 0, 0), Color(UiFont.SHADOW, a), true)


## Il pavimento in profondità dell'arena: si apre sotto la linea del pavimento mentre la telecamera
## si inclina, con una linea ogni metro che si allarga verso chi guarda.
func _draw_floor() -> void:
	var v := _floor_node
	if tilt > 0.0:
		var c_floor: Color = floor_colors["floor"]
		var c_line: Color = floor_colors["line"]
		var c_speck: Color = floor_colors["speck"]
		var top := float(_floor_y)
		var depth := roundf((View.H - ARENA_BAND.x + 8.0) * tilt)
		var band := roundf((ARENA_BAND.y - ARENA_BAND.x) * tilt)
		var vr := _visible_rect()
		var x0 := vr.position.x - 8.0
		var w := vr.size.x + 16.0
		v.draw_rect(Rect2(x0, top, w, depth), c_floor)
		var vp_x := _view_c.x
		var m := float(View.PPM)
		# Sassolini fermi nel mondo, più radi in fondo e più grandi davanti (solo con la grafica).
		if c_speck.a > 0.0:
			var x_from := int(floorf(x0 / 16.0))
			for gx in range(x_from, x_from + int(w / 16.0) + 2):
				for r in 6:
					var hsh := (gx * 73856093) ^ (r * 19349663)
					var fy := float(posmod(hsh, 997)) / 997.0
					var ry := roundf(band * (r + fy) / 6.0)
					var sx := gx * 16.0 + float(posmod(hsh >> 4, 16))
					var xr := vp_x + (sx - vp_x) * (1.0 + ry / PERSP)
					v.draw_rect(Rect2(roundf(xr), top + ry, 1.0 + float(r >= 3), 1), c_speck)
		var lx := floorf((x0 - 200.0) / m) * m
		while lx < x0 + w + 200.0:
			for r in int(band):
				var xr := vp_x + (lx - vp_x) * (1.0 + r / PERSP)
				v.draw_rect(Rect2(roundf(xr), top + r, 1, 1), c_line)
			lx += m
		# Linee di traverso: più fitte in fondo, più larghe davanti.
		for k: float in [0.2, 0.43, 0.7]:
			v.draw_rect(Rect2(x0, roundf(top + band * k), w, 1), c_line)
		v.draw_rect(Rect2(x0, top, w, 2), floor_colors["top"])
		# Il bordo davanti della fascia calpestabile, poi il marciapiede scuro fino al fondo dello schermo.
		if depth > band:
			v.draw_rect(Rect2(x0, top + band, w, depth - band), floor_colors["kerb"])
			v.draw_rect(Rect2(x0, top + band, w, 1), c_line)


func _draw_hud() -> void:
	var h := _hud
	if arena_phase != ArenaPhase.NONE:
		# Nell'arena c'è l'interfaccia dello slice, con la vita di GIG e del nemico.
		_draw_stage_hud(h)
		return
	drones.draw_hud(h)
	h.draw_rect(Rect2(0, 0, View.W, 15), Color(0, 0, 0, 0.55))
	favors.draw_tags_hud(h)
	if use_lives:
		# Decisione A di Luigi (8 novembre 2026): le vite e l'energia insieme, in alto a sinistra; il
		# nome del tratto va a destra.
		var lives := "GIG ×%d" % maxi(Game.lives, 0)
		UiFont.draw_text(h, Vector2(4, 2), lives, UiArt.color("lives", C_TEXT))
		var ex := _draw_energy(h, 4 + UiFont.text_width(lives) + 8)
		if not hazards.is_empty():
			hazards.draw_hud(h, ex + 10, tick)
		UiFont.draw_text(h, Vector2(View.W - 4, 2), hud_title, C_CYAN, 1, 2)
		_draw_lives_hud(h)
	else:
		UiFont.draw_text(h, Vector2(4, 2), hud_title, C_CYAN)
		if not hazards.is_empty() or not drones.is_empty():
			var ex := _draw_energy(h, 4 + UiFont.text_width(hud_title) + 10)
			hazards.draw_hud(h, ex + 10, tick)
		var st :="COLLEGATO" if hack_panel != "" else player.state_name()
		UiFont.draw_text(h, Vector2(View.W - 4, 2), st, C_CYAN if hack_panel != "" else C_TEXT, 1, 2)
	# La riga dei numeri del salto è di sviluppo: si accende con i riquadri (F1 o --debug-boxes).
	if not show_boxes:
		_draw_stage_hud(h)
		return
	var sub := float(PlatformPlayer.SUB)
	var info := "vel %.1f · %.1f px/tick   salto %d px (%.2f m)   in aria %d tick   spinte %d" % [
		player.vx / sub, player.vy / sub, player.last_peak, player.last_peak / float(View.PPM), player.air_ticks, player.boosts_left]
	h.draw_rect(Rect2(0, View.H - 15, View.W, 15), Color(0, 0, 0, 0.55))
	UiFont.draw_text(h, Vector2(4, View.H - 13), info, C_DIM, 1, 0, Color(0, 0, 0, 0), UiFont.SHADOW, true)
	_draw_stage_hud(h)


# ------------------------------------------------------------------ arena

## Si entra nell'arena una volta per giro, coi piedi sul pavimento oltre il punto d'ingresso e
## dentro lo schermo dell'arena (partendo più avanti con --start-x l'arena non si apre).
func _arena_starts() -> bool:
	if arena_done or _arena_cam_x < 0 or player.px < _arena_trigger_x or player.py != _floor_y:
		return false
	if player.px > _arena_cam_x + View.W - 40:
		return false
	return player.state in [PlatformPlayer.State.GROUND, PlatformPlayer.State.CROUCH, PlatformPlayer.State.SLIDE]


func _arena_data() -> Dictionary:
	return {
		"id": "stanza_arena",
		"width": grid.pixel_width(),
		"floor_band": [ARENA_BAND.x, ARENA_BAND.y],
		"waves": [{"id": arena_id, "camera_x": _arena_cam_x, "music_layer": "arena", "spawns": arena_spawns}],
	}


func _open_arena() -> void:
	arena = Level.new()
	arena.configure({"seed": 1, "input": input, "embedded": true, "lives": use_lives, "auto_tick": false, "card": false, "sound": sound,
		"data": _arena_data(), "start_x": float(player.px), "start_y": ARENA_BAND.x})
	# Il bordo dietro della fascia sta sulla linea del pavimento del platform.
	arena.position = Vector2(0, _floor_y - ARENA_BAND.x)
	_view.add_child(arena)
	arena.camera.min_x = _arena_cam_x
	arena.camera.max_x = _arena_cam_x
	arena.camera.x = _arena_cam_x
	if not lights_on:
		arena.set_lights(false)
	var g := arena.player
	# L'energia è una sola per tutta la partita (decisione A): GIG entra nell'arena con quella che ha.
	if use_lives:
		g.hp = clampi(Game.energy, 1, g.data.max_hp)
	# Prima del riavvio il braccio resta bloccato anche nell'arena: il foglio spento e la sola destra.
	if player.arm_locked:
		g.use_sheet(&"gig_spento")
		g.one_arm = true
	g.facing = player.facing
	g.play_anim(&"walk")
	arena_phase = ArenaPhase.ENTER
	_arena_t = 0
	_cam_from = _cam
	_sparks.clear()
	if pilot != null:
		pilot.arena = arena


func _arena_tick(frame: InputFrame) -> void:
	var g := arena.player
	_arena_t += 1
	match arena_phase:
		ArenaPhase.ENTER:
			# GIG fa qualche passo dentro la fascia mentre la telecamera si inclina; gli ingressi aspettano.
			var k := float(_arena_t) / TILT_IN
			tilt = _ease(k)
			g.py = ARENA_BAND.x + ENTRY_DEPTH * k
			g.anim.advance()
			if _arena_t >= TILT_IN:
				g.set_state(Fighter.State.IDLE, &"idle")
				arena_phase = ArenaPhase.FIGHT
				_arena_t = 0
				_on_arena_fight()
		ArenaPhase.FIGHT:
			arena.step(frame)
			if use_lives:
				Game.energy = clampi(g.hp, 0, Game.ENERGY_MAX)
			# Zona liberata (il livello ha già acceso VAI): si esce appena GIG è libero e coi piedi a terra.
			if arena.waves_cleared > 0 and arena.active_wave.is_empty() and g.is_free() and g.ph <= 0.0:
				arena_phase = ArenaPhase.LEAVE
				_arena_t = 0
				_leave_from_py = g.py
				_cam_from = _cam
				g.play_anim(&"walk")
		ArenaPhase.LEAVE:
			# GIG torna sul bordo dietro e la telecamera torna laterale.
			var k := float(_arena_t) / TILT_OUT
			tilt = 1.0 - _ease(k)
			g.py = lerpf(_leave_from_py, ARENA_BAND.x, k)
			g.anim.advance()
			arena.overlay.tick()
			if _arena_t >= TILT_OUT:
				player.place(roundi(g.px), _floor_y)
				player.facing = g.facing
				_overlay.go_ticks = arena.overlay.go_ticks
				arena_done = true
				_close_arena()


## Toglie l'arena, a fine scontro o quando si ricomincia.
func _close_arena() -> void:
	if arena != null:
		# Ricominciando a metà scontro, lo strato "arena" della musica resterebbe acceso.
		if sound and not arena.active_wave.is_empty():
			Music.set_layer(&"arena", false)
		_view.remove_child(arena)
		arena.queue_free()
	arena = null
	arena_phase = ArenaPhase.NONE
	tilt = 0.0
	if pilot != null:
		pilot.arena = null


func _arena_camera() -> void:
	var lock := Vector2(_arena_cam_x, _floor_y - ARENA_BAND.x)
	match arena_phase:
		ArenaPhase.ENTER:
			_cam = _cam_from.lerp(lock, _ease(float(_arena_t) / TILT_IN))
		ArenaPhase.FIGHT:
			_cam = lock
		ArenaPhase.LEAVE:
			var g := arena.player
			var back := Vector2(g.px + g.facing * 45 - View.CX, _floor_y - 188)
			back.x = clampf(back.x, 0.0, float(grid.pixel_width() - View.W))
			back.y = clampf(back.y, -80.0, float(grid.pixel_height() - View.H))
			_cam = lock.lerp(back, _ease(float(_arena_t) / TILT_OUT))
	var z := _game_zoom()
	_place_view(_game_view_center(z), z, Vector2(arena.camera.shake))


static func _ease(k: float) -> float:
	k = clampf(k, 0.0, 1.0)
	return k * k * (3.0 - 2.0 * k)


# ------------------------------------------------------------------ scene nel motore

## Da ridefinire nei tratti: l'arena passa dall'entrata allo scontro (qui si applica l'esito di una
## scena di presentazione e la si chiede con request_scene()).
func _on_arena_fight() -> void:
	pass


## Chiede la scena `id`, dalla simulazione, nel tick in cui parte: chi la chiede ne ha già applicato
## l'esito. `poses` sono le pose degli attori veri prima dell'esito (scene_pose_*), per le comparse.
## La scena parte nello stesso fotogramma, dopo il tick; nei test (che chiamano _sim_tick) non parte.
func request_scene(id: String, poses: Dictionary) -> void:
	if scenes_enabled:
		_scene_request = {"id": id, "poses": poses}


## La posa di un combattente dell'arena, in coordinate della scena dell'arena.
func scene_pose_fighter(f: Fighter) -> Dictionary:
	return {"x": f.px - _arena_cam_x, "y": f.py, "verso": f.facing, "anim": String(f.anim.name),
		"index": f.anim.index, "frame_tick": f.anim.frame_tick, "foglio": String(f.sheet.id)}


## La posa di GIG nel platform, rispetto al segno `rif` della mappa.
func scene_pose_player(rif: String) -> Dictionary:
	var r := Vector2i(grid.marks[rif][0]) if grid.marks.has(rif) else Vector2i.ZERO
	var a := player.sprite_anchor()
	return {"x": a.x - r.x, "y": a.y - r.y, "verso": player.facing, "anim": String(player.anim.name),
		"index": player.anim.index, "frame_tick": player.anim.frame_tick, "foglio": String(player.anim.sheet.id)}


func _start_scene() -> void:
	var req := _scene_request
	_scene_request = {}
	var sd := SceneData.load_scene(str(req["id"]))
	if not sd.errors.is_empty():
		push_warning("Scena %s non valida: %s" % [req["id"], "; ".join(sd.errors)])
		return
	scene_flags = {}
	scene = ScenePlayer.new()
	scene.name = "Scena"
	add_child(scene)
	# Gli attori veri restano fermi e nascosti: al loro posto recitano le comparse.
	_body.visible = false
	if arena != null:
		for f in arena.fighters:
			f.visible = false
	_sparks.clear()
	scene.start(sd, self, req["poses"], input.mode != PlayerInput.Mode.LIVE, sound)


## Un fotogramma con la simulazione ferma: recita la scena, il resto si ridisegna e basta.
func _scene_frame() -> void:
	scene.tick()
	_update_art()
	if arena != null:
		arena.shadows.queue_redraw()
	_tick_extras()
	_redraw_all()


## Dove sta una scena: l'origine delle sue coordinate nel nodo delle comparse, lo scarto di quel nodo
## nel mondo della stanza e il nodo stesso ("arena": il mondo dell'arena; "stanza": il mondo platform,
## rispetto al segno `rif`).
func scene_frame(space: String, rif: String) -> Dictionary:
	if space == "arena" and arena != null:
		return {"origin": Vector2(_arena_cam_x, 0), "offset": arena.position, "parent": arena.world}
	var r := Vector2(grid.marks[rif][0]) if rif != "" and grid.marks.has(rif) else Vector2.ZERO
	return {"origin": r, "offset": Vector2.ZERO, "parent": _view}


## Il centro dell'inquadratura del gioco, nel mondo della stanza.
func scene_camera_center() -> Vector2:
	return _view_c if _squeeze_k > 0.0 else _cam.round() + View.SIZE / 2.0


## Lo zoom da cui parte una scena: quello della telecamera che si stringe, se c'è, se no 1.
func scene_camera_zoom() -> float:
	return zoom if _squeeze_k > 0.0 else 1.0


## Quello che una scena può mostrare, nel mondo della stanza: sotto, non oltre il fondo dell'arena (o
## della mappa), sopra fin dove sale la telecamera del gioco.
func scene_bounds() -> Rect2:
	var bottom := float(grid.pixel_height())
	if arena != null:
		bottom = float(_floor_y - ARENA_BAND.x + View.H)
	return Rect2(0, -80, grid.pixel_width(), bottom + 80)


func scene_apply_camera(center: Vector2, z: float) -> void:
	_place_view(center, z)


func scene_shadow_def() -> FxLayer.FxDef:
	return arena.fx.defs.get(&"ombra") if arena != null else null


## L'interfaccia del gioco (scritte, barre, cartelli) sfuma durante la scena.
func scene_ui_alpha(a: float) -> void:
	for c: CanvasItem in [_hud, _overlay, _signs_node]:
		if c != null:
			c.modulate.a = a
	if arena != null:
		arena.hud.modulate.a = a
		arena.overlay.modulate.a = a


## Un evento della regia (per esempio "pioggia"): il disegno del tratto lo legge da scene_flags.
func scene_event(e: String) -> void:
	scene_flags[e] = true
	_on_scene_event(e)


func _on_scene_event(_e: String) -> void:
	pass


## La scena restituisce il gioco: gli attori veri ricompaiono al posto delle comparse, che erano già
## nel loro punto; le comparse che restano diventano parte del mondo; i tasti tenuti per l'ultima
## battuta non diventano pressioni. Da qui la simulazione riparte.
func scene_handoff(sp: ScenePlayer) -> void:
	sp.hide_handed_over()
	for p in sp.take_extras():
		_extras.append(p)
	_body.visible = arena == null
	if arena != null:
		for f in arena.fighters:
			f.sync_visual()
		arena.shadows.queue_redraw()
	else:
		_sync_visual()
	input.resync()
	_on_scene_handoff(sp.data.id)


func _on_scene_handoff(_id: String) -> void:
	pass


func scene_end(_sp: ScenePlayer) -> void:
	scene = null
	scene_ui_alpha(1.0)
	var z := _game_zoom()
	_place_view(_game_view_center(z), z)


func _tick_extras() -> void:
	for p in _extras:
		if is_instance_valid(p):
			p.tick()


func _clear_extras() -> void:
	for p in _extras:
		if is_instance_valid(p):
			p.queue_free()
	_extras.clear()


# ------------------------------------------------------------------ hacking

## Le celle dei cancelli, dai simboli della mappa: chiuse (piene) all'inizio.
func _build_gates() -> void:
	gates.clear()
	_gate_cells.clear()
	for id: String in panels:
		var s: String = panels[id]["gate"]
		if not grid.marks.has(s):
			continue
		var cells: Array[Vector2i] = []
		var r := Rect2i()
		for m: Vector2i in grid.marks[s]:
			var c := Vector2i((m.x - SolidGrid.TILE / 2) / SolidGrid.TILE, m.y / SolidGrid.TILE - 1)
			cells.append(c)
			_gate_cells[c] = true
			var cr := Rect2i(c * SolidGrid.TILE, Vector2i(SolidGrid.TILE, SolidGrid.TILE))
			r = cr if r.size == Vector2i.ZERO else r.merge(cr)
		gates[s] = {"cells": cells, "rect": r, "timer": 0, "lift": 0.0}
	_reset_hacking()


func _reset_hacking() -> void:
	hack_panel = ""
	hack_t = 0
	hacks_done.clear()
	for s: String in gates:
		gates[s]["timer"] = 0
		gates[s]["lift"] = 0.0
		_set_gate(s, false)


func _set_gate(s: String, open: bool) -> void:
	for c: Vector2i in gates[s]["cells"]:
		grid.set_cell(c.x, c.y, SolidGrid.Cell.EMPTY if open else SolidGrid.Cell.SOLID)


func _panel_pos(id: String) -> Vector2i:
	return grid.marks[id][0]


## Dove deve stare GIG per avere il pugno cyber sotto la presa della centralina, col verso di adesso.
func hack_spot(id: String) -> int:
	return _panel_pos(id).x - player.facing * HACK_FIST_X


## Il pannello a portata di GIG (sotto la centralina, sullo stesso piano), o "".
func panel_in_reach() -> String:
	for id: String in panels:
		if not grid.marks.has(id) or not gates.has(panels[id]["gate"]):
			continue
		if absi(player.px - hack_spot(id)) <= HACK_REACH and player.py == _panel_pos(id).y:
			return id
	return ""


## La scatola della centralina, in pixel del mondo.
func _panel_rect(id: String) -> Rect2:
	var m := _panel_pos(id)
	return Rect2(m.x - PANEL_W / 2, m.y - PANEL_BOTTOM - PANEL_H, PANEL_W, PANEL_H)


## Un tick di hacking, prima che GIG si muova: conta il tempo dei cancelli aperti e quello del
## collegamento. Collegato, GIG non cammina (riceve un ingresso vuoto) e si sistema col pugno sotto
## la presa; SALTO, lasciare SU o allontanarsi staccano il contatto. Restituisce l'ingresso da dare a GIG.
func _hack_tick(frame: InputFrame, events: PackedStringArray) -> InputFrame:
	for s: String in gates:
		var gt: Dictionary = gates[s]
		if gt["timer"] > 0:
			gt["timer"] -= 1
			if gt["timer"] == 0:
				# Il cancello non si chiude addosso a GIG: aspetta che sia passato.
				var body := Rect2i(player.left(), player.top(), player.right() - player.left(), player.height)
				if body.intersects(gt["rect"]):
					gt["timer"] = 1
				else:
					_set_gate(s, false)
					events.append("gate_close")
	var on_ground := player.state == PlatformPlayer.State.GROUND
	if hack_panel == "" and not player.arm_locked:
		var id := panel_in_reach()
		if id != "" and on_ground and frame.is_held(InputFrame.UP) and gates[panels[id]["gate"]]["timer"] == 0:
			hack_panel = id
			hack_t = 0
			events.append("hack_start")
	if hack_panel == "":
		return frame
	if not frame.is_held(InputFrame.UP) or frame.was_pressed(InputFrame.JUMP) or not on_ground or panel_in_reach() != hack_panel:
		hack_panel = ""
		hack_t = 0
		events.append("hack_cut")
		return frame
	hack_t += 1
	# Il passo che manca per arrivare col pugno sotto la presa.
	var dx := signi(hack_spot(hack_panel) - player.px)
	if dx != 0 and not grid.rect_hits_solid(player.left() + dx, player.top(), player.right() + dx, player.py):
		player.px += dx
	if hack_t >= HACK_TICKS:
		var s: String = panels[hack_panel]["gate"]
		gates[s]["timer"] = int(panels[hack_panel]["open"])
		_set_gate(s, true)
		hacks_done[hack_panel] = int(hacks_done.get(hack_panel, 0)) + 1
		last_hacked = hack_panel
		hack_panel = ""
		hack_t = 0
		events.append("hack_done")
	return InputFrame.new()


## Impronta della stanza per i test: GIG, hacking e cancelli.
func state_hash() -> int:
	var g: Array = []
	for s: String in gates:
		g.append(gates[s]["timer"])
	var lv: Array = [fall_t, continue_t, continue_left, over_t, respawn_blink, Game.lives] if use_lives else []
	# Le zone e i power-up, e con loro l'energia, solo nei tratti che li hanno: le impronte di prima restano.
	var hz: Array = hazards.state_hash() + [Game.energy] if not hazards.is_empty() else []
	var dr: Array = drones.state_hash() + [Game.energy] if not drones.is_empty() else []
	if not favors.is_empty():
		dr += favors.state_hash() + [Game.energy]
		if Game.scarica > 0:
			dr.append(Game.scarica)
	if not processions.is_empty():
		dr += processions.state_hash()
	# Le basi dei registri e la Vista, solo dove ci sono basi.
	if not registri.is_empty():
		dr += registri.state_hash() + [vista, Game.registri.size()]
	# Le celle Rompibile rotte, solo dove ce ne sono: le impronte di prima restano.
	var br: Array = [Array(grid.broken)] if not grid.broken.is_empty() else []
	return hash([player.state_hash(), hack_panel, hack_t, g, hacks_done] + lv + hz + dr + br + _stage_hash())


## I pannelli sul muro di fondo e i cancelli, con il conto alla rovescia.
func _draw_hacking(v: Node2D) -> void:
	for id: String in panels:
		if not grid.marks.has(id) or not gates.has(panels[id]["gate"]):
			continue
		var m := _panel_pos(id)
		if m.x < _vis_x0() - 60 or m.x > _vis_x1() + 60:
			continue
		_draw_panel(v, id, gates[panels[id]["gate"]])
	for s: String in gates:
		var gt: Dictionary = gates[s]
		var g: Rect2i = gt["rect"]
		if g.end.x < _vis_x0() - 20 or g.position.x > _vis_x1() + 20:
			continue
		# Il cancello sale verso il soffitto: resta visibile la parte che non è ancora rientrata.
		var h := roundf(g.size.y * (1.0 - float(gt["lift"])))
		if h > 0:
			v.draw_rect(Rect2(g.position.x, g.end.y - h, g.size.x, h), C_GATE_DARK)
			var bx := g.position.x + 3
			while bx < g.end.x - 2:
				v.draw_rect(Rect2(bx, g.end.y - h, 3, h), C_GATE)
				bx += 8
			for k in range(0, int(h), 40):
				v.draw_rect(Rect2(g.position.x, g.end.y - h + k, g.size.x, 2), C_GATE_DARK.darkened(0.3))
			v.draw_rect(Rect2(g.position.x, g.end.y - 2, g.size.x, 2), C_GATE_DARK.darkened(0.3))
		if gt["timer"] > 0:
			# Il conto alla rovescia all'altezza della testa, rosso nell'ultimo secondo.
			var cx := g.position.x + g.size.x / 2.0
			var secs := float(gt["timer"]) / Engine.physics_ticks_per_second
			var col := C_BOX if gt["timer"] <= 60 else C_TEXT
			if gt["timer"] > 60 or (gt["timer"] / 6) % 2 == 0:
				UiFont.draw_text(v, Vector2(cx, g.end.y - 140), "%.1f" % secs, col, 2, 1, C_PANEL)
			var full := float(_open_ticks(s))
			var bw := roundf(30.0 * gt["timer"] / full)
			v.draw_rect(Rect2(cx - 15, g.end.y - 114, 30, 3), C_PANEL)
			v.draw_rect(Rect2(cx - 15, g.end.y - 114, bw, 3), col)


func _open_ticks(gate: String) -> int:
	for id: String in panels:
		if panels[id]["gate"] == gate:
			return int(panels[id]["open"])
	return 1


## Una centralina di SIDERA: scatola d'acciaio con i bordi in rilievo, la targa, lo schermo, il led,
## le feritoie, la fascia di pericolo e sotto la presa dove si appoggia il pugno; un condotto la porta
## al soffitto. Lo schermo dice lo stato: in attesa, forzata (codici che scorrono e barra), aperta.
func _draw_panel(v: Node2D, id: String, gt: Dictionary) -> void:
	var r := _panel_rect(id)
	var x0 := r.position.x
	var y0 := r.position.y
	var w := r.size.x
	var h := r.size.y
	var hacking := hack_panel == id
	var open: bool = gt["timer"] > 0
	# Il condotto, dal tetto della scatola al primo pieno sopra, con le staffe ogni 40 px.
	var px := x0 + w - 11
	var cy := int(y0) / SolidGrid.TILE - 1
	while cy > 0 and grid.cell(int(px) / SolidGrid.TILE, cy) != SolidGrid.Cell.SOLID:
		cy -= 1
	var top := float((cy + 1) * SolidGrid.TILE)
	v.draw_rect(Rect2(px, top, 5, y0 - top), C_CASE_LO)
	v.draw_rect(Rect2(px + 1, top, 2, y0 - top), C_CASE)
	v.draw_rect(Rect2(px + 1, top, 1, y0 - top), C_CASE_HI.darkened(0.2))
	var by := y0 - 14
	while by > top + 4:
		v.draw_rect(Rect2(px - 1, by, 7, 3), C_CASE_LO)
		v.draw_rect(Rect2(px - 1, by, 7, 1), C_CASE)
		by -= 40
	# Ombra sul muro e scatola, coi bordi in rilievo e le viti.
	v.draw_rect(Rect2(x0 + 2, y0 + 2, w, h), Color(0, 0, 0, 0.35))
	v.draw_rect(r, C_CASE)
	v.draw_rect(Rect2(x0, y0, w, 1), C_CASE_HI)
	v.draw_rect(Rect2(x0, y0, 1, h), C_CASE_HI)
	v.draw_rect(Rect2(x0, y0 + h - 1, w, 1), C_CASE_LO)
	v.draw_rect(Rect2(x0 + w - 1, y0, 1, h), C_CASE_LO)
	for sp: Vector2 in [Vector2(2, 2), Vector2(w - 4, 2), Vector2(2, h - 10), Vector2(w - 4, h - 10)]:
		v.draw_rect(Rect2(x0 + sp.x, y0 + sp.y, 2, 2), C_CASE_LO)
		v.draw_rect(Rect2(x0 + sp.x, y0 + sp.y, 1, 1), C_CASE_HI)
	# La targa con la scritta.
	v.draw_rect(Rect2(x0 + 3, y0 + 3, w - 6, 10), C_CASE_LO)
	UiFont.draw_text(v, Vector2(x0 + w / 2.0, y0 + 3), "SIDERA", C_CASE_HI, 1, 1, Color(0, 0, 0, 0), Color(0, 0, 0, 0))
	# Lo schermo, con le righe.
	var sr := Rect2(x0 + 4, y0 + 15, w - 8, 14)
	v.draw_rect(Rect2(sr.position - Vector2(1, 1), sr.size + Vector2(2, 2)), C_CASE_LO)
	var glow := C_OK if open else C_CYAN
	v.draw_rect(sr, C_SCREEN.lerp(glow, 0.14 if (open or hacking) else 0.05))
	if open:
		UiFont.draw_text(v, Vector2(sr.get_center().x, sr.position.y + 3), "OK", C_OK, 1, 1, Color(0, 0, 0, 0), Color(0, 0, 0, 0))
	elif hacking:
		# Codici che scorrono e la barra di avanzamento.
		for row in 3:
			for col in 7:
				if ((col * 7 + row * 13 + tick / 3 + id.unicode_at(0)) * 31) % 7 < 3:
					v.draw_rect(Rect2(sr.position.x + 2 + col * 4, sr.position.y + 2 + row * 3, 3, 1), C_CYAN.darkened(0.25))
		v.draw_rect(Rect2(sr.position.x + 1, sr.end.y - 3, sr.size.x - 2, 2), C_SCREEN.lerp(C_CYAN, 0.2))
		v.draw_rect(Rect2(sr.position.x + 1, sr.end.y - 3, roundf((sr.size.x - 2) * hack_t / HACK_TICKS), 2), C_CYAN)
	else:
		# In attesa: un prompt e il cursore che lampeggia.
		v.draw_rect(Rect2(sr.position.x + 2, sr.position.y + 3, 2, 1), C_CYAN.darkened(0.4))
		v.draw_rect(Rect2(sr.position.x + 5, sr.position.y + 3, 12, 1), C_CYAN.darkened(0.55))
		v.draw_rect(Rect2(sr.position.x + 2, sr.position.y + 7, 8, 1), C_CYAN.darkened(0.55))
		if (tick / 20) % 2 == 0:
			v.draw_rect(Rect2(sr.position.x + 11, sr.position.y + 6, 3, 2), C_CYAN.darkened(0.2))
	for y in range(int(sr.position.y) + 1, int(sr.end.y), 2):
		v.draw_rect(Rect2(sr.position.x, y, sr.size.x, 1), Color(0, 0, 0, 0.25))
	# Feritoie e led.
	for i in 3:
		v.draw_rect(Rect2(x0 + 5, y0 + 32 + i * 2, 12, 1), C_CASE_LO)
	var led := C_LED_RED
	if open:
		led = C_OK
	elif hacking:
		led = C_CYAN if (tick / 3) % 2 == 0 else C_CASE_LO
	elif (tick / 45) % 3 == 2:
		led = C_LED_RED.darkened(0.6)
	v.draw_rect(Rect2(x0 + w - 10, y0 + 32, 4, 4), C_CASE_LO)
	v.draw_rect(Rect2(x0 + w - 9, y0 + 33, 2, 2), led)
	# La fascia di pericolo in fondo.
	var hy := y0 + h - 7
	for i in int(w) - 4:
		for j in 4:
			v.draw_rect(Rect2(x0 + 2 + i, hy + j, 1, 1), C_HAZARD if ((i + j) / 3) % 2 == 0 else C_CASE_LO)
	# La presa sotto la scatola, dove si appoggia il pugno.
	var cx := r.get_center().x
	v.draw_rect(Rect2(cx - 6, y0 + h, 12, 3), C_CASE_LO)
	v.draw_rect(Rect2(cx - 4, y0 + h + 1, 8, 1), C_CYAN if hacking else C_CYAN.darkened(0.6))
	if hack_panel == "" and not open and panel_in_reach() == id:
		UiFont.draw_text(v, Vector2(cx, y0 - 12), "SU", C_CYAN, 1, 1)


## Il pugno del braccio cyber (il sinistro, decisione 21) nel fotogramma di adesso, in pixel del mondo.
func _cyber_fist() -> Vector2:
	var f := Vector2i(HACK_FIST_X, -118)
	if player.anim != null and player.anim.frame().points.has("fist_l"):
		f = player.anim.frame().points["fist_l"]
	var a := player.sprite_anchor()
	return Vector2(a.x + player.facing * f.x, a.y + f.y)


## Il contatto: il pugno appoggiato alla presa, un bagliore e piccoli archi fra i due, e l'energia
## che sale lungo il braccio cyber a impulsi.
func _draw_contact(n: Node2D) -> void:
	var fist := _cyber_fist()
	var pr := _panel_rect(hack_panel)
	var plug := Vector2(pr.get_center().x, pr.end.y + 2)
	var pulse := 0.5 + 0.5 * sin(tick * 0.6)
	n.draw_circle(plug, 9.0, Color(C_CYAN, 0.10 + 0.08 * pulse))
	n.draw_circle(plug, 5.0, Color(C_CYAN, 0.22 + 0.12 * pulse))
	# Archi: due zigzag corti fra il pugno e la presa, che cambiano ogni due tick.
	for k in 2:
		var a := fist + Vector2(-3 + k * 6, -5)
		var prev := a
		for i in range(1, 4):
			var p := a.lerp(plug, float(i) / 3.0)
			if i < 3:
				p.x += float(((tick / 2 + i * 5 + k * 3) % 5) - 2)
			n.draw_line(prev.round(), p.round(), C_TEXT if i == 2 else C_CYAN, 1.0)
			prev = p
	# Impulsi lungo l'avambraccio, dal gomito al pugno.
	var elbow := fist + Vector2(-player.facing * 3, 34)
	for k in 4:
		var u := float((tick * 2 + k * 9) % 36) / 36.0
		var p := elbow.lerp(fist, u).round()
		n.draw_rect(Rect2(p - Vector2(2, 2), Vector2(4, 4)), Color(C_CYAN, 0.35))
		n.draw_rect(Rect2(p - Vector2(1, 1), Vector2(2, 2)), C_TEXT if u > 0.8 else C_CYAN)


# ------------------------------------------------------------------ effetti

func _on_event(e: String) -> void:
	_event_sound(e)
	match e:
		"braccio_a_vuoto":
			# SALTO in aria prima del riavvio: il braccio prova la Spinta e non parte. Poche scintille
			# spente dal pugno, che col braccio morto sta sul petto, sotto la barba: nascono sul davanti
			# della sagoma e schizzano in avanti, così escono subito sul fondo scuro; ricadono e muoiono
			# presto (le prime due appena cyan), senza bagliore.
			var fist := _cyber_fist() + Vector2(14 * player.facing, 0)
			for i in 5:
				var vx := _spark_rng.randf_range(1.3, 2.4) * player.facing
				var vy := _spark_rng.randf_range(-1.5, -0.2)
				_spark(fist.x, fist.y, vx, vy, _spark_rng.randi_range(11, 17), C_CYAN_DEAD if i > 1 else C_CYAN_WEAK)
		"spinta":
			# La scarica del braccio verso il basso: un ventaglio di scintille cyan.
			for i in 14:
				var a := _spark_rng.randf_range(0.25, 0.75) * PI
				var s := _spark_rng.randf_range(1.2, 3.2)
				_spark(player.px, player.py - 5, cos(a) * s * 1.25, sin(a) * s * 1.25, _spark_rng.randi_range(10, 20), C_CYAN)
		"land":
			for i in 6:
				var dir := -1.0 if i % 2 == 0 else 1.0
				_spark(player.px + dir * 8, player.py - 1, dir * _spark_rng.randf_range(0.6, 1.6), -_spark_rng.randf_range(0.1, 0.6), 10, C_DIM)
		"scatto":
			# Il colpo del braccio all'indietro: lo scatto spinge in avanti.
			for i in 12:
				var a := _spark_rng.randf_range(-0.35, 0.35) + (PI if player.facing > 0 else 0.0)
				var s := _spark_rng.randf_range(1.5, 3.5)
				_spark(player.px - player.facing * 8, player.py - 55, cos(a) * s * 1.25, sin(a) * s * 1.25, _spark_rng.randi_range(8, 16), C_CYAN)
		"rompe":
			# Lo scatto sfonda un Rompibile: schegge in avanti e in alto, da tutta la parte rotta.
			var r := Rect2(player.last_break)
			for i in 22:
				var a := _spark_rng.randf_range(-0.9, 0.5)
				var s := _spark_rng.randf_range(1.0, 3.4)
				var y := r.position.y + _spark_rng.randf() * r.size.y
				_spark(r.get_center().x, y, cos(a) * s * player.facing, sin(a) * s, _spark_rng.randi_range(14, 28),
					C_SPLINTER if i % 3 != 0 else C_PLASTER)
			_shake_t = SHAKE_TICKS
		"walljump", "wallrun":
			# Il colpo contro il muro, dal lato del muro.
			var wx := player.px + player.wall_dir * 13
			for i in 10:
				var a := _spark_rng.randf_range(-0.6, 0.6) + (PI if player.wall_dir > 0 else 0.0)
				var s := _spark_rng.randf_range(1.0, 2.8)
				_spark(wx, player.py - 38, cos(a) * s, sin(a) * s, _spark_rng.randi_range(8, 14), C_CYAN)
		"wall", "wall_spark":
			# Il braccio piantato nel muro che frena: poche scintille verso l'alto.
			var wx2 := player.px + player.wall_dir * 13
			for i in (6 if e == "wall" else 2):
				_spark(wx2, player.py - 72, -player.wall_dir * _spark_rng.randf_range(0.2, 1.0), -_spark_rng.randf_range(0.5, 1.8), 10, C_CYAN)
		"hack_done":
			# Il pannello cede: una scarica dal pannello.
			var m := _panel_rect(last_hacked).get_center()
			for i in 16:
				var a := _spark_rng.randf_range(0.0, TAU)
				var s := _spark_rng.randf_range(0.8, 2.6)
				_spark(m.x, m.y, cos(a) * s, sin(a) * s - 0.8, _spark_rng.randi_range(10, 20), C_OK if i % 3 == 0 else C_CYAN)
		"hack_cut":
			for i in 4:
				_spark(_cyber_fist().x, _cyber_fist().y, _spark_rng.randf_range(-1.0, 1.0), -_spark_rng.randf_range(0.2, 1.0), 8, C_DIM)
		"powerup":
			var pc: Color = hazards.held.color if hazards.held != null else C_CYAN
			for i in 14:
				var a := _spark_rng.randf_range(0.0, TAU)
				var s := _spark_rng.randf_range(0.8, 2.2)
				_spark(player.px, player.py - 50, cos(a) * s, sin(a) * s - 0.6, _spark_rng.randi_range(12, 22), pc)
		"slide":
			for i in 5:
				_spark(player.px - player.facing * 10, player.py - 2, -player.facing * _spark_rng.randf_range(0.5, 1.5), -_spark_rng.randf_range(0.2, 0.8), 12, C_DIM)
		"registro_lampo":
			# Il lampo della copia, piccolo come quello della Spinta, e Tere: «Questo lo teniamo.»
			var b: Registri.Base = registri.basi[registri.copying]
			for i in 10:
				var a := _spark_rng.randf_range(-0.85, -0.15) * PI
				var s := _spark_rng.randf_range(0.8, 2.2)
				_spark(b.px.x, b.px.y - Registri.SIZE.y, cos(a) * s, sin(a) * s, _spark_rng.randi_range(8, 16), C_CYAN)
			_say_in_game(Registri.LINE_TERE, "TERE")


## I suoni degli eventi: salto, atterraggio, hacking e cancelli, power-up e zone tossiche. La tosse e il
## clic del braccio a vuoto (ui_move) sono segnaposto finché car-musica non li fa.
const EVENT_SFX := {
	"powerup": [&"pickup", 0.0], "powerup_fine": [&"ui_move", -4.0], "tosse": [&"body_thud", -12.0], "ko_energia": [&"ko", -2.0],
	"jump": [&"jump", 0.0], "spinta": [&"whoosh_light", -2.0], "scatto": [&"whoosh_heavy", -2.0],
	"land": [&"land", 0.0], "hack_start": [&"hack", 0.0], "hack_done": [&"zap", 0.0],
	"hack_cut": [&"ui_move", -4.0], "gate_close": [&"bin_hit", -8.0],
	"jab": [&"whoosh_light", -4.0], "colpito": [&"hit_medium", -2.0], "rimbalzo": [&"jump", -2.0],
	"sigillo": [&"block", 0.0], "strappo": [&"grab", -8.0], "staccato": [&"throw", -4.0],
	"rompe": [&"bin_break", 0.0], "braccio_a_vuoto": [&"ui_move", -6.0],
	# La base del registro: il clic della culla, il ronzio che sale, il bip di SIDERA che diventa cyan
	# (segnaposto finché car-musica non li fa).
	"registro_clic": [&"grab", -4.0], "registro_ronzio": [&"hack", -6.0], "registro_lampo": [&"zap", -4.0],
	"registro_copiato": [&"glint", -2.0],
}
## Le scintille spente del braccio bloccato: un grigio appena azzurro.
const C_CYAN_DEAD := Color8(122, 148, 158)
## Le prime due, appena cyan.
const C_CYAN_WEAK := Color8(60, 172, 192)
## Le schegge dei Rompibili: legno marcio e intonaco.
const C_SPLINTER := Color8(150, 104, 62)
const C_PLASTER := Color8(206, 194, 170)
## I suoni dei droni, nel punto dove succedono. Segnaposto dalla cartella degli effetti, finché
## car-musica non fa la sirena, il latrato e il ronzio delle eliche.
## Lo spintone ai confratelli: una spallata smorzata.
const PROC_SFX := {"spintone": [&"body_thud", -6.0]}

const DRONE_SFX := {
	"drone_rotto": [&"bin_break", -2.0], "corazza": [&"block", -6.0], "colomba_lente": [&"glint", -6.0],
	"spruzzo": [&"whoosh_light", -8.0], "accecato": [&"zap", -10.0], "faro_rosso": [&"ui_move", -6.0],
	"sirena": [&"go_arrow", -4.0], "sigillo_sparato": [&"throw", -6.0], "sigillo_muro": [&"bin_hit", -10.0],
	"pignorato": [&"hit_light", -4.0], "abbaio": [&"hit_heavy", -6.0], "scatto_segugio": [&"whoosh_heavy", -4.0],
	"morso": [&"hit_heavy", -2.0], "non_identificabile": [&"glint", -4.0],
}


func _event_sound(e: String) -> void:
	if not sound or not EVENT_SFX.has(e):
		return
	var s: Array = EVENT_SFX[e]
	var x := player.px
	if e == "gate_close" or e == "hack_done":
		x = _cam.x + View.W / 2.0
	Sfx.play_at(s[0], x, 0.05, s[1])


func _spark(x: float, y: float, sx: float, sy: float, life: int, color: Color, burst: bool = false) -> void:
	_sparks.append([x, y, sx, sy, life, life, color, burst])


## Le luci accese o spente: quelle dell'arena qui, il tempo e i lampi nei tratti che li hanno.
func _set_lights(on: bool) -> void:
	if arena != null:
		arena.set_lights(on)


## Il colore di una scintilla della scarica a metà vita `u` (0 appena nata, 1 alla fine): bianco, poi
## cyan, poi verde acqua.
static func _burst_color(u: float) -> Color:
	if u < 0.3:
		return C_TEXT.lerp(C_CYAN, u / 0.3)
	return C_CYAN.lerp(C_TEAL, (u - 0.3) / 0.7)


func _tick_sparks() -> void:
	var keep: Array = []
	for s: Array in _sparks:
		s[0] += s[2]
		s[1] += s[3]
		s[3] += 0.12
		s[4] -= 1
		if s[4] > 0:
			keep.append(s)
	_sparks = keep


func _draw_fx(n: Node2D) -> void:
	_fx_glow.clear()
	if arena == null:
		_draw_panel_glow()
	if hack_panel != "" and arena == null:
		_draw_contact(n)
	if arena == null:
		_draw_checkpoint_lamps(n)
		hazards.draw_pickups(n, tick, _visible_rect(), _fx_glow)
		processions.draw(n, tick, _visible_rect())
		favors.draw(n, tick, _visible_rect(), player)
		drones.draw(n, tick, _visible_rect(), _fx_glow)
		drones.draw_reach(n, tick, player, favors.wanted_drones())
		favors.draw_bubbles(n, _visible_rect(), player)
	_draw_arm_glow()
	for s: Array in _sparks:
		var a := float(s[4]) / float(s[5])
		var burst: bool = s[7]
		# Le scintille cyan sbiadiscono nel bianco, come una scarica; quelle del riavvio vanno dal bianco
		# al cyan al verde acqua, con la scia dietro.
		# Le scintille spente del braccio bloccato non schiariscono e non fanno alone: si spengono e basta.
		var dead: bool = s[6] == C_CYAN_DEAD or s[6] == C_CYAN_WEAK
		var c: Color = _burst_color(1.0 - a) if burst else (s[6] if a > 0.4 or dead else C_TEXT)
		if dead and a > 0.75:
			c = Color(s[6]).lightened(0.4)
		c.a = a
		var p := Vector2(roundf(s[0]), roundf(s[1]))
		var big := a >= 0.5
		if burst:
			n.draw_line(p, (p - Vector2(s[2], s[3]) * 3.0).round(), Color(c, a * 0.45), 1.0)
		n.draw_rect(Rect2(p, Vector2(2, 2) if big else Vector2.ONE), c)
		if s[6] != C_DIM and not dead:
			_fx_glow.halo(p, 3 if big else 2, Color(c, (0.55 if burst else 0.4) * a))


## Il bagliore dei pannelli (aloni in pixel art, solo disegno). Il cyan è solo di GIG: lo schermo si
## accende di cyan mentre il braccio lo forza, sempre di più man mano che la barra si riempie, e di
## verde quando il cancello è aperto; in attesa brilla solo il led rosso.
func _draw_panel_glow() -> void:
	for id: String in panels:
		if not grid.marks.has(id) or not gates.has(panels[id]["gate"]):
			continue
		var r := _panel_rect(id)
		if r.end.x < _vis_x0() - 20 or r.position.x > _vis_x1() + 20:
			continue
		var sr := Rect2(r.position.x + 4, r.position.y + 15, r.size.x - 8, 14)
		var led := Vector2(r.end.x - 8, r.position.y + 34)
		var c := sr.get_center()
		if hack_panel == id:
			var k := float(hack_t) / HACK_TICKS
			var flick := 0.5 + 0.5 * sin(tick * 0.6)
			_fx_glow.rect(sr, Color(C_CYAN, 0.10 + 0.14 * k))
			_fx_glow.halo(c, 24 + roundi(10.0 * k), Color(C_CYAN, 0.28 + 0.32 * k + 0.08 * flick))
			if (tick / 3) % 2 == 0:
				_fx_glow.halo(led, 3, Color(C_CYAN, 0.55))
		elif gates[panels[id]["gate"]]["timer"] > 0:
			var breath := 0.5 + 0.5 * sin(tick * 0.1)
			_fx_glow.rect(sr, Color(C_OK, 0.12))
			_fx_glow.halo(c, 26, Color(C_OK, 0.32 + 0.08 * breath))
			_fx_glow.halo(led, 3, Color(C_OK, 0.5))
		elif (tick / 45) % 3 != 2:
			_fx_glow.halo(led, 3, Color(C_LED_RED, 0.4))


## Il braccio cyber acceso (fuori dall'arena, dopo il riavvio): un alone cyan che respira sul pugno.
## Il velo della Vista su quello che si vede: la tinta verde acqua, righe di scansione appena accennate
## e i bordi più scuri. Segnaposto finché car-grafica non lo rifà.
func _draw_vista_veil(n: Node2D) -> void:
	if _vista_k <= 0.0:
		return
	var r := _visible_rect().grow(2)
	n.draw_rect(r, Color(C_VISTA_VEIL, C_VISTA_VEIL.a * _vista_k))
	var line := Color(C_CYAN, 0.05 * _vista_k)
	var y := floorf(r.position.y / 3.0) * 3.0 + float(tick % 3)
	while y < r.end.y:
		n.draw_rect(Rect2(r.position.x, y, r.size.x, 1), line)
		y += 3.0
	for i in 8:
		var e := Color(0.0, 0.04, 0.06, 0.07 * _vista_k)
		var w := 6.0 * (i + 1)
		n.draw_rect(Rect2(r.position.x, r.position.y, w, r.size.y), e)
		n.draw_rect(Rect2(r.end.x - w, r.position.y, w, r.size.y), e)
		n.draw_rect(Rect2(r.position.x, r.position.y, r.size.x, w * 0.6), e)
		n.draw_rect(Rect2(r.position.x, r.end.y - w * 0.6, r.size.x, w * 0.6), e)


## L'occhio destro di GIG acceso, sopra al velo: un punto cyan con l'alone.
func _draw_vista_eye(n: Node2D) -> void:
	if _vista_k <= 0.0 or not _body.visible or player.anim == null:
		return
	var h := Vector2i(5, -95)
	if player.anim.frame().points.has("head"):
		h = player.anim.frame().points["head"]
	var a := player.sprite_anchor()
	var eye := Vector2(a.x + player.facing * (h.x + VISTA_EYE.x), a.y + h.y + VISTA_EYE.y).round()
	var k := _vista_k * (0.85 + 0.15 * sin(tick * 0.2))
	n.draw_circle(eye, 6.0, Color(C_CYAN, 0.10 * k))
	n.draw_circle(eye, 3.0, Color(C_CYAN, 0.30 * k))
	n.draw_rect(Rect2(eye.x - 1, eye.y, 2, 1), Color(0.85, 1.0, 1.0, k))


func _draw_arm_glow() -> void:
	if arena != null or not _body.visible or player.anim == null or player.anim.sheet.id != &"gig":
		return
	var k := 0.5 + 0.5 * sin(tick * 0.08)
	_fx_glow.halo(_cyber_fist(), 5, Color(C_CYAN, 0.16 + 0.08 * k))
	if hack_panel != "":
		_fx_glow.halo(_cyber_fist(), 8, Color(C_CYAN, 0.35 + 0.15 * sin(tick * 0.6)))
