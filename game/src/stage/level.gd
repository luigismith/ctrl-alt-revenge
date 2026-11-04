class_name Level
extends Node2D
## Livello "Sotto la Linea" (§6): simulazione deterministica a tick, ondate con blocco della
## telecamera e muri invisibili, oggetti di scena, pioggia, effetti, HUD, pausa e CONTINUA?.
##
## Un tick di simulazione (step) fa, in quest'ordine:
##   ingressi → [congelamento KO / rallentatore] → attori (per uid) → colpi → oggetti di scena →
##   ondate → effetti e pioggia → telecamera → interfaccia → nodi → hash dello stato.
## Il rallentatore e i congelamenti di debug (F2-F4) decidono solo se chiamare step():
## i replay registrano un InputFrame per step, quindi restano validi.

signal finished(result: Dictionary)
signal quit_to_title
signal restart_requested
signal game_over

enum Phase { PLAY, CLEAR, CONTINUE, OVER, DONE }

const LEVEL_JSON := "res://data/levels/sotto_la_linea.json"
const VIEW_W := 384
## Muri invisibili a questa distanza dai bordi della vista: mezza larghezza di uno sprite in
## guardia (22-24 px) più 2, così nessuno resta tagliato a metà dal bordo dello schermo.
const WALL_MARGIN := 26.0
const KO_FREEZE_TICKS := 26
const KO_SLOWMO_TICKS := 24
const KO_SLOWMO_RATE := 0.35
const CLEAR_TICKS := 200
const GO_ARROW_TICKS := 240
const CONTINUE_TICKS := 60

## Opzioni impostate prima di entrare nell'albero (configure).
var level_seed: int = 1
var start_x: float = -1.0
var start_y: float = -1.0
var input: PlayerInput
var sound_enabled: bool = true
var auto_tick: bool = true
var show_card: bool = true
var record_path: String = ""

var data: Dictionary = {}
var level_width: int = 1920
var band_top: float = 150.0
var band_bottom: float = 208.0
var tick: int = 0
## Tick in cui gli attori si sono davvero mossi (senza congelamenti).
var actor_ticks: int = 0
var phase: Phase = Phase.PLAY
var paused: bool = false
var director := AttackDirector

var rng: RandomNumberGenerator = RandomNumberGenerator.new()
var combat: CombatSystem
var camera: StageCamera
var backdrop: Backdrop
var fighters: Array[Fighter] = []
var props: Array[Prop] = []
var player: Gig

var cam_node: Camera2D
var world: Node2D
var fx: FxLayer
var rain: Rain
var shadows: ShadowLayer
var hud: Hud
var overlay: LevelOverlay
var debug_overlay: DebugOverlay
var _back_layer: CanvasLayer
var _front_layer: CanvasLayer

var waves: Array[Dictionary] = []
var wave_index: int = 0
var active_wave: Dictionary = {}
var waves_cleared: int = 0
var zone_cleared: bool = false
var _wave_tick: int = 0
var _pending: Array[Dictionary] = []

var _uid: int = 0
var _attack_serial: int = 0
var _freeze: int = 0
var _slowmo: int = 0
## Il tick in corso è un tick del rallentatore (anche l'ultimo, quando _slowmo arriva a 0).
var _slowmo_step: bool = false
var _slow_acc: float = 0.0
var _clear_tick: int = 0
var _continue_timer: int = 0
var _hash: HashingContext
var _final_hash: String = ""
var _debug_slow: bool = false
var _debug_freeze: bool = false
var _debug_step: bool = false
var _slow_counter: int = 0
var _replay_reported: bool = false
## Uscita dalla pausa verso il titolo o una nuova partita: il livello non avanza più.
var _leaving: bool = false
## Gli avvisi sullo sfondo si segnalano una volta sola per sessione.
static var _backdrop_warned: bool = false


## Da chiamare prima di aggiungere il livello all'albero.
func configure(opts: Dictionary) -> void:
	level_seed = int(opts.get("seed", 1))
	start_x = float(opts.get("start_x", -1.0))
	start_y = float(opts.get("start_y", -1.0))
	input = opts.get("input", PlayerInput.live())
	sound_enabled = bool(opts.get("sound", true))
	auto_tick = bool(opts.get("auto_tick", true))
	show_card = bool(opts.get("card", true))
	record_path = str(opts.get("record", ""))


func _ready() -> void:
	name = "Level"
	if input == null:
		input = PlayerInput.live()
	rng.seed = level_seed
	director.reset()
	combat = CombatSystem.new(self)
	_hash = HashingContext.new()
	_hash.start(HashingContext.HASH_SHA256)
	_load_data()
	camera = StageCamera.new(level_seed)
	_build_nodes()
	_build_props()
	_spawn_player()
	_init_camera_and_waves()
	if record_path != "":
		var r := Replay.new()
		r.level_seed = level_seed
		if start_x >= 0.0:
			r.start = {"x": start_x, "y": player.py}
		input.recorder = r
	if show_card:
		overlay.show_card(str(data.get("title", "1 · SOTTO LA LINEA")))
	if sound_enabled:
		# Dopo un GAME OVER o una pausa la musica potrebbe essere ancora abbassata.
		Music.duck(false)
		Music.play(&"stage1")
	_sync_all()


func _load_data() -> void:
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(LEVEL_JSON))
	if not (d is Dictionary):
		push_error("Dati del livello non validi: %s (si usano i valori predefiniti, senza ondate)" % LEVEL_JSON)
	data = d if d is Dictionary else {}
	level_width = int(data.get("width", 1920))
	var band: Array = data.get("floor_band", [150, 208])
	band_top = float(band[0])
	band_bottom = float(band[1])
	for w: Variant in data.get("waves", []):
		waves.append(w as Dictionary)


func _build_nodes() -> void:
	cam_node = Camera2D.new()
	cam_node.anchor_mode = Camera2D.ANCHOR_MODE_FIXED_TOP_LEFT
	cam_node.position_smoothing_enabled = false
	cam_node.drag_horizontal_enabled = false
	cam_node.drag_vertical_enabled = false
	add_child(cam_node)
	cam_node.make_current()

	_back_layer = CanvasLayer.new()
	_back_layer.name = "Sfondo"
	_back_layer.layer = -1
	add_child(_back_layer)
	_front_layer = CanvasLayer.new()
	_front_layer.name = "PrimoPiano"
	_front_layer.layer = 1
	add_child(_front_layer)

	world = Node2D.new()
	world.name = "Mondo"
	add_child(world)
	shadows = ShadowLayer.new()
	shadows.name = "Ombre"
	shadows.level = self
	shadows.z_index = 60
	world.add_child(shadows)
	fx = FxLayer.new()
	fx.name = "Effetti"
	fx.load_defs()
	world.add_child(fx)
	debug_overlay = DebugOverlay.new()
	debug_overlay.level = self
	debug_overlay.z_index = 3000
	debug_overlay.visible = OS.is_debug_build() and Game.options.debug_boxes
	world.add_child(debug_overlay)
	_build_lights()

	backdrop = Backdrop.new()
	var env_path := str(data.get("env", "res://assets/env/sotto_la_linea/layers.json"))
	if not backdrop.load_json(env_path):
		if not backdrop.errors.is_empty():
			push_warning("Sfondo non valido (%s): uso il segnaposto" % "; ".join(backdrop.errors))
		backdrop.use_placeholder(level_seed)
	elif not backdrop.warnings.is_empty() and OS.is_debug_build() and not _backdrop_warned:
		_backdrop_warned = true
		push_warning("Sfondo (%s): %s" % [env_path, "; ".join(backdrop.warnings)])
	backdrop.build(_back_layer, _front_layer, level_seed)

	rain = Rain.new()
	rain.name = "Pioggia"
	rain.z_index = 50
	rain.setup(level_seed, fx, Vector2(band_top, band_bottom))
	_front_layer.add_child(rain)
	# Gli spruzzi a terra stanno nel mondo, con le ombre e sotto gli attori.
	var splashes := Node2D.new()
	splashes.name = "SpruzziPioggia"
	splashes.z_index = 61
	world.add_child(splashes)
	rain.set_splash_canvas(splashes, true)

	var hud_layer := CanvasLayer.new()
	hud_layer.name = "Interfaccia"
	hud_layer.layer = 5
	add_child(hud_layer)
	hud = Hud.new()
	hud.level = self
	hud_layer.add_child(hud)
	overlay = LevelOverlay.new()
	hud_layer.add_child(overlay)


func _next_uid() -> int:
	_uid += 1
	return _uid


func next_attack_serial() -> int:
	_attack_serial += 1
	return _attack_serial


func _build_props() -> void:
	for pv: Variant in data.get("props", []):
		var p: Dictionary = pv
		match str(p.get("type", "")):
			"bin":
				var b := PropBin.new()
				b.setup_bin(self, _next_uid(), float(p.get("x", 1050)), float(p.get("y", 162)))
				_add_prop(b)
			"cable":
				var c := PropCable.new()
				c.setup_cable(self, _next_uid(), float(p.get("x0", 1230)), float(p.get("x1", 1270)))
				_add_prop(c)


func _add_prop(p: Prop) -> void:
	props.append(p)
	world.add_child(p)


func spawn_pickup(x: float, y: float, pop: float) -> void:
	var a := PropApple.new()
	a.setup_apple(self, _next_uid(), x, clampf(y, band_top, band_bottom), pop)
	_add_prop(a)


func _spawn_player() -> void:
	player = Gig.new()
	player.setup_gig(self, _next_uid())
	var ps: Array = data.get("player_start", [56, 182])
	player.px = start_x if start_x >= 0.0 else float(ps[0])
	player.py = start_y if start_y >= 0.0 else float(ps[1])
	fighters.append(player)
	world.add_child(player)


## Crea un nemico che entra da fuori schermo (side +1 da destra, -1 da sinistra).
func spawn_thug(type_id: StringName, side: int, y: float, wave_id: String) -> Thug:
	var t := Thug.new()
	t.setup_thug(type_id, self, _next_uid(), rng.randi())
	t.wave_id = wave_id
	t.px = camera.x + VIEW_W + 28.0 if side > 0 else camera.x - 28.0
	t.py = clampf(y, band_top, band_bottom)
	fighters.append(t)
	world.add_child(t)
	t.enter_from(camera.x + VIEW_W - 56.0 if side > 0 else camera.x + 56.0)
	t.sync_visual()
	return t


func _init_camera_and_waves() -> void:
	camera.min_x = 0
	camera.max_x = level_width - VIEW_W
	camera.snap_to(player.px)
	# Partendo oltre lo schermo di un'ondata, quell'ondata conta come già finita.
	while wave_index < waves.size() and player.px > int(waves[wave_index].get("camera_x", 0)) + VIEW_W:
		wave_index += 1
		waves_cleared += 1
	_update_camera_limits()
	camera.x = clampi(camera.x, camera.min_x, camera.max_x)


func _update_camera_limits() -> void:
	if not active_wave.is_empty():
		var lx := int(active_wave.get("camera_x", 0))
		camera.min_x = lx
		camera.max_x = lx
		return
	camera.min_x = 0
	camera.max_x = level_width - VIEW_W
	if wave_index < waves.size():
		camera.max_x = mini(camera.max_x, int(waves[wave_index].get("camera_x", camera.max_x)))


# --- Tick ----------------------------------------------------------------------------------------

func _physics_process(_delta: float) -> void:
	if not auto_tick or _leaving:
		return
	if OS.is_debug_build():
		_debug_keys()
	match phase:
		Phase.CONTINUE:
			_continue_tick()
			return
		Phase.OVER:
			overlay.tick()
			if overlay.game_over_ticks > 150:
				phase = Phase.DONE
				game_over.emit()
			return
		Phase.DONE:
			return
	if paused:
		_pause_menu_tick()
		return
	if input.mode == PlayerInput.Mode.LIVE and Input.is_action_just_pressed(&"pause") and phase == Phase.PLAY:
		_open_pause()
		return
	if _debug_freeze and not _debug_step:
		return
	_debug_step = false
	if _debug_slow:
		_slow_counter += 1
		if _slow_counter % 4 != 0:
			return
	step()
	_after_step()


## Un tick di simulazione.
func step() -> void:
	if phase == Phase.DONE or phase == Phase.OVER:
		return
	var frame := input.next_frame(tick)
	player.feed_input(frame, tick)
	var move := true
	_slowmo_step = false
	if _freeze > 0:
		_freeze -= 1
		move = false
		if _freeze == 0:
			_slowmo = KO_SLOWMO_TICKS
			_slow_acc = 0.0
	elif _slowmo > 0:
		_slowmo_step = true
		_slowmo -= 1
		_slow_acc += KO_SLOWMO_RATE
		if _slow_acc >= 1.0:
			_slow_acc -= 1.0
		else:
			move = false
	if move:
		_actors_tick()
	# Gli effetti si animano anche durante il congelamento del KO (lampi e scintille).
	fx.tick()
	camera.tick_shake()
	_update_camera()
	hud.tick()
	overlay.tick()
	var finish_now := false
	if phase == Phase.CLEAR:
		_clear_tick += 1
		finish_now = _clear_tick == CLEAR_TICKS
	_sync_all()
	# final_hash() chiude il contesto: da lì in poi l'hash non cambia più.
	if _final_hash == "":
		_hash.update(var_to_bytes(state_snapshot()))
	tick += 1
	# La fine del livello si emette dopo l'hash del tick: chi la riceve e stampa final_hash()
	# ottiene lo stesso valore dei test, che leggono l'hash dopo l'ultimo step.
	if finish_now:
		_finish()


func _actors_tick() -> void:
	for f in fighters:
		f.sim_tick()
	combat.resolve()
	for p in props:
		p.sim_tick()
	_update_waves()
	rain.tick(camera.x)
	_cleanup()
	actor_ticks += 1


func _cleanup() -> void:
	for i in range(fighters.size() - 1, -1, -1):
		var f := fighters[i]
		if f.removed and f != player:
			director.forget(f, tick)
			fighters.remove_at(i)
			f.queue_free()
	for i in range(props.size() - 1, -1, -1):
		if props[i].removed:
			props[i].queue_free()
			props.remove_at(i)


func _update_camera() -> void:
	if player.state != Fighter.State.DEAD:
		camera.follow(player.px)
	camera.settle()


func _after_step() -> void:
	if _replay_reported or not input.replay_finished(tick):
		return
	_replay_reported = true
	if Game.options.print_hash or Game.options.quit_at_end:
		print("Replay finito al tick %d, hash %s" % [tick, final_hash()])
	if Game.options.quit_at_end:
		_save_recording()
		print("DONE")
		Game.quit_clean(0)


# --- Ondate --------------------------------------------------------------------------------------

func _update_waves() -> void:
	if active_wave.is_empty():
		if wave_index < waves.size() and camera.x >= int(waves[wave_index].get("camera_x", 0)):
			_start_wave(waves[wave_index])
		return
	_wave_tick += 1
	var still: Array[Dictionary] = []
	for s in _pending:
		if _wave_tick >= int(s.get("delay", 0)):
			spawn_thug(StringName(str(s.get("type", "thug_punk"))), int(s.get("side", 1)), float(s.get("y", 180)), str(active_wave.get("id", "")))
		else:
			still.append(s)
	_pending = still
	# L'ondata finisce quando l'ultimo nemico è sparito (dopo la caduta e il lampeggio),
	# non appena va KO: "VAI" e "ZONA LIBERATA" non compaiono mentre il corpo vola ancora.
	if _pending.is_empty() and _freeze == 0 and _slowmo == 0 and wave_enemies_present() == 0:
		_finish_wave()


func _start_wave(w: Dictionary) -> void:
	active_wave = w
	_wave_tick = 0
	_pending.clear()
	for s: Variant in w.get("spawns", []):
		_pending.append(s as Dictionary)
	_update_camera_limits()
	if sound_enabled and str(w.get("music_layer", "")) != "":
		Music.set_layer(StringName(str(w["music_layer"])), true)
	Game.count(&"waves_started")


func _finish_wave() -> void:
	var w := active_wave
	active_wave = {}
	wave_index += 1
	waves_cleared += 1
	Game.count(&"waves_cleared")
	if sound_enabled and str(w.get("music_layer", "")) != "":
		Music.set_layer(StringName(str(w["music_layer"])), false)
	if bool(w.get("final", false)):
		zone_cleared = true
		phase = Phase.CLEAR
		_clear_tick = 0
		overlay.clear_ticks = 0
		if sound_enabled:
			Music.play_jingle(&"clear")
		# Dopo l'ultima ondata la telecamera resta ferma sull'arena (i limiti non cambiano).
		return
	overlay.go_ticks = GO_ARROW_TICKS
	if sound_enabled:
		Sfx.play(&"go_arrow")
	_update_camera_limits()


func wave_enemies_alive() -> int:
	var n := 0
	var wid := str(active_wave.get("id", ""))
	for f in fighters:
		if f is Thug and (f as Thug).wave_id == wid and not f.dead and not f.removed:
			n += 1
	return n


## Nemici dell'ondata ancora nel mondo, compresi quelli KO che non sono ancora spariti.
func wave_enemies_present() -> int:
	var n := 0
	var wid := str(active_wave.get("id", ""))
	for f in fighters:
		if f is Thug and (f as Thug).wave_id == wid and not f.removed:
			n += 1
	return n


func on_fighter_ko(f: Fighter, _attacker: Entity) -> void:
	if f is Thug:
		var t := f as Thug
		Game.add_score(t.data.ko_score)
		Game.count(StringName("ko_" + String(t.data.id)))
		if sound_enabled:
			Sfx.play(&"ko")
		director.forget(t, tick)
		if not active_wave.is_empty() and t.wave_id == str(active_wave.get("id", "")) and _pending.is_empty() \
				and wave_enemies_alive() == 0:
			_freeze = KO_FREEZE_TICKS
			add_shake(0.45)
			fx.spawn(&"ko_flash", t.px, t.py - t.ph - 44.0, 1, 2900)
			Game.count(&"ko_freezes")
	elif f == player:
		Game.count(&"gig_ko")
		player.release_grab(false)


## Chiamata da GIG alla fine del lampeggio dopo il KO.
func on_player_died() -> void:
	var left := Game.lose_life()
	# A zona già liberata (KO quasi insieme a quello dell'ultimo nemico) GIG rientra comunque,
	# senza CONTINUA?: la fase resta CLEAR e il livello finisce come sempre.
	if left > 0 or zone_cleared:
		player.respawn()
		Game.count(&"respawns")
	else:
		phase = Phase.CONTINUE
		_continue_timer = 0
		overlay.continue_count = 9
		if sound_enabled:
			Music.duck(true)


func on_enemy_hit(t: Thug) -> void:
	hud.show_target(t)


func _finish() -> void:
	phase = Phase.DONE
	_save_recording()
	# Con --quit-at-end l'hash lo stampa Main; senza, lo si stampa qui (anche senza replay).
	if Game.options.print_hash and not Game.options.quit_at_end:
		print("Livello finito al tick %d, hash %s" % [tick, final_hash()])
	finished.emit({"score": Game.score, "ticks": tick, "time_s": tick / 60.0})


# --- Pausa e CONTINUA? ----------------------------------------------------------------------------

func _open_pause() -> void:
	paused = true
	overlay.paused = true
	overlay.pause_index = 0
	overlay.queue_redraw()
	if sound_enabled:
		Sfx.play(&"ui_pause")
		Music.duck(true)


func _close_pause() -> void:
	paused = false
	overlay.paused = false
	overlay.queue_redraw()
	# I tasti tenuti nel menu (ATTACCO per confermare, A del joypad) non diventano pressioni
	# nel primo tick di gioco.
	input.resync()
	if sound_enabled:
		Music.duck(false)


## RICOMINCIA ed ESCI AL TITOLO: il menu sparisce ma il livello resta fermo durante la
## dissolvenza (la schermata seguente toglie l'abbassamento della musica).
func _leave_from_pause() -> void:
	_leaving = true
	overlay.paused = false
	overlay.queue_redraw()


func _pause_menu_tick() -> void:
	overlay.queue_redraw()
	if _menu_pressed(&"move_up"):
		overlay.pause_index = posmod(overlay.pause_index - 1, LevelOverlay.PAUSE_ITEMS.size())
		_ui_sfx(&"ui_move")
	elif _menu_pressed(&"move_down"):
		overlay.pause_index = posmod(overlay.pause_index + 1, LevelOverlay.PAUSE_ITEMS.size())
		_ui_sfx(&"ui_move")
	elif Input.is_action_just_pressed(&"menu_back"):
		_close_pause()
	elif Input.is_action_just_pressed(&"menu_confirm") or Input.is_action_just_pressed(&"attack"):
		_ui_sfx(&"ui_confirm")
		match overlay.pause_index:
			0:
				_close_pause()
			1:
				_leave_from_pause()
				restart_requested.emit()
			2:
				_leave_from_pause()
				quit_to_title.emit()


func _continue_tick() -> void:
	overlay.tick()
	_continue_timer += 1
	if Input.is_action_just_pressed(&"menu_confirm") or Input.is_action_just_pressed(&"attack"):
		_ui_sfx(&"ui_confirm")
		overlay.continue_count = -1
		Game.continue_run()
		player.respawn()
		phase = Phase.CLEAR if zone_cleared else Phase.PLAY
		# Il tasto premuto per continuare non deve diventare un attacco al primo tick.
		input.resync()
		if sound_enabled:
			Music.duck(false)
		return
	if _continue_timer >= CONTINUE_TICKS:
		_continue_timer = 0
		overlay.continue_count -= 1
		if overlay.continue_count < 0:
			phase = Phase.OVER
			overlay.game_over_ticks = 0
			if sound_enabled:
				# Si sfuma restando abbassati; il titolo e il livello seguente tolgono l'abbassamento.
				Music.stop(1.0)


func _menu_pressed(action: StringName) -> bool:
	return Input.is_action_just_pressed(action)


func _ui_sfx(n: StringName) -> void:
	if sound_enabled:
		Sfx.play(n)


func _debug_keys() -> void:
	if Input.is_action_just_pressed(&"debug_boxes"):
		debug_overlay.visible = not debug_overlay.visible
	if Input.is_action_just_pressed(&"debug_slow"):
		_debug_slow = not _debug_slow
	if Input.is_action_just_pressed(&"debug_freeze"):
		_debug_freeze = not _debug_freeze
	if Input.is_action_just_pressed(&"debug_step") and _debug_freeze:
		_debug_step = true
	if Input.is_action_just_pressed(&"debug_lights"):
		set_lights(not lights_on)


# --- Servizi per gli attori ---------------------------------------------------------------------

func view_left() -> float:
	return float(camera.x)


func view_right() -> float:
	return float(camera.x + VIEW_W)


## Muri invisibili: i bordi della vista (bloccata durante le ondate) e del livello.
func clamp_x(_e: Entity, x: float) -> float:
	var lo := maxf(view_left() + WALL_MARGIN, WALL_MARGIN)
	var hi := minf(view_right() - WALL_MARGIN, level_width - WALL_MARGIN)
	return clampf(x, lo, hi)


## Vero durante i 26 tick di congelamento dopo l'ultimo KO di un'ondata.
func ko_freeze_active() -> bool:
	return _freeze > 0


## Tick trascorsi dall'inizio del congelamento del KO finale (0 nel tick del KO); -1 fuori.
func ko_freeze_elapsed() -> int:
	return KO_FREEZE_TICKS - _freeze if _freeze > 0 else -1


## Vero per tutta la sequenza del KO finale: congelamento più rallentatore (26 + 24 tick),
## compreso il tick che consuma l'ultimo passo del rallentatore.
func ko_sequence_active() -> bool:
	return _freeze > 0 or _slowmo > 0 or _slowmo_step


func add_shake(trauma: float) -> void:
	camera.add_trauma(trauma)


func enemies() -> Array[Thug]:
	var out: Array[Thug] = []
	for f in fighters:
		if f is Thug and not f.removed:
			out.append(f as Thug)
	return out


## Nemico afferrabile davanti a GIG (§5): entro 18 px in orizzontale e 4 in profondità,
## che non attacca, non è in aria e non è a terra.
func find_grab_target(g: Gig) -> Fighter:
	var best: Fighter = null
	var best_d := 1e9
	for t in enemies():
		if t.dead or t.invuln > 0 or t.is_airborne():
			continue
		if not (t.state == Fighter.State.IDLE or t.state == Fighter.State.WALK or t.state == Fighter.State.HURT):
			continue
		var dx := t.px - g.px
		if dx * g.facing < 0.0:
			continue
		if absf(dx) > Gig.GRAB_RANGE_X or absf(t.py - g.py) > Gig.GRAB_RANGE_Y:
			continue
		if absf(dx) < best_d:
			best_d = absf(dx)
			best = t
	return best


## Bersagli dei colpi in ordine di uid: combattenti e oggetti di scena colpibili.
func hittables() -> Array[Entity]:
	var out: Array[Entity] = []
	for f in fighters:
		out.append(f)
	for p in props:
		if p is PropBin:
			out.append(p)
	out.sort_custom(func(a: Entity, b: Entity) -> bool: return a.uid < b.uid)
	return out


func shadow_casters() -> Array[Entity]:
	var out: Array[Entity] = []
	for p in props:
		out.append(p)
	for f in fighters:
		out.append(f)
	return out


# --- Disegno, stato, registrazione ---------------------------------------------------------------

func _sync_all() -> void:
	for f in fighters:
		f.sync_visual()
	for p in props:
		p.sync_visual()
	cam_node.position = Vector2(camera.x + camera.shake.x, camera.shake.y)
	_back_layer.offset = Vector2(camera.shake)
	_front_layer.offset = Vector2(camera.shake)
	backdrop.update(camera.x, tick)
	_update_lights()
	shadows.queue_redraw()
	if debug_overlay.visible:
		debug_overlay.queue_redraw()


## Stato essenziale della simulazione, per l'hash di determinismo.
func state_snapshot() -> Array:
	var s: Array = [tick, actor_ticks, Game.score, camera.x, wave_index, _freeze, _slowmo, director.holder_uid]
	for f in fighters:
		s.append_array([f.uid, f.state, f.px, f.py, f.ph, f.hp, f.facing, String(f.anim.name), f.anim.index, f.hitstop, f.invuln])
	for p in props:
		s.append_array([p.uid, p.px, p.py, p.ph, p.removed])
	return s


## Hash SHA-256 di tutti gli stati dall'inizio del livello (si calcola una volta sola).
func final_hash() -> String:
	if _final_hash == "":
		_final_hash = _hash.finish().hex_encode()
	return _final_hash


func _save_recording() -> void:
	if input.recorder == null or record_path == "":
		return
	var path := record_path
	if not path.is_absolute_path() and not path.begins_with("res://") and not path.begins_with("user://"):
		path = "user://" + path
	var err := input.recorder.save_file(path)
	if err == OK:
		print("Replay salvato: %s (%d tick)" % [path, input.recorder.length])
	else:
		push_warning("Impossibile salvare il replay in %s" % path)


func _exit_tree() -> void:
	if phase != Phase.DONE:
		_save_recording()


# --- Luci dinamiche ------------------------------------------------------------------------------

## Luci del livello (campo "lights" del JSON): illuminano solo gli attori con la normal map (maschera
## Fighter.LIGHT_MASK_ACTORS), mai gli sfondi, che hanno la luce già dipinta. Sono solo disegno: non toccano la
## simulazione (i replay non cambiano). F5 (build di debug) o --no-lights le spengono.
## Tipi: "neon" (insegna dello sfondo, pulsa con i neon), "lamp" (lampada sulla travata del primo piano: si
## sposta con la sua parallasse), "cable" (scintille del cavo: si accende nei fotogrammi del lampo), "lightning"
## (lampo del temporale, sopra la vista, raro e deterministico).
var lights_on: bool = true
var _lights: Array[Dictionary] = []
var _lights_root: Node2D


func _build_lights() -> void:
	_lights_root = Node2D.new()
	_lights_root.name = "Luci"
	world.add_child(_lights_root)
	var tex := GradientTexture2D.new()
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 128
	tex.height = 128
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	tex.gradient = g
	var i := 0
	for v: Variant in data.get("lights", []):
		if not (v is Dictionary):
			continue
		var d: Dictionary = v
		var l := PointLight2D.new()
		l.texture = tex
		l.color = Color.html(str(d.get("color", "#ffffff")))
		l.energy = float(d.get("energy", 0.5))
		l.texture_scale = float(d.get("radius", 100)) / 64.0
		l.height = float(d.get("height", 30))
		l.range_item_cull_mask = Fighter.LIGHT_MASK_ACTORS
		l.blend_mode = Light2D.BLEND_MODE_ADD
		l.position = Vector2(float(d.get("x", 0)), float(d.get("y", 0)))
		_lights_root.add_child(l)
		_lights.append({"light": l, "kind": str(d.get("kind", "neon")), "energy": l.energy,
			"x": l.position.x, "scroll": float(d.get("scroll", 1.0)), "phase": float(i) * 1.7})
		i += 1
	set_lights(not Game.options.no_lights)


func set_lights(on: bool) -> void:
	lights_on = on
	for e in _lights:
		(e["light"] as PointLight2D).enabled = on


func _update_lights() -> void:
	if not lights_on:
		return
	for e in _lights:
		var l: PointLight2D = e["light"]
		var base: float = e["energy"]
		match String(e["kind"]):
			"neon":
				# stessa pulsazione lenta dei neon dello sfondo (Backdrop._levels)
				l.energy = base * (0.9 + 0.1 * sin(tick * 0.035 + float(e["phase"])))
			"lamp":
				# la lampada sta sulla travata con parallasse "scroll": nel mondo si sposta con la telecamera
				l.position.x = float(e["x"]) - (float(e["scroll"]) - 1.0) * camera.x
			"cable":
				l.energy = base * _cable_flash()
			"lightning":
				l.position.x = camera.x + 192.0
				l.energy = base * _lightning(tick)


## 1 nei fotogrammi del lampo del cavo (0 e 3 del ciclo di 6), poco nel resto.
func _cable_flash() -> float:
	for p in props:
		if p is PropCable:
			var k := p.anim.index % 6
			return 1.0 if k == 0 or k == 3 else 0.12
	return 0.0


## Lampo del temporale: ogni 9 s circa (deterministico, dal tick) due bagliori ravvicinati.
func _lightning(t: int) -> float:
	var period := 540
	var k := t % period
	var start := 120 + (t / period * 197) % 240
	var u := k - start
	if u < 0 or u > 14:
		return 0.0
	if u < 3:
		return 1.0
	if u < 6:
		return 0.2
	if u < 9:
		return 0.75
	return 0.75 * float(14 - u) / 5.0
