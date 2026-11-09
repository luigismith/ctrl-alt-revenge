extends RefCounted
## Test automatici del gameplay. Si lanciano con run_tests.gd (vedi lì).
## Ogni check stampa "ok   - nome" oppure "FAIL - nome (dettagli)".

const Harness := preload("res://tests/harness.gd")
## Varianti dei fogli: per i tempi degli attacchi valgono gli AttackData del personaggio base.
## Le varianti e i nemici che usano gli attacchi di un altro personaggio (il rider tira il jab del punk).
const SHEET_BASE := {&"gig_spento": &"gig", &"rider": &"thug_punk", &"esattore": &"thug_bruiser"}
const REPLAY_DIR := "res://tests/replays"

var root: Node
var count: int = 0
var failures: int = 0


func check(condition: bool, test_name: String, detail: String = "") -> void:
	count += 1
	if condition:
		print("ok   - " + test_name)
	else:
		failures += 1
		printerr("FAIL - %s%s" % [test_name, (" (" + detail + ")") if detail != "" else ""])


func run(tree_root: Node) -> bool:
	root = tree_root
	_test_settings()
	_test_frame_anim()
	_test_retime()
	_test_replay_format()
	_test_combo_chain()
	_test_combo_miss_and_buffer()
	_test_hitstop()
	_test_grab_conditions()
	_test_thrown_body()
	_test_throw_release()
	_test_enemy_attacks()
	_test_bruiser_armor()
	_test_lives()
	_test_attack_director()
	_test_ko_freeze()
	_test_ko_visibility()
	_test_air_hit_lands()
	_test_clear_and_last_life()
	_test_grab_at_wall()
	_test_knee_ko()
	_test_armor_keeps_turn()
	_test_enter_not_hittable()
	_test_combo_reset_on_hurt()
	_test_one_arm()
	_test_replay_end()
	_test_credits_glyphs()
	_test_json_files()
	_test_palette_variants()
	_test_replays()
	_test_platform()
	_test_arm_locked()
	_test_room_arena()
	_test_room_hacking()
	_test_hazards()
	_test_room_hazards()
	_test_drones()
	_test_drone_sprites()
	_test_procession_sprites()
	_test_favors()
	_test_firme()
	_test_breakables()
	_test_scene_hook()
	_test_processions()
	_test_rider()
	_test_esattore()
	_test_messo()
	_test_prologue_lives()
	_test_ldtk()
	_test_rider_frenzy()
	_test_prologue()
	_test_prologue_v2()
	_test_prologue_interiors()
	_test_scene_files()
	_test_pignoramento()
	_test_rinforzi()
	_test_scene_voices()
	_test_scene_thoughts()
	_test_scene_mural()
	_test_scene_writing()
	_test_title_menu()
	_test_new_game_chain()
	return failures == 0


# --- Il menu del titolo ----------------------------------------------------------------------------

## NUOVA PARTITA, i CAPITOLI col sottomenu e INDIETRO, le voci del PC e del browser. Il titolo non
## entra nell'albero: _ready (piani, musica, Wind Day) non gira, si prova solo la logica delle voci.
func _test_title_menu() -> void:
	var t := TitleScreen.new()
	t.web = false
	check(t.items() == PackedStringArray(["NUOVA PARTITA", "CAPITOLI", "STANZA DI PROVA", "CREDITI", "ESCI"]), "Titolo: le voci del PC", str(t.items()))
	check(t.choose(0) == &"new_game", "Titolo: NUOVA PARTITA dà new_game")
	check(t.choose(2) == &"test_room" and t.choose(3) == &"show_credits" and t.choose(4) == &"quit_game", "Titolo: stanza di prova, crediti ed esci")
	check(t.choose(1) == &"" and t.in_chapters and t._index == 0, "Titolo: CAPITOLI apre il sottomenu, sulla prima voce")
	check(t.items() == PackedStringArray(["PROLOGO", "2 · IL WIND DAY", "INDIETRO"]), "Titolo: i capitoli e INDIETRO", str(t.items()))
	check(t.choose(0) == &"prologue" and t.choose(1) == &"start_game", "Titolo: i capitoli danno prologue e start_game")
	check(t.choose(2) == &"" and not t.in_chapters and t._index == 1, "Titolo: INDIETRO torna al menu, su CAPITOLI")
	t.web = true
	check(t.items() == PackedStringArray(["NUOVA PARTITA", "CAPITOLI", "CREDITI"]), "Titolo: nel browser niente stanza di prova né ESCI", str(t.items()))
	check(t.choose(2) == &"show_credits", "Titolo: nel browser la terza voce è CREDITI")
	t.free()


## NUOVA PARTITA in main.gd, a tick finti: titolo → prologo (con le righe di dopo) → alla fine la dissolvenza
## lenta, con la musica che sfuma → lo slice, con la sua scheda e coi tasti, anche se il prologo l'ha
## giocato il pilota → la dissolvenza torna corta.
func _test_new_game_chain() -> void:
	# La telecamera larga è normale; --camera-stretta la spegne.
	check(SessionOptions.parse(PackedStringArray([])).wide_camera
		and not SessionOptions.parse(PackedStringArray(["--camera-stretta"])).wide_camera,
		"Opzioni: la telecamera larga è accesa senza opzioni, --camera-stretta la spegne")
	var saved := Game.options
	Game.options = SessionOptions.parse(PackedStringArray(["--autopilot", "stanza"]))
	Game.options.room = false
	Game.options.autostart = false
	var m: Node = load("res://scenes/main.tscn").instantiate()
	root.add_child(m)
	var tick := func(n: int) -> void:
		for i in n:
			m._physics_process(0.0)
	check(m._screen is TitleScreen, "Nuova partita: si parte dal titolo", str(m._screen))
	m._go(m._start_new_game)
	tick.call(m.FADE_TICKS)
	var p := m._screen as Prologue
	check(p != null and p.next_title == m.AFTER_PROLOGUE and p.pilot != null,
		"Nuova partita: dopo la dissolvenza il prologo, che sa cosa viene dopo", str(m._screen))
	tick.call(m.FADE_TICKS)
	check(m._fade_dir == 0, "Nuova partita: la dissolvenza d'entrata nel prologo finisce")
	if p != null:
		p.prologue_finished.emit({"ticks": 1, "prologue": true})
	check(m._fade_len == m.FADE_SLOW and m._fade_dir == 1 and Music.current_track() == &"",
		"Nuova partita: a fine prologo la dissolvenza lenta, e la musica sfuma", "%d tick, musica %s" % [m._fade_len, Music.current_track()])
	tick.call(m.FADE_SLOW / 2)
	var half: float = m._fade.color.a
	tick.call(m.FADE_SLOW - m.FADE_SLOW / 2 - 1)
	check(m._screen == p and half > 0.4 and half < 0.6, "Nuova partita: il prologo resta finché lo schermo non è nero", "a metà %.2f" % half)
	tick.call(1)
	var lvl := m._screen as Level
	check(lvl != null and lvl.overlay.card_title == "2 · IL WIND DAY" and lvl.overlay.card_art == "stage_card_2" and lvl.input.mode == PlayerInput.Mode.LIVE,
		"Nuova partita: poi lo slice, con la scheda «2 · IL WIND DAY» e coi tasti", str(m._screen))
	tick.call(m.FADE_SLOW)
	check(m._fade_dir == 0 and m._fade.color.a == 0.0 and m._fade_len == m.FADE_TICKS,
		"Nuova partita: lo slice entra in 50 tick, poi le dissolvenze tornano corte", "%d, %.2f" % [m._fade_len, m._fade.color.a])
	root.remove_child(m)
	m.free()
	Game.options = saved
	Game.reset_run()


# --- Impostazioni ----------------------------------------------------------------------------------

func _test_settings() -> void:
	check(ProjectSettings.get_setting("display/window/size/viewport_width") == View.W and View.W == 480, "risoluzione interna larga 480")
	check(ProjectSettings.get_setting("display/window/size/viewport_height") == View.H and View.H == 270, "risoluzione interna alta 270")
	check(ProjectSettings.get_setting("display/window/stretch/scale_mode") == "integer", "scala intera")
	check(Engine.physics_ticks_per_second == 60, "fisica a 60 tick")
	check(not bool(ProjectSettings.get_setting("physics/common/physics_interpolation")), "interpolazione della fisica spenta")
	check(ResourceLoader.exists("res://scenes/main.tscn"), "la scena principale esiste")
	for a in Controls.KEYS:
		for k: int in Controls.KEYS[a]:
			check(k != KEY_SHIFT, "nessuna azione su Shift (%s)" % a)


# --- FrameAnim -------------------------------------------------------------------------------------

static func _clip(ticks: Array, loop: bool, tags: Array = [], events: Array = []) -> AnimClip:
	var c := AnimClip.new()
	c.name = &"prova"
	c.loop = loop
	for i in ticks.size():
		var f := AnimFrame.new()
		f.rect = Rect2i(0, 0, 4, 4)
		f.ticks = ticks[i]
		if i < tags.size():
			f.tags = AnimFrame.tags_from_names(tags[i])
		if i < events.size():
			f.events = PackedStringArray(events[i])
		f.dx = i
		c.frames.append(f)
	return c


func _test_frame_anim() -> void:
	var fa := FrameAnim.new(null)
	var c := _clip([3, 2, 4], false, [], [["sfx:a"], ["sfx:b"], ["glint"]])
	fa.play(&"prova", c)
	var seq: Array[int] = [fa.index]
	var ev_ticks: Dictionary = {0: fa.take_events()}
	var finished_at := -1
	for t in range(1, 12):
		fa.advance()
		seq.append(fa.index)
		var e := fa.take_events()
		if not e.is_empty():
			ev_ticks[t] = e
		if fa.finished and finished_at < 0:
			finished_at = t
	check(seq.slice(0, 9) == [0, 0, 0, 1, 1, 2, 2, 2, 2], "FrameAnim: ogni fotogramma resta esattamente i suoi tick", str(seq))
	check(finished_at == 9, "FrameAnim: un'animazione di 9 tick finisce al tick 9", str(finished_at))
	check(ev_ticks.keys() == [0, 3, 5], "FrameAnim: gli eventi scattano quando il fotogramma inizia", str(ev_ticks))
	check(fa.index == 2 and fa.finished, "FrameAnim: a fine animazione resta sull'ultimo fotogramma")

	var lp := FrameAnim.new(null)
	lp.play(&"giro", _clip([2, 3], true))
	var lseq: Array[int] = [lp.index]
	for t in 10:
		lp.advance()
		lseq.append(lp.index)
	check(lseq == [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0], "FrameAnim: il loop riparte senza tick persi", str(lseq))

	var hold := FrameAnim.new(null)
	hold.play(&"tieni", _clip([2, 1, 3], false, [[], ["hold"], []]))
	for t in 20:
		hold.advance()
	check(hold.index == 1 and not hold.finished and hold.is_holding(), "FrameAnim: il fotogramma hold resta fermo")
	hold.release_hold()
	check(hold.index == 2, "FrameAnim: release_hold fa proseguire")

	var dxa := FrameAnim.new(null)
	dxa.play(&"dx", _clip([1, 1, 1], false))
	var total := dxa.take_dx()
	for t in 3:
		dxa.advance()
		total += dxa.take_dx()
	check(total == 0 + 1 + 2, "FrameAnim: il dx di ogni fotogramma si applica una volta", str(total))


func _test_retime() -> void:
	var c := _clip([4, 2, 5, 5, 5], false, [[], ["active"], [], [], []], [["sfx:w"], [], [], [], []])
	var r := c.retimed(3, 2, 9)
	check(r.segment_ticks() == Vector3i(3, 2, 9), "Ritemporizzazione: avvio, attivo e recupero come l'AttackData", str(r.segment_ticks()))
	check(r.total_ticks() == 14, "Ritemporizzazione: totale 14 tick per jab1")
	check(r.frames[0].events == PackedStringArray(["sfx:w"]), "Ritemporizzazione: gli eventi restano")
	var many := _clip([1, 1, 1, 1, 1, 1], false, [[], [], [], [], ["active"], []], [["sfx:a"], ["sfx:b"], [], [], [], []])
	var r2 := many.retimed(2, 1, 1)
	check(r2.segment_ticks() == Vector3i(2, 1, 1), "Ritemporizzazione: più fotogrammi che tick", str(r2.segment_ticks()))
	var evs := PackedStringArray()
	for f in r2.frames:
		evs.append_array(f.events)
	check(evs.has("sfx:a") and evs.has("sfx:b"), "Ritemporizzazione: gli eventi dei fotogrammi saltati non si perdono", str(evs))
	var air := _clip([2, 3, 6], false, [[], ["active"], ["air", "hold"]])
	var r3 := air.retimed(4, 8, -1)
	check(r3.segment_ticks() == Vector3i(4, 8, 6) and r3.frames[r3.frames.size() - 1].has_tag(AnimFrame.TAG_HOLD), "Ritemporizzazione in aria: il fotogramma hold resta")


func _test_replay_format() -> void:
	var r := Replay.new()
	r.level_seed = 3
	var held := [0, InputFrame.RIGHT, InputFrame.RIGHT, InputFrame.RIGHT | InputFrame.ATTACK, InputFrame.RIGHT, 0]
	for t in held.size():
		r.record(t, held[t], held[t] & ~(held[t - 1] if t > 0 else 0))
	var back := Replay.from_dict(JSON.parse_string(JSON.stringify(r.to_dict())))
	var ok := back != null and back.length == held.size()
	var got: Array = []
	if back != null:
		back.rewind()
		for t in held.size():
			var f := back.frame_at(t)
			got.append([f.held, f.pressed])
	check(ok and got == [[0, 0], [2, 2], [2, 0], [18, 16], [2, 0], [0, 0]], "Replay: andata e ritorno in JSON con i tasti appena premuti", str(got))


# --- Combo, buffer, hitstop --------------------------------------------------------------------------

## Livello di prova lontano dalle ondate, con un punk fermo davanti a GIG a `dist` px.
func _duel(script: Dictionary, dist: float) -> Dictionary:
	var held: Dictionary = script
	var input := PlayerInput.from_provider(func(t: int) -> int: return int(held.get(t, 0)))
	var lvl := Harness.make_level(root, input, 375.0, 225.0)
	var punk := lvl.spawn_thug(&"thug_punk", 1, 225.0, "")
	punk.ai_enabled = false
	punk.px = lvl.player.px + dist
	punk.py = lvl.player.py
	punk.facing = -1
	punk.set_state(Fighter.State.IDLE)
	return {"level": lvl, "punk": punk}


## Tasti: un tocco di attacco ogni `every` tick a partire da `from`, per `n` volte.
static func _taps(from: int, every: int, n: int) -> Dictionary:
	var d := {}
	for i in n:
		d[from + i * every] = InputFrame.ATTACK
	return d


## Avvia la simulazione e annota gli attacchi iniziati da GIG: [[tick, id], ...].
static func _attack_log(lvl: Level, ticks: int) -> Array:
	var out: Array = []
	var serial := -1
	for i in ticks:
		lvl.step()
		var g := lvl.player
		if g.attack != null and g.attack_serial != serial:
			serial = g.attack_serial
			out.append([lvl.tick - 1, String(g.attack.id)])
	return out


func _test_combo_chain() -> void:
	var d := _duel(_taps(2, 4, 30), 37.5)
	var lvl: Level = d["level"]
	var log := _attack_log(lvl, 110)
	var ids: Array = log.map(func(e: Array) -> String: return e[1])
	check(ids.slice(0, 4) == ["gig_jab1", "gig_jab2", "gig_hook", "gig_kick"], "Combo: jab1 → jab2 → gancio → calcio se i colpi vanno a segno", str(ids))
	var punk: Thug = d["punk"]
	check(punk.hp == 48 - 4 - 4 - 7 - 12, "Combo: danni 4 + 4 + 7 + 12", "vita %d" % punk.hp)
	check(Game.score == 10 + 10 + 20 + 50, "Combo: punti 10 + 10 + 20 + 50", str(Game.score))
	Harness.free_level(lvl)


## Col braccio bloccato (prima del riavvio) la sola destra: diretto → diretto → mazza se i colpi vanno a
## segno, niente presa camminando contro il nemico, niente calcio in salto.
func _test_one_arm() -> void:
	var d := _duel(_taps(2, 4, 8), 37.5)
	var lvl: Level = d["level"]
	var g := lvl.player
	g.one_arm = true
	g.use_sheet(&"gig_spento")
	check(g.sheet.id == &"gig_spento" and g.anim.sheet == g.sheet, "Braccio bloccato: GIG usa il foglio spento", str(g.sheet.id))
	var punk: Thug = d["punk"]
	var ids: Array = []
	var serial := -1
	var knocked := false
	for i in 110:
		lvl.step()
		if g.attack != null and g.attack_serial != serial:
			serial = g.attack_serial
			ids.append(String(g.attack.id))
		knocked = knocked or punk.state == Fighter.State.KNOCK_AIR
	check(ids == ["gig_jab2", "gig_jab2b", "gig_mazza"], "Braccio bloccato: diretto → diretto → mazza se i colpi vanno a segno", str(ids))
	check(punk.hp == 48 - 4 - 4 - 14 and knocked, "Braccio bloccato: danni 4 + 4 + 14, la mazza atterra", "vita %d, a terra %s" % [punk.hp, knocked])
	check(Game.score == 10 + 10 + 50, "Braccio bloccato: punti 10 + 10 + 50", str(Game.score))
	Harness.free_level(lvl)
	# Camminando contro il nemico non lo afferra: la presa vuole due mani.
	var keys := {}
	for t in 50:
		keys[t] = InputFrame.RIGHT
	d = _duel(keys, 40.0)
	lvl = d["level"]
	g = lvl.player
	g.one_arm = true
	var grabbed := false
	for i in 60:
		lvl.step()
		grabbed = grabbed or g.state == Fighter.State.GRAB
	check(not grabbed, "Braccio bloccato: niente presa camminando contro il nemico")
	Harness.free_level(lvl)
	# In salto il tasto attacco non fa niente (e non resta nel buffer fino all'atterraggio).
	d = _duel({2: InputFrame.JUMP, 10: InputFrame.ATTACK}, 150.0)
	lvl = d["level"]
	g = lvl.player
	g.one_arm = true
	var log := _attack_log(lvl, 70)
	check(log.is_empty() and g.state != Fighter.State.JUMP, "Braccio bloccato: niente calcio in salto", str(log))
	Harness.free_level(lvl)
	# La salita della sporgenza, che la fisica del platform legge, dura uguale nei due fogli.
	var a := SpriteSheet.get_sheet(&"gig").clip(&"ledge_climb").total_ticks()
	var b := SpriteSheet.get_sheet(&"gig_spento").clip(&"ledge_climb").total_ticks()
	check(a == b, "Salita della sporgenza lunga uguale col braccio libero e bloccato", "%d e %d tick" % [a, b])


func _test_combo_miss_and_buffer() -> void:
	# A vuoto: il tasto ripete sempre jab1.
	var d := _duel(_taps(2, 4, 12), 150.0)
	var lvl: Level = d["level"]
	var log := _attack_log(lvl, 60)
	var ids: Array = log.map(func(e: Array) -> String: return e[1])
	check(ids.size() >= 3 and ids.all(func(s: String) -> bool: return s == "gig_jab1"), "Combo: a vuoto ripete jab1", str(ids))
	# Il jab1 dura 14 tick: un tocco 8 tick prima della fine parte appena finisce.
	if log.size() >= 2:
		check(int(log[1][0]) - int(log[0][0]) == 14, "jab1 a vuoto dura 14 tick (3 + 2 + 9)", str(log.slice(0, 2)))
	Harness.free_level(lvl)

	# Buffer di 8 tick: un tocco vale nel tick in cui arriva e nei 7 seguenti.
	# jab1 parte al tick P e lascia GIG libero al tick P + 14.
	var start := 2
	d = _duel({start: InputFrame.ATTACK, start + 7: InputFrame.ATTACK}, 150.0)
	lvl = d["level"]
	log = _attack_log(lvl, 40)
	check(log.size() == 2 and int(log[1][0]) == int(log[0][0]) + 14, "Buffer: un tocco 7 tick prima della fine viene tenuto", str(log))
	Harness.free_level(lvl)

	d = _duel({start: InputFrame.ATTACK, start + 6: InputFrame.ATTACK}, 150.0)
	lvl = d["level"]
	log = _attack_log(lvl, 40)
	check(log.size() == 1, "Buffer: un tocco 8 tick prima della fine scade", str(log))
	Harness.free_level(lvl)


func _test_hitstop() -> void:
	var d := _duel({2: InputFrame.ATTACK}, 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	var hit_tick := -1
	for i in 30:
		lvl.step()
		if punk.hp < 48:
			hit_tick = lvl.tick - 1
			break
	check(hit_tick == 2 + 3, "jab1 colpisce al primo tick attivo (avvio 3)", str(hit_tick))
	check(g.hitstop == 5 and punk.hitstop == 7, "Hitstop jab1: 5 a GIG, 7 al punk", "%d/%d" % [g.hitstop, punk.hitstop])
	check(punk.flash == 2, "Lampo bianco di 2 tick sulla vittima")
	var gx := g.anim.index
	var px := punk.px
	var flashes := 0
	for i in 5:
		lvl.step()
		if punk.flash > 0:
			flashes += 1
		check(g.anim.index == gx and punk.px == px, "Hitstop: attaccante e vittima fermi (tick %d)" % i)
	check(flashes == 1, "Il lampo dura 2 tick in tutto", str(flashes))
	lvl.step()
	check(g.hitstop == 0 and punk.hitstop == 1, "Dopo 5 tick GIG riparte, il punk ha ancora 1 tick di hitstop", "%d/%d" % [g.hitstop, punk.hitstop])
	check(not g.hit_registry.is_empty(), "Un attacco colpisce la stessa vittima una volta sola")
	Harness.free_level(lvl)


func _test_grab_conditions() -> void:
	# Presa: entro 23 px e 5 px di profondità, camminando contro il nemico.
	var held := {}
	for t in 40:
		held[t] = InputFrame.RIGHT
	var d := _duel(held, 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var grabbed_at := -1
	for i in 40:
		lvl.step()
		if lvl.player.state == Fighter.State.GRAB:
			grabbed_at = i
			break
	check(grabbed_at >= 0, "Presa automatica camminando contro il punk", "tick %d" % grabbed_at)
	check(punk.state == Fighter.State.GRABBED, "Il punk è nello stato di presa")
	# La vittima scivola fino all'offset della voce victim in GRAB_SETTLE_TICKS, senza scatti.
	var worst_step := 0.0
	var last := (punk.px - lvl.player.px) * lvl.player.facing
	for i in Gig.GRAB_SETTLE_TICKS:
		lvl.step()
		var now := (punk.px - lvl.player.px) * lvl.player.facing
		worst_step = maxf(worst_step, absf(now - last))
		last = now
	var e := lvl.player.anim.frame().victim_entry(&"thug_punk")
	var want_dx := float(e[0]) if not e.is_empty() else 23.0
	check(absf((punk.px - lvl.player.px) * lvl.player.facing - want_dx) < 0.01, "La vittima arriva all'offset del campo victim", "%.1f invece di %.1f" % [(punk.px - lvl.player.px) * lvl.player.facing, want_dx])
	check(worst_step <= 5.0, "Presa: la vittima si avvicina senza scatti (al massimo 5 px per tick)", "%.1f px" % worst_step)
	# Fuori corsia di 7,5 px: nessuna presa.
	Harness.free_level(lvl)
	d = _duel(held, 37.5)
	lvl = d["level"]
	punk = d["punk"]
	punk.py += 7.5
	var any := false
	for i in 40:
		lvl.step()
		any = any or lvl.player.state == Fighter.State.GRAB
	check(not any, "Nessuna presa fuori dai 5 px di profondità")
	Harness.free_level(lvl)
	# La vittima si libera dopo 90 tick.
	d = _duel(held, 37.5)
	lvl = d["level"]
	punk = d["punk"]
	var start := -1
	var free_at := -1
	for i in 200:
		lvl.step()
		if start < 0 and punk.state == Fighter.State.GRABBED:
			start = lvl.tick
		if start >= 0 and punk.state != Fighter.State.GRABBED:
			free_at = lvl.tick
			break
	check(start >= 0 and free_at - start == 90, "Il nemico si libera dopo 90 tick", str(free_at - start))
	Harness.free_level(lvl)


func _test_thrown_body() -> void:
	# Presa del primo punk, poi tre tocchi: due ginocchiate e la proiezione verso il secondo.
	var held := {}
	for t in 16:
		held[t] = InputFrame.RIGHT
	for k in 3:
		held[30 + k * 24] = InputFrame.ATTACK
	var d := _duel(held, 37.5)
	var lvl: Level = d["level"]
	var a: Thug = d["punk"]
	var b := lvl.spawn_thug(&"thug_punk", 1, 225.0, "")
	b.ai_enabled = false
	b.px = lvl.player.px + 137.5
	b.py = lvl.player.py
	b.facing = -1
	b.set_state(Fighter.State.IDLE)
	var b_down := false
	for i in 220:
		lvl.step()
		b_down = b_down or b.state == Fighter.State.KNOCK_AIR or b.state == Fighter.State.KNOCK_DOWN
	check(Game.stat(&"throws") == 1 and Game.stat(&"hit_gig_knee") == 2, "Presa: due ginocchiate poi la proiezione al terzo tocco", str(Game.stats))
	check(Game.stat(&"hit_gig_throw_body") == 1 and b_down, "Il corpo proiettato colpisce e atterra l'altro nemico", "colpi %d" % Game.stat(&"hit_gig_throw_body"))
	check(a.hp == 48 - 6 - 6 - 14, "Danni della presa: 6 + 6 + 14", "vita %d" % a.hp)
	Harness.free_level(lvl)


## La proiezione non ha fotogrammi attivi: la ritemporizzazione li tiene tutti, e al rilascio
## (tick 8) la vittima parte da dove la disegna la voce victim del fotogramma del rilascio.
func _test_throw_release() -> void:
	var sheet := SpriteSheet.get_sheet(&"gig")
	var throw := load("res://data/attacks/gig_throw.tres") as AttackData
	var c := sheet.attack_clip(&"throw", throw)
	check(c.frames.size() == sheet.clip(&"throw").frames.size() and c.total_ticks() == throw.startup + throw.recovery,
		"Proiezione ritemporizzata: tutti i fotogrammi, %d + %d tick" % [throw.startup, throw.recovery],
		"%d fotogrammi, %d tick" % [c.frames.size(), c.total_ticks()])
	var starts: Array[int] = []
	var t := 0
	for f in c.frames:
		starts.append(t)
		t += f.ticks
	check(starts.has(throw.startup), "Proiezione: un fotogramma inizia al tick del rilascio (%d)" % throw.startup, str(starts))
	for back in [false, true]:
		var held := {}
		for k in 16:
			held[k] = InputFrame.RIGHT
		for k in 3:
			held[30 + k * 24] = InputFrame.ATTACK
		if back:
			held[78] = InputFrame.ATTACK | InputFrame.LEFT
		var d := _duel(held, 37.5)
		var lvl: Level = d["level"]
		var punk: Thug = d["punk"]
		var g := lvl.player
		var got := -999.0
		var want := -1.0
		for i in 200:
			lvl.step()
			if punk.state == Fighter.State.THROWN:
				got = (punk.px - g.px) * g.facing
				var e := g.anim.frame().victim_entry(&"thug_punk")
				want = float(e[0]) if not e.is_empty() else Gig.THROW_RELEASE_DX
				break
		var what := "all'indietro" if back else "in avanti"
		check(absf(got - want) < 0.01, "Proiezione %s: al rilascio la vittima parte dal dx della voce victim" % what, "%.1f invece di %.1f" % [got, want])
		check(g.facing == (-1 if back else 1) and signf(punk.px - g.px) == (-1.0 if back else 1.0),
			"Proiezione %s: la vittima vola dalla parte giusta" % what, "facing %d, vittima a %.0f" % [g.facing, punk.px - g.px])
		Harness.free_level(lvl)


## Ogni attacco nemico, partendo dalla distanza scelta dall'intelligenza, colpisce GIG fermo.
func _test_enemy_attacks() -> void:
	for spec: Array in [[&"thug_punk", &"thug_punk_jab"], [&"thug_punk", &"thug_punk_haymaker"], [&"thug_bruiser", &"thug_bruiser_punch"]]:
		var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
		var g := lvl.player
		var t := lvl.spawn_thug(spec[0], 1, 225.0, "")
		t.ai_enabled = false
		var atk := load("res://data/attacks/%s.tres" % spec[1]) as AttackData
		t.px = g.px + t._reach(atk)
		t.py = g.py
		t.facing = -1
		t.set_state(Fighter.State.IDLE)
		g.facing = 1
		t.start_attack(atk, lvl.next_attack_serial())
		var hit_at := -1
		for i in atk.total_ticks() + 2:
			lvl.step()
			if g.hp < g.data.max_hp:
				hit_at = i
				break
		check(hit_at >= 0 and g.hp == g.data.max_hp - atk.damage, "%s colpisce GIG dalla distanza scelta dall'IA" % spec[1], "distanza %.0f, vita %d" % [t._reach(atk), g.hp])
		# L'attacco parte prima del primo step: lo step i è il tick i + 1 dall'inizio.
		check(hit_at + 1 == atk.startup, "%s colpisce %d tick dopo l'inizio (fine dell'avvio)" % [spec[1], atk.startup], str(hit_at + 1))
		Harness.free_level(lvl)


## Armatura del bruto: durante l'avvio del pugno i jab non lo fermano, il gancio sì.
func _test_bruiser_armor() -> void:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
	var g := lvl.player
	var b := lvl.spawn_thug(&"thug_bruiser", 1, 225.0, "")
	b.ai_enabled = false
	b.px = g.px + 50.0
	b.py = g.py
	b.facing = -1
	b.set_state(Fighter.State.IDLE)
	var punch := load("res://data/attacks/thug_bruiser_punch.tres") as AttackData
	b.start_attack(punch, lvl.next_attack_serial())
	for i in 4:
		lvl.step()
	var hp0 := b.hp
	lvl.combat.apply_hit(g, b, g.attacks[&"gig_jab1"], Vector2(b.px, b.py - 75), 1)
	check(b.state == Fighter.State.ATTACK and b.hp == hp0 - 4, "Bruto con armatura: il jab fa danno ma non lo ferma")
	lvl.combat.apply_hit(g, b, g.attacks[&"gig_hook"], Vector2(b.px, b.py - 75), 1)
	check(b.state == Fighter.State.HURT, "Bruto con armatura: il gancio lo ferma")
	Harness.free_level(lvl)


func _test_lives() -> void:
	var d := _duel({}, 250.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	var hay := load("res://data/attacks/thug_punk_haymaker.tres") as AttackData
	g.hp = 1
	lvl.combat.apply_hit(punk, g, hay, Vector2(g.px, g.py - 75), -1)
	check(g.dead and g.state == Fighter.State.KNOCK_AIR, "GIG a 0 di vita vola a terra")
	var respawned_at := -1
	for i in 400:
		lvl.step()
		if Game.lives == 2 and g.state != Fighter.State.DEAD and not g.dead:
			respawned_at = i
			break
	check(respawned_at > 0 and g.hp == g.data.max_hp and g.invuln > 60, "Una vita in meno, poi rientra con la vita piena e invulnerabile", "tick %d, vita %d, invuln %d" % [respawned_at, g.hp, g.invuln])
	check(g.ph > 125.0, "Il rientro avviene dall'alto")
	# Ultima vita: CONTINUA?
	for i in 200:
		lvl.step()
	Game.lives = 1
	g.invuln = 0
	g.hp = 1
	lvl.combat.apply_hit(punk, g, hay, Vector2(g.px, g.py - 75), -1)
	for i in 400:
		lvl.step()
		if lvl.phase == Level.Phase.CONTINUE:
			break
	check(lvl.phase == Level.Phase.CONTINUE and Game.lives == 0, "Senza vite si passa a CONTINUA?")
	Harness.free_level(lvl)


# --- AttackDirector --------------------------------------------------------------------------------

func _test_attack_director() -> void:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 1950.0, 230.0)
	AttackDirector.keep_log = true
	var thugs: Array[Thug] = []
	thugs.append(lvl.spawn_thug(&"thug_punk", 1, 213.0, "prova"))
	thugs.append(lvl.spawn_thug(&"thug_punk", -1, 245.0, "prova"))
	thugs.append(lvl.spawn_thug(&"thug_bruiser", 1, 238.0, "prova"))
	var worst := 0
	var attacks_seen := 0
	for i in 2400:
		# GIG non muore: la prova riguarda solo i turni d'attacco.
		lvl.player.hp = lvl.player.data.max_hp
		lvl.step()
		var active := 0
		for t in lvl.enemies():
			if not t.active_hitboxes().is_empty():
				active += 1
		worst = maxi(worst, active)
	var starts: Dictionary = {}
	var releases: Dictionary = {}
	var last_start := -100000
	var min_gap := 100000
	var same_ok := true
	for e: Array in AttackDirector.events:
		var tick: int = e[0]
		var id: int = e[1]
		if e[2] == "start":
			attacks_seen += 1
			min_gap = mini(min_gap, tick - last_start)
			last_start = tick
			if releases.has(id) and tick - int(releases[id]) < 36:
				same_ok = false
			starts[id] = tick
		elif e[2] == "release":
			releases[id] = tick
	check(attacks_seen >= 6, "AttackDirector: i nemici attaccano davvero", str(attacks_seen))
	check(worst <= 1, "AttackDirector: mai due nemici in attacco attivo insieme", str(worst))
	check(min_gap >= AttackDirector.GLOBAL_GAP, "AttackDirector: almeno 0,35 s fra due attacchi nemici", str(min_gap))
	check(same_ok, "AttackDirector: almeno 0,6 s fra due attacchi dello stesso nemico")
	AttackDirector.keep_log = false
	Harness.free_level(lvl)


func _test_ko_freeze() -> void:
	# L'ultimo KO di un'ondata congela tutto per 26 tick, poi 0,4 s al 35%.
	var d := _duel({}, 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	lvl.active_wave = {"id": "prova"}
	punk.wave_id = "prova"
	punk.hp = 4
	var g := lvl.player
	var atk: AttackData = g.attacks[&"gig_jab1"]
	lvl.combat.apply_hit(g, punk, atk, Vector2(punk.px, punk.py - 75), 1)
	var a0 := lvl.actor_ticks
	for i in 26:
		lvl.step()
	check(lvl.actor_ticks == a0, "KO finale: 26 tick di congelamento", str(lvl.actor_ticks - a0))
	for i in 24:
		lvl.step()
	var moved := lvl.actor_ticks - a0
	check(moved >= 8 and moved <= 9, "KO finale: poi 24 tick al 35% della velocità", str(moved))
	Harness.free_level(lvl)


## Durante tutta la sequenza del KO finale (26 + 24 tick) GIG resta visibile anche se sta
## lampeggiando per l'invulnerabilità; la vittima non resta tutta bianca per 26 tick.
func _test_ko_visibility() -> void:
	var d := _duel({}, 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	lvl.active_wave = {"id": "prova"}
	punk.wave_id = "prova"
	punk.hp = 4
	# Invulnerabilità a 57: dopo un tick vale 56 (fase accesa) e nel rallentatore, finito
	# l'hitstop del jab, scende a 55 (fase spenta del lampeggio, 4 tick su 8).
	g.invuln = 57
	lvl.step()
	lvl.combat.apply_hit(g, punk, g.attacks[&"gig_jab1"], Vector2(punk.px, punk.py - 75), 1)
	var hidden := 0
	var white := 0
	var ticks := 0
	for i in 60:
		lvl.step()
		if not lvl.ko_sequence_active():
			break
		ticks += 1
		if not g.visible:
			hidden += 1
		if lvl.ko_freeze_active() and float(punk._mat.get_shader_parameter(&"flash")) > 0.5:
			white += 1
	check(ticks == Level.KO_FREEZE_TICKS + Level.KO_SLOWMO_TICKS, "KO finale: la sequenza dura 26 + 24 tick", str(ticks))
	check(hidden == 0, "KO finale: GIG visibile per tutta la sequenza anche mentre lampeggia", "%d tick invisibile" % hidden)
	check(white > 0 and white <= 16, "KO finale: la vittima non resta bianca per tutto il congelamento", "%d tick su 26" % white)
	Harness.free_level(lvl)


## Un colpo leggero (jab del punk) che prende GIG in salto lo atterra: niente GIG sospeso.
func _test_air_hit_lands() -> void:
	var d := _duel({2: InputFrame.JUMP}, 250.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	var jab := load("res://data/attacks/thug_punk_jab.tres") as AttackData
	var hit := false
	var seen_down := false
	for i in 220:
		lvl.step()
		if not hit and g.ph > 22.5:
			punk.px = g.px + 37.5
			lvl.combat.apply_hit(punk, g, jab, Vector2(g.px, g.py - g.ph - 75), 0)
			hit = true
		seen_down = seen_down or g.state == Fighter.State.KNOCK_DOWN
	check(hit and seen_down, "Jab su GIG in salto: GIG viene atterrato", "stato %d" % g.state)
	check(g.ph == 0.0 and g.state != Fighter.State.KNOCK_AIR, "Jab su GIG in salto: GIG torna a terra", "ph %.1f" % g.ph)
	Harness.free_level(lvl)


## GIG perde l'ultima vita quasi insieme al KO dell'ultimo nemico: niente CONTINUA? sopra
## ZONA LIBERATA e il livello finisce lo stesso (prima restava bloccato dopo il continue).
func _test_clear_and_last_life() -> void:
	for gap in [0, 8]:
		var d := _duel({}, 37.5)
		var lvl: Level = d["level"]
		var punk: Thug = d["punk"]
		var g := lvl.player
		lvl.active_wave = {"id": "prova", "final": true}
		punk.wave_id = "prova"
		punk.hp = 1
		Game.lives = 1
		g.hp = 1
		var ended := [false]
		lvl.finished.connect(func(_r: Dictionary) -> void: ended[0] = true)
		var hay := load("res://data/attacks/thug_punk_haymaker.tres") as AttackData
		lvl.combat.apply_hit(punk, g, hay, Vector2(g.px, g.py - 75), -1)
		for i in gap:
			lvl.step()
		lvl.combat.apply_hit(g, punk, g.attacks[&"gig_jab1"], Vector2(punk.px, punk.py - 75), 1)
		var went_continue := false
		for i in 900:
			lvl.step()
			went_continue = went_continue or lvl.phase == Level.Phase.CONTINUE
			if ended[0]:
				break
		check(not went_continue, "Ultima vita persa a zona liberata (%d tick): niente CONTINUA?" % gap)
		check(ended[0] and lvl.zone_cleared, "Ultima vita persa a zona liberata (%d tick): il livello finisce" % gap)
		Harness.free_level(lvl)


## Presa e proiezione contro il muro della vista bloccata: la coppia resta dentro i muri.
func _test_grab_at_wall() -> void:
	var held := {}
	for t in 30:
		held[t] = InputFrame.RIGHT
	held[40] = InputFrame.ATTACK
	held[64] = InputFrame.ATTACK
	held[88] = InputFrame.ATTACK
	var d := _duel(held, 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	lvl.camera.min_x = lvl.camera.x
	lvl.camera.max_x = lvl.camera.x
	var wall := lvl.view_right() - Level.WALL_MARGIN
	punk.px = wall
	g.px = wall - 50.0
	var worst := 0.0
	var released_at := -1.0
	for i in 160:
		lvl.step()
		if punk.state == Fighter.State.GRABBED or punk.state == Fighter.State.THROWN or punk.state == Fighter.State.KNOCK_AIR:
			worst = maxf(worst, punk.px - wall)
		if released_at < 0.0 and punk.state == Fighter.State.THROWN:
			released_at = punk.px
	check(Game.stat(&"grabs") >= 1 and Game.stat(&"throws") == 1, "Presa al muro: presa e proiezione", str(Game.stats))
	check(worst <= 0.01, "Presa al muro: la vittima non va mai oltre il muro", "%.1f px oltre" % worst)
	check(released_at > 0.0 and released_at <= wall + 0.01, "Proiezione al muro: rilascio dentro il muro", "%.1f (muro %.1f)" % [released_at, wall])
	Harness.free_level(lvl)


## Ginocchiata che manda KO: la vittima vola in knock_air e GIG non la tiene più.
func _test_knee_ko() -> void:
	var held := {}
	for t in 16:
		held[t] = InputFrame.RIGHT
	held[30] = InputFrame.ATTACK
	var d := _duel(held, 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	punk.hp = 6
	var ko_at := -1
	var flew := false
	for i in 120:
		lvl.step()
		if ko_at < 0 and punk.dead:
			ko_at = i
		if ko_at >= 0 and punk.hitstop == 0 and punk.ph > 0.0:
			flew = flew or (punk.anim.name == &"knock_air" and punk.draw_dy == 0)
	check(ko_at >= 0 and g.grab_partner == null and g.state != Fighter.State.GRAB, "Ginocchiata KO: GIG lascia la vittima")
	check(flew, "Ginocchiata KO: la vittima vola via con knock_air", "anim %s" % punk.anim.name)
	Harness.free_level(lvl)


## Un jab sul bruto durante l'avvio con armatura non gli toglie il turno d'attacco.
func _test_armor_keeps_turn() -> void:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
	var g := lvl.player
	var b := lvl.spawn_thug(&"thug_bruiser", 1, 225.0, "")
	b.ai_enabled = false
	b.px = g.px + 50.0
	b.py = g.py
	b.facing = -1
	b.set_state(Fighter.State.IDLE)
	check(lvl.director.request(b, lvl.tick), "Armatura: il bruto ottiene il turno")
	lvl.director.on_attack_start(b, lvl.tick)
	b.start_attack(load("res://data/attacks/thug_bruiser_punch.tres") as AttackData, lvl.next_attack_serial())
	for i in 4:
		lvl.step()
	lvl.combat.apply_hit(g, b, g.attacks[&"gig_jab1"], Vector2(b.px, b.py - 75), 1)
	check(b.state == Fighter.State.ATTACK and lvl.director.is_holder(b), "Armatura: dopo il jab il bruto tiene il turno finché il pugno non finisce")
	Harness.free_level(lvl)


## Un nemico che entra da fuori schermo non si può colpire finché non supera il muro.
func _test_enter_not_hittable() -> void:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
	var t := lvl.spawn_thug(&"thug_punk", 1, 225.0, "")
	var jab: AttackData = lvl.player.attacks[&"gig_jab1"]
	check(t.state == Fighter.State.ENTER and not t.can_be_hit_by(lvl.player, jab), "Nemico che entra: fuori dai muri non si può colpire")
	for i in 120:
		lvl.step()
		if t.px <= lvl.view_right() - Level.WALL_MARGIN - 1.0:
			break
	check(t.can_be_hit_by(lvl.player, jab), "Nemico che entra: dentro i muri si può colpire")
	Harness.free_level(lvl)


## Una combo interrotta da un colpo riparte da jab1.
func _test_combo_reset_on_hurt() -> void:
	var d := _duel(_taps(2, 4, 3), 37.5)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	for i in 24:
		lvl.step()
	var step_before := g.combo_step
	var jab := load("res://data/attacks/thug_punk_jab.tres") as AttackData
	lvl.combat.apply_hit(punk, g, jab, Vector2(g.px, g.py - 75), -1)
	check(step_before > 0 and g.combo_step == 0 and g.combo_timer == 0, "Combo interrotta da un colpo: riparte da jab1", "passo %d -> %d" % [step_before, g.combo_step])
	Harness.free_level(lvl)


## I testi dei crediti usano solo caratteri che il font sa disegnare: un carattere mancante
## diventerebbe un riquadro con il codice (per esempio "2192" per la freccia).
func _test_credits_glyphs() -> void:
	var c := CreditsScreen.new()
	c._build()
	var missing := {}
	var lines := 0
	for l: Array in c._lines:
		if l[3] != null:
			continue
		lines += 1
		var f := UiFont.external_font(bool(l[2]))
		for ch in str(l[0]):
			if ch != " " and f != null and not f.has_char(ch.unicode_at(0)):
				missing[ch] = true
	check(lines > 100 and missing.is_empty(), "Crediti: ogni carattere è nel font", "%d righe, mancano %s" % [lines, str(missing.keys())])
	var has_logo := false
	for l: Array in c._lines:
		has_logo = has_logo or l[3] != null
	check(has_logo, "Crediti: il titolo è il logo, non testo a scala 2")
	c.free()
	# La sezione MUSICA con brani finti: il risultato non dipende dalla musica del laboratorio di quel PC.
	var fake := PackedStringArray(["\"Il messo (alla porta)\" (Suno Pro)",
			"\"Un titolo lunghissimo che va a capo perché supera la riga dei crediti\" (Suno Pro)"])
	check(_credits_music_ok(fake), "Crediti: la sezione MUSICA elenca i brani caricati", "%d brani finti" % fake.size())
	check(_credits_music_ok(PackedStringArray()), "Crediti: senza musica la sezione MUSICA lo dice")
	# credits.txt salvato da un editor di Windows (CRLF): titoli puliti e brani al loro posto.
	var crlf := CreditsScreen.new()
	crlf.music_lines = fake
	crlf._add_text("# CODICE\r\nUna riga\r\n# MUSICA\r\nAltra riga\r\n")
	var t2 := PackedStringArray()
	for l: Array in crlf._lines:
		t2.append(str(l[0]))
	crlf.free()
	check(t2.has("CODICE") and t2.has("MUSICA") and t2.has(fake[0]) and not ("\r" in "".join(t2)),
			"Crediti: i fine riga CRLF di credits.txt non sporcano i titoli", str(t2))


## I crediti completi con `tracks` come brani caricati: c'è la sezione MUSICA e ci sono tutti i brani
## (un titolo lungo va a capo come ogni riga, si cercano i suoi pezzi), o la riga NO_MUSIC.
func _credits_music_ok(tracks: PackedStringArray) -> bool:
	var c := CreditsScreen.new()
	c.music_lines = tracks
	c._build()
	var texts := PackedStringArray()
	for l: Array in c._lines:
		texts.append(str(l[0]))
	c.free()
	var ok := texts.has("MUSICA")
	if tracks.is_empty():
		return ok and texts.has(CreditsScreen.NO_MUSIC)
	for t in tracks:
		for part in CreditsScreen.word_wrap(UiFont.safe_text(t, true), CreditsScreen.MAX_CHARS):
			ok = ok and texts.has(part)
	return ok


## A replay finito nessun tasto resta tenuto.
func _test_replay_end() -> void:
	var r := Replay.new()
	for t in 4:
		r.record(t, InputFrame.RIGHT, InputFrame.RIGHT if t == 0 else 0)
	r.rewind()
	var held_after := -1
	for t in 6:
		var f := r.frame_at(t)
		if t >= 4:
			held_after = maxi(held_after, f.held)
	check(held_after == 0, "Replay finito: nessun tasto tenuto dopo l'ultimo tick", str(held_after))


# --- File JSON ------------------------------------------------------------------------------------

func _test_json_files() -> void:
	var sheets: PackedStringArray = []
	for dir: String in ["res://assets/sprites", "res://assets/props"]:
		if DirAccess.dir_exists_absolute(dir):
			for sub in DirAccess.get_directories_at(dir):
				var p := dir.path_join(sub).path_join(sub + ".json")
				if FileAccess.file_exists(p):
					sheets.append(p)
			for f in DirAccess.get_files_at(dir):
				if f.ends_with(".json"):
					sheets.append(dir.path_join(f))
	for f in DirAccess.get_files_at("res://assets/sprites/_placeholder"):
		if f.ends_with(".json"):
			sheets.append("res://assets/sprites/_placeholder".path_join(f))
	for p in sheets:
		var s := SpriteSheet.load_json(p)
		check(s.errors.is_empty(), "JSON sprite valido: %s" % p, "; ".join(s.errors.slice(0, 3)))
		if SpriteSheet.REQUIRED.has(s.id):
			check(s.missing_required().is_empty(), "Animazioni richieste presenti: %s" % p, ", ".join(s.missing_required()))
		_check_attack_timing(s)
	if FileAccess.file_exists(FxLayer.FX_JSON):
		var fx := FxLayer.new()
		fx.load_defs()
		check(fx.errors.is_empty(), "fx.json valido", "; ".join(fx.errors))
		fx.free()
	var env := "res://assets/env/sotto_la_linea/layers.json"
	if FileAccess.file_exists(env):
		var b := Backdrop.new()
		check(b.load_json(env), "layers.json valido", "; ".join(b.errors))
	var lv: Variant = JSON.parse_string(FileAccess.get_file_as_string(Level.LEVEL_JSON))
	check(lv is Dictionary and int(lv.get("width", 0)) == 2400 and (lv["waves"] as Array).size() == 2, "Dati del livello leggibili")
	for name in ["gig", "thug_punk", "thug_bruiser"]:
		var fd := load("res://data/fighters/%s.tres" % name) as FighterData
		check(fd != null and fd.max_hp > 0, "FighterData %s" % name)
	for f in DirAccess.get_files_at("res://data/attacks"):
		if f.ends_with(".tres"):
			var a := load("res://data/attacks/" + f) as AttackData
			check(a != null and a.id == StringName(f.get_basename()), "AttackData %s" % f)


## Le varianti di colore dei nemici cambiano colori che esistono davvero nel loro sprite: con un render
## nuovo la tavolozza può cambiare, e le varianti smetterebbero di funzionare senza avvisare.
func _test_palette_variants() -> void:
	for f in DirAccess.get_files_at("res://data/fighters"):
		if not f.ends_with(".tres"):
			continue
		var fd := load("res://data/fighters/" + f) as FighterData
		if fd == null or fd.palette_variants.is_empty():
			continue
		var s := SpriteSheet.get_sheet(fd.sprite_id)
		if s.source != SpriteSheet.Source.REAL:
			continue
		var want: Array[Color] = []
		for v: Dictionary in fd.palette_variants:
			for k: String in v:
				var c := Color.html(k)
				if not want.has(c):
					want.append(c)
		var img := s.texture.get_image()
		for y in img.get_height():
			if want.is_empty():
				break
			for x in img.get_width():
				var c := img.get_pixel(x, y)
				if c.a > 0.0:
					for i in range(want.size() - 1, -1, -1):
						if c.r == want[i].r and c.g == want[i].g and c.b == want[i].b:
							want.remove_at(i)
		var missing := PackedStringArray()
		for c in want:
			missing.append("#" + c.to_html(false))
		check(missing.is_empty(), "Varianti di colore presenti nello sprite: %s" % fd.id, ", ".join(missing))


## Le animazioni d'attacco ritemporizzate hanno esattamente i tempi dell'AttackData. Le varianti di un
## personaggio usano gli attacchi del personaggio base (gig_spento: gig_jab2, gig_mazza...).
func _check_attack_timing(s: SpriteSheet) -> void:
	var who := String(SHEET_BASE.get(s.id, s.id)) + "_"
	for f in DirAccess.get_files_at("res://data/attacks"):
		var a := load("res://data/attacks/" + f) as AttackData
		if a == null or a.anim == &"" or not String(a.id).begins_with(who):
			continue
		if not s.has_anim(a.anim) or a.active == 0:
			continue
		var c := s.attack_clip(a.anim, a)
		var seg := c.segment_ticks()
		var want := Vector3i(a.startup, a.active, seg.z if a.air else a.recovery)
		check(seg == want, "Tempi di %s in %s" % [a.id, s.json_path.get_file()], "%s invece di %s" % [seg, want])


# --- Replay ---------------------------------------------------------------------------------------

func _play(file: String) -> Dictionary:
	var r := Replay.load_file(REPLAY_DIR.path_join(file))
	if r == null:
		return {}
	var lvl := Harness.level_from_replay(root, r)
	var seen := {}
	var cam_locked_at := -1
	var go_with_bodies := false
	var cam_after_clear: Array[int] = []
	for i in r.length:
		lvl.step()
		seen[lvl.player.state] = true
		if not lvl.active_wave.is_empty() and lvl.camera.min_x == lvl.camera.max_x:
			cam_locked_at = lvl.camera.x
		if lvl.overlay.go_ticks > 0 and not lvl.enemies().is_empty():
			go_with_bodies = true
		if lvl.zone_cleared:
			cam_after_clear.append(lvl.camera.x)
	var out := {"level": lvl, "replay": r, "states": seen, "cam_locked_at": cam_locked_at, "hash": lvl.final_hash(),
		"stats": Game.stats.duplicate(), "score": Game.score, "go_with_bodies": go_with_bodies,
		"cam_after_clear": cam_after_clear}
	return out


func _test_replays() -> void:
	var files := DirAccess.get_files_at(REPLAY_DIR)
	for f in ["combo_punk.json", "grab_throw.json", "cable_touch.json", "cable_jump.json", "arena.json", "demo.json"]:
		check(files.has(f), "Replay presente: %s" % f)
	var res := _play("combo_punk.json")
	if not res.is_empty():
		var lvl: Level = res["level"]
		var st: Dictionary = res["stats"]
		check(lvl.waves_cleared >= 1 and st.get(&"ko_thug_punk", 0) == 1, "Replay combo: GIG sconfigge il punk dell'ondata 1")
		check(st.get(&"hit_gig_hook", 0) >= 1 and st.get(&"hit_gig_kick", 0) >= 1 and st.get(&"grabs", 0) == 0, "Replay combo: solo combo, con gancio e calcio finale", str(st))
		check(lvl.player.is_alive(), "Replay combo: GIG resta in piedi")
		check(res["cam_locked_at"] == 720, "Replay combo: la telecamera si blocca sull'ondata 1", str(res["cam_locked_at"]))
		check(not bool(res["go_with_bodies"]), "Replay combo: VAI compare solo dopo che il corpo del punk è sparito")
		var first: String = res["hash"]
		Harness.free_level(lvl)
		var again := _play("combo_punk.json")
		check(again.get("hash", "") == first, "Determinismo: due esecuzioni dello stesso replay, stesso hash", "%s / %s" % [first.left(12), str(again.get("hash", "")).left(12)])
		if not again.is_empty():
			Harness.free_level(again["level"])
	res = _play("grab_throw.json")
	if not res.is_empty():
		var st: Dictionary = res["stats"]
		check(st.get(&"grabs", 0) >= 1 and st.get(&"hit_gig_knee", 0) == 2 and st.get(&"hit_gig_throw", 0) == 1, "Replay presa: presa, due ginocchiate e proiezione", str(st))
		Harness.free_level(res["level"])
	res = _play("cable_touch.json")
	if not res.is_empty():
		var lvl: Level = res["level"]
		var st: Dictionary = res["stats"]
		var states: Dictionary = res["states"]
		check(st.get(&"cable_zaps_gig", 0) == 1 and lvl.player.hp == 110, "Replay cavo toccato: 10 di danno", "vita %d, scosse %d" % [lvl.player.hp, st.get(&"cable_zaps_gig", 0)])
		check(states.has(Fighter.State.KNOCK_DOWN), "Replay cavo toccato: GIG viene atterrato")
		Harness.free_level(lvl)
	res = _play("cable_jump.json")
	if not res.is_empty():
		var lvl: Level = res["level"]
		var st: Dictionary = res["stats"]
		check(st.get(&"cable_zaps_gig", 0) == 0 and lvl.player.hp == 120 and lvl.player.px > 1588.0, "Replay cavo saltato: nessun danno, GIG oltre il cavo", "x %.0f, vita %d" % [lvl.player.px, lvl.player.hp])
		Harness.free_level(lvl)
	res = _play("arena.json")
	if not res.is_empty():
		var lvl: Level = res["level"]
		var st: Dictionary = res["stats"]
		check(res["cam_locked_at"] == 1920, "Replay arena: la telecamera si blocca sull'arena", str(res["cam_locked_at"]))
		check(st.get(&"ko_thug_punk", 0) >= 1 and st.get(&"ko_thug_bruiser", 0) == 1, "Replay arena: KO del punk e del bruto")
		check(lvl.zone_cleared and lvl.active_wave.is_empty(), "Replay arena: dopo i KO la zona è liberata")
		var cams: Array[int] = res["cam_after_clear"]
		check(not cams.is_empty() and cams.all(func(x: int) -> bool: return x == 1920), "Replay arena: dopo ZONA LIBERATA la telecamera resta sull'arena", str(cams.slice(0, 3)))
		var first: String = res["hash"]
		Harness.free_level(lvl)
		var again := _play("arena.json")
		check(again.get("hash", "") == first, "Determinismo: l'arena rigiocata dà lo stesso hash")
		if not again.is_empty():
			Harness.free_level(again["level"])
	res = _play("demo.json")
	if not res.is_empty():
		var lvl: Level = res["level"]
		var r: Replay = res["replay"]
		var st: Dictionary = res["stats"]
		check(r.length >= 3600 and r.length <= 5400, "Replay dimostrativo lungo 60-90 s", "%.1f s" % (r.length / 60.0))
		check(lvl.zone_cleared, "Replay dimostrativo: zona liberata")
		check(st.get(&"bins_broken", 0) == 1 and st.get(&"apples", 0) == 1 and st.get(&"throws", 0) >= 1 and st.get(&"cable_zaps_gig", 0) == 0, "Replay dimostrativo: bidone, mela, proiezione, cavo saltato", str(st))
		Harness.free_level(lvl)


# --- Platform: la stanza di prova --------------------------------------------------------------------

const _L := InputFrame.LEFT
const _R := InputFrame.RIGHT
const _U := InputFrame.UP
const _D := InputFrame.DOWN
const _J := InputFrame.JUMP
const _S := InputFrame.DASH
const _A := InputFrame.ATTACK


## Una griglia vuota larga w e alta h celle, con il pavimento pieno dalla riga floor_row in giù.
static func _room(w: int, h: int, floor_row: int) -> SolidGrid:
	var g := SolidGrid.new(w, h)
	for y in range(floor_row, h):
		for x in w:
			g.set_cell(x, y, SolidGrid.Cell.SOLID)
	return g


static func _box(g: SolidGrid, x0: int, x1: int, y0: int, y1: int, c: SolidGrid.Cell = SolidGrid.Cell.SOLID) -> void:
	for y in range(y0, y1 + 1):
		for x in range(x0, x1 + 1):
			g.set_cell(x, y, c)


## GIG fermo con i piedi sul pavimento alla colonna di pixel x.
static func _pp(g: SolidGrid, x: int, floor_row: int) -> PlatformPlayer:
	var p := PlatformPlayer.new(PlatformMoves.new(), g)
	p.place(x, floor_row * SolidGrid.TILE)
	return p


## Fa girare `ticks` tick tenendo i tasti dati da fn(t) -> int; i tasti appena premuti si
## calcolano come dal vivo. Restituisce gli eventi di tutti i tick, ognuno con il suo tick.
static func _run_pp(p: PlatformPlayer, ticks: int, fn: Callable) -> Array:
	var ev: Array = []
	var prev := 0
	for t in ticks:
		var held: int = fn.call(t)
		p.step(InputFrame.new(held, held & ~prev))
		prev = held
		for e in p.events:
			ev.append([t, e])
	return ev


static func _count_events(ev: Array, event_name: String) -> int:
	var n := 0
	for e: Array in ev:
		if e[1] == event_name:
			n += 1
	return n


func _test_platform() -> void:
	var m := PlatformMoves.new()
	# Le misure sono a 60 px/m (blocchi da 20 px): T è un blocco.
	var T := SolidGrid.TILE
	# Fermo sul pavimento: non affonda e non cade.
	var g := _room(40, 14, 10)
	var p := _pp(g, 125, 10)
	_run_pp(p, 60, func(_t: int) -> int: return 0)
	check(p.state == PlatformPlayer.State.GROUND and p.py == 10 * T, "Platform: fermo sul pavimento resta a terra", "stato %s, y %d" % [p.state_name(), p.py])

	# Salto pieno e salto corto: il salto è variabile.
	p = _pp(g, 125, 10)
	_run_pp(p, 90, func(t: int) -> int: return _J if t < 40 else 0)
	var full := p.last_peak
	check(full >= 69 and full <= 94 and p.state == PlatformPlayer.State.GROUND and p.py == 10 * T,
		"Platform: salto pieno fra 69 e 94 px, e si riatterra", "%d px, stato %s" % [full, p.state_name()])
	p = _pp(g, 125, 10)
	_run_pp(p, 90, func(t: int) -> int: return _J if t < 2 else 0)
	check(p.last_peak > 0 and p.last_peak < full * 0.5, "Platform: lasciando subito SALTO il salto è basso", "%d px contro %d" % [p.last_peak, full])

	# Spinta: un solo doppio salto per volta in aria, e va più in alto del salto da solo.
	p = _pp(g, 125, 10)
	var ev := _run_pp(p, 120, func(t: int) -> int: return _J if (t < 20 or (t >= 22 and t < 50) or (t >= 52 and t < 60)) else 0)
	check(_count_events(ev, "spinta") == 1, "Platform: una sola Spinta per salto", "%d" % _count_events(ev, "spinta"))
	check(p.last_peak > full + 38, "Platform: con la Spinta si arriva più in alto", "%d px contro %d" % [p.last_peak, full])

	# Coyote time: subito dopo il bordo il salto vale ancora da terra e non consuma la Spinta.
	var gc := _room(40, 14, 10)
	_box(gc, 12, 39, 10, 12, SolidGrid.Cell.EMPTY)
	var off := [0]
	p = _pp(gc, 188, 10)
	var pc := p
	ev = _run_pp(p, 80, func(t: int) -> int:
		if pc.state == PlatformPlayer.State.AIR and off[0] == 0:
			off[0] = t
		if off[0] > 0 and t == off[0] + 3:
			return _R | _J
		return _R)
	check(off[0] > 0 and _count_events(ev, "jump") == 1 and _count_events(ev, "spinta") == 0,
		"Platform: coyote time, salto da terra 3 tick dopo il bordo",
		"lasciato al tick %d, salti %d, spinte %d" % [off[0], _count_events(ev, "jump"), _count_events(ev, "spinta")])
	off = [0]
	p = _pp(gc, 188, 10)
	var pc2 := p
	ev = _run_pp(p, 80, func(t: int) -> int:
		if pc2.state == PlatformPlayer.State.AIR and off[0] == 0:
			off[0] = t
		if off[0] > 0 and t == off[0] + m.coyote_ticks + 3:
			return _R | _J
		return _R)
	check(_count_events(ev, "jump") == 0 and _count_events(ev, "spinta") == 1, "Platform: dopo il coyote time SALTO è la Spinta",
		"salti %d, spinte %d" % [_count_events(ev, "jump"), _count_events(ev, "spinta")])

	# Buffer: senza Spinte, SALTO premuto poco prima di toccare terra salta all'atterraggio.
	p = _pp(g, 125, 10)
	var pb := p
	var pressed_at := [0]
	ev = _run_pp(p, 200, func(t: int) -> int:
		if t < 30:
			return _J if t < 20 or (t >= 22 and t < 28) else 0
		# In discesa, a meno di 10 px dal pavimento: un tocco di SALTO.
		if pressed_at[0] == 0 and pb.vy > 0 and pb.py >= 10 * T - 10 and pb.boosts_left == 0:
			pressed_at[0] = t
			return _J
		return 0)
	check(pressed_at[0] > 0 and _count_events(ev, "jump") == 2, "Platform: SALTO premuto prima di atterrare vale all'atterraggio",
		"premuto al tick %d, salti %d" % [pressed_at[0], _count_events(ev, "jump")])

	# Piattaforma sottile: si sale da sotto, ci si resta sopra, GIÙ + SALTO fa scendere.
	var gt := _room(40, 16, 13)
	_box(gt, 4, 12, 11, 11, SolidGrid.Cell.THIN)
	p = _pp(gt, 160, 13)
	_run_pp(p, 100, func(t: int) -> int: return _J if t < 30 else 0)
	check(p.state == PlatformPlayer.State.GROUND and p.py == 11 * T, "Platform: si sale da sotto su una piattaforma sottile", "stato %s, y %d" % [p.state_name(), p.py])
	_run_pp(p, 60, func(t: int) -> int: return (_D | _J) if t == 2 else (_D if t < 2 else 0))
	check(p.py == 13 * T, "Platform: GIÙ + SALTO scende dalla piattaforma sottile", "y %d" % p.py)

	# Niente compenetrazioni: da molto in alto si atterra esattamente sul pavimento.
	var gf := _room(10, 60, 58)
	p = PlatformPlayer.new(PlatformMoves.new(), gf)
	p.place(100, 125)
	_run_pp(p, 200, func(_t: int) -> int: return 0)
	check(p.state == PlatformPlayer.State.GROUND and p.py == 58 * T, "Platform: cadendo forte si atterra sul pavimento, senza attraversarlo", "y %d" % p.py)

	# Sporgenza: saltando verso un muro alto 7 blocchi ci si aggrappa e si sale.
	var gl := _room(40, 20, 16)
	_box(gl, 14, 20, 9, 15)
	p = _pp(gl, 250, 16)
	var pl := p
	var hung := [false]
	ev = _run_pp(p, 260, func(t: int) -> int:
		if pl.state == PlatformPlayer.State.LEDGE_HANG:
			hung[0] = true
			return _U if t % 4 == 0 else 0
		if hung[0]:
			return 0
		return (_R | _J) if t < 25 else _R)
	check(hung[0], "Platform: saltando verso il muro ci si aggrappa alla sporgenza", "eventi %s" % str(ev))
	check(p.state == PlatformPlayer.State.GROUND and p.py == 9 * T and p.px > 14 * T, "Platform: dalla sporgenza si sale in cima al muro",
		"stato %s, x %d, y %d" % [p.state_name(), p.px, p.py])

	# Muri da 5 e 6 blocchi (100 e 120 px), oltre il salto: lo spigolo arriva all'altezza del petto o
	# della testa e sotto non c'è posto per le gambe da appeso, così GIG scavalca. Non ci sono muri
	# impossibili fra 80 e 120 px.
	for rows in [4, 5, 6]:
		var gw := _room(40, 20, 16)
		_box(gw, 14, 20, 16 - rows, 15)
		p = _pp(gw, 250, 16)
		var pw := p
		var top_y: int = (16 - rows) * T
		var on_top := [false]
		_run_pp(p, 300, func(t: int) -> int:
			if pw.state == PlatformPlayer.State.GROUND and pw.py == top_y:
				on_top[0] = true
			if on_top[0]:
				return 0
			if pw.state == PlatformPlayer.State.LEDGE_HANG:
				return _U if t % 4 == 0 else 0
			return (_R | _J) if (t % 60) < 25 else _R)
		check(on_top[0], "Platform: muro di %d blocchi superato senza Spinta" % rows,
			"stato %s, x %d, y %d" % [p.state_name(), p.px, p.py])

	# Scivolata sotto un soffitto basso: si passa, e alla fine ci si rialza.
	var gs := _room(60, 16, 13)
	_box(gs, 20, 26, 0, 9)
	p = _pp(gs, 150, 13)
	var ps := p
	var slid := [-1]
	_run_pp(p, 320, func(t: int) -> int:
		# GIÙ all'imbocco del cunicolo, a 50 px, come farebbe un giocatore.
		if slid[0] < 0 and ps.px >= 338:
			slid[0] = t
		if slid[0] >= 0 and t < slid[0] + 3:
			return _R | _D
		return _R if t < 280 else 0)
	check(p.px > 27 * T and p.state == PlatformPlayer.State.GROUND, "Platform: la scivolata passa sotto un soffitto basso",
		"x %d, stato %s" % [p.px, p.state_name()])
	p = _pp(gs, 150, 13)
	_run_pp(p, 150, func(_t: int) -> int: return _R)
	check(p.px < 20 * T, "Platform: in piedi non si entra nel cunicolo", "x %d" % p.px)

	# Deterministico: gli stessi ingressi danno lo stesso stato.
	var hashes: Array[int] = []
	for i in 2:
		var gd := SolidGrid.load_file(TestRoom.MAP)
		var start: Vector2i = gd.marks["G"][0]
		p = PlatformPlayer.new(PlatformMoves.new(), gd)
		p.place(start.x, start.y)
		_run_pp(p, 900, func(t: int) -> int:
			var k := _R
			if t % 70 < 22:
				k |= _J
			if t % 70 == 26:
				k |= _J
			if t % 211 == 100:
				k |= _D
			return k)
		hashes.append(p.state_hash())
	check(hashes[0] == hashes[1], "Platform: gli stessi ingressi danno lo stesso stato (hash)")

	# La mappa della stanza si legge, con la partenza e i cartelli.
	var gm := SolidGrid.load_file(TestRoom.MAP)
	var signs_ok := true
	for k: String in TestRoom.SIGNS:
		signs_ok = signs_ok and gm.marks.has(k)
	check(gm.width > 100 and gm.marks.has("G") and signs_ok, "Platform: la mappa della stanza ha partenza e cartelli", "%d×%d" % [gm.width, gm.height])

	# Contro un muro, tenendo la direzione: velocità ferma a zero e animazione da fermo, senza
	# scatti fra fermo e corsa (prima GIG "tremava").
	var sheet := SpriteSheet.get_sheet(&"gig")
	var gm2 := _room(40, 14, 10)
	_box(gm2, 14, 20, 0, 9)
	p = PlatformPlayer.new(PlatformMoves.new(), gm2, sheet)
	p.place(225, 10 * T)
	var pm := p
	var still := [true]
	_run_pp(p, 120, func(t: int) -> int:
		if t >= 60 and (pm.vx != 0 or pm.anim.name != &"idle"):
			still[0] = false
		return _R)
	check(still[0] and p.right() == 14 * T, "Platform: spingendo contro il muro GIG sta fermo, senza tremare",
		"x %d, vx %d, animazione %s" % [p.px, p.vx, p.anim.name])

	# Scivolata con GIÙ e la direzione anche da fermi, insieme o a pochi tick di distanza.
	for gap in [0, 2]:
		p = _pp(g, 125, 10)
		ev = _run_pp(p, 40, func(t: int) -> int:
			var k := _D if t < 20 else 0
			if t >= gap and t < 20:
				k |= _R
			return k)
		check(_count_events(ev, "slide") == 1, "Platform: GIÙ e DESTRA da fermi fanno scivolare (a %d tick)" % gap, "eventi %s" % str(ev))
	# GIÙ da solo accovaccia; la direzione dopo un po' fa camminare accovacciati, senza scivolare.
	p = PlatformPlayer.new(PlatformMoves.new(), g, sheet)
	p.place(125, 10 * T)
	ev = _run_pp(p, 60, func(t: int) -> int: return _D if t < 20 else _D | _R)
	var cw_ok := not sheet.has_anim(&"crouch_walk") or p.anim.name == &"crouch_walk"
	check(_count_events(ev, "slide") == 0 and p.state == PlatformPlayer.State.CROUCH and p.px > 125 and cw_ok,
		"Platform: da accovacciati la direzione fa camminare accovacciati",
		"stato %s, x %d, animazione %s" % [p.state_name(), p.px, p.anim.name])

	# Aggancio e salita con lo sprite: le mani sullo spigolo, e alla fine della salita il busto e
	# il piede più basso sono dove si trova GIG in cima, senza scatti.
	var gk := _room(40, 20, 16)
	_box(gk, 14, 22, 9, 15)
	p = PlatformPlayer.new(PlatformMoves.new(), gk, sheet)
	p.place(250, 16 * T)
	var pk := p
	var rec := {"grip": Vector2i(-99, -99), "hang": 0, "last_feet": Vector2(), "jump": 0.0, "prev_state": -1}
	_run_pp(p, 260, func(t: int) -> int:
		var a := pk.sprite_anchor()
		var fr: AnimFrame = pk.anim.frame()
		var pts: Dictionary = fr.points
		var torso_x: float = fr.hurt[0].position.x + fr.hurt[0].size.x * 0.5
		var feet := Vector2(a) + Vector2(pk.facing * torso_x, maxi(pts["foot_l"].y, pts["foot_r"].y))
		if rec["prev_state"] == PlatformPlayer.State.LEDGE_CLIMB and pk.state == PlatformPlayer.State.GROUND:
			rec["jump"] = feet.distance_to(rec["last_feet"])
		rec["last_feet"] = feet
		rec["prev_state"] = pk.state
		if pk.state == PlatformPlayer.State.LEDGE_HANG:
			rec["hang"] += 1
			rec["grip"] = a + Vector2i(pk.facing * pts["grip"].x, pts["grip"].y)
			return _U if rec["hang"] == 12 else 0
		if rec["hang"] > 0:
			return 0
		return (_R | _J) if t < 25 else _R)
	var corner := Vector2i(14 * T, 9 * T)
	check(rec["hang"] > 0 and absi(rec["grip"].x - corner.x) <= 3 and absi(rec["grip"].y - corner.y) <= 3,
		"Platform: appeso, le mani di GIG sono sullo spigolo", "mani %s, spigolo %s" % [str(rec["grip"]), str(corner)])
	check(p.state == PlatformPlayer.State.GROUND and p.py == 9 * T and rec["jump"] <= 7.5,
		"Platform: a fine salita lo sprite non scatta", "stato %s, scatto di busto e piedi %.1f px, x %d" % [p.state_name(), rec["jump"], p.px])

	# Appeso, le scarpe non entrano mai nel pavimento: contro muri da 5 a 8 blocchi, se GIG si
	# appende, il piede più basso dello sprite resta sopra la riga del pavimento.
	var feet_ok := true
	var feet_info := ""
	var hangs := 0
	for rows in [5, 6, 7, 8]:
		var gh := _room(40, 20, 16)
		_box(gh, 14, 22, 16 - rows, 15)
		p = PlatformPlayer.new(PlatformMoves.new(), gh, sheet)
		p.place(250, 16 * T)
		var ph := p
		var low := [-999]
		_run_pp(p, 120, func(t: int) -> int:
			if ph.state == PlatformPlayer.State.LEDGE_HANG:
				var pts: Dictionary = ph.anim.frame().points
				low[0] = maxi(low[0], ph.sprite_anchor().y + maxi(pts["foot_l"].y, pts["foot_r"].y))
				return 0
			return (_R | _J) if t < 25 else _R)
		if low[0] > -999:
			hangs += 1
			if low[0] > 16 * T - 2:
				feet_ok = false
				feet_info += "muro di %d blocchi: piedi a %d, pavimento a %d; " % [rows, low[0], 16 * T]
	check(feet_ok and hangs >= 2, "Platform: appeso, i piedi di GIG restano sopra il pavimento",
		"%s appeso su %d muri" % [feet_info, hangs])

	# Freno col braccio: in caduta contro un muro GIG scivola piano.
	var gw2 := _room(40, 30, 26)
	_box(gw2, 14, 20, 0, 25)
	p = _pp(gw2, 250, 26)
	var pw2 := p
	var max_fall := [0]
	ev = _run_pp(p, 160, func(t: int) -> int:
		if pw2.state == PlatformPlayer.State.WALL_SLIDE and t > 60:
			max_fall[0] = maxi(max_fall[0], pw2.vy)
		return (_R | _J) if t < 25 else _R)
	check(_count_events(ev, "wall") >= 1 and max_fall[0] > 0 and max_fall[0] <= PlatformPlayer.to_sub(m.wall_slide_speed),
		"Platform: contro il muro il braccio frena la caduta", "eventi %d, caduta massima %d" % [_count_events(ev, "wall"), max_fall[0]])

	# Salto a muro: fra due muri vicini si risale un pozzo.
	var gp := _room(30, 40, 36)
	_box(gp, 8, 9, 0, 35)
	_box(gp, 14, 15, 0, 35)
	p = _pp(gp, 12 * T, 36)
	var ppz := p
	var dir := [1]
	var hold := [0]
	var last := [0]
	_run_pp(p, 600, func(t: int) -> int:
		var k := 0
		if t < 20:
			k = _J | _R
		elif ppz.state == PlatformPlayer.State.WALL_SLIDE:
			if last[0] & _J:
				k = 0
			else:
				dir[0] = -ppz.wall_dir
				hold[0] = 14
				k = _J
		else:
			k = _R if dir[0] > 0 else _L
			if hold[0] > 0:
				hold[0] -= 1
				k |= _J
		last[0] = k
		return k)
	check(p.py < 36 * T - 312, "Platform: con il salto a muro si risale un pozzo", "y %d (partenza %d)" % [p.py, 36 * T])

	# Scatto: in aria, 3 blocchi in avanti, dritto, uno solo per salto.
	p = _pp(gc, 125, 10)
	p.place(125, 125)
	var pd := p
	var d0 := [0, 0, false]
	ev = _run_pp(p, 40, func(t: int) -> int:
		if t == 2:
			d0[0] = pd.px
			d0[1] = pd.py
			return _S | _R
		if pd.state == PlatformPlayer.State.DASH and pd.py != d0[1]:
			d0[2] = true
		if t == 20:
			return _S | _R
		return _R)
	check(_count_events(ev, "scatto") == 1 and not d0[2], "Platform: uno scatto per salto, dritto", "scatti %d, dritto %s" % [_count_events(ev, "scatto"), str(not d0[2])])
	p = _pp(g, 125, 10)
	p.place(125, 75)
	var x0 := p.px
	_run_pp(p, 9, func(t: int) -> int: return _S if t == 0 else 0)
	check(absi(p.px - x0 - 60) <= 5, "Platform: lo scatto fa circa 3 blocchi", "%d px" % (p.px - x0))

	# Corsa sul muro: di corsa contro il muro e SALTO si sale più che col salto; da fermi no.
	var gr := _room(40, 30, 26)
	_box(gr, 20, 25, 0, 25)
	p = _pp(gr, 125, 26)
	var pr := p
	var hit_wall := [false]
	var best := [0]
	ev = _run_pp(p, 140, func(t: int) -> int:
		best[0] = maxi(best[0], 26 * T - pr.py)
		if pr.right() >= 20 * T:
			hit_wall[0] = true
		return (_R | _J) if hit_wall[0] and best[0] == 0 else _R)
	check(_count_events(ev, "wallrun") == 1 and best[0] >= 106 and best[0] <= 150,
		"Platform: la corsa sul muro sale di circa due blocchi più del salto", "corse %d, %d px" % [_count_events(ev, "wallrun"), best[0]])
	p = _pp(gr, 20 * T - 14, 26)
	ev = _run_pp(p, 80, func(t: int) -> int: return (_R | _J) if t < 30 else _R)
	check(_count_events(ev, "wallrun") == 0, "Platform: da fermi contro il muro non c'è la corsa sul muro", "corse %d" % _count_events(ev, "wallrun"))


# --- Platform: zone tossiche e power-up ------------------------------------------------------------

## Una corsia di 60 celle col pavimento alla riga 7: "~" è una zona corta (3 celle), "%" una lunga
## (12 celle); `extra` mette dei segni (power-up) alla riga 6, colonna → segno.
static func _hz_grid(extra: Dictionary = {}) -> SolidGrid:
	var rows := PackedStringArray()
	for y in 8:
		var r := ""
		for x in 60:
			var c := "#" if y == 7 else "."
			if y >= 2 and y <= 6 and x >= 10 and x <= 12:
				c = "~"
			if y >= 2 and y <= 6 and x >= 25 and x <= 36:
				c = "%"
			if y == 6 and extra.has(x):
				c = extra[x]
			r += c
		rows.append(r)
	return SolidGrid.from_rows(rows)


## GIG da x per `ticks` tick coi tasti di fn(t), con le zone e i power-up dati: l'energia che resta
## (partendo da `energy`), il tick del primo danno, le zone e GIG.
func _hz_run(g: SolidGrid, zm: Dictionary, pm: Dictionary, x: int, ticks: int, fn: Callable, energy: int = 120) -> Dictionary:
	var hz := Hazards.new()
	hz.build(g, zm, pm)
	var p := _pp(g, x, 7)
	var e := energy
	var first := -1
	var prev := 0
	for t in ticks:
		var held: int = fn.call(t)
		p.step(InputFrame.new(held, held & ~prev))
		prev = held
		var d := hz.step(t, p, e)
		e -= d
		if d > 0 and first < 0:
			first = t
	return {"energy": e, "first": first, "hz": hz, "p": p}


func _test_hazards() -> void:
	var ok := true
	for id: String in ["bomboletta", "abbonamento", "mascherina", "sovraccarico", "giubbotto", "badge", "ombrello"]:
		var d := Hazards.powerup(id)
		ok = ok and d != null and d.id == StringName(id) and d.label != ""
	for id: String in ["polvere", "fanghi", "gas", "seno", "nube"]:
		var d := Hazards.hazard(id)
		ok = ok and d != null and d.id == StringName(id) and d.damage_s > 0.0
	var pol := Hazards.hazard("polvere")
	check(ok and pol.damage_s == 2.0 and pol.delay_s == 1.0 and pol.cycle_s == 6.0 and pol.active_s == 3.0
		and Hazards.powerup("mascherina").start_amount() == 1200 and Hazards.hazard("fanghi").min_energy == 1
		and Hazards.powerup("bomboletta").start_amount() == 3,
		"Zone e power-up: i tipi del catalogo si leggono coi loro numeri")

	var g := _hz_grid()
	var always := {"tipo": "polvere", "ciclo_s": 6.0, "attiva_s": 6.0}
	var hz := Hazards.new()
	hz.build(g, {"~": always, "%": always})
	check(hz.zones.size() == 2 and hz.zones[0].rect == Rect2i(200, 40, 60, 100) and hz.zones[1].rect == Rect2i(500, 40, 240, 100),
		"Zone: ogni gruppo di celle col segno diventa un rettangolo", "%d zone" % hz.zones.size())

	# Chi passa svelto non paga: la zona corta si attraversa in meno di un secondo.
	var r := _hz_run(g, {"~": always}, {}, 150, 80, func(_t: int) -> int: return _R)
	check(r["energy"] == 120 and r["p"].px > 300, "Zone: chi passa svelto non paga", "energia %d, x %d" % [r["energy"], r["p"].px])
	# Chi resta dentro paga dopo 1 s, poi 2 punti al secondo: un punto ogni 30 tick.
	r = _hz_run(g, {"%": always}, {}, 600, 360, func(_t: int) -> int: return 0)
	check(r["energy"] == 110 and r["first"] >= 60 and r["first"] <= 90, "Zone: dentro la polvere si paga dopo 1 s, poi 2 punti al secondo",
		"energia %d, primo danno al tick %d" % [r["energy"], r["first"]])
	# A raffiche (3 s accesa ogni 6): si paga solo da accesa, e il ritardo riparte a ogni raffica.
	r = _hz_run(g, {"%": {"tipo": "polvere"}}, {}, 600, 720, func(_t: int) -> int: return 0)
	var z: Hazards.Zone = r["hz"].zones[0]
	check(r["energy"] == 112 and z.warning(330) and not z.warning(329) and not z.is_active(359) and z.is_active(360),
		"Zone: la polvere va a raffiche, col preavviso di mezzo secondo", "energia %d" % r["energy"])
	# La mascherina: la si prende davanti alla polvere e la si passa senza danno.
	r = _hz_run(_hz_grid({20: "1"}), {"%": always}, {"1": "mascherina"}, 300, 200, func(_t: int) -> int: return _R)
	var rh: Hazards = r["hz"]
	check(r["energy"] == 120 and r["p"].px > 760 and rh.held != null and rh.held.id == &"mascherina" and rh.left < rh.total,
		"Power-up: con la mascherina la polvere non fa male", "energia %d, x %d" % [r["energy"], r["p"].px])
	# Uno alla volta: il nuovo sostituisce il vecchio; l'abbonamento agisce subito e non tocca quello che si ha.
	Game.reset_run()
	Game.lives = 2
	r = _hz_run(_hz_grid({16: "1", 19: "3", 22: "2", 40: "2"}), {}, {"1": "mascherina", "3": "sovraccarico", "2": "abbonamento"}, 300, 200,
		func(_t: int) -> int: return _R)
	rh = r["hz"]
	check(rh.held != null and rh.held.id == &"sovraccarico" and rh.damage_mult() == 2 and rh.breaks_guard() and not rh.immune(),
		"Power-up: uno alla volta, il nuovo sostituisce il vecchio", "ha %s" % (rh.held.id if rh.held != null else &"niente"))
	check(Game.lives == 3 and rh.toast == "RINNOVATO", "Power-up: l'abbonamento dà una vita, fino a tre",
		"vite %d, scritta %s" % [Game.lives, rh.toast])
	Game.reset_run()
	# I fanghi rallentano e non portano l'energia sotto 1.
	r = _hz_run(g, {"%": {"tipo": "fanghi"}}, {}, 500, 60, func(_t: int) -> int: return _R, 2)
	var free := _hz_run(g, {}, {}, 500, 60, func(_t: int) -> int: return _R)
	check(r["energy"] == 1 and r["p"].px < free["p"].px - 50, "Zone: i fanghi rallentano e non uccidono da soli",
		"energia %d, x %d contro %d" % [r["energy"], r["p"].px, free["p"].px])
	# L'ombrello: in caduta, tenendo SALTO, si plana; il tempo passa solo planando.
	var tall := _room(20, 40, 39)
	var hu := Hazards.new()
	hu.build(tall)
	hu._take(Hazards.powerup("ombrello"))
	var pu := PlatformPlayer.new(PlatformMoves.new(), tall)
	pu.place(200, 100)
	var max_vy := 0
	for t in 90:
		pu.step(InputFrame.new(_J, _J if t == 0 else 0))
		hu.step(t, pu, 120)
		if t > 40:
			max_vy = maxi(max_vy, pu.vy)
	var pn := PlatformPlayer.new(PlatformMoves.new(), tall)
	pn.place(200, 100)
	for t in 90:
		pn.step(InputFrame.new(_J, _J if t == 0 else 0))
	check(max_vy <= PlatformPlayer.to_sub(0.9) and pu.py < pn.py - 100 and hu.left < hu.total and hu.left > hu.total - 90,
		"Power-up: con l'ombrello si plana tenendo SALTO, e il tempo passa solo planando",
		"vy %d, y %d contro %d, resta %d/%d" % [max_vy, pu.py, pn.py, hu.left, hu.total])
	# Il giubbotto assorbe tre colpi, la bomboletta ha tre usi, il badge si spegne attaccando.
	var hg := Hazards.new()
	hg._take(Hazards.powerup("giubbotto"))
	var absorbed := [hg.absorb_hit(), hg.absorb_hit(), hg.absorb_hit(), hg.absorb_hit()]
	hg._take(Hazards.powerup("bomboletta"))
	var used := [hg.use(), hg.use(), hg.use(), hg.use()]
	hg._take(Hazards.powerup("badge"))
	var hidden := hg.invisible()
	hg.on_attack()
	check(absorbed == [true, true, true, false] and used == [true, true, true, false] and hidden and not hg.invisible(),
		"Power-up: giubbotto da tre colpi, bomboletta da tre usi, badge che si spegne attaccando",
		"%s %s %s" % [absorbed, used, hidden])

	# Dal livello LDtk: i campi maggiori di zero cambiano il tipo, gli altri lo lasciano.
	var gl := _room(40, 10, 9)
	gl.entities.append({"tipo": "Tossica", "pos": Vector2i(100, 80), "size": Vector2i(120, 100),
		"campi": {"tipo": "gas", "danno_s": 0.0, "ritardo_s": 0.5, "ciclo_s": 0.0, "attiva_s": 0.0}})
	gl.entities.append({"tipo": "PowerUp", "pos": Vector2i(300, 160), "size": Vector2i(20, 20),
		"campi": {"tipo": "badge", "ricompare": false}})
	var hl := Hazards.new()
	hl.build(gl)
	var zl: Hazards.Zone = hl.zones[0] if not hl.zones.is_empty() else null
	var ok_l := zl != null and zl.def.id == &"gas" and zl.damage10 == 40 and zl.delay_t == 30 and zl.cycle_t == 240 \
		and zl.active_t == 90 and zl.rect == Rect2i(100, 80, 120, 100) and hl.pickups.size() == 1 and not hl.pickups[0].respawns
	if ok_l:
		hl.pickups[0].taken = true
		hl.reset()
		ok_l = hl.pickups[0].taken
		hl.reset(true)
		ok_l = ok_l and not hl.pickups[0].taken
	check(ok_l, "Zone e power-up: dal livello LDtk, coi campi che cambiano il tipo; senza «ricompare» un power-up non torna")


## Nella stanza di prova: le due polveri, la mascherina e l'abbonamento; a energia zero si ricomincia,
## con le vite se ne perde una.
func _test_room_hazards() -> void:
	var gm := SolidGrid.load_file(TestRoom.MAP)
	var m: Vector2i = gm.marks["m"][0]
	var gx: Vector2i = gm.marks["g"][0]
	var runs: Array[Dictionary] = []
	for k in 2:
		var room := _hack_room(Vector2i(m.x - 40, m.y), Callable(), ["P"])
		room.hacks_done["P"] = 1
		Game.lives = 2
		var tall: Hazards.Zone = room.hazards.zones[1]
		var out := {"masked": false, "e_in": -1, "e_out": -1, "end": -1}
		for t in 2400:
			room._sim_tick()
			var inside := room.player.right() > tall.rect.position.x and room.player.left() < tall.rect.end.x
			if inside and out["e_in"] < 0:
				out["e_in"] = Game.energy
				out["masked"] = room.hazards.immune()
			if out["e_in"] >= 0 and out["e_out"] < 0 and room.player.left() > tall.rect.end.x:
				out["e_out"] = Game.energy
			if room.player.px >= gx.x - 20 and out["end"] < 0:
				out["end"] = t
			if out["end"] >= 0 and t > out["end"] + 120:
				break
		out["zones"] = room.hazards.zones.size()
		out["pickups"] = room.hazards.pickups.size()
		out["lives"] = Game.lives
		out["hash"] = room.state_hash()
		runs.append(out)
		_free_room(room)
	var a := runs[0]
	check(a["zones"] == 2 and a["pickups"] == 2, "Stanza: in fondo ci sono le due polveri, la mascherina e l'abbonamento",
		"%d zone, %d power-up" % [a["zones"], a["pickups"]])
	check(a["masked"] and a["e_in"] > 0 and a["e_out"] == a["e_in"] and a["lives"] == 3 and a["end"] > 0,
		"Stanza: il pilota prende la mascherina, passa la polvere alta senza danno, prende l'abbonamento e arriva in fondo",
		"maschera %s, energia %d → %d, vite %d, fine %d" % [a["masked"], a["e_in"], a["e_out"], a["lives"], a["end"]])
	check(runs[0]["hash"] == runs[1]["hash"] and runs[0]["end"] == runs[1]["end"], "Stanza: due giri nelle zone tossiche vengono uguali")

	# A energia zero: nella stanza si ricomincia con l'energia piena, con le vite se ne perde una.
	var tz: Rect2i = Hazards._components(gm.marks["%"])[0]
	var inside_at := Vector2i(tz.get_center().x, gm.marks["n"][0].y)
	var room2 := _hack_room(inside_at, func(_t: int) -> int: return 0)
	Game.energy = 1
	var refilled := -1
	for t in 200:
		room2._sim_tick()
		if Game.energy == Game.ENERGY_MAX:
			refilled = t
			break
	check(refilled >= 60 and refilled <= 95, "Energia: a zero nella stanza si ricomincia, con l'energia piena", "tick %d" % refilled)
	_free_room(room2)
	var room3 := _hack_room(inside_at, func(_t: int) -> int: return 0)
	room3.use_lives = true
	Game.energy = 1
	for t in 100:
		room3._sim_tick()
	check(room3.fall_t >= 0 and Game.lives == 2 and Game.energy == 0, "Energia: a zero, con le vite, se ne perde una",
		"buio %d, vite %d, energia %d" % [room3.fall_t, Game.lives, Game.energy])
	_free_room(room3)
	Game.reset_run()


# --- Platform: i droni (Colomba, Vedetta, Segugio) ---------------------------------------------------

## Una corsia di 60 celle col pavimento alla riga 12 (y = 240) e un drone per ogni voce di `ds`:
## [tipo, cella, stato, colonne del percorso].
static func _dr_grid(ds: Array) -> SolidGrid:
	var rows := PackedStringArray()
	for y in 13:
		rows.append("#".repeat(60) if y == 12 else ".".repeat(60))
	var g := SolidGrid.from_rows(rows)
	var i := 0
	for d: Array in ds:
		var c: Vector2i = d[1]
		var path: Array = []
		for col: int in d[3]:
			path.append(Vector2i(col, c.y))
		g.entities.append({"tipo": "Nemico", "iid": "d%d" % i, "livello": "T", "pos": c, "size": Vector2i(25, 100),
			"px": Vector2i(c.x * SolidGrid.TILE + SolidGrid.TILE / 2, (c.y + 1) * SolidGrid.TILE),
			"campi": {"tipo": d[0], "stato": d[2], "percorso": path}})
		i += 1
	return g


## GIG da x (in aria se `y` è sopra il pavimento) per `ticks` tick coi tasti di fn(t), coi droni
## della griglia: il danno, gli eventi dei droni e di GIG, il primo tick col danno.
func _dr_run(g: SolidGrid, x: int, y: int, ticks: int, fn: Callable) -> Dictionary:
	var dr := Drones.new()
	dr.build(g)
	var p := PlatformPlayer.new(PlatformMoves.new(), g)
	p.place(x, y)
	p.can_jab = true
	var dmg := 0
	var first := -1
	var ev: Array = []
	var pev: Array = []
	var blind := 0
	var prev := 0
	for t in ticks:
		var held: int = fn.call(t)
		p.step(InputFrame.new(held, held & ~prev))
		prev = held
		var n := p.events.size()
		var d := dr.step(p)
		for e in p.events:
			pev.append(e)
		for e: Array in dr.events:
			ev.append(e[0])
		blind = maxi(blind, dr.blind_t)
		dmg += d
		if d > 0 and first < 0:
			first = t
	return {"dmg": dmg, "first": first, "ev": ev, "pev": pev, "dr": dr, "p": p, "blind": blind,
		"hash": hash([p.state_hash(), dr.state_hash()])}


func _test_drones() -> void:
	var still := func(_t: int) -> int: return 0
	var right := func(_t: int) -> int: return InputFrame.RIGHT
	# Il Segugio: GIG fermo davanti, al limite della vista. Il primo scatto si ferma corto (la vista
	# arriva più in là dello scatto), ma il Segugio si avvicina e al secondo morde: 8 e una spinta.
	var r := _dr_run(_dr_grid([["segugio", Vector2i(30, 11), "ronda", [20, 40]]]), 760, 240, 300, still)
	var ev: Array = r["ev"]
	var bite := ev.find("morso")
	check(ev.find("abbaio") == 0 and ev.find("scatto_segugio") == 1 and bite > 2 and r["dmg"] >= Drones.DASH_DAMAGE
		and (r["pev"] as Array).has("colpito"),
		"Segugio: abbaia e scatta; il primo scatto resta corto, chi resta fermo viene morso al secondo (8 e una spinta)",
		"eventi %s, danno %d" % [str(ev), r["dmg"]])
	var r2 := _dr_run(_dr_grid([["segugio", Vector2i(30, 11), "ronda", [20, 40]]]), 760, 240, 300, still)
	check(r["hash"] == r2["hash"], "Droni: due giri uguali vengono uguali")
	# Alle spalle, entro 3 celle: lo fiuta, dopo mezzo secondo si gira e abbaia.
	r = _dr_run(_dr_grid([["segugio", Vector2i(30, 11), "ronda", [20, 40]]]), 540, 240, 120, still)
	var dg: Drones.Drone = (r["dr"] as Drones).drones[0]
	check((r["ev"] as Array).has("abbaio") and dg.dir == -1, "Segugio: GIG alle spalle, lo fiuta, si gira e abbaia",
		"eventi %s, verso %d" % [str(r["ev"]), dg.dir])
	# Saltandolo mentre scatta, non morde.
	var hop := func(t: int) -> int: return InputFrame.JUMP if t >= 30 and t < 50 else 0
	r = _dr_run(_dr_grid([["segugio", Vector2i(30, 11), "ronda", [20, 40]]]), 720, 240, 140, hop)
	check((r["ev"] as Array).has("scatto_segugio") and not (r["ev"] as Array).has("morso"),
		"Segugio: chi lo salta mentre scatta non viene morso", "eventi %s, danno %d" % [str(r["ev"]), r["dmg"]])

	# Il salto in testa: GIG cade sul dorso, il Segugio si rompe e GIG rimbalza, senza danno.
	r = _dr_run(_dr_grid([["segugio", Vector2i(30, 11), "fermo", []]]), 610, 120, 40, still)
	var dr: Drones = r["dr"]
	check(dr.is_broken("d0") and r["dmg"] == 0 and (r["pev"] as Array).has("rimbalzo"),
		"Droni: un salto in testa li rompe al primo colpo, e GIG ci rimbalza sopra",
		"rotto %s, danno %d, eventi %s" % [dr.is_broken("d0"), r["dmg"], str(r["pev"])])

	# Il jab: sul Segugio che non ansima fa solo «tonk»; la Colomba posata si rompe e il gradino sparisce.
	var press := func(t: int) -> int: return InputFrame.ATTACK if t == 2 else 0
	r = _dr_run(_dr_grid([["segugio", Vector2i(21, 11), "fermo", []]]), 360, 240, 20, press)
	dr = r["dr"]
	check(not dr.is_broken("d0") and (r["ev"] as Array).has("corazza"), "Segugio: il jab rimbalza sulla corazza, se non ansima",
		"eventi %s" % str(r["ev"]))
	var gc := _dr_grid([["colomba", Vector2i(20, 11), "fermo", []]])
	var dc := Drones.new()
	dc.build(gc)
	dc.reset()
	var perch := gc.cell(20, 11) == SolidGrid.Cell.THIN
	gc.set_cell(20, 11, SolidGrid.Cell.EMPTY)
	r = _dr_run(gc, 370, 240, 20, press)
	dr = r["dr"]
	dr.reset()
	check(perch and dr.is_broken("d0") and gc.cell(20, 11) == SolidGrid.Cell.EMPTY and r["dmg"] == 0,
		"Colomba: posata fa da gradino; col jab si rompe e il gradino sparisce",
		"gradino %s, rotta %s, cella %d" % [perch, dr.is_broken("d0"), gc.cell(20, 11)])

	# Il segno a portata di jab: il riquadro è quello del colpo vero, nei tick in cui colpisce, e lo
	# porta solo il drone che una Persona chiede e non ha ancora avuto.
	var pj := PlatformPlayer.new(PlatformMoves.new(), _dr_grid([]))
	pj.place(600, 240)
	pj.can_jab = true
	var same := true
	var seen := 0
	var pprev := 0
	for t in 14:
		var held: int = InputFrame.ATTACK if t == 1 else 0
		pj.step(InputFrame.new(held, held & ~pprev))
		pprev = held
		var jb := pj.jab_box()
		if jb.has_area():
			seen += 1
			same = same and jb == Drones.jab_reach(pj)
	var fv := Favors.new()
	var qa := Favors.Person.new()
	qa.serve = "v1"
	var qb := Favors.Person.new()
	qb.serve = "v2"
	qb.thanked = true
	fv.persone.append(qa)
	fv.persone.append(qb)
	var want := fv.wanted_drones()
	check(seen > 0 and same and want.size() == 1 and want[0] == "v1",
		"Droni: il segno «a portata di jab» usa il riquadro del colpo vero, e solo sul drone chiesto da una Persona",
		"tick col colpo %d, uguali %s, chiesti %s" % [seen, same, str(want)])

	# La Colomba in ronda: GIG sotto, la lente si accende, scende e spruzza; acceca, niente danno.
	r = _dr_run(_dr_grid([["colomba", Vector2i(20, 4), "ronda", [15, 25]]]), 410, 240, 120, still)
	ev = r["ev"]
	check(ev.find("colomba_lente") >= 0 and ev.find("spruzzo") > ev.find("colomba_lente") and r["blind"] > 0 and r["dmg"] == 0,
		"Colomba: GIG sotto, si accende la lente, poi scende e spruzza: acceca e non toglie energia",
		"eventi %s, accecato %d, danno %d" % [str(ev), r["blind"], r["dmg"]])

	# La Vedetta: GIG nel cono per 1 s, luce rossa, sirena, sigillo; incollato si stacca con 8 tasti.
	var mash := func(t: int) -> int: return InputFrame.JUMP if t > 200 and t % 4 == 0 else 0
	r = _dr_run(_dr_grid([["vedetta", Vector2i(20, 3), "ronda", [15, 25]]]), 480, 240, 320, mash)
	ev = r["ev"]
	var pev: Array = r["pev"]
	check(ev.find("faro_rosso") >= 0 and ev.find("sirena") > ev.find("faro_rosso") and ev.find("sigillo_sparato") > ev.find("sirena")
		and ev.has("pignorato") and r["dmg"] == Drones.SEAL_DAMAGE and pev.has("sigillo") and pev.has("staccato")
		and pev.count("strappo") == Drones.SEAL_PRESSES - 1,
		"Vedetta: vede GIG, luce rossa, sirena e sigillo «pignorato» da 6; si stacca con 8 tasti",
		"eventi %s, danno %d, strappi %d" % [str(ev), r["dmg"], pev.count("strappo")])
	# Sotto una tettoia il faro non arriva.
	var gt := _dr_grid([["vedetta", Vector2i(20, 3), "ronda", [15, 25]]])
	for x in range(18, 32):
		gt.set_cell(x, 6, SolidGrid.Cell.THIN)
	r = _dr_run(gt, 480, 240, 300, still)
	check(not (r["ev"] as Array).has("faro_rosso"), "Vedetta: sotto una tettoia GIG non si vede", "eventi %s" % str(r["ev"]))

	# I droni del prologo: sei Colombe in A; in B tre Vedette in ronda, quella della bici e il Segugio.
	var count := func(level: String) -> Dictionary:
		var d := Drones.new()
		d.build(SolidGrid.load_file(Prologue.PROLOGUE_MAP + "#" + level))
		var c := {}
		for x in d.drones:
			c[x.tipo] = int(c.get(x.tipo, 0)) + 1
		return c
	var ca: Dictionary = count.call("Prologo_A_Cimitero")
	var cb: Dictionary = count.call("Prologo_B_Fuga")
	check(ca.get("colomba", 0) == 6 and cb.get("vedetta", 0) == 4 and cb.get("segugio", 0) == 1,
		"Droni: il prologo ha sei Colombe al cimitero, quattro Vedette e un Segugio nella Fuga", "A %s, B %s" % [ca, cb])


# --- Platform: i favori (ristori, oggetti, Persone e battute) ---------------------------------------

## La corsia dei droni con le entità dei favori: [tipo, iid, x, y, campi], coi piedi a (x, y).
static func _fv_grid(ents: Array, drones: Array = []) -> SolidGrid:
	var g := _dr_grid(drones)
	for e: Array in ents:
		g.entities.append({"tipo": e[0], "iid": e[1], "livello": "T", "px": Vector2i(e[2], e[3]),
			"pos": Vector2i(e[2] / SolidGrid.TILE, e[3] / SolidGrid.TILE - 1), "size": Vector2i(20, 20), "campi": e[4]})
	return g


## Gli sprite veri del Segugio e della Vedetta: ogni fase ha la sua animazione, i punti per gli aloni
## e la luce del fotogramma; la Colomba resta greybox. Il disegno non tocca la simulazione.
func _test_drone_sprites() -> void:
	var dr := Drones.new()
	var need := {"vedetta": ["patrol", "spot", "broken"],
		"segugio": ["idle", "patrol", "sniff", "bark", "dash", "pant", "broken"]}
	var pts := {"vedetta": ["beacon", "lamp"], "segugio": ["eye", "beacon", "vent", "collar"]}
	for tipo: String in need:
		var sh := dr._sheet(tipo)
		var miss: Array = []
		var bad: Array = []
		if sh != null:
			for a: String in need[tipo]:
				if not sh.has_anim(StringName(a)):
					miss.append(a)
					continue
				for f in sh.clip(StringName(a)).frames:
					var lit := f.tags & (AnimFrame.TAG_LIGHT_PATROL | AnimFrame.TAG_LIGHT_ALERT | AnimFrame.TAG_LIGHT_OFF)
					for k: String in pts[tipo]:
						if not f.points.has(k):
							bad.append("%s senza %s" % [a, k])
					if lit == 0:
						bad.append("%s senza luce" % a)
		check(sh != null and sh.has_normals and miss.is_empty() and bad.is_empty() and sh.warnings.is_empty(),
			"Droni: lo sprite di %s ha animazioni, normal map, punti e luci" % tipo,
			"mancano %s; %s; avvisi %s" % [miss, bad.slice(0, 3), sh.warnings.slice(0, 3) if sh != null else []])
	check(dr._sheet("colomba") == null, "Droni: la Colomba resta greybox", "")
	# Ogni fase porta a un'animazione che c'è, a destra e a sinistra il fotogramma è lo stesso.
	var missing: Array = []
	for tipo: String in need:
		var d := Drones.Drone.new()
		d.tipo = tipo
		for ph: int in Drones.Phase.values():
			d.phase = ph
			for br: bool in [false, true]:
				d.broken = br
				var n := dr.anim_name(d)
				if not (n in need[tipo].map(func(a: String) -> StringName: return StringName(a))) or dr._sprite_frame(d, 37) == null:
					missing.append("%s/%d/%s" % [tipo, ph, n])
	check(missing.is_empty(), "Droni: ogni fase del Segugio e della Vedetta ha la sua animazione", str(missing.slice(0, 4)))
	# La Vedetta che punta GIG dopo lo spintone ha la luce d'avviso, quella rotta è spenta.
	var dv := Drones.Drone.new()
	dv.tipo = "vedetta"
	dv.lock = 5
	var fl := dr._sprite_frame(dv, 3)
	dv.broken = true
	var fb := dr._sprite_frame(dv, 3)
	check(fl != null and fl.has_tag(AnimFrame.TAG_LIGHT_ALERT) and fb != null and fb.has_tag(AnimFrame.TAG_LIGHT_OFF),
		"Droni: la Vedetta che punta GIG è in avviso, quella rotta è spenta", "")

## I perdoni veri della processione: le animazioni coi tempi del gioco (la nazzicata alla velocità
## della fila, barcollo e scansa lunghi quanto la fila aperta) e quale tocca a chi.
func _test_procession_sprites() -> void:
	var pr := Processions.new()
	var sh := pr._sheet()
	var ok := sh != null and sh.has_normals and sh.warnings.is_empty()
	var info := ""
	if ok:
		for a: String in ["nazzica", "barcollo", "scansa", "idle"]:
			if not sh.has_anim(StringName(a)):
				ok = false
				info += " manca " + a
		if ok:
			var tot := [sh.clip(&"nazzica").total_ticks(), sh.clip(&"barcollo").total_ticks(), sh.clip(&"scansa").total_ticks()]
			ok = tot == [2 * Processions.NAZZICA_PHASE, Processions.PUSH_OPEN, Processions.PUSH_OPEN] \
				and sh.clip(&"nazzica").loop and not sh.clip(&"barcollo").loop
			info = str(tot)
	check(ok, "Processione: lo sprite dei perdoni ha nazzica, barcollo, scansa e idle coi tempi del gioco", info)
	var w := Processions.Walk.new()
	w.dir = 1
	w.moving = true
	var walk := [Processions.anim_name(w, 0), Processions.anim_name(w, 1)]
	w.moving = false
	var still := Processions.anim_name(w, 0)
	w.open_t = Processions.PUSH_OPEN
	var push := [Processions.anim_name(w, 0), Processions.anim_name(w, 1)]
	w.dir = -1
	var push_left := [Processions.anim_name(w, 0), Processions.anim_name(w, 1)]
	check(walk == [&"nazzica", &"nazzica"] and still == &"idle" and push == [&"barcollo", &"scansa"] \
			and push_left == [&"scansa", &"barcollo"],
		"Processione: barcolla quello di coda, si scansa quello davanti, nazzica chi avanza",
		"%s %s %s %s" % [walk, still, push, push_left])
	# I due della coppia vanno sfasati di mezzo ciclo.
	w.open_t = 0
	w.moving = true
	var f0 := pr.brother_frame(w, 0, 10)
	var f1 := pr.brother_frame(w, 1, 10 + Processions.NAZZICA_PHASE)
	var f2 := pr.brother_frame(w, 1, 10)
	check(f0 != null and f0 == f1 and f0 != f2, "Processione: i due confratelli nazzicano sfasati", "")

## Le firme di Totò (le tag REVENGE): si prendono passandoci sopra, una volta sola, e restano prese
## alla ripartenza; quelle in alto non si prendono da terra. Nella Fuga del prologo ce ne sono tre.
func _test_firme() -> void:
	var right := func(_t: int, _p: PlatformPlayer, _f: Favors) -> int: return InputFrame.RIGHT
	var tags := [["Firma", "f1", 500, 220, {"numero": 1}], ["Firma", "f2", 600, 60, {"numero": 2}]]
	var r := _fv_run(_fv_grid(tags), 300, 200, right)
	var fv: Favors = r["fv"]
	check(not fv.is_empty() and fv.firme.size() == 2 and fv.firme[0].numero == 1 and fv.firme[0].taken
		and not fv.firme[1].taken and (r["ev"] as Array).count("firma") == 1 and fv.firme_prese() == 1,
		"Firme: GIG prende la tag passandoci sopra, quella in alto resta", "eventi %s" % str(r["ev"]))
	var r2 := _fv_run(_fv_grid(tags), 300, 200, right)
	check(r["hash"] == r2["hash"], "Firme: due giri uguali vengono uguali")
	fv.reset()
	var kept := fv.firme[0].taken
	fv.reset(true)
	check(kept and not fv.firme[0].taken, "Firme: la tag presa resta presa alla ripartenza, non a partita nuova", "")
	var fb := Favors.new()
	fb.build(SolidGrid.load_file(Prologue.PROLOGUE_MAP + "#Prologo_B_Fuga"))
	var nums: Array = []
	for f in fb.firme:
		nums.append(f.numero)
	nums.sort()
	check(nums == [1, 2, 3] and fb.tag_sheet() != null and fb.tag_sheet().has_anim(&"accesa") and fb.tag_sheet().has_anim(&"presa"),
		"Firme: nella Fuga del prologo ci sono le tre tag REVENGE, con lo sprite accesa e presa", str(nums))

## I Rompibili: pieni finché GIG non li sfonda di spalla. Dopo il riavvio con lo scatto: a terra SCATTO
## parte solo con un Rompibile davanti, in aria lo scatto rompe quello che incontra. Prima del riavvio,
## col braccio bloccato, a piena corsa. Il muro pieno resta.
func _test_breakables() -> void:
	# Un muro alla colonna 20, con una porta marcia alta quanto GIG (righe 10-14) sul pavimento (riga 15).
	var door := func(rompibile: bool) -> SolidGrid:
		var g := _room(40, 20, 15)
		_box(g, 20, 20, 0, 14)
		if rompibile:
			for y in range(10, 15):
				g.breakable[y * g.width + 20] = true
		return g
	var push := func(t: int) -> int: return _R | (_S if t == 20 else 0)
	var g: SolidGrid = door.call(true)
	var p := _pp(g, 340, 15)
	var ev := _run_pp(p, 60, push)
	var names: Array = []
	for e: Array in ev:
		names.append(e[1])
	check(g.cell(20, 12) == SolidGrid.Cell.EMPTY and g.cell(20, 9) == SolidGrid.Cell.SOLID and g.broken.size() == 5
		and g.breakable.is_empty() and p.px > 420 and names.count("rompe") == 1,
		"Rompibili: la spallata rompe la porta marcia e GIG passa", "GIG %d, rotte %d, eventi %s" % [p.px, g.broken.size(), names])
	var g2: SolidGrid = door.call(false)
	var p2 := _pp(g2, 340, 15)
	_run_pp(p2, 60, push)
	check(g2.cell(20, 12) == SolidGrid.Cell.SOLID and p2.px < 400 and p2.state != PlatformPlayer.State.DASH,
		"Rompibili: davanti a un muro pieno SCATTO a terra non fa niente", "GIG %d" % p2.px)
	# Dopo il riavvio la corsa da sola non rompe: ci vuole lo scatto.
	var run := func(_t: int) -> int: return _R
	var g5: SolidGrid = door.call(true)
	var p5 := _pp(g5, 240, 15)
	_run_pp(p5, 60, run)
	check(g5.broken.is_empty() and p5.px < 400, "Rompibili: dopo il riavvio la corsa senza scatto non rompe", "rotte %d" % g5.broken.size())
	# Col braccio bloccato (prima del riavvio): a piena corsa la spalla sfonda la porta, appoggiati no.
	var g3: SolidGrid = door.call(true)
	var p3 := _pp(g3, 240, 15)
	p3.arm_locked = true
	var ev3 := _run_pp(p3, 70, run)
	check(g3.broken.size() == 5 and p3.px > 420 and _count_events(ev3, "rompe") == 1,
		"Rompibili: col braccio bloccato la porta si sfonda a piena corsa", "GIG %d, rotte %d" % [p3.px, g3.broken.size()])
	var g6: SolidGrid = door.call(true)
	var p6 := _pp(g6, 384, 15)
	p6.arm_locked = true
	_run_pp(p6, 40, push)
	check(g6.broken.is_empty() and p6.px < 400, "Rompibili: col braccio bloccato, senza rincorsa, la porta resta",
		"GIG %d, rotte %d" % [p6.px, g6.broken.size()])
	# In aria: una parete di cassette alta (righe 4-11, sopra il pavimento una fessura di 3 celle piene).
	var g4 := _room(40, 20, 15)
	_box(g4, 20, 20, 0, 14)
	for y in range(4, 12):
		g4.breakable[y * g4.width + 20] = true
	var p4 := _pp(g4, 340, 15)
	var hop := func(t: int) -> int: return _R | (_J if t >= 2 and t < 14 else 0) | (_S if t == 14 else 0)
	_run_pp(p4, 80, hop)
	check(g4.broken.size() == 8 and p4.px > 420, "Rompibili: lo scatto in aria rompe la parete e GIG passa",
		"GIG %d,%d, rotte %d" % [p4.px, p4.py, g4.broken.size()])
	# Nel prologo: la porticina di A4 sono le sei celle Rompibile della colonna 188, righe 22-27.
	var ga := SolidGrid.load_file(Prologue.PROLOGUE_MAP + "#Prologo_A_Cimitero")
	var cells: Array = ga.breakable.keys()
	cells.sort()
	var want: Array = []
	for y in range(22, 28):
		want.append(y * ga.width + 188)
	check(cells == want, "Rompibili: in A la porticina della scala è Rompibile", str(cells))

## I raccordi fra gioco e murale (l'aggancio): aprendo MP13 la telecamera del gioco va dove lo sprite di
## GIG combacia con la sua figura, la figura compare per prima e lo spray parte da lei; sciogliendo MP08
## il murale se ne va dai bordi verso la figura di GIG, che sfuma per ultima.
func _test_scene_hook() -> void:
	var sd := SceneData.load_scene(Prologue.PASSAGGIO)
	check(sd.errors.is_empty() and str((sd.steps[1] as Dictionary).get("aggancio", "")) == "gig",
		"Aggancio: il passaggio al capitolo 1 aggancia MP13 a GIG", "; ".join(sd.errors))
	var room := _prologue_room(Callable(), Prologue.PROLOGUE_MAP)
	# GIG come al fermo del prologo: in aria, sulla posa della figura.
	room.player.anim.show_frame(&"jump_arc", Prologue.OUTRO_ARC)
	room._scene_request = {"id": Prologue.PASSAGGIO, "poses": {"gig": room.scene_pose_player("")}}
	room._start_scene()
	var sp := room.scene
	var frames := 0
	while sp.mural() == null and frames < 200:
		room._scene_frame()
		frames += 1
	var m := sp.mural()
	check(m != null and m.hooked == "gig" and frames >= ScenePlayer.HOOK_TICKS and frames <= ScenePlayer.HOOK_TICKS + 3,
		"Aggancio: prima la telecamera del gioco va su GIG, poi il murale", "fotogramma %d" % frames)
	if m == null:
		_free_room(room)
		return
	var p: ScenePuppet = sp.puppets["gig"]
	var sr := p.body_rect()
	var z := room.zoom
	var s_feet := room._view.position + Vector2(sr.get_center().x, sr.end.y) * z
	var fr := m.figure_rect("gig")
	var v := m.view()
	var f_feet := View.SIZE / 2.0 + (Vector2(fr.get_center().x, fr.end.y) - Vector2(v[0])) * float(v[1])
	# La figura è la stessa posa dello sprite: altezza e larghezza combaciano tutte e due (entro un pixel
	# del gioco a zoom 2); lo zoom del gioco è il 2 intero chiesto dal passaggio ("aggancio_zoom").
	var s_size := sr.size * z
	var f_size := fr.size * float(v[1])
	check(s_feet.distance_to(f_feet) <= 3.0 and absf(s_size.y - f_size.y) <= 1.0 and absf(s_size.x - f_size.x) <= 2.0
			and is_equal_approx(z, 2.0),
		"Aggancio: all'apertura di MP13 lo sprite di GIG e la sua figura combaciano (piedi e grandezza), a zoom 2",
		"sprite %s grande %s, figura %s grande %s, zoom del gioco %.2f" % [s_feet, s_size, f_feet, f_size, z])
	# Le gocce cyan sotto i piedi della figura non sono corpo: i piedi sono quelli veri.
	var tex_h := 0.0
	for f: Dictionary in m._figures:
		if str(f["name"]) == "gig":
			tex_h = (f["tex"] as Texture2D).get_size().y
	check(fr.size.y > 60.0 and fr.size.y < tex_h - 10.0,
		"Aggancio: il corpo della figura di MP13 non conta le gocce sotto i piedi", "alto %.0f su %.0f" % [fr.size.y, tex_h])
	for i in SceneMural.HOOK_FADE_TICKS:
		room._scene_frame()
	var fig_a := 0.0
	var other_a := 1.0
	for f: Dictionary in m._figures:
		if str(f["name"]) == "gig":
			fig_a = (f["sprite"] as Sprite2D).modulate.a
		else:
			other_a = minf(other_a, (f["sprite"] as Sprite2D).modulate.a)
	check(m.amount() < 0.4 and fig_a >= 0.99 and other_a == 0.0 and p.modulate.a <= 0.01
			and is_equal_approx(float(m._mat.get_shader_parameter(&"focus_mix")), SceneMural.HOOK_MIX)
			and Vector2(m._mat.get_shader_parameter(&"focus")) == fr.get_center(),
		"Aggancio: la figura compare per prima, le altre a fine spray, lo sprite sfuma sotto di lei e lo spray parte dalla figura",
		"spray %.2f, figura %.2f, altre %.2f, sprite %.2f" % [m.amount(), fig_a, other_a, p.modulate.a])
	_free_room(room)

	# Sciogliendo MP08 (le figure di MP06): dai bordi verso GIG, che resta fino in fondo.
	var m8 := SceneMural.new()
	m8.setup({"id": "prologo/mp08_titolo", "rivela": false})
	check(m8.hook("gig") and not m8.hook("nessuno") and m8.hooked == "gig", "Aggancio: MP08 aggancia la figura di GIG di MP06")
	m8.melt(90)
	var c8 := m8.figure_rect("gig").get_center()
	check(bool(m8._mat.get_shader_parameter(&"melt_inward")) and Vector2(m8._mat.get_shader_parameter(&"melt_center")) == c8,
		"Aggancio: MP08 si scioglie verso la figura di GIG")
	var gig_a: Array = []
	var far_a: Array = []
	for i in 90:
		m8.tick()
		for f: Dictionary in m8._figures:
			if str(f["name"]) == "gig":
				gig_a.append((f["sprite"] as Sprite2D).modulate.a)
			elif str(f["name"]) == "perdoni":
				far_a.append((f["sprite"] as Sprite2D).modulate.a)
	check(gig_a.size() == 90 and far_a.size() == 90 and gig_a[60] == 1.0 and far_a[60] < 1.0 and gig_a[89] == 0.0 and m8.is_closed(),
		"Aggancio: sciogliendo, la figura di GIG se ne va per ultima",
		"GIG %s, perdoni %s" % [gig_a.slice(55, 90, 5), far_a.slice(55, 90, 5)])
	m8.free()

## GIG da x sul pavimento per `ticks` tick coi tasti di fn(t, p, favori), coi favori e i droni
## della griglia: l'energia alla fine, gli eventi dei favori e i favori.
func _fv_run(g: SolidGrid, x: int, ticks: int, fn: Callable, energy: int = 60) -> Dictionary:
	var fv := Favors.new()
	fv.build(g)
	var dr := Drones.new()
	dr.build(g)
	var p := PlatformPlayer.new(PlatformMoves.new(), g)
	p.place(x, 240)
	p.can_jab = true
	var ev: Array = []
	var prev := 0
	var opened_at := -1
	for t in ticks:
		var held: int = fn.call(t, p, fv)
		var fr := InputFrame.new(held, held & ~prev)
		prev = held
		p.step(fr)
		dr.step(p)
		energy = fv.step(p, fr.was_pressed(InputFrame.UP), dr, energy)
		for e: Array in fv.events:
			ev.append(e[0])
		if fv.changed and opened_at < 0:
			opened_at = t
	return {"energy": energy, "ev": ev, "fv": fv, "dr": dr, "p": p, "opened_at": opened_at,
		"hash": hash([p.state_hash(), fv.state_hash(), energy])}


func _test_favors() -> void:
	var right := func(_t: int, _p: PlatformPlayer, _f: Favors) -> int: return InputFrame.RIGHT
	# I ristori: si prendono passandoci sopra; non superano 120, la scarcella arriva a 150.
	var r := _fv_run(_fv_grid([["Ristoro", "r0", 400, 240, {"tipo": "taralli"}]]), 300, 60, right, 50)
	var r2 := _fv_run(_fv_grid([["Ristoro", "r0", 400, 240, {"tipo": "taralli"}]]), 300, 60, right, 110)
	var r3 := _fv_run(_fv_grid([["Ristoro", "r0", 400, 240, {"tipo": "scarcella"}]]), 300, 60, right, 100)
	var r4 := _fv_run(_fv_grid([["Ristoro", "r0", 400, 240, {"tipo": "taralli"}]]), 300, 60, right, 140)
	check(r["energy"] == 70 and (r["ev"] as Array).count("ristoro") == 1 and r2["energy"] == Game.ENERGY_MAX
		and r3["energy"] == Favors.OVER_MAX and r4["energy"] == 140,
		"Ristori: i taralli danno 20 fino a 120, la scarcella arriva a 150 e niente toglie l'energia in più",
		"taralli %d, al tetto %d, scarcella %d, sopra %d" % [r["energy"], r2["energy"], r3["energy"], r4["energy"]])

	# La Persona che non chiede niente ringrazia subito, e il ristoro del premio compare solo allora.
	var prize := [["Persona", "q0", 500, 240, {"id": "x", "chiede": "", "serve": "", "premio": ["r0"], "ringrazia": ""}],
		["Ristoro", "r0", 600, 240, {"tipo": "panzerotto"}]]
	var fv0 := Favors.new()
	fv0.build(_fv_grid(prize))
	r = _fv_run(_fv_grid(prize), 300, 200, right, 40)
	var fv: Favors = r["fv"]
	var far := [["Persona", "q0", 1100, 240, {"id": "x", "chiede": "", "serve": "", "premio": ["r0"], "ringrazia": ""}],
		["Ristoro", "r0", 600, 240, {"tipo": "panzerotto"}]]
	r2 = _fv_run(_fv_grid(far), 300, 200, right, 40)
	check(fv0.ristori[0].hidden and fv.persone[0].thanked and fv.is_open("r0") and r["energy"] == 100
		and not (r2["fv"] as Favors).ristori[0].taken and r2["energy"] == 40,
		"Persone: il ristoro del premio è nascosto finché la Persona non ringrazia",
		"nascosto %s, grazie %s, energia %d, senza grazie %d" % [fv0.ristori[0].hidden, fv.persone[0].thanked, r["energy"], r2["energy"]])

	# I fiori: SU li prende, GIG li porta al loculo e SU li posa; la signora ringrazia e apre il premio.
	var flowers := [["Oggetto", "o0", 400, 240, {"tipo": "fiori", "per": "L0"}],
		["Battuta", "L0", 700, 240, {"chi": "persona", "id_testo": "", "quando": "vista"}],
		["Persona", "q0", 900, 240, {"id": "signora", "chiede": "", "serve": "L0", "premio": ["g0"], "ringrazia": ""}]]
	var carry := func(t: int, p: PlatformPlayer, f: Favors) -> int:
		if t < 6:
			return InputFrame.UP if t == 3 else 0
		if f.oggetti[0].state == 1 and p.px >= 700:
			return InputFrame.UP if t % 8 == 0 else 0
		return InputFrame.RIGHT
	r = _fv_run(_fv_grid(flowers), 400, 200, carry)
	fv = r["fv"]
	var ev: Array = r["ev"]
	check(ev.find("preso") >= 0 and ev.find("posato") > ev.find("preso") and ev.find("grazie") > ev.find("posato")
		and fv.oggetti[0].state == 2 and fv.oggetti[0].px == Vector2i(700, 240) and fv.is_open("g0"),
		"Oggetti: SU prende i fiori, al loculo SU li posa, e la signora ringrazia e apre il premio",
		"eventi %s, stato %d" % [str(ev), fv.oggetti[0].state])
	r2 = _fv_run(_fv_grid(flowers), 400, 200, carry)
	check(r["hash"] == r2["hash"], "Favori: due giri uguali vengono uguali")
	# Le pose della signora, solo disegno: tiene i fiori (che per terra non si disegnano), li porge quando
	# chiede, guarda su verso il loculo quando GIG li ha presi, ringrazia coi taralli e poi resta lì.
	var fp := Favors.new()
	fp.build(_fv_grid(flowers))
	var sg: Favors.Person = fp.persone[0]
	var sp_poses := []
	var held0 := fp.in_hands(fp.oggetti[0])
	sp_poses.append("%s %d" % [fp.person_pose(sg, 1000, 5)[1], fp.person_pose(sg, 1000, 5)[3]])
	sg.asked = true
	sp_poses.append("%s %d" % [fp.person_pose(sg, 1000, 5)[1], fp.person_pose(sg, 1000, 5)[3]])
	fp.oggetti[0].state = 1
	sp_poses.append("%s %d" % [fp.person_pose(sg, 1000, 5)[1], fp.person_pose(sg, 1000, 5)[3]])
	fp.oggetti[0].state = 2
	sg.thanked = true
	sp_poses.append("%s %d" % [fp.person_pose(sg, 1000, 5)[1], fp.person_pose(sg, 1000, 5)[3]])
	sg.thanked_t = 500
	sp_poses.append("%s %d" % [fp.person_pose(sg, 1000, 5)[1], fp.person_pose(sg, 1000, 5)[3]])
	var sheets_ok := fp.person_sheet("signora") != null and fp.person_sheet("signora_dopo") != null 		and fp.person_sheet("fruttivendolo") != null and fp.person_sheet("x") == null
	check(sheets_ok and held0 and not fp.in_hands(fp.oggetti[0])
			and sp_poses == ["idle 1", "porge 1", "guarda_su -1", "taralli 1", "idle 1"],
		"Persone: la signora ha lo sprite vero, tiene i fiori, li porge, guarda il loculo e ringrazia coi taralli",
		"fogli %s, in mano %s, pose %s" % [sheets_ok, held0, sp_poses])
	# Lontano dal loculo i fiori non si posano; alla ripartenza tornano a terra, il favore fatto resta.
	var wrong := func(t: int, _p: PlatformPlayer, _f: Favors) -> int:
		return InputFrame.UP if t == 3 or t == 40 else (InputFrame.RIGHT if t > 5 and t < 20 else 0)
	r = _fv_run(_fv_grid(flowers), 400, 60, wrong)
	fv = r["fv"]
	var still_held: bool = fv.held != null
	fv.reset()
	var done: Favors = r2["fv"]
	done.reset()
	check(still_held and fv.held == null and fv.oggetti[0].state == 0 and fv.oggetti[0].px == Vector2i(400, 240)
		and done.persone[0].thanked and done.is_open("g0") and done.oggetti[0].state == 2,
		"Oggetti: lontano dal posto giusto restano in mano; alla ripartenza tornano a terra, i favori fatti restano",
		"in mano %s, stato %d" % [still_held, fv.oggetti[0].state])

	# La Persona servita da un drone rotto: GIG rompe la Colomba col jab, e lei ringrazia.
	var jab := func(t: int, _p: PlatformPlayer, _f: Favors) -> int: return InputFrame.ATTACK if t == 2 else 0
	var gd := _fv_grid([["Persona", "q0", 450, 240, {"id": "f", "chiede": "", "serve": "d0", "premio": ["g0"], "ringrazia": ""}]],
		[["colomba", Vector2i(20, 11), "fermo", []]])
	r = _fv_run(gd, 370, 30, jab)
	fv = r["fv"]
	var broke: bool = (r["dr"] as Drones).is_broken("d0")
	check(broke and fv.persone[0].thanked and fv.is_open("g0") and r["opened_at"] > 0,
		"Persone: il fruttivendolo ringrazia quando il drone che gli serve è rotto, e il premio si apre",
		"rotto %s, grazie %s, aperto al tick %d" % [broke, fv.persone[0].thanked, r["opened_at"]])

	# Le battute: «vista» quando GIG è vicino, «passaggio» quando la supera; una volta sola.
	var back := func(t: int, _p: PlatformPlayer, _f: Favors) -> int: return InputFrame.RIGHT if t < 200 else InputFrame.LEFT
	r = _fv_run(_fv_grid([["Battuta", "b0", 600, 240, {"chi": "gig", "id_testo": "", "quando": "vista"}],
		["Battuta", "b1", 650, 240, {"chi": "gig", "id_testo": "", "quando": "passaggio"}]]), 300, 400, back)
	fv = r["fv"]
	check((r["ev"] as Array).count("battuta") == 2 and fv.battute[0].said and fv.battute[1].said,
		"Battute: la «vista» e il «passaggio» si dicono una volta sola", "eventi %s" % str(r["ev"]))

	# Il caffè dà uno scatto: GIG corre più lontano, poi torna alla velocità normale.
	r = _fv_run(_fv_grid([["Ristoro", "r0", 330, 240, {"tipo": "caffe"}]]), 300, 120, right)
	r2 = _fv_run(_fv_grid([["Ristoro", "r0", 330, 240, {"tipo": "taralli"}]]), 300, 120, right)
	r3 = _fv_run(_fv_grid([["Ristoro", "r0", 330, 240, {"tipo": "caffe"}]]), 300, 260, right)
	var pc: PlatformPlayer = r["p"]
	var pt: PlatformPlayer = r2["p"]
	check(pc.px > pt.px + 20 and pc.boost_pct == Favors.COFFEE_PCT and (r3["p"] as PlatformPlayer).boost_pct == 100
		and (r3["fv"] as Favors).coffee_t == 0,
		"Ristori: il caffè dà uno scatto di due secondi e mezzo, poi la corsa torna normale",
		"col caffè %d, coi taralli %d" % [pc.px, pt.px])

	# La bombola di ARIA+ non ridà energia: ricarica la Scarica.
	r = _fv_run(_fv_grid([["Ristoro", "r0", 400, 240, {"tipo": "bombola"}]]), 300, 60, right, 50)
	check(r["energy"] == 50 and (r["ev"] as Array).has("scarica"),
		"Ristori: la bombola ricarica la Scarica e non l'energia", "energia %d, eventi %s" % [r["energy"], str(r["ev"])])

	# La battuta «dopo_arena» aspetta la fine dell'arena, ovunque sia GIG, e si dice una volta.
	var fa0 := Favors.new()
	var ga := _fv_grid([["Battuta", "b0", 2000, 240, {"chi": "gig", "id_testo": "", "quando": "dopo_arena"}]])
	fa0.build(ga)
	var pa := PlatformPlayer.new(PlatformMoves.new(), ga)
	pa.place(300, 240)
	var said := 0
	for t in 120:
		fa0.arena_done = t >= 60
		fa0.step(pa, false, null, 60)
		said += (fa0.events as Array).filter(func(e: Array) -> bool: return e[0] == "battuta").size()
		if t == 59 and fa0.battute[0].said:
			said = -100
	check(said == 1, "Battute: la «dopo_arena» parte appena finisce l'arena, una volta sola", "dette %d" % said)

	# Le voci delle battute in gioco del prologo: dove ci sono testi e voci (sviluppo), tornano tutte.
	if SceneLines.available("prologo") and SceneVoices.dir_of("prologo") != "":
		var mute: Array = []
		for id: String in ["signora_1", "signora_2", "fruttivendolo_1", "loculo_marito"]:
			var tx := SceneLines.find("prologo", Favors.LINES_SCENE, id)
			if tx == "" or SceneVoices.voice("prologo", Favors.LINES_SCENE, id, tx).is_empty():
				mute.append(id)
		check(mute.is_empty(), "Voci: le battute in gioco del prologo hanno la voce giusta", "mute %s" % str(mute))

	# Il prologo: la signora coi fiori e tre ristori al cimitero; il fruttivendolo nella Fuga.
	# Quello che chiedono e i premi puntano a cose che esistono.
	var census := func(level: String) -> Array:
		var g := SolidGrid.load_file(Prologue.PROLOGUE_MAP + "#" + level)
		var f := Favors.new()
		f.build(g)
		var d := Drones.new()
		d.build(g)
		var ok := true
		for q in f.persone:
			var known := q.serve == ""
			for it in f.oggetti:
				known = known or it.per == q.serve
			for x in d.drones:
				known = known or x.iid == q.serve
			ok = ok and known and not q.premio.is_empty()
			for e: Dictionary in g.entities:
				if String(e["iid"]) in q.premio:
					ok = ok and String(e["tipo"]) in ["Ristoro", "Cancello"]
		return [f.persone.size(), f.oggetti.size(), f.ristori.size(), ok]
	var fa: Array = census.call("Prologo_A_Cimitero")
	var fb: Array = census.call("Prologo_B_Fuga")
	check(fa[0] == 1 and fa[1] == 1 and fa[2] >= 3 and fa[3] and fb[0] == 1 and fb[3],
		"Favori: nel prologo la signora coi fiori al cimitero e il fruttivendolo nella Fuga, coi riferimenti giusti",
		"A %s, B %s" % [fa, fb])


# --- Platform: le processioni (muro morbido, portone, la Vedetta davanti ai cappucci) -----------------

## La corsia dei droni con una processione di 80×100 coi piedi a (x, 240), che va fino alla
## colonna `to` e gira nel portone della colonna `door` (-1: niente portone).
static func _pr_grid(x: int, to: int, door: int, vel: float = 0.6, drones: Array = []) -> SolidGrid:
	var g := _dr_grid(drones)
	var c := {"percorso": [Vector2i(x / SolidGrid.TILE, 11), Vector2i(to, 11)], "velocita": vel, "nascosta": false}
	if door >= 0:
		c["sparisce_a"] = Vector2i(door, 11)
	g.entities.append({"tipo": "Processione", "iid": "p0", "livello": "T", "px": Vector2i(x, 240),
		"pos": Vector2i(x / SolidGrid.TILE, 7), "size": Vector2i(80, 100), "campi": c})
	return g


## GIG da x per `ticks` tick coi tasti di fn(t), con le processioni e i droni della griglia, nell'ordine
## della stanza: GIG, processioni, droni.
func _pr_run(g: SolidGrid, x: int, ticks: int, fn: Callable) -> Dictionary:
	var pr := Processions.new()
	pr.build(g)
	var dr := Drones.new()
	dr.build(g)
	var p := PlatformPlayer.new(PlatformMoves.new(), g)
	p.place(x, 240)
	p.can_jab = true
	var ev: Array = []
	var evt: Array = []
	var dmg := 0
	var jabs := 0
	var prev := 0
	for t in ticks:
		var held: int = fn.call(t)
		var fr := InputFrame.new(held, held & ~prev)
		p.step(fr)
		prev = held
		if p.jab_t > 0:
			jabs += 1
		pr.step(p, fr.was_pressed(InputFrame.DASH))
		for e: Array in pr.events:
			ev.append(e[0])
			evt.append([e[0], t])
		dr.shields = pr.shields()
		if pr.pushed:
			dr.alert_pending = true
		dmg += dr.step(p)
		for e: Array in dr.events:
			ev.append(e[0])
			evt.append([e[0], t])
	return {"ev": ev, "evt": evt, "pr": pr, "dr": dr, "p": p, "dmg": dmg, "jabs": jabs,
		"hash": hash([p.state_hash(), pr.state_hash(), dr.state_hash()])}


func _test_processions() -> void:
	var right := func(_t: int) -> int: return InputFrame.RIGHT
	var still := func(_t: int) -> int: return 0
	# Il muro morbido: GIG che le corre dietro si ferma al bordo, senza danno, e lei va avanti.
	var r := _pr_run(_pr_grid(400, 40, -1), 250, 200, right)
	var p: PlatformPlayer = r["p"]
	var w: Processions.Walk = (r["pr"] as Processions).walks[0]
	check(p.right() <= w.rect().position.x and p.right() >= w.rect().position.x - 4 and r["dmg"] == 0 and w.px() > 400,
		"Processione: GIG che le va contro si ferma al bordo, senza danno, e lei avanza",
		"GIG %d, bordo %d, processione %d" % [p.right(), w.rect().position.x, w.px()])
	# GIG fermo davanti: lei aspetta che si tolga.
	r = _pr_run(_pr_grid(400, 40, -1), 470, 600, still)
	p = r["p"]
	w = (r["pr"] as Processions).walks[0]
	check(w.rect().end.x <= p.left() and w.px() < 440 and p.px == 470,
		"Processione: con GIG fermo davanti si ferma e aspetta", "fine %d, GIG %d" % [w.rect().end.x, p.left()])
	# Vicino a lei il jab non parte; lontano sì.
	var jab := func(t: int) -> int: return InputFrame.ATTACK if t % 30 == 5 else 0
	r = _pr_run(_pr_grid(400, 40, -1), 335, 60, jab)
	var r2 := _pr_run(_pr_grid(400, 40, -1), 150, 60, jab)
	check(r["jabs"] == 0 and r2["jabs"] > 0, "Processione: vicino ai confratelli il colpo non parte",
		"vicino %d, lontano %d" % [r["jabs"], r2["jabs"]])
	# Alla fine del percorso gira nel portone e sparisce: non ferma più niente.
	r = _pr_run(_pr_grid(400, 22, 23), 100, 500, still)
	var pr: Processions = r["pr"]
	check((r["ev"] as Array).count("portone") == 1 and pr.walks[0].gone and pr.shields().is_empty(),
		"Processione: alla fine gira nel portone e sparisce", "eventi %s" % str(r["ev"]))
	r2 = _pr_run(_pr_grid(400, 22, 23), 100, 500, still)
	check(r["hash"] == r2["hash"], "Processione: due giri uguali vengono uguali")

	# La Vedetta sopra la processione: il faro si ferma sui cappucci, «SOGGETTO NON IDENTIFICABILE», e
	# GIG lì accanto non viene visto. Senza processione, lo stesso GIG lo vede.
	var ved := [["vedetta", Vector2i(20, 3), "ronda", [15, 25]]]
	r = _pr_run(_pr_grid(420, 40, -1, 0.0, ved), 480, 240, still)
	var ev: Array = r["ev"]
	var r3 := _dr_run(_dr_grid(ved), 480, 240, 240, still)
	var d: Drones.Drone = (r["dr"] as Drones).drones[0]
	check(ev.has("non_identificabile") and not ev.has("faro_rosso") and r["dmg"] == 0 and (r3["ev"] as Array).has("faro_rosso"),
		"Vedetta: davanti ai cappucci si ferma, «non identificabile», e GIG accanto alla processione passa",
		"eventi %s, senza processione %s, fase %d" % [str(ev), str(r3["ev"]), d.phase])

	# Lo spintone: SCATTO a terra attaccato alla coda. La fila si apre e GIG passa davanti; senza
	# SCATTO resta dietro. La Vedetta lì sopra lo prende subito: faro rosso, poi il sigillo.
	var shove := func(t: int) -> int: return InputFrame.RIGHT | (InputFrame.DASH if t == 60 else 0)
	r = _pr_run(_pr_grid(400, 40, -1), 250, 160, shove)
	p = r["p"]
	w = (r["pr"] as Processions).walks[0]
	r2 = _pr_run(_pr_grid(400, 40, -1), 250, 160, right)
	check((r["ev"] as Array).count("spintone") == 1 and p.left() >= w.rect().end.x and r["dmg"] == 0
		and (r2["p"] as PlatformPlayer).right() <= (r2["pr"] as Processions).walks[0].rect().position.x,
		"Processione: con lo spintone la fila si apre e GIG passa davanti; senza resta dietro",
		"GIG %d, fronte %d, eventi %s" % [p.left(), w.rect().end.x, str(r["ev"])])
	var shove2 := func(t: int) -> int: return InputFrame.RIGHT | (InputFrame.DASH if t == 30 else 0)
	r = _pr_run(_pr_grid(420, 40, -1, 0.0, ved), 330, 120, shove2)
	var et: Array = r["evt"]
	var t_push := -1
	var t_red := -1
	var t_seal := -1
	for x: Array in et:
		if x[0] == "spintone" and t_push < 0:
			t_push = x[1]
		elif x[0] == "faro_rosso" and t_push >= 0 and t_red < 0:
			t_red = x[1]
		elif x[0] == "sigillo_sparato" and t_push >= 0 and t_seal < 0:
			t_seal = x[1]
	check(t_push >= 0 and t_red >= t_push and t_red <= t_push + 1 and t_seal > t_red and t_seal <= t_push + Drones.ALERT_TICKS + 2,
		"Vedetta: dopo lo spintone il faro prende GIG subito e il sigillo parte",
		"spintone %d, faro %d, sigillo %d" % [t_push, t_red, t_seal])
	r2 = _pr_run(_pr_grid(420, 40, -1, 0.0, ved), 330, 120, shove2)
	check(r["hash"] == r2["hash"], "Processione: due spintoni uguali vengono uguali")

	# Nella Fuga del prologo c'è una processione, che finisce nel portone.
	var pb := Processions.new()
	pb.build(SolidGrid.load_file(Prologue.PROLOGUE_MAP + "#Prologo_B_Fuga"))
	check(pb.walks.size() == 1 and pb.walks[0].door and not pb.walks[0].hidden and pb.walks[0].stops.size() >= 2,
		"Processione: nella Fuga del prologo c'è la processione, che finisce nel portone",
		"%d processioni" % pb.walks.size())


# --- Platform: l'arena della stanza -----------------------------------------------------------------

## Un giro nell'arena della stanza col pilota automatico, partendo 100 px prima del punto d'ingresso
## (più indietro GIG sarebbe dentro il blocco del cunicolo).
## Restituisce i numeri che i test confrontano.
func _arena_run(max_ticks: int) -> Dictionary:
	Game.reset_run()
	SpriteSheet.clear_cache()
	var pilot := RoomPilot.new()
	var room := TestRoom.new()
	room.configure({"input": PlayerInput.from_provider(pilot.decide, pilot), "pilot": pilot, "sound": false})
	root.add_child(room)
	room.set_physics_process(false)
	room._start = Vector2i(room._arena_trigger_x - 100, room._floor_y)
	room._reset()
	var out := {"open": -1, "fight": -1, "close": -1, "max_tilt": 0.0, "lock_ok": true, "spawned": 0,
		"wave_started": false, "room_x_after": 0, "state_after": "", "tilt_after": -1.0, "cam_y_lock": 0.0}
	for t in max_ticks:
		var before := room.arena_phase
		room._sim_tick()
		room._follow_camera()
		if room.arena != null:
			out["max_tilt"] = maxf(out["max_tilt"], room.tilt)
			out["spawned"] = maxi(out["spawned"], room.arena.enemies().size())
			out["wave_started"] = out["wave_started"] or not room.arena.active_wave.is_empty()
		if before == TestRoom.ArenaPhase.NONE and room.arena_phase == TestRoom.ArenaPhase.ENTER:
			out["open"] = t
		if before == TestRoom.ArenaPhase.ENTER and room.arena_phase == TestRoom.ArenaPhase.FIGHT:
			out["fight"] = t
			out["cam_y_lock"] = room._cam.y
		if room.arena_phase == TestRoom.ArenaPhase.FIGHT:
			out["lock_ok"] = out["lock_ok"] and roundi(room._cam.x) == room._arena_cam_x and room.arena.camera.x == room._arena_cam_x
		if before == TestRoom.ArenaPhase.LEAVE and room.arena_phase == TestRoom.ArenaPhase.NONE:
			out["close"] = t
			out["px_close"] = room.player.px
		if out["close"] >= 0 and t >= out["close"] + 120:
			break
	out["room_x_after"] = room.player.px
	out["state_after"] = room.player.state_name()
	out["tilt_after"] = room.tilt
	out["done"] = room.arena_done
	out["trigger"] = room._arena_trigger_x
	out["floor_y"] = room._floor_y
	out["hash"] = room.player.state_hash()
	room.get_parent().remove_child(room)
	room.free()
	return out


## GIG col braccio bloccato (il prologo prima del riavvio): solo il salto semplice e le sporgenze
## con una mano, che chiedono di tenere SU.
func _test_arm_locked() -> void:
	var T := SolidGrid.TILE
	var g := _room(40, 14, 10)
	var p := _pp(g, 125, 10)
	_run_pp(p, 90, func(t: int) -> int: return _J if t < 40 else 0)
	var full := p.last_peak
	p = _pp(g, 125, 10)
	p.arm_locked = true
	var ev := _run_pp(p, 120, func(t: int) -> int: return _J if (t < 20 or (t >= 22 and t < 50)) else 0)
	check(_count_events(ev, "spinta") == 0 and absi(p.last_peak - full) <= 1, "Braccio bloccato: niente Spinta, il salto resta quello semplice",
		"spinte %d, %d px contro %d" % [_count_events(ev, "spinta"), p.last_peak, full])
	# Il SALTO premuto in aria non fa niente, ma lo si sente: l'evento del clic a vuoto, una volta.
	check(_count_events(ev, "braccio_a_vuoto") == 1, "Braccio bloccato: SALTO in aria fa il clic a vuoto, una volta",
		"clic %d" % _count_events(ev, "braccio_a_vuoto"))
	# Premuto poco prima di atterrare diventa il salto all'atterraggio: niente clic.
	p = _pp(g, 125, 10)
	p.arm_locked = true
	var pa := p
	var near := [-1]
	ev = _run_pp(p, 150, func(t: int) -> int:
		if t < 10:
			return _J
		if near[0] < 0 and pa.state == PlatformPlayer.State.AIR and pa.vy > 0 and pa.py >= 10 * T - 12:
			near[0] = t
			return _J
		return 0)
	check(near[0] > 0 and _count_events(ev, "braccio_a_vuoto") == 0 and _count_events(ev, "jump") == 2,
		"Braccio bloccato: SALTO poco prima di atterrare è il salto dopo, senza clic",
		"premuto al tick %d, clic %d, salti %d" % [near[0], _count_events(ev, "braccio_a_vuoto"), _count_events(ev, "jump")])
	# Col braccio libero il SALTO in aria è la Spinta, mai il clic.
	p = _pp(g, 125, 10)
	ev = _run_pp(p, 120, func(t: int) -> int: return _J if (t < 20 or (t >= 22 and t < 50)) else 0)
	check(_count_events(ev, "braccio_a_vuoto") == 0 and _count_events(ev, "spinta") == 1, "Braccio libero: SALTO in aria è la Spinta, senza clic",
		"clic %d, spinte %d" % [_count_events(ev, "braccio_a_vuoto"), _count_events(ev, "spinta")])
	p = _pp(g, 125, 10)
	p.arm_locked = true
	var dashed := [false]
	var pd := p
	_run_pp(p, 80, func(t: int) -> int:
		if pd.state == PlatformPlayer.State.DASH:
			dashed[0] = true
		return _R | (_J if t < 20 else 0) | (_S if t == 12 else 0))
	check(not dashed[0], "Braccio bloccato: niente scatto in aria", "")

	# Contro un muro alto: niente freno col braccio né salto a muro.
	var gw := _room(40, 30, 26)
	_box(gw, 20, 21, 0, 25)
	p = PlatformPlayer.new(PlatformMoves.new(), gw)
	p.arm_locked = true
	p.place(370, 10 * T)
	var pw := p
	var walled := [false]
	ev = _run_pp(p, 150, func(t: int) -> int:
		if pw.state == PlatformPlayer.State.WALL_SLIDE or pw.state == PlatformPlayer.State.WALL_RUN:
			walled[0] = true
		return _R | (_J if t % 10 < 5 else 0))
	var wj := _count_events(ev, "walljump") + _count_events(ev, "wallrun") + _count_events(ev, "wall")
	check(not walled[0] and wj == 0, "Braccio bloccato: niente freno col braccio né salto a muro",
		"al muro %s, eventi dei muri %d" % [str(walled[0]), wj])

	# Sporgenza con una mano: i colpetti di SU non bastano, tenendolo si sale dopo lo sforzo.
	var gl := _room(40, 20, 16)
	_box(gl, 14, 20, 9, 15)
	p = _pp(gl, 250, 16)
	p.arm_locked = true
	var pl := p
	var hung := [-1]
	_run_pp(p, 200, func(t: int) -> int:
		if pl.state == PlatformPlayer.State.LEDGE_HANG and hung[0] < 0:
			hung[0] = t
		if hung[0] >= 0:
			return _U if t % 4 == 0 else 0
		return (_R | _J) if t < 25 else _R)
	check(hung[0] >= 0 and p.state == PlatformPlayer.State.LEDGE_HANG, "Braccio bloccato: ci si appende, e i colpetti di SU non fanno salire",
		"appeso al tick %d, stato %s" % [hung[0], p.state_name()])
	var held_from := [-1]
	var climbed := [-1]
	_run_pp(p, 120, func(t: int) -> int:
		if held_from[0] < 0:
			held_from[0] = t
		if pl.state == PlatformPlayer.State.LEDGE_CLIMB and climbed[0] < 0:
			climbed[0] = t
		return _U)
	_run_pp(p, 60, func(_t: int) -> int: return 0)
	check(climbed[0] - held_from[0] >= PlatformPlayer.ONE_HAND_STRAIN - 1 and p.state == PlatformPlayer.State.GROUND and p.py == 9 * T,
		"Braccio bloccato: tenendo SU si sale, dopo lo sforzo", "salita dopo %d tick, stato %s, y %d" % [climbed[0] - held_from[0], p.state_name(), p.py])

	# Col braccio bloccato non si forza la centralina.
	var gm := SolidGrid.load_file(TestRoom.MAP)
	var pm: Vector2i = gm.marks["P"][0]
	var room := _hack_room(Vector2i(pm.x - TestRoom.HACK_FIST_X, pm.y), func(_t: int) -> int: return _U)
	room.player.arm_locked = true
	for t in 90:
		room._sim_tick()
	check(room.hacks_done.is_empty() and room.hack_panel == "", "Braccio bloccato: niente hacking", "forzati %s" % str(room.hacks_done))
	_free_room(room)


func _test_room_arena() -> void:
	var a := _arena_run(4000)
	check(a["open"] >= 0 and a["open"] < 120, "Arena: oltre il punto d'ingresso, coi piedi a terra, la stanza entra nell'arena", "tick %d" % a["open"])
	check(a["fight"] == a["open"] + TestRoom.TILT_IN and is_equal_approx(a["max_tilt"], 1.0),
		"Arena: la telecamera si inclina del tutto in %d tick, poi si combatte" % TestRoom.TILT_IN, "inizio %d, scontro %d, inclinazione %.2f" % [a["open"], a["fight"], a["max_tilt"]])
	check(a["lock_ok"] and is_equal_approx(a["cam_y_lock"], a["floor_y"] - TestRoom.ARENA_BAND.x),
		"Arena: durante lo scontro la telecamera resta bloccata, col pavimento sul bordo dietro della fascia", "y %.0f" % a["cam_y_lock"])
	check(a["wave_started"] and a["spawned"] >= 1, "Arena: arrivano gli Esattori", "nemici %d" % a["spawned"])
	check(a["close"] > a["fight"] and a["done"] and a["tilt_after"] == 0.0,
		"Arena: a scontro finito la telecamera torna laterale e l'arena si chiude", "fine %d, inclinazione %.2f" % [a["close"], a["tilt_after"]])
	check(a["room_x_after"] > a.get("px_close", 1 << 30) + 100,
		"Arena: dopo l'arena GIG riprende il platform e va avanti", "x %d → %d, stato %s" % [a.get("px_close", -1), a["room_x_after"], a["state_after"]])
	var b := _arena_run(4000)
	check(a["close"] == b["close"] and a["hash"] == b["hash"], "Arena: due giri uguali finiscono allo stesso tick e nello stesso stato",
		"%d / %d" % [a["close"], b["close"]])


# --- Platform: l'hacking della stanza ("Collega e corri") -------------------------------------------

## Una stanza di prova pronta, con GIG fermo in `start` e gli ingressi da `input_fn` (o dal pilota
## automatico, se `plan` non è vuoto).
func _hack_room(start: Vector2i, input_fn: Callable, plan: Array[String] = []) -> TestRoom:
	Game.reset_run()
	SpriteSheet.clear_cache()
	var room := TestRoom.new()
	if plan.is_empty():
		room.configure({"input": PlayerInput.from_provider(input_fn), "sound": false})
	else:
		var pilot := RoomPilot.new()
		pilot.hack_plan = plan
		room.configure({"input": PlayerInput.from_provider(pilot.decide, pilot), "pilot": pilot, "sound": false})
	root.add_child(room)
	room.set_physics_process(false)
	room._start = start
	room._reset()
	return room


func _free_room(room: TestRoom) -> void:
	room.get_parent().remove_child(room)
	room.free()


## Un giro del pilota dal cartello dell'hacking, con il piano dato: quando forza i pannelli e fin
## dove arriva.
func _hack_run(plan: Array[String], max_ticks: int) -> Dictionary:
	var gm := SolidGrid.load_file(TestRoom.MAP)
	var k: Vector2i = gm.marks["k"][0]
	var room := _hack_room(Vector2i(k.x - 60, k.y), Callable(), plan)
	var out := {"done": {}, "max_x": 0, "end_tick": -1}
	var far: Rect2i = room.gates[";"]["rect"]
	for t in max_ticks:
		room._sim_tick()
		for id: String in room.hacks_done:
			if not out["done"].has(id):
				out["done"][id] = t
		out["max_x"] = maxi(out["max_x"], room.player.px)
		if room.player.left() > far.end.x and out["end_tick"] < 0:
			out["end_tick"] = t
			break
	out["hash"] = room.state_hash()
	out["far_x"] = far.position.x
	_free_room(room)
	return out


func _test_room_hacking() -> void:
	var gm := SolidGrid.load_file(TestRoom.MAP)
	var ok := true
	for id: String in TestRoom.PANELS:
		ok = ok and gm.marks.has(id) and gm.marks.has(TestRoom.PANELS[id]["gate"])
	check(ok and gm.marks.has("k") and gm.marks.has("l"), "Hacking: la mappa ha i tre pannelli, i loro cancelli e i cartelli")

	# Il cancello è chiuso; tenere SU per HACK_TICKS lo apre. Collegato, GIG non cammina: fa solo i
	# passi che mancano per avere il pugno cyber sotto la presa, e lì resta.
	var p: Vector2i = gm.marks["P"][0]
	var keys := [InputFrame.UP]
	var room := _hack_room(p, func(_t: int) -> int: return keys[0])
	var gate: Dictionary = room.gates["|"]
	var c0: Vector2i = gate["cells"][0]
	check(room.grid.cell(c0.x, c0.y) == SolidGrid.Cell.SOLID, "Hacking: all'inizio il cancello è chiuso (pieno)")
	var spot := room.hack_spot("P")
	var opened := -1
	var steady := true
	var prev := room.player.px
	for t in TestRoom.HACK_TICKS + 5:
		room._sim_tick()
		if room.hack_panel != "":
			steady = steady and absi(room.player.px - prev) <= 1 and absi(room.player.px - spot) <= absi(prev - spot)
		prev = room.player.px
		if opened < 0 and room.hacks_done.has("P"):
			opened = t
	check(opened == TestRoom.HACK_TICKS - 1 and room.grid.cell(c0.x, c0.y) == SolidGrid.Cell.EMPTY and steady and room.player.px == spot,
		"Hacking: dopo %d tick con SU il cancello si apre, con GIG fermo col pugno sotto la presa" % TestRoom.HACK_TICKS,
		"tick %d, x %d (posto %d)" % [opened, room.player.px, spot])
	# Il cancello resta aperto per il suo tempo, poi si richiude.
	keys[0] = 0
	var open_ticks: int = TestRoom.PANELS["P"]["open"]
	var closed := -1
	for t in open_ticks + 10:
		room._sim_tick()
		if closed < 0 and room.grid.cell(c0.x, c0.y) == SolidGrid.Cell.SOLID:
			closed = t
	check(closed >= open_ticks - 6 and closed <= open_ticks, "Hacking: il cancello si richiude dopo %d tick" % open_ticks, "tick %d" % closed)
	_free_room(room)

	# Lasciando SU prima del tempo il cavo si stacca e il cancello resta chiuso.
	room = _hack_room(p, func(t: int) -> int: return InputFrame.UP if t < TestRoom.HACK_TICKS - 10 else 0)
	for t in TestRoom.HACK_TICKS + 10:
		room._sim_tick()
	check(room.hacks_done.is_empty() and room.hack_panel == "" and room.grid.cell(c0.x, c0.y) == SolidGrid.Cell.SOLID,
		"Hacking: lasciando SU prima del tempo il cancello resta chiuso")
	_free_room(room)

	# Il cancello non si chiude addosso a GIG: aspetta che sia passato.
	room = _hack_room(Vector2i(gate["rect"].position.x + 20, p.y), func(_t: int) -> int: return 0)
	room.gates["|"]["timer"] = 1
	room._set_gate("|", true)
	room._sim_tick()
	room._sim_tick()
	check(room.grid.cell(c0.x, c0.y) == SolidGrid.Cell.EMPTY and room.gates["|"]["timer"] > 0,
		"Hacking: il cancello non si chiude addosso a GIG")
	_free_room(room)

	# I due pannelli: nell'ordine giusto (prima il ballatoio) si passa; nell'ordine sbagliato il
	# cancello lontano si richiude prima che GIG arrivi.
	var good := _hack_run(["P", "R", "Q"], 3000)
	check(good["done"].has("P") and good["done"].has("R") and good["done"].has("Q") and good["end_tick"] > 0,
		"Hacking: nell'ordine giusto (P, poi R sul ballatoio, poi Q) GIG passa tutti i cancelli",
		"forzati %s, fine %d, x massima %d" % [good["done"], good["end_tick"], good["max_x"]])
	var bad := _hack_run(["P", "Q", "R"], 3000)
	check(bad["done"].has("Q") and bad["done"].has("R") and bad["end_tick"] < 0 and bad["max_x"] < bad["far_x"],
		"Hacking: nell'ordine sbagliato (Q prima di R) il cancello lontano si richiude prima",
		"forzati %s, x massima %d" % [bad["done"], bad["max_x"]])
	var again := _hack_run(["P", "R", "Q"], 3000)
	check(again["end_tick"] == good["end_tick"] and again["hash"] == good["hash"],
		"Hacking: due giri uguali finiscono allo stesso tick e nello stesso stato", "%d / %d" % [good["end_tick"], again["end_tick"]])


# --- Il rider (decisione 63) -------------------------------------------------------------------------

## Un rider già in campo accanto a GIG, fermo, pronto a tentare il pignoramento.
func _rider_grab_setup(input_fn: Callable) -> Array:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(input_fn), 375.0, 225.0)
	var g := lvl.player
	var r := lvl.spawn_thug(&"rider", 1, 225.0, "") as Rider
	r.px = g.px + Rider.GRAB_DX
	r.py = g.py
	r.set_state(Fighter.State.IDLE)
	g.facing = 1
	lvl.director.request(r, lvl.tick)
	r._start_pignora(g, 1)
	return [lvl, g, r]


func _test_rider() -> void:
	# Si divincola: premendo a ripetizione GIG si libera prima che il pignoramento riesca.
	var s := _rider_grab_setup(func(t: int) -> int: return InputFrame.ATTACK if t % 4 == 0 else 0)
	var lvl: Level = s[0]
	var g: Gig = s[1]
	var r: Rider = s[2]
	check(g.state == Fighter.State.GRABBED and r.state == Fighter.State.GRAB, "Rider: il pignoramento afferra GIG")
	var freed := -1
	for i in Rider.PIGNORA_TICKS + 10:
		lvl.step()
		if g.state != Fighter.State.GRABBED:
			freed = i
			break
	check(freed >= 0 and freed < Rider.PIGNORA_TICKS and g.arm_off == 0 and g.invuln > 0 and r.state == Fighter.State.HURT,
		"Rider: con %d pressioni GIG si divincola, e il rider barcolla" % Gig.ESCAPE_PRESSES, "tick %d, braccio %d, stato del rider %d" % [freed, g.arm_off, r.state])
	check(not lvl.director.is_holder(r) and r.retreat > 0, "Rider: dopo il pignoramento lascia il turno e scappa")
	Harness.free_level(lvl)

	# Non si divincola: il braccio resta sospeso, con poco danno.
	s = _rider_grab_setup(func(_t: int) -> int: return 0)
	lvl = s[0]
	g = s[1]
	r = s[2]
	for i in Rider.PIGNORA_TICKS + 2:
		lvl.step()
	check(g.state != Fighter.State.GRABBED and g.arm_off > Gig.ARM_OFF_TICKS - 5 and g.hp == g.data.max_hp - Rider.PIGNORA_DAMAGE,
		"Rider: senza divincolarsi il braccio resta sospeso per %d tick" % Gig.ARM_OFF_TICKS, "braccio %d, vita %d" % [g.arm_off, g.hp])
	Harness.free_level(lvl)

	# Braccio sospeso: pugni a metà danno, niente presa, niente calcio in salto; poi torna.
	var keys := [0]
	lvl = Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return keys[0]), 375.0, 225.0)
	g = lvl.player
	var t := lvl.spawn_thug(&"thug_punk", 1, 225.0, "")
	t.ai_enabled = false
	t.px = g.px + 30.0
	t.py = g.py
	t.set_state(Fighter.State.IDLE)
	g.facing = 1
	g.arm_off = 200
	keys[0] = InputFrame.ATTACK
	var hp0 := t.hp
	for i in 30:
		lvl.step()
		keys[0] = 0
		if t.hp < hp0:
			break
	var jab := load("res://data/attacks/gig_jab1.tres") as AttackData
	check(hp0 - t.hp == maxi(1, roundi(jab.damage * 0.5)), "Braccio sospeso: il jab fa metà danno", "%d su %d" % [hp0 - t.hp, jab.damage])
	for i in 40:
		lvl.step()
	t.px = g.px + 20.0
	t.py = g.py
	t.set_state(Fighter.State.IDLE)
	keys[0] = InputFrame.RIGHT
	var grabbed := false
	for i in 30:
		lvl.step()
		grabbed = grabbed or g.state == Fighter.State.GRAB
	check(not grabbed, "Braccio sospeso: camminando contro un nemico non lo si afferra")
	keys[0] = 0
	t.px = g.px + 200.0
	for i in 10:
		lvl.step()
	keys[0] = InputFrame.JUMP
	lvl.step()
	keys[0] = 0
	for i in 8:
		lvl.step()
	var in_air := g.state == Fighter.State.JUMP
	keys[0] = InputFrame.ATTACK
	var kicked := false
	for i in 30:
		lvl.step()
		keys[0] = 0
		kicked = kicked or g.state == Fighter.State.ATTACK
	check(in_air and not kicked, "Braccio sospeso: niente calcio in salto", "in aria %s, calcio %s" % [in_air, kicked])
	for i in 200:
		lvl.step()
	check(g.arm_off == 0, "Braccio sospeso: dopo %d tick il braccio torna" % Gig.ARM_OFF_TICKS, str(g.arm_off))
	Harness.free_level(lvl)

	# Colpisce e scappa: dopo il suo attacco il rider si allontana di corsa.
	lvl = Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
	g = lvl.player
	r = lvl.spawn_thug(&"rider", 1, 225.0, "") as Rider
	var attacked := -1
	var far := false
	for i in 900:
		lvl.step()
		if attacked < 0 and (r.state == Fighter.State.ATTACK or r.state == Fighter.State.GRAB):
			attacked = i
		if attacked >= 0 and r.retreat > 0 and absf(r.px - g.px) > 90.0:
			far = true
			break
	check(attacked >= 0 and far, "Rider: colpisce e poi scappa oltre 90 px", "attacco al tick %d, distanza %.0f" % [attacked, absf(r.px - g.px)])
	Harness.free_level(lvl)


# --- L'esattore di professione (decisione 63) --------------------------------------------------------

## Un esattore fermo davanti a GIG, rivolto verso di lui, a `dx` px (GIG guarda a destra).
func _esattore_setup(dx: float, ai: bool) -> Array:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
	var g := lvl.player
	var e := lvl.spawn_thug(&"esattore", 1, 225.0, "") as Esattore
	e.ai_enabled = ai
	e.px = g.px + dx
	e.py = g.py
	e.facing = -1
	e.set_state(Fighter.State.IDLE)
	g.facing = 1
	return [lvl, g, e]


## GIG colpisce l'esattore con `atk_id`, come se il colpo arrivasse adesso.
func _gig_hits(lvl: Level, g: Gig, e: Fighter, atk_id: StringName) -> void:
	g.start_attack(g.attacks[atk_id], lvl.next_attack_serial())
	lvl.combat.apply_hit(g, e, g.attacks[atk_id], Vector2(e.px, e.py - 75), 1)
	g.set_state(Fighter.State.IDLE)
	e.hitstop = 0


func _test_esattore() -> void:
	# La guardia: da davanti para due pugni senza danno, al terzo la guardia salta e barcolla.
	var s := _esattore_setup(40.0, false)
	var lvl: Level = s[0]
	var g: Gig = s[1]
	var e: Esattore = s[2]
	var hp0 := e.hp
	_gig_hits(lvl, g, e, &"gig_jab1")
	_gig_hits(lvl, g, e, &"gig_jab2")
	check(e.hp == hp0 and e.guard_hits == 2 and e.is_free(), "Esattore: da davanti para i pugni, senza danno",
		"vita %d → %d, parati %d" % [hp0, e.hp, e.guard_hits])
	_gig_hits(lvl, g, e, &"gig_hook")
	check(e.hp == hp0 and e.state == Fighter.State.HURT and e.stun >= Esattore.GUARD_BREAK_STUN - 1 and e.guard_hits == 0,
		"Esattore: al terzo colpo parato la guardia salta e barcolla", "stato %d, stordimento %d" % [e.state, e.stun])
	var stun0 := e.stun
	_gig_hits(lvl, g, e, &"gig_jab1")
	check(e.hp < hp0 and e.stun >= stun0 - 1, "Esattore: con la guardia rotta i pugni fanno danno, e non accorciano il barcollare",
		"vita %d, stordimento %d → %d" % [e.hp, stun0, e.stun])
	Harness.free_level(lvl)

	# Il calcio in salto e i colpi alle spalle passano.
	s = _esattore_setup(40.0, false)
	lvl = s[0]
	g = s[1]
	e = s[2]
	hp0 = e.hp
	_gig_hits(lvl, g, e, &"gig_air_kick")
	check(e.hp < hp0, "Esattore: il calcio in salto passa la guardia", "vita %d → %d" % [hp0, e.hp])
	Harness.free_level(lvl)
	s = _esattore_setup(40.0, false)
	lvl = s[0]
	g = s[1]
	e = s[2]
	e.facing = 1
	hp0 = e.hp
	_gig_hits(lvl, g, e, &"gig_jab1")
	check(e.hp < hp0, "Esattore: alle spalle non para")
	Harness.free_level(lvl)

	# La carica: si abbassa lampeggiando, poi corre lungo la corsia e atterra GIG.
	s = _esattore_setup(Esattore.CHARGE_DX, true)
	lvl = s[0]
	g = s[1]
	e = s[2]
	lvl.director.request(e, lvl.tick)
	e._start_charge(g)
	var ran := -1
	var hit := -1
	for i in Esattore.CHARGE_WIND + 80:
		lvl.step()
		if ran < 0 and e.charge == Esattore.Charge.RUN:
			ran = i
		if hit < 0 and g.state == Fighter.State.KNOCK_AIR:
			hit = i
			break
	check(ran >= Esattore.CHARGE_WIND - 2 and ran <= Esattore.CHARGE_WIND + 1 and hit > ran,
		"Esattore: la carica parte dopo %d tick di preparazione e atterra GIG nella sua corsia" % Esattore.CHARGE_WIND, "corsa %d, colpo %d" % [ran, hit])
	# Il fermo dell'impatto (hitstop) e poi la frenata.
	for i in 12:
		lvl.step()
	check(e.charge == Esattore.Charge.NONE and e.dizzy == 0 and not lvl.director.is_holder(e),
		"Esattore: preso GIG, frena senza stordirsi e lascia il turno")
	Harness.free_level(lvl)

	# La carica a vuoto: GIG cambia corsia, l'esattore sbatte contro il bordo e resta stordito.
	s = _esattore_setup(Esattore.CHARGE_DX, true)
	lvl = s[0]
	g = s[1]
	e = s[2]
	lvl.director.request(e, lvl.tick)
	e._start_charge(g)
	g.py += 30.0
	var dizzy_at := -1
	for i in Esattore.CHARGE_WIND + Esattore.CHARGE_MAX:
		lvl.step()
		if e.dizzy > 0:
			dizzy_at = i
			break
	var edge := minf(absf(e.px - lvl.view_left()), absf(e.px - lvl.view_right()))
	check(dizzy_at > 0 and e.state == Fighter.State.HURT and edge < Level.WALL_MARGIN + 20.0 and g.state != Fighter.State.KNOCK_AIR,
		"Esattore: a vuoto sbatte contro il bordo e resta stordito", "tick %d, distanza dal bordo %.0f" % [dizzy_at, edge])
	var st := e.stun
	_gig_hits(lvl, g, e, &"gig_jab1")
	check(e.stun >= st - 1 and e.state == Fighter.State.HURT, "Esattore: stordito, i pugni non lo svegliano prima")
	Harness.free_level(lvl)


# --- Il prologo -------------------------------------------------------------------------------------

## Il prologo pronto, col pilota automatico o con gli ingressi di `input_fn`. Di base quello di prima,
## in un livello solo; `file` sceglie il prologo nuovo, a due livelli.
func _prologue_room(input_fn: Callable = Callable(), file: String = Prologue.PROLOGUE_V1) -> Prologue:
	Game.reset_run()
	# I registri copiati restano per la sessione: ogni giro di prova parte senza.
	Game.registri.clear()
	SpriteSheet.clear_cache()
	var room := Prologue.new()
	room.map_file = file
	if input_fn.is_valid():
		room.configure({"input": PlayerInput.from_provider(input_fn), "sound": false})
	else:
		var pilot := RoomPilot.new()
		room.configure({"input": PlayerInput.from_provider(pilot.decide, pilot), "pilot": pilot, "sound": false})
	root.add_child(room)
	room.set_physics_process(false)
	room._reset()
	return room


## Il prologo intero col pilota: dove passa e quando finisce.
func _prologue_run(max_ticks: int) -> Dictionary:
	var room := _prologue_room()
	var out := {"end": -1, "locked_ok": true, "mimmo": -1, "arena": -1, "door": -1, "reboot": -1, "rain_before": false,
		"rain_fight": false, "fight": -1, "rinforzi": -1, "results": []}
	room.prologue_finished.connect(func(r: Dictionary) -> void: (out["results"] as Array).append([room.tick, r]))
	for t in max_ticks:
		room._sim_tick()
		room._follow_camera()
		if not room.rebooted:
			out["locked_ok"] = out["locked_ok"] and room.player.arm_locked and room.player.boosts_left == 0
		if room.seen_mimmo and out["mimmo"] < 0:
			out["mimmo"] = t
		if room.arena_done and out["arena"] < 0:
			out["arena"] = t
		if room.arena_phase == TestRoom.ArenaPhase.FIGHT and out["fight"] < 0:
			out["fight"] = t
			out["rain_fight"] = room.raining
		if room.raining and room.arena == null and out["arena"] < 0:
			out["rain_before"] = true
		if room.seen_rinforzi and out["rinforzi"] < 0:
			out["rinforzi"] = t
		if room.door_closed and out["door"] < 0:
			out["door"] = t
		if room.rebooted and out["reboot"] < 0:
			out["reboot"] = t
		if room.finished:
			out["end"] = t
			break
	out["raining"] = room.raining
	out["hash"] = room.state_hash()
	# Dopo la fine la scritta resta END_HOLD tick, poi la partita passa alla fine della demo, una volta.
	var end_tick := room.tick
	for t in Prologue.END_HOLD + 30:
		room._sim_tick()
	out["end_tick"] = end_tick
	out["unlocked"] = not room.player.arm_locked
	_free_room(room)
	return out


func _test_prologue() -> void:
	var gm := SolidGrid.load_file(Prologue.PROLOGUE_V1)
	var missing: Array[String] = []
	for m: String in ["M", "X", "Z", "/"] + Prologue.CHECKPOINT_SIGNS:
		if not gm.marks.has(m):
			missing.append(m)
	check(missing.is_empty(), "Prologo: la mappa ha la tomba, il banco, il tetto, la porta e i cartelli delle ripartenze", ", ".join(missing))
	var a := _prologue_run(9000)
	check(a["mimmo"] >= 0 and a["mimmo"] < a["arena"], "Prologo: la vignetta della tomba di Mimmo, poi il pignoramento", "tomba %d, arena %d" % [a["mimmo"], a["arena"]])
	check(a["locked_ok"], "Prologo: fino al riavvio il braccio sinistro è bloccato e la Spinta non c'è")
	check(not a["rain_before"] and a["rain_fight"] and a["raining"], "Prologo: piove dall'arrivo degli Esattori (decisione 54)",
		"prima %s, allo scontro %s, alla fine %s" % [a["rain_before"], a["rain_fight"], a["raining"]])
	check(a["rinforzi"] > a["arena"] and a["rinforzi"] < a["door"],
		"Prologo: dopo lo scontro, sul muro del cimitero, i rinforzi", "arena %d, muro %d, porta %d" % [a["arena"], a["rinforzi"], a["door"]])
	check(a["arena"] < a["door"] and a["door"] < a["reboot"] and a["unlocked"],
		"Prologo: nel garage la porta si chiude, poi il riavvio sblocca il braccio", "porta %d, riavvio %d" % [a["door"], a["reboot"]])
	check(a["end"] > a["reboot"] and a["end"] - a["reboot"] < Prologue.DOOR_BREAK,
		"Prologo: dal lucernario sul tetto prima che la porta ceda, ed è la fine", "riavvio %d, fine %d" % [a["reboot"], a["end"]])
	var res: Array = a["results"]
	check(res.size() == 1 and int(res[0][0]) == int(a["end_tick"]) + Prologue.END_HOLD and int(res[0][1]["ticks"]) == int(a["end_tick"]) 		and bool(res[0][1]["prologue"]), "Prologo: la scritta della fine resta 4 s, poi una volta sola la fine della demo", str(res))
	var b := _prologue_run(9000)
	check(a["end"] == b["end"] and a["hash"] == b["hash"], "Prologo: due giri uguali finiscono allo stesso tick e nello stesso stato", "%d / %d" % [a["end"], b["end"]])
	# Con GIG ancora dentro quando la porta cede, si riparte dal banco.
	var room := _prologue_room(func(t: int) -> int: return _L if t < 40 else 0)
	room.rebooted = true
	room.checkpoint = Prologue.CHECKPOINT_SIGNS.find("j")
	room._reset()
	var x: Vector2i = room.grid.marks["X"][0]
	var moved := false
	for t in Prologue.DOOR_BREAK + 2:
		room._sim_tick()
		moved = moved or room.player.px != x.x
	check(moved and room.player.px == x.x and room.player.py == x.y and room.door_t > Prologue.DOOR_BREAK - 10,
		"Prologo: se la porta cede con GIG nel garage, si riparte dal banco", "x %d (banco %d), porta %d" % [room.player.px, x.x, room.door_t])
	_free_room(room)
	# F5 (debug_lights) spegne e riaccende anche le luci del tempo, il sole e il cielo; di base sono accese.
	room = _prologue_room()
	var lit := func() -> Array: return [room.weather._sun.enabled, room.weather._sky.enabled]
	var start: Array = lit.call()
	room._set_lights(false)
	var off: Array = lit.call()
	room._set_lights(true)
	var on: Array = lit.call()
	check(start == [true, true] and off == [false, false] and on == [true, true],
		"Prologo: le luci del tempo sono accese e F5 le spegne e le riaccende", "%s %s %s" % [start, off, on])
	_free_room(room)


## Le voci delle battute (SceneVoices): un manifest finto in user://. Una voce si usa solo se
## testo_sha1 torna con il testo e se il file c'è; altrimenti la battuta resta muta.
func _test_scene_voices() -> void:
	var root := "user://test_voci"
	DirAccess.make_dir_recursive_absolute(root + "/finto")
	var testo := "Una battuta di prova, con gli accenti: è così."
	var man := {"formato": 1, "battute": {
		"scena/giusta": {"file": "scena/giusta.ogg", "durata_s": 1.0, "testo_sha1": testo.sha1_text(), "inviluppo": [0, 50, 90]},
		"scena/vecchia": {"file": "scena/vecchia.ogg", "durata_s": 1.0, "testo_sha1": "0000", "inviluppo": [50]}}}
	var f := FileAccess.open(root + "/finto/manifest.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(man))
	f.close()
	SceneVoices.root_override = ProjectSettings.globalize_path(root)
	SceneVoices.clear_cache()
	check(SceneVoices.dir_of("finto") != "", "Voci: il manifest si trova")
	check(SceneVoices.voice("finto", "scena", "vecchia", testo).is_empty(), "Voci: una voce vecchia (sha1 diverso) resta muta")
	check(SceneVoices.voice("finto", "scena", "giusta", testo).is_empty(), "Voci: senza il file OGG la battuta resta muta")
	check(SceneVoices.voice("finto", "scena", "manca", testo).is_empty(), "Voci: una battuta senza voce resta muta")
	check(SceneVoices.dir_of("nessuno") == "" or SceneVoices.dir_of("nessuno").ends_with("/nessuno"), "Voci: un capitolo senza voci")
	SceneVoices.root_override = ""
	SceneVoices.clear_cache()
	DirAccess.remove_absolute(root + "/finto/manifest.json")
	DirAccess.remove_absolute(root + "/finto")
	DirAccess.remove_absolute(root)


## I pensieri di Totò (decisione 97): i tre puntini davanti, una volta sola; nelle scene del prologo
## la voce fuori campo è un pensiero, arancio e senza nome.
func _test_scene_thoughts() -> void:
	var dots := UiFont.safe_text(ScenePlayer.THOUGHT_DOTS, true)
	check(ScenePlayer.thought_text("Avevo undici anni.") == dots + "Avevo undici anni.", "Pensieri: i tre puntini davanti")
	check(ScenePlayer.thought_text("…Già detto.") == "…Già detto.", "Pensieri: i puntini non si raddoppiano")
	check(ScenePlayer.thought_text("...Già detto.") == "...Già detto.", "Pensieri: nemmeno con tre punti")
	for id in ["introduzione", "ricordo_mimmo", "passaggio_1"]:
		var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/scene/%s.json" % id))
		var a: Dictionary = d["attori"]["narratore"]
		check(bool(a.get("pensiero", false)) and str(a.get("colore", "")) == "#ff9a5a" and str(a.get("nome", "x")) == "",
			"Pensieri: in %s il narratore pensa, in arancio e senza nome" % id)

## Il passo «murale» (SceneMural): un murale finto in user://, dipinto a spray sopra il gioco nell'ordine
## di murale_rivela.png, che scorre e poi se ne va con lo spray all'indietro; da solo si chiude anche
## quando la scena si salta. Poi i dati del murale vero di MP06 (il cimitero).
func _test_scene_mural() -> void:
	var base := "user://murales_finti"
	var dir := base + "/prova/finto"
	DirAccess.make_dir_recursive_absolute(dir)
	var img := Image.create(512, 288, false, Image.FORMAT_RGBA8)
	img.fill(Color8(200, 60, 120))
	img.save_png(dir + "/murale.png")
	var rv := Image.create(512, 288, false, Image.FORMAT_L8)
	for x in 512:
		for y in 288:
			rv.set_pixel(x, y, Color(x / 511.0, x / 511.0, x / 511.0))
	rv.save_png(dir + "/murale_rivela.png")
	var em := Image.create(512, 288, false, Image.FORMAT_RGBA8)
	em.fill(Color(0, 0, 0, 0))
	em.save_png(dir + "/murale_emis.png")
	var fig := Image.create(10, 10, false, Image.FORMAT_RGBA8)
	fig.fill(Color.WHITE)
	fig.save_png(dir + "/figura_prova.png")
	var js := {"id": "finto", "capitolo": "prova", "scorri": {"da": [0, 0], "a": [32, 18]},
		"figure": [{"nome": "prova", "file": "figura_prova.png", "x": 100, "y": 50, "profondita": 2.0}]}
	var f := FileAccess.open(dir + "/murale.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(js))
	f.close()
	SceneMural.dir = base

	# Il copione: i parametri ammessi e quelli sbagliati.
	var sd := SceneData.new()
	sd.id = "prova_murale"
	sd._parse({"formato": 1, "spazio": "stanza", "passi": [
		{"fai": "murale", "id": "prova/finto", "tick": 100, "rivela_tick": 20},
		{"fai": "attendi", "tick": 30},
		{"fai": "murale", "chiudi": true, "rivela_tick": 20}]})
	check(sd.errors.is_empty(), "Murale: il passo è valido nel copione", "; ".join(sd.errors))
	var bad := SceneData.new()
	bad._parse({"formato": 1, "passi": [{"fai": "murale", "da": 5}, {"fai": "murale", "id": "a/b", "colore": 1}]})
	check(bad.errors.size() == 3, "Murale: senza id, con \"da\" non [x, y] o un parametro in più, il copione è sbagliato", "; ".join(bad.errors))
	check(SceneMural.exists({"id": "prova/finto"}) and SceneMural.exists({"id": "finto", "capitolo": "prova"})
		and not SceneMural.exists({"id": "prova/manca"}), "Murale: si trova con \"<capitolo>/<id>\" o con \"capitolo\"")

	# Il murale da solo: inquadratura, spray, scorrimento, chiusura.
	var m := SceneMural.new()
	m.setup({"id": "prova/finto", "tick": 100, "rivela_tick": 20})
	root.add_child(m)
	check(m.errors.is_empty() and m._figures.size() == 1, "Murale: si carica, con la sua figura", "; ".join(m.errors))
	check(m.c0 == Vector2(240, 135) and m.c1 == Vector2(272, 153) and m.amount() == 0.0,
		"Murale: lo scorrimento di murale.json, e all'inizio non c'è ancora niente", "%s %s" % [m.c0, m.c1])
	var mat: ShaderMaterial = m._sprite.material
	for i in 10:
		m.tick()
	var half_p := float(mat.get_shader_parameter(&"progress"))
	for i in 10:
		m.tick()
	check(half_p > 0.3 and half_p < 0.8 and m.is_revealed() and is_equal_approx(float(mat.get_shader_parameter(&"progress")), 1.0 + SceneMural.EDGE),
		"Murale: lo spray lo dipinge in rivela_tick, a metà si vede metà", "%.2f" % half_p)
	var fs: Sprite2D = m._figures[0]["sprite"]
	check(is_equal_approx(fs.modulate.a, 1.0), "Murale: a spray finito c'è anche la figura")
	for i in 80:
		m.tick()
	check(m.is_scrolled() and (m.view()[0] as Vector2) == Vector2(272, 153) and m._sprite.position == Vector2(-32, -18),
		"Murale: in \"tick\" scorre fino al riquadro di arrivo", "%s" % m._sprite.position)
	check(fs.position == Vector2(100 - 32 * 2, 50 - 18 * 2), "Murale: la figura davanti (profondità 2) scorre il doppio", "%s" % fs.position)
	var g := {}
	for i in SceneMural.PULSE_TICKS:
		m.tick()
		g[snappedf(float(mat.get_shader_parameter(&"glow")), 0.05)] = true
	check(g.size() > 4, "Murale: le luci pulsano", "%d" % g.size())
	m.close(10)
	for i in 10:
		m.tick()
	check(m.is_closed() and float(mat.get_shader_parameter(&"progress")) == 0.0, "Murale: chiuso, lo spray all'indietro lo toglie tutto")
	var cut := SceneMural.new()
	cut.setup({"id": "prova/finto", "rivela": false, "luci": false, "da": [8, 4], "a": [8, 4]})
	check(cut.is_revealed() and cut.c0 == Vector2(248, 139) and cut.c1 == cut.c0 and is_equal_approx(float(cut._mat.get_shader_parameter(&"glow")), 1.0),
		"Murale: con \"rivela\" falso è uno stacco, \"da\"/\"a\" del passo vincono, senza \"luci\" non pulsa")
	cut.free()
	m.free()

	# Nel lettore delle scene: sopra il gioco, poi via, con la simulazione ferma.
	SceneData._cache["prova_murale"] = sd
	var room := _prologue_room()
	room._scene_request = {"id": "prova_murale", "poses": {}}
	room._start_scene()
	var sp := room.scene
	var sim_tick := room.tick
	room._scene_frame()
	check(sp != null and sp.mural() != null and sp.mural().get_parent() == sp._mural_layer and sp._mural_layer.layer < 15,
		"Murale: nel lettore sta in un suo livello, sotto lo sfocato, le bande e le battute")
	var opened := -1
	var frames := 1
	while sp != null and is_instance_valid(sp) and sp.holds_sim() and frames < 1000:
		room._scene_frame()
		frames += 1
		if opened < 0 and sp._step_i >= 2:
			opened = frames
	check(opened == 21, "Murale: la scena aspetta la fine dello spray (e va avanti al fotogramma dopo)", "%d" % opened)
	check(frames >= 20 + 30 + 20 and frames < 80 and sp._murals.is_empty(), "Murale: con \"chiudi\" se ne va e la scena va avanti", "%d" % frames)
	check(room.tick == sim_tick, "Murale: durante il murale la simulazione resta ferma")
	for i in ScenePlayer.OUTRO + 2:
		if room.scene != null:
			room._scene_frame()
	_free_room(room)

	# Saltata a metà: il murale si chiude da solo nell'uscita.
	var sd2 := SceneData.new()
	sd2.id = "prova_murale_2"
	sd2._parse({"formato": 1, "spazio": "stanza", "passi": [{"fai": "murale", "id": "prova/finto", "rivela_tick": 10},
		{"fai": "attendi", "tick": 500}]})
	SceneData._cache["prova_murale_2"] = sd2
	room = _prologue_room()
	room._scene_request = {"id": "prova_murale_2", "poses": {}}
	room._start_scene()
	sp = room.scene
	for i in 40:
		room._scene_frame()
	var mm := sp.mural()
	sp._skip()
	check(mm != null and mm.closing, "Murale: se la scena si salta, il murale comincia a chiudersi")
	for i in ScenePlayer.OUTRO:
		sp.tick()
	check(room.scene == null and is_instance_valid(mm) and mm.is_closed(), "Murale: a fine uscita lo spray all'indietro è finito, si vede il gioco")
	_free_room(room)
	SceneData.clear_cache()
	SceneMural.dir = SceneMural.DIR_DEFAULT
	for n in ["murale.png", "murale_rivela.png", "murale_emis.png", "figura_prova.png", "murale.json"]:
		DirAccess.remove_absolute(dir + "/" + n)
	DirAccess.remove_absolute(dir)
	DirAccess.remove_absolute(base + "/prova")
	DirAccess.remove_absolute(base)

	# Il murale vero di MP06, il cimitero: parte da zoom 2 su GIG e allarga, con le due figure.
	var mp := SceneMural.new()
	mp.setup({"id": "prologo/mp06_cimitero"})
	var mp06: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(
		SceneMural.DIR_DEFAULT + "/prologo/mp06_cimitero/murale.json"))
	var cam: Dictionary = mp06["camera"]
	var c0 := Vector2(cam["centro_da"][0], cam["centro_da"][1])
	var n_fig: int = (mp06["figure"] as Array).size()
	check(mp.errors.is_empty() and mp.size == Vector2(480, 270) and n_fig >= 2 and mp._figures.size() == n_fig
		and mp.z0 == 2.0 and mp.z1 == 1.0 and mp.c0 == c0 and mp.c1 == Vector2(240, 135),
		"Murale: MP06 si carica con la camera di murale.json (zoom 2 su GIG, poi tutto)", "; ".join(mp.errors))
	for i in mp.scroll_n:
		mp.tick()
	check(mp._sprite.position == Vector2.ZERO and mp._sprite.scale == Vector2.ONE,
		"Murale: alla fine MP06 combacia pixel per pixel con lo schermo", "%s" % mp._sprite.position)
	mp.free()

## Le scritte sui murales, lo scioglimento nel gioco e il nero: il copione, il murale da solo, il lettore
## e i murales veri del prologo.
func _test_scene_writing() -> void:
	# Il copione: i passi nuovi e i loro errori.
	var ok := SceneData.new()
	ok._parse({"formato": 1, "spazio": "stanza", "passi": [
		{"fai": "nero", "entra": true, "tick": 1},
		{"fai": "murale", "id": "a/b", "scritte": [{"id": "t", "zona": [0, 0, 4, 4]}]},
		{"fai": "bande", "entra": true, "sopra": false},
		{"fai": "scritta", "id": "t", "tick": 10, "modo": "scrivi"},
		{"fai": "murale", "sciogli": true, "rivela_tick": 10}]})
	check(ok.errors.is_empty(), "Scritte: nero, scritte, bande solo sotto e sciogli sono validi nel copione", "; ".join(ok.errors))
	var bad := SceneData.new()
	bad._parse({"formato": 1, "passi": [{"fai": "scritta"}, {"fai": "scritta", "id": "t", "modo": "pennello"},
		{"fai": "murale", "id": "a/b", "scritte": [{"id": "t", "zona": [1, 2]}]}]})
	check(bad.errors.size() == 3, "Scritte: senza id, con un modo sconosciuto o una zona sbagliata, il copione è sbagliato", "; ".join(bad.errors))

	# Un murale finto: fondo scuro, due lettere chiare su una riga e una sotto; una scritta in un file.
	var base := "user://murales_scritte"
	var dir := base + "/prova/scritta"
	DirAccess.make_dir_recursive_absolute(dir)
	var bg := Color8(40, 40, 60)
	var img := Image.create(200, 120, false, Image.FORMAT_RGBA8)
	img.fill(bg)
	for r: Rect2i in [Rect2i(20, 30, 10, 10), Rect2i(34, 30, 10, 10), Rect2i(20, 50, 11, 6)]:
		img.fill_rect(r, Color.WHITE)
	img.save_png(dir + "/murale.png")
	var sc := Image.create(200, 120, false, Image.FORMAT_RGBA8)
	sc.fill(Color(0, 0, 0, 0))
	sc.fill_rect(Rect2i(100, 80, 11, 6), Color.YELLOW)
	sc.save_png(dir + "/scritta_reg.png")
	var js := {"id": "scritta", "capitolo": "prova", "scritte": [{"nome": "reg", "file": "scritta_reg.png"}],
		"passaggio": {"centro": [100, 60], "camera": {"x": 10, "y": 20}}}
	var f := FileAccess.open(dir + "/murale.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(js))
	f.close()
	SceneMural.dir = base
	var st := {"id": "prova/scritta", "rivela_tick": 10, "scritte": [{"id": "tit", "zona": [16, 26, 34, 34]}]}
	var ids := SceneMural.writing_ids(st)
	check(ids.has("reg") and ids.has("tit") and not ids.has("logo"), "Scritte: il murale sa quali scritte ha", ", ".join(ids))

	var m := SceneMural.new()
	m.setup(st)
	root.add_child(m)
	check(m.errors.is_empty() and m.has_writing("tit") and m.has_writing("reg") and not m.has_writing("logo"),
		"Scritte: quelle staccate dalla zona e quelle di murale.json", "; ".join(m.errors))
	var wt: Dictionary = m.writings.get("tit", {})
	var wr: Dictionary = m.writings.get("reg", {})
	check(not wt.is_empty() and Vector2(wt["pos"]) == Vector2(16, 26) and int(wt["glyphs"]) == 3 and str(wt["mode"]) == "spray",
		"Scritte: la zona staccata ha le sue tre lettere, su due righe, a spray", "%s" % [wt.get("glyphs")])
	var hole := m._sprite.texture.get_image().get_pixel(24, 34)
	var over: Image = wt.get("img")
	check(hole.is_equal_approx(bg) and over != null and over.get_pixel(24 - 16, 34 - 26).is_equal_approx(Color.WHITE),
		"Scritte: nella vignetta il buco si riempie col fondo, la scritta sta sopra", "%s" % hole)
	check(not wr.is_empty() and Vector2(wr["pos"]) == Vector2(100, 80) and str(wr["mode"]) == "scrivi" and int(wr["glyphs"]) == 1,
		"Scritte: quella di murale.json sta dove è dipinta, netta")
	var wmat: ShaderMaterial = wt["mat"]
	check(m.writing_done("manca") and not m.write("manca") and float(wmat.get_shader_parameter(&"progress")) == 0.0,
		"Scritte: prima del passo non si vede; una che non c'è non ferma la scena")
	m.write("tit", 30)
	for i in 15:
		m.tick()
	var mid := float(wmat.get_shader_parameter(&"progress"))
	check(not m.writing_done("tit") and mid > 0.3 and mid < 0.8, "Scritte: a metà dei tick è dipinta a metà", "%.2f" % mid)
	for i in 15:
		m.tick()
	check(m.writing_done("tit") and float(wmat.get_shader_parameter(&"progress")) > 1.0, "Scritte: alla fine è dipinta tutta")
	m.write("tit", 10, "scrivi")
	check(str(wt["mode"]) == "scrivi" and (wt["drips"] as Array).is_empty() and float(wmat.get_shader_parameter(&"fresh")) == 0.0
		and not m.writing_done("tit"), "Scritte: col modo «scrivi» riparte netta, senza colature né vernice fresca")
	check(m.handoff_camera() == Vector2(10, 20), "Sciogli: la telecamera del gioco al passaggio è quella di murale.json")
	m.melt(20)
	check(m.melting and m.closing and bool(m._mat.get_shader_parameter(&"melt"))
		and m._mat.get_shader_parameter(&"melt_center") == Vector2(100, 60), "Sciogli: parte dal centro del passaggio")
	for i in 20:
		m.tick()
	check(m.is_closed(), "Sciogli: in \"rivela_tick\" il murale se n'è andato")
	m.free()

	# Nel lettore: il nero sotto il murale, le bande solo sotto, la scritta, e lo scioglimento che lascia
	# la telecamera del gioco dove dice il murale.
	var sd := SceneData.new()
	sd.id = "prova_scritte"
	sd._parse({"formato": 1, "spazio": "stanza", "passi": [
		{"fai": "nero", "entra": true, "tick": 1},
		{"fai": "murale", "id": "prova/scritta", "rivela_tick": 10, "tick": 20, "scritte": [{"id": "tit", "zona": [16, 26, 34, 34]}]},
		{"fai": "bande", "entra": true, "sopra": false},
		{"fai": "scritta", "id": "tit", "tick": 10},
		{"fai": "nero", "entra": false, "tick": 1},
		{"fai": "murale", "sciogli": true, "rivela_tick": 10}]})
	SceneData._cache["prova_scritte"] = sd
	var room := _prologue_room()
	room._scene_request = {"id": "prova_scritte", "poses": {}}
	room._start_scene()
	var sp := room.scene
	var sim_tick := room.tick
	var black_max := 0.0
	var black_under := false
	var top_off := false
	var melt_cam: Variant = null
	var frames := 0
	while sp != null and is_instance_valid(sp) and sp.holds_sim() and frames < 400:
		room._scene_frame()
		frames += 1
		black_max = maxf(black_max, sp._black_a)
		if sp._black_a > 0.0 and not sp._murals.is_empty():
			black_under = black_under or sp._black.get_index() < sp._murals[0].get_index()
		top_off = top_off or (sp._step_i >= 3 and not sp._bars_top)
		if melt_cam == null and not sp._murals.is_empty() and sp._murals[-1].melting:
			melt_cam = sp._view_center(sp._cam_c, sp._cam_z)
	check(black_max == 1.0 and black_under, "Nero: entra sopra il gioco e sotto i murales")
	check(top_off, "Bande: con \"sopra\" falso entra solo quella di sotto")
	check(melt_cam == Vector2(10, 20) + View.SIZE / 2.0, "Sciogli: sotto il murale la telecamera è già quella del gioco", "%s" % [melt_cam])
	check(frames < 400 and sp._murals.is_empty() and room.tick == sim_tick,
		"Sciogli: la scena aspetta lo scioglimento, con la simulazione ferma", "%d" % frames)
	for i in ScenePlayer.OUTRO + 2:
		if room.scene != null:
			room._scene_frame()
	_free_room(room)

	# Saltata prima dello scioglimento: il murale si scioglie, non si chiude a spray.
	var sd2 := SceneData.new()
	sd2.id = "prova_scritte_2"
	sd2._parse({"formato": 1, "spazio": "stanza", "passi": [{"fai": "murale", "id": "prova/scritta", "rivela_tick": 10},
		{"fai": "attendi", "tick": 500}, {"fai": "murale", "sciogli": true}]})
	SceneData._cache["prova_scritte_2"] = sd2
	room = _prologue_room()
	room._scene_request = {"id": "prova_scritte_2", "poses": {}}
	room._start_scene()
	sp = room.scene
	for i in 40:
		room._scene_frame()
	var mm := sp.mural()
	sp._skip()
	check(mm != null and mm.melting, "Sciogli: se la scena si salta prima, il murale si scioglie lo stesso")
	for i in ScenePlayer.OUTRO + 2:
		if room.scene != null:
			sp.tick()
	check(room.scene == null, "Sciogli: saltata, la scena finisce nell'uscita")
	_free_room(room)
	SceneData.clear_cache()
	SceneMural.dir = SceneMural.DIR_DEFAULT
	for n in ["murale.png", "scritta_reg.png", "murale.json"]:
		DirAccess.remove_absolute(dir + "/" + n)
	DirAccess.remove_absolute(dir)
	DirAccess.remove_absolute(base + "/prova")
	DirAccess.remove_absolute(base)

	# I murales veri: MP08 riusa MP06 e il logo, le righe di MP10, i titoli staccati di MP05 e MP13.
	var m8 := SceneMural.new()
	m8.setup({"id": "prologo/mp08_titolo"})
	check(SceneMural.exists({"id": "prologo/mp08_titolo"}) and m8.errors.is_empty() and m8.size == Vector2(480, 270)
		and m8._figures.size() == (JSON.parse_string(FileAccess.get_file_as_string(
			SceneMural.DIR_DEFAULT + "/prologo/mp06_cimitero/murale.json"))["figure"] as Array).size()
		and m8.has_writing("logo") and m8.handoff_camera() == Vector2(35, 230),
		"Murales: MP08 riusa MP06 con le sue figure, ha il logo e si scioglie a cam (35, 230)",
		"; ".join(m8.errors) + " camera %s" % m8.handoff_camera())
	m8.free()
	var m10 := SceneMural.new()
	m10.setup({"id": "prologo/mp10_registro"})
	var regs := true
	for i in range(1, 5):
		regs = regs and m10.has_writing("registro_%d" % i)
	check(m10.errors.is_empty() and regs, "Murales: MP10 ha le quattro righe del registro", "; ".join(m10.errors))
	m10.free()
	for pair: Array in [["prologo/mp05_carmine", "scritta_1", [118, 1, 230, 47]], ["prologo/mp13_tetti", "titolo_1", [135, 18, 245, 26]]]:
		var mz := SceneMural.new()
		mz.setup({"id": pair[0], "scritte": [{"id": pair[1], "zona": pair[2]}]})
		var w: Dictionary = mz.writings.get(pair[1], {})
		check(mz.errors.is_empty() and not w.is_empty() and int(w["glyphs"]) >= 6,
			"Murales: da %s si stacca la scritta %s, lettera per lettera" % [pair[0], pair[1]], "%s" % [w.get("glyphs")])
		mz.free()


## I rinforzi al muro: GIG in cima al muro del cimitero chiede la scena; la scena recita da sola, senza
## battute, con la simulazione ferma; i rider restano sotto il muro, GIG riparte da dov'era.
func _test_rinforzi() -> void:
	SceneData.clear_cache()
	var sd := SceneData.load_scene(Prologue.RINFORZI)
	check(sd.errors.is_empty() and sd.space == "stanza" and sd.rif == "h" and sd.line_ids().is_empty(),
		"Rinforzi: il copione è valido, nel mondo platform e senza battute", "; ".join(sd.errors))
	var room := _prologue_room()
	var asked := false
	for t in 6000:
		room._sim_tick()
		room._follow_camera()
		if room.seen_rinforzi:
			asked = str(room._scene_request.get("id", "")) == Prologue.RINFORZI
			break
	check(asked and room._on_wall_top() and room.player.facing == 1, "Rinforzi: in cima al muro la stanza chiede la scena")
	if not asked:
		_free_room(room)
		return
	var px := room.player.px
	var py := room.player.py
	var sim_tick := room.tick
	room._start_scene()
	var sp := room.scene
	check(sp != null and sp.holds_sim(), "Rinforzi: la scena parte")
	if sp == null:
		_free_room(room)
		return
	var h := Vector2(room.grid.marks["h"][0])
	var g0 := Vector2((sp.puppets["gig"] as ScenePuppet).px, (sp.puppets["gig"] as ScenePuppet).py)
	check(g0.distance_to(Vector2(room.player.sprite_anchor())) < 1.0, "Rinforzi: la comparsa di GIG parte dal GIG del gioco",
		"%s / %s" % [g0, room.player.sprite_anchor()])
	var frames := 0
	while sp.holds_sim() and frames < 4000:
		room._scene_frame()
		frames += 1
	check(not sp.holds_sim() and frames > 300 and frames < 1200, "Rinforzi: la scena finisce da sola, in automatico", "%d fotogrammi" % frames)
	check(room.tick == sim_tick and room.player.px == px and room.player.py == py, "Rinforzi: durante la scena la simulazione resta ferma")
	var under := 0
	for p in room._extras:
		if is_instance_valid(p) and absf(p.py - h.y) < 1.0 and p.px > h.x - 80 and p.px < h.x + Prologue.RINFORZI_TOP.x:
			under += 1
	check(under == 3, "Rinforzi: a scena finita i tre rider restano al cancello, sotto il muro", "%d" % under)
	for i in ScenePlayer.OUTRO + 2:
		sp.tick()
	check(room.scene == null and is_equal_approx(room.zoom, 1.0), "Rinforzi: le bande escono e la telecamera torna quella del gioco")
	_free_room(room)


# --- Il messo e i rider col braccio segnato (decisione 63) ------------------------------------------

## Il messo: compare al suo posto, mira lungo la corsia e segna il braccio, si evita uscendo dalla
## corsia, un colpo interrompe la mira, scappa da GIG, chiama i rider (al massimo tre), una combo e giù.
func _test_messo() -> void:
	var keys := [0]
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return keys[0]), 375.0, 225.0)
	var g := lvl.player
	g.hp = 100000
	var m := lvl.spawn_thug(&"messo", -1, g.py, "", {"x": g.px - lvl.camera.x + 160.0, "verso": -1}) as Messo
	check(m != null and m.state == Fighter.State.IDLE and is_equal_approx(m.px, g.px + 160.0) and m.facing == -1,
		"Messo: con \"x\" compare già al suo posto, fermo")
	if m == null:
		Harness.free_level(lvl)
		return
	check(m._call_timer == Messo.FIRST_CALL and Messo.FIRST_CALL <= 120 and Messo.CALL_EVERY <= 300,
		"Messo: la prima chiamata dei rinforzi arriva presto", "dopo %d tick, poi ogni %d" % [m._call_timer, Messo.CALL_EVERY])
	m._call_timer = 100000
	m._aim_timer = 0
	var marked_at := -1
	for i in 200:
		lvl.step()
		if g.marked > 0:
			marked_at = i
			break
	check(marked_at >= Messo.AIM_TICKS - 5 and marked_at < 160, "Messo: mira lungo la corsia di GIG e il laser gli segna il braccio", "tick %d" % marked_at)
	check(lvl.director.holder_uid != m.uid, "Messo: non chiede il turno d'attacco")
	# Uscendo dalla corsia mentre mira, il laser va a vuoto.
	g.marked = 0
	m._aim_timer = 0
	var aimed := false
	for i in 240:
		lvl.step()
		if m.act == Messo.Act.AIM and not aimed:
			aimed = true
			keys[0] = _D
		if aimed and m.act != Messo.Act.AIM:
			break
	keys[0] = 0
	check(aimed and g.marked == 0, "Messo: uscendo dalla corsia il laser va a vuoto", "mira %s, segno %d" % [aimed, g.marked])
	# Colpito mentre mira: il laser si interrompe.
	m._aim_timer = 0
	var hit := false
	for i in 240:
		lvl.step()
		if m.act == Messo.Act.AIM and m.act_t > 20:
			m.set_state(Fighter.State.HURT, &"hurt_high")
			m.stun = 12
			hit = true
			break
	for i in Messo.AIM_TICKS + 20:
		lvl.step()
	check(hit and g.marked == 0 and m.act != Messo.Act.AIM, "Messo: colpito mentre mira, il laser si interrompe", "colpito %s, segno %d" % [hit, g.marked])
	# GIG si avvicina: il messo si allontana.
	m._aim_timer = 100000
	m.px = g.px + 70.0
	m.py = g.py
	var d0 := absf(m.px - g.px)
	for i in 60:
		lvl.step()
	check(absf(m.px - g.px) > d0 + 30.0, "Messo: se GIG si avvicina si allontana", "%.0f → %.0f" % [d0, absf(m.px - g.px)])
	for i in 60:
		lvl.step()
	# I rinforzi: un rider a chiamata, ma non più di MAX_RIDERS in campo.
	m._call_timer = 0
	var riders0 := m.riders_alive()
	for i in Messo.CALL_AT + 2:
		lvl.step()
	check(m.riders_alive() == riders0 + 1, "Messo: chiama un rider ogni %d tick" % Messo.CALL_EVERY, "%d → %d" % [riders0, m.riders_alive()])
	for i in Messo.MAX_RIDERS:
		var r := lvl.spawn_thug(&"rider", 1, g.py, "")
		r.ai_enabled = false
	m._call_timer = 0
	var before := m.riders_alive()
	for i in Messo.CALL_TICKS + 5:
		lvl.step()
	check(before >= Messo.MAX_RIDERS and m.riders_alive() == before, "Messo: con %d rider in campo non ne chiama altri" % Messo.MAX_RIDERS,
		"%d → %d" % [before, m.riders_alive()])
	var dmg := 0
	for id in Gig.CHAIN_ONE_ARM:
		dmg += (load("res://data/attacks/%s.tres" % id) as AttackData).damage
	check(dmg < m.data.max_hp and dmg * 2 >= m.data.max_hp, "Messo: servono due combo col braccio bloccato per metterlo KO",
		"combo %d, vita %d" % [dmg, m.data.max_hp])
	# L'autodifesa: dopo DEFEND_HITS colpi di fila, con GIG vicino, la scossa del tablet.
	for r in lvl.fighters:
		if r is Rider:
			r.hp = 0
			r.dead = true
			r.removed = true
			r.visible = false
	m._call_timer = 100000
	m._aim_timer = 100000
	m._stop_act()
	m.set_state(Fighter.State.IDLE, &"idle")
	m.px = g.px + 50.0
	m.py = g.py
	m.facing = -1
	m.hit_streak = Messo.DEFEND_HITS
	var hp0 := g.hp
	lvl.step()
	check(m.is_pulsing(), "Messo: dopo %d colpi di fila si difende con la scossa del tablet" % Messo.DEFEND_HITS, "stato %s" % m.state)
	var jab := load("res://data/attacks/gig_jab2.tres") as AttackData
	check(m.try_block(g, jab), "Messo: mentre carica la scossa para i colpi")
	m.hitstop = 0
	var downed := false
	for i in m.pulse_attack.startup + m.pulse_attack.active + 4:
		lvl.step()
		if g.state in [Fighter.State.KNOCK_AIR, Fighter.State.KNOCK_DOWN]:
			downed = true
	check(downed and g.hp < hp0, "Messo: la scossa butta giù GIG, se gli sta addosso", "a terra %s, vita %d → %d" % [downed, hp0, g.hp])
	for i in 80:
		lvl.step()
		if not m.is_pulsing():
			break
	check(not m.is_pulsing() and not m.try_block(g, jab), "Messo: finita la scossa torna colpibile")
	check(m._call_timer <= 0 or m.act == Messo.Act.CALL, "Messo: dopo la scossa chiama subito un rider", "timer %d" % m._call_timer)
	# Lontano da GIG la serie si azzera senza scossa; e da sola, lasciato in pace, si spegne.
	m._call_timer = 100000
	m._stop_act()
	for i in 60:
		lvl.step()
	m.set_state(Fighter.State.IDLE, &"idle")
	m.px = g.px + 250.0
	m.hit_streak = Messo.DEFEND_HITS
	lvl.step()
	check(not m.is_pulsing() and m.hit_streak == 0, "Messo: con GIG lontano la scossa non parte")
	m.hit_streak = 2
	for i in Messo.STREAK_RESET + 5:
		lvl.step()
	check(m.hit_streak == 0, "Messo: la serie di colpi si azzera dopo %d tick senza colpi" % Messo.STREAK_RESET)
	Harness.free_level(lvl)


# --- Le vite ----------------------------------------------------------------------------------------

## GIG fuori dal fondo della mappa nel prologo: quanti tick fino alla ripartenza (o al CONTINUA?).
func _lives_fall(room: Prologue) -> int:
	room.player.place(room.player.px, room.grid.pixel_height() + TestRoom.FALL_OUT + 6)
	var started := false
	for t in TestRoom.FALL_TICKS + 20:
		room._sim_tick()
		started = started or room.fall_t >= 0
		if started and room.fall_t < 0:
			return t
	return -1


## Le vite del prologo (Luigi, 8 novembre 2026): la fossa costa una vita e si riparte dall'ultima
## ripartenza; senza vite CONTINUA? e poi GAME OVER; il KO nell'arena ospitata costa una vita.
## Il prologo disegnato in LDtk è lo stesso livello della mappa di testo da cui viene (prologo.txt,
## rifatto dal .ldtk con tools/ldtk/livelli_ldtk.py): celle, segni nello stesso ordine e ripartenze.
## Poi i controlli della legenda: il prologo li passa, un livello sbagliato no.
func _test_ldtk() -> void:
	var txt := SolidGrid.load_file("res://data/platform/prologo.txt")
	var m := LdtkMap.read(Prologue.PROLOGUE_V1)
	var g := m.grid
	check(g.width == txt.width and g.height == txt.height, "ldtk: misure del prologo",
		"%dx%d contro %dx%d" % [g.width, g.height, txt.width, txt.height])
	check(g.cells == txt.cells, "ldtk: celle uguali alla mappa di testo")
	check(g.marks.keys() == txt.marks.keys(), "ldtk: stesse lettere, nello stesso ordine",
		"%s contro %s" % [g.marks.keys(), txt.marks.keys()])
	var same := true
	for k: String in txt.marks:
		same = same and g.marks.get(k, []) == txt.marks[k]
	check(same, "ldtk: segni nelle stesse posizioni")
	check(g.checkpoints == Prologue.CHECKPOINT_SIGNS, "ldtk: le ripartenze sono i cartelli del prologo",
		str(g.checkpoints))
	var texts := true
	for k: String in g.signs:
		texts = texts and g.marks.has(k) and not String(g.signs[k][0]).is_empty()
	check(g.signs.size() == 9 and texts, "ldtk: i nove cartelli hanno titolo", str(g.signs.keys()))
	check(SolidGrid.load_file(Prologue.PROLOGUE_V1).cells == txt.cells, "ldtk: load_file legge il .ldtk")
	var voids := 0
	for v in m.values:
		voids += int(v == LdtkMap.Val.VUOTO)
	check(voids == 30, "ldtk: le tre fosse sono Vuoto", str(voids))
	check(m.check(), "ldtk: il prologo passa i controlli", ", ".join(m.errors))
	# Gli unici avvisi sono i quattro pieni sospesi che il prologo ha già (alle celle 92,12, 130,6,
	# 236,0 e 300,9): nessuna fossa senza Vuoto e nessuna cella che il motore non fa.
	var others := 0
	for wn in m.warnings:
		others += int(not wn.begins_with("pieno sospeso"))
	check(others == 0 and m.warnings.size() == 4, "ldtk: il prologo ha solo i pieni sospesi noti", ", ".join(m.warnings))
	# L'arena viene dalla sua zona, che cade dove la metteva il cartello f; l'uscita va fuori dal file.
	var ar: Array[Dictionary] = g.arenas
	var f: Vector2i = g.marks["f"][0]
	check(ar.size() == 1 and ar[0]["id"] == "pignoramento" and ar[0]["ripartenza"] == "f"
		and (ar[0]["rect"] as Rect2i).position.x == f.x + TestRoom.ARENA_CAM_FROM_SIGN and (ar[0]["rect"] as Rect2i).end.y == f.y,
		"ldtk: l'arena del prologo è la sua zona, dove la metteva il cartello f", str(ar))
	check(g.next_level == "capitolo-1" and LdtkMap.next_path(Prologue.PROLOGUE_V1, g) == "" and m.levels == PackedStringArray(["Prologo"]),
		"ldtk: l'uscita del prologo porta al capitolo 1, fuori dal file", g.next_level)
	_test_ldtk_levels()
	# Un livello sbagliato: una ripartenza sopra la prima fossa e un pannello che non apre niente.
	var bad := LdtkMap.read(Prologue.PROLOGUE_V1)
	bad.entities.append({"tipo": "Ripartenza", "iid": "r", "livello": "Entita", "px": Vector2i(48 * 20 + 10, 480),
		"pos": Vector2i.ZERO, "size": Vector2i(20, 20), "campi": {}})
	bad.entities.append({"tipo": "Pannello", "iid": "p", "livello": "Entita", "px": Vector2i(1000, 400),
		"pos": Vector2i.ZERO, "size": Vector2i(20, 20), "campi": {"apre": [], "chiude": []}})
	# E un rider sulle piattaforme, dove stanno solo i droni; una colomba lì invece va bene.
	for t: String in ["rider", "colomba"]:
		bad.entities.append({"tipo": "Nemico", "iid": t, "livello": "Entita", "px": Vector2i(1200, 460),
			"pos": Vector2i.ZERO, "size": Vector2i(25, 100), "campi": {"tipo": t, "arena": null}})
	var failed := not bad.check()
	var joined := " | ".join(bad.errors)
	check(failed and "sopra la fossa" in joined and "Pannello" in joined and "Nemico rider" in joined
		and not "Nemico colomba" in joined and bad.errors.size() == 3, "ldtk: i controlli trovano gli errori", joined)


## Un file con due livelli, come il prologo nuovo (prologo_v2.ldtk, A e B): si legge l'uno o l'altro,
## l'uscita di A porta a B, e l'arena di A chiude sul suo cartello.
func _test_ldtk_levels() -> void:
	var path := "user://test_livelli.ldtk"
	var ent := func(tipo: String, iid: String, px: Vector2i, size: Vector2i, pivot: Array, campi: Dictionary) -> Dictionary:
		var fi := []
		for k: String in campi:
			fi.append({"__identifier": k, "__value": campi[k]})
		return {"__identifier": tipo, "iid": iid, "px": [px.x, px.y], "width": size.x, "height": size.y,
			"__pivot": pivot, "fieldInstances": fi}
	var level := func(id: String, w: int, ents: Array, zones: Array) -> Dictionary:
		var csv := []
		for y in 6:
			for x in w:
				csv.append(1 if y == 5 else 0)
		return {"identifier": id, "layerInstances": [
			{"__identifier": "Zone", "entityInstances": zones},
			{"__identifier": "Entita", "entityInstances": ents},
			{"__identifier": "Collisioni", "__cWid": w, "__cHei": 6, "intGridCsv": csv, "entityInstances": []}]}
	var a: Dictionary = level.call("A", 40, [
		ent.call("Partenza", "pa", Vector2i(30, 100), Vector2i(20, 40), [0.5, 1], {"dopo_riavvio": false}),
		ent.call("Cartello", "cf", Vector2i(500, 100), Vector2i(20, 40), [0.5, 1], {"id": "f", "titolo": "ARENA", "riga": "", "ripartenza": true}),
		ent.call("Uscita", "ua", Vector2i(780, 100), Vector2i(40, 100), [0.5, 1], {"prossima": "B"})],
		[ent.call("Arena", "ar", Vector2i(200, 0), Vector2i(480, 100), [0, 0],
			{"id": "prova", "inclinata": true, "corsie": 3, "fine": "messo_ko", "ripartenza": {"entityIid": "cf"}})])
	var b: Dictionary = level.call("B", 30, [
		ent.call("Partenza", "pb", Vector2i(30, 100), Vector2i(20, 40), [0.5, 1], {"dopo_riavvio": false}),
		ent.call("Uscita", "ub", Vector2i(580, 100), Vector2i(40, 100), [0.5, 1], {"prossima": null})], [])
	var fa := FileAccess.open(path, FileAccess.WRITE)
	fa.store_string(JSON.stringify({"levels": [a, b]}))
	fa.close()
	check(LdtkMap.level_names(path) == PackedStringArray(["A", "B"]), "ldtk: un file con due livelli, A e B")
	var ma := LdtkMap.read(path)
	var mb := LdtkMap.read(path + "#B")
	check(ma.grid.width == 40 and mb.grid.width == 30 and LdtkMap.read(path + "#A").grid.width == 40,
		"ldtk: senza nome si legge il primo livello, col nome quello scelto", "%d, %d" % [ma.grid.width, mb.grid.width])
	check(LdtkMap.next_path(path, ma.grid) == path + "#B" and LdtkMap.next_path(path + "#B", mb.grid) == "",
		"ldtk: l'uscita di A porta a B, quella di B fuori dal file")
	var ar: Array[Dictionary] = ma.grid.arenas
	check(ar.size() == 1 and ar[0]["rect"] == Rect2i(200, 0, 480, 100) and ar[0]["ripartenza"] == "f" and ar[0]["fine"] == "messo_ko"
		and mb.grid.arenas.is_empty(), "ldtk: l'arena di A è la sua zona e chiude sul cartello f", str(ar))
	check(ma.check(), "ldtk: il livello A passa i controlli", ", ".join(ma.errors))
	check(mb.check() and "Uscita" in " ".join(mb.warnings), "ldtk: un'uscita senza prossima è un avviso", ", ".join(mb.warnings))
	# Un'arena senza ripartenza è un errore.
	ma.entities[ma.entities.size() - 1]["campi"]["ripartenza"] = null
	check(not ma.check() and "Arena prova" in " ".join(ma.errors), "ldtk: un'arena senza ripartenza è un errore", ", ".join(ma.errors))
	LdtkMap._parsed.erase(path)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))

## Il prologo nuovo, in due livelli dello stesso file: la partenza sotto l'introduzione, le ripartenze
## di A e di B, la leva del cancello, il passaggio da A a B e la fine, sempre uguali da un giro all'altro.
## Gli interni del prologo v2 (la galleria A4): le zone di LDtk, la copertura, le ante e gli stipiti,
## lo stacco di 0,3 s, i limiti della telecamera e niente pioggia dentro. Tutto solo disegno.
func _test_prologue_interiors() -> void:
	var room := _prologue_room(Callable(), Prologue.PROLOGUE_MAP)
	var names: Array = room._interiors.map(func(z: Dictionary) -> String: return z["nome"])
	var gal: Dictionary = room._interiors[names.find("galleria")] if names.has("galleria") else {}
	var dry := false
	for r: Rect2 in room.weather.dry:
		dry = dry or (not gal.is_empty() and r == gal["rect"])
	check(names.has("galleria") and names.has("deposito") and gal["rect"] == Rect2(2940, 432, 1160, 248)
		and gal["cam"] == [2876.0, 4624.0, 432.0, 680.0] and gal["stacco"] and room._cam_zones.size() == 2 and dry,
		"Interni: la galleria e il deposito di A4 vengono da LDtk, coi limiti della telecamera, e dentro non piove",
		"interni %s, galleria %s, telecamere %d, asciutta %s" % [names, gal, room._cam_zones.size(), dry])
	# La tavola: la copertura sopra la scena e le persone, le ante 64x140 sopra di lei, gli stipiti sopra
	# GIG, la moto nuova e la luce dell'uscita.
	var gate: Sprite2D = room._gallery_states.get("cancello_chiuso")
	var moto := false
	for sp: Sprite2D in room._scene_art:
		moto = moto or (str(sp.name) == "Galleria_a4_moto_rider" and sp.position == Vector2(4665, 592))
	var jambs := 0
	for n in room._cover_nodes:
		if n.z_index == 8 and jambs == 0:  # il primo è di A4; dopo viene il palo del cantiere
			jambs += n.get_child_count()
	var exit_light := room._gallery_lights.any(func(l: PointLight2D) -> bool: return str(l.name).contains("uscita"))
	check(room._covers.size() == 1 and room._covers[0].position == Vector2(2876, 432) and gate != null
		and gate.position == Vector2(4548, 540) and gate.texture.get_size() == Vector2(64, 140)
		and gate.get_parent().z_index == 6 and room._gallery_gates.has(Rect2(4548, 540, 64, 140)) and jambs == 2
		and moto and exit_light,
		"Interni: in A4 la copertura, le ante 64x140, i due stipiti, la moto nuova e la luce dell'uscita",
		"copertura %d, cancello %s, stipiti %d, moto %s, uscita %s" % [room._covers.size(),
			gate.position if gate != null else Vector2.ZERO, jambs, moto, exit_light])
	# Fuori, davanti all'arco: copertura piena, GIG sopra di lei, la vista non passa 2984.
	room.player.place(2900, 680)
	room._reset_interiors()
	for i in 40:
		room._follow_camera()
	var out_ok := room._cover_k == 1.0 and room._body.z_index == 7 and room._visible_rect().end.x <= 2984.0
	var out_s := "copertura %.2f, z %d, vista %s" % [room._cover_k, room._body.z_index, room._visible_rect()]
	# Dentro: lo stacco annerisce, a metà la vista salta dentro i limiti e la copertura sparisce.
	room.player.place(2960, 680)
	room._follow_camera()
	var dark := room._cut_alpha() > 0.0 and room._zone_shown == -1
	for i in Prologue.CUT_TICKS / 2 - 1:
		room._follow_camera()
	var v := room._visible_rect()
	var in_ok := room._zone_shown >= 0 and room._cover_k == 0.0 and room._cut_alpha() == 1.0 and v.position.x >= 2876.0 \
		and v.position.y >= 432.0 and room._body.z_index == 0
	for i in Prologue.CUT_TICKS:
		room._follow_camera()
	in_ok = in_ok and room._cut_alpha() == 0.0
	var in_s := "vista %s, copertura %.2f, nero %.2f" % [v, room._cover_k, room._cut_alpha()]
	# Sul tetto (dal vano della scala): stacco anche dall'alto, poi copertura piena e telecamera libera.
	room.player.place(3820, 420)
	for i in Prologue.CUT_TICKS + Prologue.LIMIT_BLEND:
		room._follow_camera()
	var roof_ok := room._zone_shown == -1 and room._cover_k == 1.0 and room._view_push == Vector2.ZERO
	# Un passo dentro e subito fuori: lo stacco si riavvolge e non cambia niente.
	room.player.place(2900, 680)
	room._reset_interiors()
	room.player.place(2960, 680)
	for i in 3:
		room._follow_camera()
	room.player.place(2900, 680)
	for i in Prologue.CUT_TICKS:
		room._follow_camera()
	var back_ok := room._zone_shown == -1 and room._cut_t == 0 and room._cover_k == 1.0
	check(out_ok and dark and in_ok and roof_ok and back_ok,
		"Interni: fuori la vista si ferma all'arco, entrando lo stacco a gradini porta dentro i limiti, dal tetto si esce, un passo indietro riavvolge",
		"fuori %s %s; nero %s; dentro %s %s; tetto %s (spinta %s); indietro %s" % [out_ok, out_s, dark, in_ok, in_s,
			roof_ok, room._view_push, back_ok])
	# S1, il ricovero del custode: niente stacco, la facciata (con l'emissione e la luce della targa) sfuma
	# in 0,3 s quando GIG entra dalla breccia, con un k suo (la copertura di A4 resta piena), e torna fuori
	# e sul tetto.
	var s1: Dictionary = room._secrets[0] if room._secrets.size() == 1 else {}
	var s1_k := func() -> float: return float(s1.get("k", -1.0))
	var s1_mount := not s1.is_empty() and (s1["arte"][0] as Sprite2D).position == Vector2(2580, 570) \
		and (s1["arte"] as Array).size() == 2 and (s1["luci"] as Array).size() == 1 \
		and str((s1["luci"][0][0] as PointLight2D).name) == "Luce_targa_eterna" \
		and ((s1["arte"][0] as Sprite2D).get_parent() as Node2D).z_index == 6
	room.player.place(2560, 680)
	room._reset_interiors()
	for i in 4:
		room._follow_camera()
	var s1_out: float = s1_k.call()
	room.player.place(2680, 680)
	for i in Prologue.CUT_TICKS / 2:
		room._follow_camera()
	var s1_mid: float = s1_k.call()
	for i in Prologue.CUT_TICKS / 2:
		room._follow_camera()
	room._update_gallery()
	var s1_in: float = s1_k.call()
	var s1_hidden := not s1.is_empty() and not (s1["arte"][0] as Sprite2D).visible \
		and not (s1["luci"][0][0] as PointLight2D).visible
	var s1_nocut := room._cut_t == 0 and room._cover_k == 1.0
	room.player.place(2680, 540)
	for i in Prologue.CUT_TICKS:
		room._follow_camera()
	room._update_gallery()
	var s1_roof: float = s1_k.call()
	var s1_lit := not s1.is_empty() and (s1["arte"][0] as Sprite2D).visible \
		and is_equal_approx((s1["luci"][0][0] as PointLight2D).energy, 0.12)
	check(s1_mount and s1_out == 1.0 and is_equal_approx(s1_mid, 0.5) and s1_in == 0.0 and s1_hidden and s1_nocut
			and s1_roof == 1.0 and s1_lit,
		"Prologo v2: in S1 la facciata del ricovero sfuma senza stacco quando GIG entra, e torna fuori",
		"montata %s, fuori %.2f, a metà %.2f, dentro %.2f (nascosta %s, niente stacco %s), sul tetto %.2f (accesa %s)" % [
			s1_mount, s1_out, s1_mid, s1_in, s1_hidden, s1_nocut, s1_roof, s1_lit])
	# Un salto dal vano che sfiora il soffitto (piedi 5 px sopra il bordo) non fa uno stacco; con la vista
	# larga, dentro la galleria lo zoom torna stretto nel nero e fuori torna largo.
	room.wide_cam = true
	room._px_s = 3
	room.player.place(3820, 680)
	room._reset_interiors()
	var wide_in := room._wide_k
	room.player.place(3820, 427)
	for i in 4:
		room._follow_camera()
	var graze_ok := room._zone_raw >= 0 and room._cut_t == 0
	room.player.place(3820, 420)
	for i in Prologue.CUT_TICKS / 2:
		room._follow_camera()
	var wide_mid := room._wide_k
	for i in Prologue.CUT_TICKS:
		room._follow_camera()
	room.wide_cam = false
	room._px_s = 1
	check(graze_ok and wide_in == 0.0 and wide_mid == 1.0 and room._zone_shown == -1,
		"Interni: un salto che sfiora il soffitto non fa lampeggiare lo stacco; con la vista larga dentro è stretta, cambia nel nero",
		"sfiora %s, zoom dentro %.2f, a metà dello stacco %.2f, zona %d" % [graze_ok, wide_in, wide_mid, room._zone_shown])
	room.queue_free()


func _test_prologue_v2() -> void:
	var room := _prologue_room(Callable(), Prologue.PROLOGUE_MAP)
	room._follow_camera()
	check(room._levels.size() == 2 and room.level == 0 and room._cps().size() == 4,
		"Prologo v2: due livelli, si parte da A con le sue quattro ripartenze",
		"%d livelli, livello %d, %d ripartenze" % [room._levels.size(), room.level, room._cps().size()])
	check(room.player.px == 230 and room.player.py == 680 and is_equal_approx(room._cam.y, 450.0),
		"Prologo v2: GIG parte sotto la lapide e la telecamera tiene il pavimento a 230 px dall'alto",
		"GIG %d,%d, telecamera y %.0f" % [room.player.px, room.player.py, room._cam.y])
	# L'introduzione si scioglie nel gioco dove MP08 dice, spostato in basso come la grafica di A.
	var m8 := SceneMural.new()
	m8.setup({"id": "prologo/mp08_titolo"})
	var hand: Variant = m8.handoff_camera()
	check(room.art_offset_y == Prologue.ART_SHIFT_Y and hand is Vector2
		and (hand as Vector2) + Vector2(0, room.art_offset_y) == room._cam.round(),
		"Prologo v2: la partenza di A combacia con l'inquadratura di MP06 e MP08",
		"murale %s + %d, gioco %s" % [hand, room.art_offset_y, room._cam])
	m8.free()
	# Le ripartenze di A: dopo l'arena (f) si riparte a scontro finito e sotto la pioggia.
	var arena_cp := room._arena_cp()
	room.checkpoint = arena_cp
	room._reset()
	var f: Vector2i = room.grid.marks[room._cps()[arena_cp]][0]
	check(room.arena_done and room.raining and room.player.px == f.x - 30 and room.player.py == f.y,
		"Prologo v2: la ripartenza dell'arena riparte a scontro finito, sotto la pioggia",
		"arena %s, pioggia %s, GIG %d,%d" % [room.arena_done, room.raining, room.player.px, room.player.py])
	# La galleria A4: la scena al suo posto, il grigio che lì non si disegna, le colonne davanti solo nel
	# loro tratto; all'inizio la porticina è intera e il cancello del deposito chiuso.
	var g0 := room.gallery_state()
	var cols: Backdrop.Layer = null
	var a4_layers: Array = room._galleries[0].layers if not room._galleries.is_empty() else []
	for l: Backdrop.Layer in a4_layers:
		if l.z >= 1000:
			cols = l
	check(room.art_holes.size() == 6 and room.art_holes[3] == Rect2(2760, 200, 1960, 520) and room._art_extra.size() == 4
		and cols != null
		and Backdrop.alpha(cols, 2700) == 0.0 and Backdrop.alpha(cols, 3300) == 1.0 and Backdrop.alpha(cols, 3950) == 0.0,
		"Prologo v2: la galleria A4 è montata, con le colonne davanti nel loro tratto", "buchi %s" % [room.art_holes])
	# A6, il cantiere davanti al muro: la scena al suo posto, il cartellone provvisorio di A4 tolto (ora è
	# nella scena), i ferri davanti solo lungo il cantiere.
	var a6_front: Backdrop.Layer = null
	if room._galleries.size() > 1:
		for l: Backdrop.Layer in room._galleries[1].layers:
			if l.z >= 1000:
				a6_front = l
	var billboard := false
	for sp: Sprite2D in room._scene_art:
		billboard = billboard or sp.name.contains("cartellone")
	check(room.art_holes.size() == 6 and room.art_holes[4] == Rect2(4600, 402, 880, 398)
		and room.art_holes[5] == Rect2(5480, 200, 1480, 600) and not billboard
		and a6_front != null and Backdrop.alpha(a6_front, 5400) == 0.0 and Backdrop.alpha(a6_front, 6200) == 1.0,
		"Prologo v2: la tavola A6 è montata, senza il cartellone provvisorio di A4", "buchi %s, cartellone %s" % [
			room.art_holes, billboard])
	# A5, il piazzale del pignoramento: il chiavistello sopra la sua leva, il sigillo SIDERA che tremola
	# quando GIG gli arriva davanti, il pavimento dipinto dell'arena; poi la soglia del cantiere, col palo
	# davanti a GIG.
	var latch_lever := false
	for l in room._levers:
		latch_lever = latch_lever or (room._lever_drawn(l["px"]) and int(l["px"].x) > 4560 and int(l["px"].x) < 4720)
	var seal_ok := false
	if room._gallery_states.has("sigillo_1"):
		var sr := Prologue._sprite_rect(room._gallery_states["sigillo_1"])
		var keep := Vector2i(room.player.px, room.player.py)
		room.player.px = int(sr.get_center().x)
		room.player.py = room._floor_y
		room._seal_near = false
		room._seal_from = -100000
		seal_ok = room._tick_seal() == 0
		room.player.px = keep.x
		room.player.py = keep.y
		room._seal_near = false
		room._seal_from = -100000
	var post := false
	for n in room._cover_nodes:
		for c in n.get_children():
			post = post or (n.z_index == 8 and str(c.name).contains("cantiere_davanti") and c.position == Vector2(5470, 542))
	check(latch_lever and seal_ok and room._gallery_states.has("chiavistello_tirato")
		and room._gallery_states.has("varco_lampeggiante_acceso") and not room._arena_floor.is_empty()
		and room._arena_floor["x"] == 4560 and room._arena_floor["y"] == 680 and post,
		"Prologo v2: A5 e la soglia del cantiere, col chiavistello, il sigillo, il pavimento dell'arena e il palo davanti",
		"leva %s, sigillo %s, pavimento %s, palo %s" % [latch_lever, seal_ok, room._arena_floor.get("x"), post])
	# A1-A3, dall'ingresso alla galleria: tre tavole di fila da x 0 a 2920, senza la scena di prima (A1 ne
	# riusa le colonne 0-25), e ognuna con le sue luci in additivo.
	var old_scene := false
	for sp: Sprite2D in room._scene_art:
		old_scene = old_scene or str(sp.name).begins_with("Scena_")
	var a_emis := 0
	for n in room._room_node.get_children():
		if n is Sprite2D and str(n.name) in ["Galleria_a1_emis", "Galleria_a2_emis", "Galleria_a3_emis"]:
			a_emis += 1
	check(room.art_holes.size() == 6 and room.art_holes.slice(0, 3) == [Rect2(0, 200, 720, 600),
			Rect2(720, 200, 960, 600), Rect2(1680, 200, 1240, 600)] and not old_scene and a_emis == 3,
		"Prologo v2: in A le tavole A1-A3 coprono da 0 a 2920, al posto della scena di prima",
		"buchi %s, scena di prima %s, emissioni %d" % [room.art_holes, old_scene, a_emis])
	# I fondi larghi: cielo, lontano, cappelle e lapidi di tutto A, allo zoom della vista. Della grafica di
	# prima restano solo la prima schermata e il suo primo piano.
	var old_names: Array = []
	for l: Backdrop.Layer in room.backdrop.layers:
		old_names.append(l.name)
	var wide: Dictionary = {}
	if room._wide_art != null:
		for l: Backdrop.Layer in room._wide_art.layers:
			wide[l.name] = l
	check(wide.size() == 12 and room._art_view.size() == 1 and old_names == ["davanti"],
		"Prologo v2: in A i fondi sono i piani larghi, al posto del cielo, del medio e del vicino di prima",
		"larghi %s, di prima %s" % [wide.keys(), old_names])
	# I tre veli: rosa fino ad A3, scirocco in A4, pioggia da A5. Il velo dopo sfuma sopra quello prima,
	# che resta pieno sotto: a ogni telecamera ogni piano ha almeno un velo pieno (niente trasparenze).
	var ramp := func(n: String, xs: Array) -> Array:
		return xs.map(func(x: int) -> float: return snappedf(Backdrop.alpha(wide[n], x), 0.01) if wide.has(n) else -1.0)
	var sky := [ramp.call("cielo_rosa", [2780, 3780, 3800]), ramp.call("cielo_chiude", [2780, 3280, 3780, 4680, 4700]),
		ramp.call("cielo_pioggia", [3780, 4230, 4680, 6240])]
	var holes: Array = []
	if wide.size() == 12:
		for g: String in ["cielo", "lontano", "medio", "vicino"]:
			for x in range(0, 6241, 20):
				var full := false
				for l: Backdrop.Layer in room._wide_art.layers:
					full = full or (l.name.begins_with(g + "_") and Backdrop.alpha(l, x) >= 1.0)
				if not full:
					holes.append("%s@%d" % [g, x])
	check(sky == [[1.0, 1.0, 0.0], [0.0, 0.5, 1.0, 1.0, 0.0], [0.0, 0.5, 1.0, 1.0]] and holes.is_empty(),
		"Prologo v2: lungo A i fondi passano dal rosa allo scirocco alla pioggia, senza buchi", "cielo %s, buchi %s" % [
			sky, holes.slice(0, 6)])
	# Coprono la vista larga (720x405) in tutto A: abbastanza larghi per la corsa del bordo sinistro
	# (0-6240), e il medio e il vicino dipinti fino sotto il bordo basso anche con la vista più su e più giù
	# (cima da -147 a 395): niente più cappelle che si staccano dal muro in A6.
	var short: Array = []
	for n: String in wide:
		var l: Backdrop.Layer = wide[n]
		var run := mini(l.x_to, 6240) - l.origin_x
		if l.texture.get_width() < 720 + ceili(run * l.scroll):
			short.append("%s largo %d" % [n, l.texture.get_width()])
		if n.begins_with("medio") or n.begins_with("vicino"):
			for top: int in [-147, 395]:
				var bottom := l.y - roundi((top - room._wide_art.cam_ref_y) * l.scroll_y) + l.texture.get_height()
				if bottom < 405:
					short.append("%s fondo %d a cima %d" % [n, bottom, top])
	check(wide.size() == 12 and short.is_empty(), "Prologo v2: i fondi larghi di A coprono la vista larga ovunque",
		str(short))
	check(g0.get("porta_intera") == true and g0.get("porta_rotta") == false and g0.get("cancello_chiuso") == true
		and g0.get("cancello_aperto") == false,
		"Prologo v2: la porticina è intera e il cancello del deposito chiuso", str(g0))
	# In A6, prima della leva: il quadro giù, i fari spenti, il cancelletto chiuso, i LED accesi, e i
	# lampeggianti che si alternano.
	room.tick = 0
	room._update_gallery()
	var l0 := room.gallery_state()
	room.tick = Prologue.BLINK_TICKS
	room._update_gallery()
	var l1 := room.gallery_state()
	check(l0.get("quadro_giu") == true and l0.get("quadro_su") == false and l0.get("fari_spenti") == true
		and l0.get("fari_accesi") == false and l0.get("cancelletto_chiuso") == true and l0.get("led_eterna") == true
		and l0.get("lampeggianti_accesi") != l1.get("lampeggianti_accesi")
		and l0.get("lampeggianti_accesi") != l0.get("lampeggianti_spenti"),
		"Prologo v2: in A6, prima della leva, il quadro è giù, i fari spenti e i lampeggianti lampeggiano",
		"%s / %s" % [l0, l1])
	# La leva apre il suo cancello: le celle chiuse sono piene, aperte vuote.
	var gate: Dictionary = {}
	var lever: Dictionary = {}
	for l: Dictionary in room._levers:
		for g: Dictionary in room._gates2:
			if g["iid"] in l["apre"]:
				gate = g
				lever = l
	var cell: Vector2i = gate["cells"][0] if not gate.is_empty() else Vector2i.ZERO
	var closed := not gate.is_empty() and room.grid.cell(cell.x, cell.y) == SolidGrid.Cell.SOLID
	if not lever.is_empty():
		room.pulled.append(String(lever["iid"]))
		room._apply_gates()
	check(closed and room.grid.cell(cell.x, cell.y) == SolidGrid.Cell.EMPTY,
		"Prologo v2: la leva apre il suo cancello", "cancello %s, cella %s" % [gate.get("iid", "nessuno"), cell])
	# Il cancello disegnato segue quello della sua leva; la porticina si rompe quando la mappa si apre.
	for l: Dictionary in room._levers:
		for g: Dictionary in room._gates2:
			if g["iid"] in l["apre"] and room._gate_drawn(g["rect"]):
				room.pulled.append(String(l["iid"]))
	room._apply_gates()
	room._update_gallery()
	var g1 := room.gallery_state()
	for y in range(22, 28):
		room.grid.set_cell(188, y, SolidGrid.Cell.EMPTY)
	room._update_gallery()
	var g2 := room.gallery_state()
	check(g1["cancello_aperto"] and not g1["cancello_chiuso"] and g1["porta_intera"]
		and g2["porta_rotta"] and not g2["porta_intera"],
		"Prologo v2: il cancello della galleria si apre con la leva, la porticina si mostra rotta quando si apre",
		"%s / %s" % [g1, g2])
	check(g1.get("quadro_su") == true and g1.get("quadro_giu") == false and g1.get("fari_accesi") == true
		and g1.get("cancelletto_aperto") == true and g1.get("cancelletto_chiuso") == false,
		"Prologo v2: in A6 la leva alza il quadro, accende i fari e apre il cancelletto", str(g1))
	_free_room(room)

	# Il giro intero col pilota, due volte: deve venire uguale.
	var runs: Array[Dictionary] = []
	for k in 2:
		room = _prologue_room(Callable(), Prologue.PROLOGUE_MAP)
		var out := {"arena": -1, "lever": -1, "switch": -1, "reboot": -1, "end": -1, "b_start": Vector2i(-1, -1),
			"b_rain": false, "b_cps": 0, "b_cp": -1}
		for t in 9000:
			room._sim_tick()
			room._follow_camera()
			if room.arena_done and out["arena"] < 0:
				out["arena"] = t
			if not room.pulled.is_empty() and out["lever"] < 0:
				out["lever"] = t
			if room.level == 1 and out["switch"] < 0:
				out["switch"] = t
				out["b_start"] = Vector2i(room.player.px, room.player.py)
				out["b_rain"] = room.raining
				out["b_cps"] = room._cps().size()
			if room.level == 1:
				out["b_cp"] = maxi(out["b_cp"], room.checkpoint)
			if room.rebooted and out["reboot"] < 0:
				out["reboot"] = t
			if room.finished:
				out["end"] = t
				var pose := room.scene_pose_player("")
				out["outro"] = [room.outro_t, room.player.state == PlatformPlayer.State.AIR, room.player.vy,
					"%s %d" % [pose["anim"], pose["index"]]]
				break
		out["hash"] = room.state_hash()
		out["registri"] = Game.registri.keys()
		runs.append(out)
		if k == 1:
			# Una ripartenza di B: dopo il riavvio si riparte dal banco del garage, la X.
			var x: Vector2i = room.grid.marks["X"][0]
			room.finished = false
			room._reset()
			check(room.level == 1 and room.player.px == x.x and room.player.py == x.y,
				"Prologo v2: in B, dopo il riavvio, si riparte dal banco", "livello %d, GIG %d,%d" % [room.level, room.player.px, room.player.py])
		_free_room(room)
	var r := runs[0]
	var b: Vector2i = SolidGrid.load_file(Prologue.PROLOGUE_MAP + "#Prologo_B_Fuga").marks["G"][0]
	check(r["arena"] > 0 and r["lever"] > r["arena"] and r["switch"] > r["lever"],
		"Prologo v2: in A il pilota fa l'arena, tira la leva ed esce", "arena %d, leva %d, uscita %d" % [r["arena"], r["lever"], r["switch"]])
	check(r["b_start"] == b and r["b_rain"] and r["b_cps"] == 3,
		"Prologo v2: B comincia dalla sua partenza, sotto la pioggia, con tre ripartenze",
		"GIG %s (partenza %s), pioggia %s, %d ripartenze" % [r["b_start"], b, r["b_rain"], r["b_cps"]])
	check(r["b_cp"] == 2 and r["reboot"] > r["switch"] and r["end"] > r["reboot"],
		"Prologo v2: in B il pilota passa le ripartenze, riavvia il braccio e finisce",
		"ripartenza %d, riavvio %d, fine %d" % [r["b_cp"], r["reboot"], r["end"]])
	var outro: Array = r.get("outro", [0, false, -1, ""])
	check(int(outro[0]) > Prologue.OUTRO_RUN and int(outro[0]) <= 90 and bool(outro[1]) and int(outro[2]) < 0
			and str(outro[3]) == "jump_arc %d" % Prologue.OUTRO_ARC,
		"Prologo v2: all'uscita GIG corre e salta da solo, e il prologo finisce poco prima dell'apice, sulla posa della figura di MP13 (entro un secondo e mezzo)",
		"tick %d, in aria %s, vy %d, posa %s" % [int(outro[0]), outro[1], int(outro[2]), outro[3]])
	check(runs[0]["hash"] == runs[1]["hash"] and runs[0]["end"] == runs[1]["end"],
		"Prologo v2: due giri del pilota vengono uguali", "%s / %s" % [runs[0]["hash"], runs[1]["hash"]])
	check(str(runs[0]["registri"]) == str(["registro_prologo_1"]) and str(runs[1]["registri"]) == str(["registro_prologo_1"]),
		"Registro: nel garage il pilota copia la base dello scaffale, con la Vista", str(runs[0]["registri"]))

	# --livello sceglie il livello da cui partire.
	Game.options.level_name = "Prologo_B_Fuga"
	room = _prologue_room(Callable(), Prologue.PROLOGUE_MAP)
	Game.options.level_name = ""
	check(room.level == 1 and room.player.px == b.x and room.player.py == b.y,
		"Prologo v2: --livello Prologo_B_Fuga parte da B", "livello %d, GIG %d,%d" % [room.level, room.player.px, room.player.py])
	# La base del registro sullo scaffale di B4: si copia con SU, solo col braccio vivo, in un secondo.
	var regs := room.registri
	var base: Registri.Base = regs.basi[0] if regs.basi.size() == 1 else null
	check(base != null and base.id == "registro_prologo_1" and base.px == Vector2i(3810, 580) and not base.read,
		"Registro: in B c'è una base sola, registro_prologo_1, sullo scaffale di B4 a (3810, 580)",
		"basi %d" % regs.basi.size())
	if base != null:
		room.player.place(base.px.x - 12, base.px.y)
		var up := InputFrame.new(InputFrame.UP, InputFrame.UP)
		var dead := regs.step(up, room.player, false)
		var started := regs.step(up, room.player, true)
		var busy_ticks := 0
		var evs: Array = []
		while regs.step(InputFrame.new(), room.player, true):
			busy_ticks += 1
			evs.append_array(Array(regs.events))
		evs.append_array(Array(regs.events))
		check(not dead and started and busy_ticks == Registri.COPY_TICKS - 1 and base.read
				and Game.registri.has("registro_prologo_1") and Registri.count() == 1 and room.player.facing == 1
				and str(evs) == str(["registro_ronzio", "registro_lampo", "registro_copiato"]),
			"Registro: SU accanto alla base copia il registro in un secondo, solo dopo il riavvio, e il conto va a 1 su 15",
			"senza braccio %s, partita %s, %d tick, letta %s, conto %d, eventi %s" % [dead, started, busy_ticks, base.read,
				Registri.count(), evs])
		var again := regs.step(up, room.player, true)
		regs.reset()
		check(not again and base.read and regs.near(room.player) < 0,
			"Registro: una base letta resta letta, anche alla ripartenza, e non si copia due volte", "di nuovo %s" % again)
	Game.registri.clear()
	# B2: le palazzine dei Tamburi, con la bici e la serranda del fruttivendolo e le luci in additivo.
	var b0 := room.gallery_state()
	var hole_b2: Rect2 = room.art_holes[1] if room.art_holes.size() > 1 else Rect2()
	var emis_b2: Sprite2D = room._room_node.get_node_or_null("Galleria_b2_emis")
	check(hole_b2 == Rect2(720, 0, 1960, 880) and emis_b2 != null and not room._scene_art.has(emis_b2)
			and (emis_b2.material as CanvasItemMaterial).blend_mode == CanvasItemMaterial.BLEND_MODE_ADD
			and b0.size() == 10,
		"Prologo v2: in B le palazzine B2 sono montate, con le luci in additivo",
		"buchi %s, stati %s" % [room.art_holes, b0])
	# B1, la piazzetta del fioraio davanti al muro del cimitero: a (0, 0), prima di B2, con le sue luci.
	var emis_b1: Sprite2D = room._room_node.get_node_or_null("Galleria_b1_emis")
	check(not room.art_holes.is_empty() and room.art_holes[0] == Rect2(0, 0, 720, 880) and emis_b1 != null
			and (emis_b1.material as CanvasItemMaterial).blend_mode == CanvasItemMaterial.BLEND_MODE_ADD,
		"Prologo v2: in B la tavola B1 è montata a (0, 0), prima di B2, con le luci in additivo",
		"buchi %s" % [room.art_holes])
	# I fondi di B sono i piani larghi (cielo, lontano, medio e il vicino dell'isolato dietro), allo zoom
	# della vista: coprono la corsa del bordo sinistro (0-3840), e il medio e il vicino sono dipinti fino
	# sotto il bordo basso anche con la vista più su e più giù (cima da -147 a 475).
	var wide_b: Dictionary = {}
	if room._wide_art != null:
		for l: Backdrop.Layer in room._wide_art.layers:
			wide_b[l.name] = l
	var short_b: Array = []
	for n: String in wide_b:
		var l: Backdrop.Layer = wide_b[n]
		if l.texture.get_width() < View.W + ceili((3840 - l.origin_x) * l.scroll):
			short_b.append("%s largo %d" % [n, l.texture.get_width()])
		if n == "medio" or n == "vicino":
			for top: int in [-147, 475]:
				var bottom := l.y - roundi((top - room._wide_art.cam_ref_y) * l.scroll_y) + l.texture.get_height()
				if bottom < 405:
					short_b.append("%s fondo %d a cima %d" % [n, bottom, top])
	check(wide_b.keys() == ["cielo", "lontano", "medio", "vicino"] and room._art_view.size() == 1
			and room._galleries.is_empty() and short_b.is_empty(),
		"Prologo v2: in B i fondi sono i piani larghi, e coprono la vista larga ovunque",
		"larghi %s, vestizioni con piani %d, corti %s" % [wide_b.keys(), room._galleries.size(), short_b])
	check(b0.get("bici_sigillo", false) and not b0.get("bici_libera", true)
			and b0.get("serranda_chiusa", false) and not b0.get("serranda_aperta", true),
		"Prologo v2: in B la bici ha il sigillo e la serranda è chiusa", str(b0))
	# Il fruttivendolo ringrazia (la sua Vedetta è rotta): apre la serranda e la bici è libera.
	var fr: Favors.Person = null
	for q in room.favors.persone:
		if q.ringrazia.begins_with("fruttivendolo"):
			fr = q
	if fr != null:
		fr.thanked = true
		for pr: Variant in fr.premio:
			room.favors.opened.append(str(pr))
	room._apply_gates()
	room._update_gallery()
	var b_thanks := room.gallery_state()
	# La botola la alza lui: si vede aperta dal fotogramma della posa in cui l'anta è sopra la testa.
	var lift := -1
	var fs := room.favors.person_sheet("fruttivendolo")
	if fr != null and fs != null:
		lift = fs.clip(&"sollievo").total_ticks()
		for i in Favors.BOTOLA_UP_FRAME:
			lift += fs.clip(&"botola").frames[i].ticks
		fr.thanked_t = lift - 1
		room._update_gallery()
	var b_half := room.gallery_state()
	if fr != null:
		fr.thanked_t = lift
	room._update_gallery()
	var b1 := room.gallery_state()
	check(fr != null and b1.get("bici_libera", false) and not b1.get("bici_sigillo", true)
			and b1.get("serranda_aperta", false) and not b1.get("serranda_chiusa", true)
			and b_thanks.get("serranda_chiusa", false) and b_half.get("serranda_chiusa", false) and lift > 0,
		"Prologo v2: il fruttivendolo ringrazia, la bici è libera e la serranda si apre quando lui alza l'anta",
		"subito %s, a %d-1 %s, poi %s" % [b_thanks, lift, b_half, b1])
	# Le pose del fruttivendolo: in ansia, il grazie, la botola verso la cantina (a destra), il «di qua».
	var poses := []
	if fr != null and fs != null:
		for k in [0, 10, 40, 200]:
			fr.thanked_t = k
			var po := room.favors.person_pose(fr, fr.px.x - 100, 7)
			poses.append("%s %d" % [po[1], po[3]])
		fr.thanked = false
		poses.append("%s %d" % [room.favors.person_pose(fr, fr.px.x - 100, 7)[1], room.favors.person_pose(fr, fr.px.x - 100, 7)[3]])
		fr.thanked = true
		fr.thanked_t = lift
	check(poses == ["sollievo -1", "sollievo -1", "botola 1", "diqua 1", "idle -1"],
		"Prologo v2: il fruttivendolo ha lo sprite vero, ringrazia guardando GIG e alza la botola verso la cantina",
		str(poses))
	# B3, il forno e lo scavo: dopo B2 e sopra (sotto terra si toccano, colonne 128-139). All'inizio il
	# sacchetto c'è, la porta della 168 è aperta e del fumo si vede un fotogramma alla volta.
	var b3_above := false
	var i2 := -1
	for sp: Sprite2D in room._scene_art:
		if sp.name.ends_with("b2_scena"):
			i2 = sp.get_index()
		elif sp.name.ends_with("b3_scena"):
			b3_above = i2 >= 0 and sp.get_index() > i2
	var smoke := [b0.get("fumo_1"), b0.get("fumo_2"), b0.get("fumo_3")].count(true)
	check(room.art_holes.size() == 4 and room.art_holes[2] == Rect2(2560, 200, 880, 680) and b3_above
			and b0.get("sacchetto") == true and b0.get("porta_chiusa") == false and smoke == 1,
		"Prologo v2: in B la tavola B3 è montata sopra B2, col sacchetto, la porta aperta e il fumo",
		"buchi %s, sopra %s, stati %s" % [room.art_holes, b3_above, b0])
	# B4, il garage: dopo B3, dalla cima alla terra (colonne 172-227), con le luci dipinte in additivo.
	# Sopra il tetto la tavola è trasparente, e lì si vedono i fondi larghi.
	var b4_ok := false
	for sp: Sprite2D in room._scene_art:
		if sp.name.ends_with("b4_scena"):
			b4_ok = sp.get_index() > i2
	var b4_em := false
	for n in room._room_node.get_children():
		if n is Sprite2D and str(n.name).ends_with("b4_emis"):
			b4_em = (n as Sprite2D).material is CanvasItemMaterial 					and ((n as Sprite2D).material as CanvasItemMaterial).blend_mode == CanvasItemMaterial.BLEND_MODE_ADD
	check(room.art_holes.size() == 4 and room.art_holes[3] == Rect2(3440, 0, 1120, 880) and b4_ok and b4_em,
		"Prologo v2: in B la tavola B4, il garage, è montata dopo B3 con le sue luci dipinte",
		"buchi %s, scena %s, luci %s" % [room.art_holes, b4_ok, b4_em])
	# Le luci vive di B2, B3 e B4 (maxischermo, portone, botola, forno, grata, lampada del garage): sei
	# sugli attori, e sulla scena gli aloni ad anello (sei) e le pozze (maxischermo, portone, forno, lampada). Solo le
	# tavole prendono gli aloni; il forno tremola e il maxischermo pulsa; si spengono con le altre.
	var actors_l := 0
	var scene_l := 0
	var lit := true
	for l in room._gallery_lights:
		lit = lit and l.enabled
		if l.range_item_cull_mask == Fighter.LIGHT_MASK_ACTORS:
			actors_l += 1
		elif l.range_item_cull_mask == room.LIGHT_MASK_SCENE:
			scene_l += 1
	var scene_masked := true
	for sp in room._scene_art:
		if sp is Sprite2D and str(sp.name).begins_with("Galleria_") and not room._covers.has(sp):
			scene_masked = scene_masked and (sp.light_mask & room.LIGHT_MASK_SCENE) != 0
	var breathes: bool = room.light_rhythm("tremola", 10, 0.0) != room.light_rhythm("tremola", 30, 0.0) 		and room.light_rhythm("pulsa", 0, 0.0) != room.light_rhythm("pulsa", 40, 0.0) 		and room.light_rhythm("", 30, 0.0) == 1.0
	room._set_lights(false)
	var off := room._gallery_lights.all(func(l: PointLight2D) -> bool: return not l.enabled)
	room._set_lights(true)
	check(lit and off and actors_l == 18 and scene_l == 14 and scene_masked and breathes,
		"Prologo v2: in B le luci vive illuminano gli attori, gli aloni la scena, e si spengono con F5",
		"attori %d, scena %d, tavole %s, respiro %s, %s" % [actors_l, scene_l, scene_masked, breathes, room._gallery_lights.map(func(l: PointLight2D) -> String: return "%s %s" % [l.name, l.enabled])])
	# GIG prende i taralli: il sacchetto sparisce. La porta si chiude dietro di lui: si vede chiusa. Il
	# fumo passa al fotogramma dopo.
	for it in room.favors.ristori:
		if it.tipo == "taralli":
			it.taken = true
	room.door_closed = true
	var t0 := room.tick
	room.tick = t0 + Prologue.SMOKE_TICKS
	room._update_gallery()
	var b2 := room.gallery_state()
	var moved := false
	for k: String in ["fumo_1", "fumo_2", "fumo_3"]:
		moved = moved or (b0.get(k) == true and b2.get(k) == false)
	check(b2.get("sacchetto") == false and b2.get("porta_chiusa") == true and moved,
		"Prologo v2: in B3 il sacchetto sparisce coi taralli, la porta si chiude e il fumo gira", str(b2))
	room.tick = t0
	room.door_closed = false
	# B4, il garage vestito: la facciata con la sua finestra e gli stipiti di fuori si vedono fuori; il
	# muro di dentro, gli stipiti di dentro e la porta chiusa vista da dentro solo dentro; la luce
	# fredda della porta solo dentro e con la porta aperta.
	var names := func(arr: Array) -> Array:
		return arr.map(func(n: Node) -> String: return str(n.name)).filter(func(n: String) -> bool: return n.contains("b4_"))
	var add := func(sp: Sprite2D) -> bool:
		return sp != null and sp.material is CanvasItemMaterial 			and (sp.material as CanvasItemMaterial).blend_mode == CanvasItemMaterial.BLEND_MODE_ADD
	var glow_b4: Array = names.call(room._cover_glow)
	var in_b4: Array = names.call(room._inside_art)
	var add_ok := true
	for sp: Sprite2D in room._cover_glow:
		if str(sp.name).ends_with("copertura_emis"):
			add_ok = add_ok and add.call(sp)
	check(str(names.call(room._covers)) == str(["Galleria_b4_copertura"])
			and str(glow_b4) == str(["Galleria_b4_copertura_emis", "Galleria_b4_stipiti_fuori"])
			and str(in_b4) == str(["Galleria_b4_dentro", "Galleria_b4_stipiti_dentro", "Galleria_b4_porta_dentro"])
			and room._door_light != null and str(room._door_light.name) == "Galleria_b4_luce_porta"
			and add.call(room._door_light) and add_ok,
		"Prologo v2: in B4 la facciata, il dentro, gli stipiti dei due lati e la luce della porta sono montati",
		"copertura %s, fuori %s, dentro %s" % [names.call(room._covers), glow_b4, in_b4])
	var vis := func() -> String:
		var o: Array = []
		for sp: Sprite2D in room._covers + room._cover_glow + room._inside_art + [room._door_light]:
			if sp.visible and str(sp.name).begins_with("Galleria_b4_"):
				o.append(str(sp.name).trim_prefix("Galleria_b4_"))
		o.sort()
		return ",".join(o)
	room._cover_k = 1.0
	room._update_gallery()
	var v_out: String = vis.call()
	room._cover_k = 0.0
	room._update_gallery()
	var v_open: String = vis.call()
	room.door_closed = true
	room._update_gallery()
	var v_shut: String = vis.call()
	room.door_closed = false
	check(v_out == "copertura,copertura_emis,stipiti_fuori" and v_open == "dentro,luce_porta,stipiti_dentro"
			and v_shut == "dentro,porta_dentro,stipiti_dentro",
		"Prologo v2: in B4 fuori si vede la facciata, dentro il muro e la luce della porta, che si spegne con la porta chiusa",
		"fuori %s; dentro aperta %s; dentro chiusa %s" % [v_out, v_open, v_shut])
	# Il lucernario (colonne 186-189): lì piove anche nel garage, e la copertura sfuma coi piedi di GIG
	# negli ultimi 40 px sopra il tetto, senza stacco. La base del registro (190, 28) resta libera.
	var roof := room._roof_holes.map(func(h: Rect2) -> String: return "%d-%d" % [h.position.x, h.end.x])
	var dry_at := func(p: Vector2) -> bool:
		return room._dry_rects().any(func(r: Rect2) -> bool: return r.has_point(p))
	var garage: Rect2 = Rect2()
	for z in room._interiors:
		if (z["rect"] as Rect2).has_point(Vector2(3760, 600)):
			garage = z["rect"]
	room._cut_t = 0
	room.player.place(3760, int(garage.position.y) - 20)
	room._tick_interiors(true)
	var mid_k: float = room._cover_k
	room.player.place(3760, int(garage.position.y) - 60)
	room._tick_interiors(true)
	var high_k: float = room._cover_k
	# Sul bordo del tetto accanto (colonna 185) la facciata resta piena: sfuma solo sopra il buco.
	room.player.place(3712, int(garage.position.y) - 20)
	room._tick_interiors(true)
	var edge_k: float = room._cover_k
	check(roof.has("3720-3800") and not dry_at.call(Vector2(3760, 600)) and dry_at.call(Vector2(3600, 600))
			and dry_at.call(Vector2(3900, 600)) and is_equal_approx(mid_k, 0.5) and high_k == 1.0 and edge_k == 1.0
			and room.grid.cell(190, 28) == SolidGrid.Cell.EMPTY,
		"Prologo v2: dal lucernario di B4 piove nel garage e la copertura sfuma coi piedi, solo sopra il buco",
		"buchi %s, garage %s, a metà %.2f, sopra %.2f, sul bordo %.2f, cella del registro %d" % [roof, garage, mid_k,
			high_k, edge_k, room.grid.cell(190, 28)])
	# Le cantine sotto B2 e B3: fuori la copertura; dentro il muro riacceso, la sua emissione, la terra
	# sopra il soffitto e sette luci che si accendono solo dentro. Il telaio della botola sta sotto le
	# serrande. Dentro non piove, tranne sotto la grata (2660-2760); la botola chiusa non fa buco.
	var cant_cover: Array = room._covers.map(func(n: Node) -> String: return str(n.name)).filter(
		func(n: String) -> bool: return n.contains("cantine"))
	var cant_in: Array = room._inside_art.map(func(n: Node) -> String: return str(n.name)).filter(
		func(n: String) -> bool: return n.contains("cantine"))
	cant_in.sort()
	var above_sp: Sprite2D = room._room_node.find_child("Galleria_cantine_sopra", true, false)
	var above_z := above_sp != null and (above_sp.get_parent() as Node2D).z_index == 6
	var cant_em: Sprite2D = room._room_node.get_node_or_null("Galleria_cantine_emis")
	var frame_sp: Sprite2D = room._room_node.get_node_or_null("Galleria_cantine_telaio")
	var shut: Sprite2D = room._gallery_states.get("serranda_chiusa")
	var frame_under := frame_sp != null and shut != null and frame_sp.get_index() < shut.get_index()
	room._cover_k = 1.0
	room._update_gallery()
	var lit_out: bool = room._inside_lights.any(func(p: Array) -> bool: return (p[0] as PointLight2D).visible)
	room._cover_k = 0.0
	room._update_gallery()
	var lit_in: bool = room._inside_lights.all(func(p: Array) -> bool:
		return (p[0] as PointLight2D).visible and is_equal_approx((p[0] as PointLight2D).energy, float(p[1])))
	room._cover_k = 1.0
	room._update_gallery()
	check(str(cant_cover) == str(["Galleria_cantine_copertura"])
			and str(cant_in) == str(["Galleria_cantine_dentro", "Galleria_cantine_emis", "Galleria_cantine_sopra"])
			and above_z
			and add.call(cant_em) and frame_under and room._inside_lights.size() == 7 and not lit_out and lit_in
			and roof.has("2660-2760") and not roof.any(func(h: String) -> bool: return h.begins_with("1240"))
			and dry_at.call(Vector2(2000, 800)) and not dry_at.call(Vector2(2710, 800)),
		"Prologo v2: le cantine sono montate, con le luci solo dentro e la pioggia solo sotto la grata",
		"copertura %s, dentro %s, terra a z 6 %s, telaio sotto %s, luci %d fuori %s dentro %s, buchi %s" % [cant_cover,
			cant_in, above_z, frame_under, room._inside_lights.size(), lit_out, lit_in, roof])
	# Lo stacco alla botola: dall'alto, coi piedi che passano y 720 fra 1240 e 1280.
	room._cut_t = 0
	room.player.place(1260, 700)
	room._tick_interiors(true)
	room.player.place(1260, 740)
	room._tick_interiors()
	check(room._cut_t > 0, "Prologo v2: scendendo dalla botola nelle cantine c'è lo stacco", "stacco %d" % room._cut_t)
	# Dentro le cantine la telecamera mostra anche la terra sopra il soffitto (da y 610): lì non piove,
	# tranne sopra la grata. Fuori, sopra le cantine, c'è la strada e piove.
	var ci := -1
	for i in room._interiors.size():
		if (room._interiors[i]["rect"] as Rect2).position == Vector2(1218, 720):
			ci = i
	room._zone_shown = ci
	room._sync_dry()
	var band_in: bool = room.weather._is_dry(Vector2(2000, 650)) and not room.weather._is_dry(Vector2(2710, 650))
	room._zone_shown = -1
	room._sync_dry()
	var band_out: bool = room.weather._is_dry(Vector2(2000, 650))
	check(ci >= 0 and band_in and not band_out,
		"Prologo v2: dentro le cantine non piove sulla terra sopra il soffitto, ma sì dalla grata; fuori piove",
		"interno %d, dentro %s, fuori asciutto %s" % [ci, band_in, band_out])
	# Il cortile del panificio (B3): l'ombra sopra la scena di B3 e dietro GIG, il portone sopra GIG
	# con gli stipiti, la luce della strada in additivo, e il led SIDERA che lampeggia 1 s ogni 3.
	var shade: Sprite2D = room._room_node.get_node_or_null("Galleria_cortile_ombra")
	var b3_scene: Sprite2D = room._room_node.get_node_or_null("Galleria_b3_scena")
	var gate_sp: Sprite2D = room._room_node.find_child("Galleria_cortile_portone", true, false)
	var yard_em: Sprite2D = room._room_node.get_node_or_null("Galleria_cortile_luce")
	var led: PointLight2D = room._room_node.find_child("Luce_telecamera_sidera", true, false)
	var shade_ok := shade != null and b3_scene != null and shade.show_behind_parent 		and shade.get_index() > b3_scene.get_index()
	var gate_ok := gate_sp != null and (gate_sp.get_parent() as Node2D).z_index == 8
	var blink := [Prologue.light_rhythm("lampeggia", 0, 0.0), Prologue.light_rhythm("lampeggia", 59, 0.0),
		Prologue.light_rhythm("lampeggia", 60, 0.0), Prologue.light_rhythm("lampeggia", 179, 0.0)]
	check(shade_ok and gate_ok and add.call(yard_em) and led != null and str(blink) == str([1.0, 1.0, 0.0, 0.0])
			and room.find_child("Luce_strada_portone", true, false) != null,
		"Prologo v2: il cortile ha l'ombra sopra B3, il portone sopra GIG, la luce della strada e il led che lampeggia",
		"ombra %s, portone %s, luce %s, led %s, lampeggio %s" % [shade_ok, gate_ok, yard_em, led, blink])
	_free_room(room)


func _test_prologue_lives() -> void:
	var keys := [0]
	var room := _prologue_room(func(_t: int) -> int: return keys[0])
	check(room.use_lives and Game.lives == Game.START_LIVES, "Vite: il prologo comincia con %d vite" % Game.START_LIVES, "%d" % Game.lives)
	# Le fosse non hanno fondo: sotto l'ultima riga vuota si cade fuori, sotto quella piena si sta.
	var g := room.grid
	var pit := -1
	for x in g.width:
		if g.cell(x, g.height - 1) == SolidGrid.Cell.EMPTY:
			pit = x
			break
	check(pit >= 0 and g.cell(pit, g.height) == SolidGrid.Cell.EMPTY and g.cell(0, g.height) == SolidGrid.Cell.SOLID,
		"Vite: le fosse del prologo non hanno fondo, il resto del bordo sotto sì", "colonna %d" % pit)
	var pit_end := pit
	while g.cell(pit_end + 1, g.height - 1) == SolidGrid.Cell.EMPTY:
		pit_end += 1
	room.player.place((pit + pit_end + 1) * SolidGrid.TILE / 2, g.pixel_height() - 2 * SolidGrid.TILE)
	var fell := false
	for i in 120:
		room._sim_tick()
		if room.fall_t >= 0:
			fell = true
			break
	check(fell and Game.lives == Game.START_LIVES - 1, "Vite: dentro la fossa GIG cade fuori dalla mappa e perde la vita", "y %d, stato %d, vite %d" % [room.player.py, room.player.state, Game.lives])
	while room.fall_t >= 0:
		room._sim_tick()
	Game.reset_run()
	var t := _lives_fall(room)
	check(Game.lives == Game.START_LIVES - 1 and t >= TestRoom.FALL_TICKS - 2 and room.continue_t < 0,
		"Vite: cadere in una fossa costa una vita", "vite %d, %d tick" % [Game.lives, t])
	var start := room._checkpoint_pos(-1)
	check(Vector2i(room.player.px, room.player.py) == start and room.respawn_blink > 0,
		"Vite: senza ripartenze superate si riparte dalla tomba, lampeggiando", "%s / %s" % [Vector2i(room.player.px, room.player.py), start])
	# La ripartenza: il cartello superato coi piedi a terra accende la spia.
	var e: Vector2i = room.grid.marks[Prologue.CHECKPOINT_SIGNS[0]][0]
	room.player.place(e.x + 2, e.y)
	room._sim_tick()
	var lamps := room._checkpoint_lamps()
	check(room.checkpoint == 0 and room.checkpoint_tag > 0 and lamps.size() == Prologue.CHECKPOINT_SIGNS.size() and lamps[0][1] and not lamps[1][1],
		"Vite: superato il cartello la spia della ripartenza si accende", "ripartenza %d, spie %s" % [room.checkpoint, lamps])
	_lives_fall(room)
	check(Vector2i(room.player.px, room.player.py) == room._checkpoint_pos(0) and Game.lives == Game.START_LIVES - 2,
		"Vite: dopo la caduta si riparte dall'ultima ripartenza", "%s, vite %d" % [Vector2i(room.player.px, room.player.py), Game.lives])
	var h0 := room.state_hash()
	# L'ultima vita: CONTINUA?, e ATTACCO riparte con le vite piene.
	_lives_fall(room)
	check(Game.lives == 0 and room.continue_t >= 0 and room.continue_left == 9 and room.state_hash() != h0,
		"Vite: senza vite compare CONTINUA? da 9", "vite %d, conto %d" % [Game.lives, room.continue_left])
	var px := room.player.px
	keys[0] = _A
	room._sim_tick()
	keys[0] = 0
	check(room.continue_t >= 0, "Vite: il tasto ancora premuto non risponde a CONTINUA?")
	for i in TestRoom.CONTINUE_GRACE + 2:
		room._sim_tick()
	keys[0] = _A
	room._sim_tick()
	keys[0] = 0
	room._sim_tick()
	check(room.continue_t < 0 and Game.lives == Game.START_LIVES and room.player.px == px,
		"Vite: ATTACCO a CONTINUA? riparte dalla ripartenza con %d vite" % Game.START_LIVES, "vite %d" % Game.lives)
	# Senza risposta il conto arriva a 0, poi GAME OVER e il titolo.
	Game.lives = 1
	var quit := [0]
	room.quit_to_title.connect(func() -> void: quit[0] += 1)
	_lives_fall(room)
	for i in TestRoom.CONTINUE_TICKS * 10 + 5:
		room._sim_tick()
	check(room.continue_t < 0 and room.over_t >= 0 and quit[0] == 0, "Vite: senza risposta a CONTINUA? arriva il GAME OVER", "over %d" % room.over_t)
	for i in TestRoom.GAME_OVER_TICKS + 5:
		room._sim_tick()
	check(quit[0] == 1, "Vite: dopo il GAME OVER si torna al titolo, una volta", "%d" % quit[0])
	_free_room(room)
	# La stanza di prova non ha vite: la caduta riparte e basta.
	Game.reset_run()
	var tr := TestRoom.new()
	tr.configure({"input": PlayerInput.from_provider(func(_t: int) -> int: return 0), "sound": false})
	root.add_child(tr)
	tr.set_physics_process(false)
	tr.player.place(tr.player.px, tr.grid.pixel_height() + 70)
	for i in 30:
		tr._sim_tick()
	check(not tr.use_lives and Game.lives == Game.START_LIVES and tr.fall_t < 0, "Vite: nella stanza di prova cadere non costa vite")
	_free_room(tr)
	# Il KO nell'arena ospitata da un tratto con le vite.
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
	lvl.embedded = true
	lvl.embedded_lives = true
	lvl.on_player_died()
	check(Game.lives == Game.START_LIVES - 1 and not lvl.wants_continue, "Vite: il KO nell'arena del prologo costa una vita", "vite %d" % Game.lives)
	Game.lives = 1
	lvl.on_player_died()
	check(Game.lives == 0 and lvl.wants_continue, "Vite: l'ultimo KO nell'arena chiede CONTINUA? all'ospite")
	Harness.free_level(lvl)


## Col braccio segnato i rider non aspettano il turno: attaccano insieme, ognuno col suo recupero.
func _test_rider_frenzy() -> void:
	var res: Array[int] = []
	for marked: bool in [false, true]:
		var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 375.0, 225.0)
		var g := lvl.player
		g.hp = 100000
		lvl.director.keep_log = true
		lvl.spawn_thug(&"rider", 1, g.py, "", {"x": g.px - lvl.camera.x + 110.0, "verso": -1})
		lvl.spawn_thug(&"rider", -1, g.py, "", {"x": g.px - lvl.camera.x - 110.0, "verso": 1})
		for i in 600:
			if marked:
				g.marked = 100
			lvl.step()
		var starts: Array = lvl.director.events.filter(func(e: Array) -> bool: return e[2] == "start")
		var together := 0
		for a in starts.size():
			for b in range(a + 1, starts.size()):
				if starts[b][1] != starts[a][1] and int(starts[b][0]) - int(starts[a][0]) < AttackDirector.GLOBAL_GAP:
					together += 1
		res.append(together)
		lvl.director.keep_log = false
		Harness.free_level(lvl)
	check(res[0] == 0, "Rider: senza segno attaccano uno alla volta", "%d attacchi ravvicinati" % res[0])
	check(res[1] > 0, "Rider: col braccio di GIG segnato attaccano insieme", "%d attacchi ravvicinati" % res[1])


# --- Le scene nel motore (decisione 68) ------------------------------------------------------------

## I copioni delle scene: formato, attori, fogli e primi piani. Le battute: nel copione pubblico solo
## gli id, il testo nel file privato (se c'è: durante lo sviluppo), uguale alla sceneggiatura e lungo
## al massimo due righe.
func _test_scene_files() -> void:
	var ids: Array[String] = []
	for f in DirAccess.get_files_at(SceneData.DIR):
		if f.ends_with(".json"):
			ids.append(f.get_basename())
	check(ids.has(Prologue.PIGNORAMENTO), "Scene: c'è il copione del pignoramento", ", ".join(ids))
	for id in ids:
		SceneData.clear_cache()
		var sd := SceneData.load_scene(id)
		check(sd.errors.is_empty(), "Scene: il copione %s è valido" % id, "; ".join(sd.errors))
		var bad: Array[String] = []
		var faces: Array[String] = []
		for actor: String in sd.actors:
			var a: Dictionary = sd.actors[actor]
			var tipo := str(a.get("tipo", ""))
			if tipo != "" and not ResourceLoader.exists("res://data/fighters/%s.tres" % tipo):
				bad.append("%s: tipo %s" % [actor, tipo])
			var foglio := str(a.get("foglio", ""))
			if foglio != "" and not FileAccess.file_exists("res://assets/sprites/%s/%s.json" % [foglio, foglio]):
				bad.append("%s: foglio %s" % [actor, foglio])
			var cu := str(a.get("primo_piano", ""))
			if cu != "" and not faces.has(cu):
				faces.append(cu)
		for st: Dictionary in sd.steps:
			var cu2 := str(st.get("primo_piano", ""))
			if cu2 != "" and not faces.has(cu2):
				faces.append(cu2)
		for cu in faces:
			var found := false
			for n: String in [cu + "_dx", cu + "_sx", cu]:
				found = found or ResourceLoader.exists("res://assets/ui/closeups/%s.png" % n)
			if not found:
				bad.append("primo piano %s" % cu)
		var writings: Array = []
		for st: Dictionary in sd.steps:
			var fai := str(st.get("fai", ""))
			if fai == "murale" and not bool(st.get("chiudi", false)) and not bool(st.get("sciogli", false)):
				if not SceneMural.exists(st):
					bad.append("murale %s" % str(st.get("id", "")))
				else:
					writings.append_array(SceneMural.writing_ids(st))
			if fai == "scritta" and not writings.has(str(st.get("id", ""))):
				bad.append("scritta %s" % str(st.get("id", "")))
		check(bad.is_empty(), "Scene: attori, fogli, primi piani, murales e scritte del copione %s ci sono" % id, ", ".join(bad))
		if sd.lines_file == "" or not SceneLines.available(sd.lines_file):
			check(true, "Scene: le battute del copione %s (file privato assente: controllo saltato)" % id)
			continue
		var raw := FileAccess.get_file_as_string(SceneData.path_of(id))
		var md_path := SceneLines.private_dir().path_join("../sceneggiatura.md").simplify_path()
		var md := FileAccess.get_file_as_string(md_path) if FileAccess.file_exists(md_path) else ""
		var missing: Array[String] = []
		var leaked: Array[String] = []
		var long: Array[String] = []
		var differ: Array[String] = []
		for lid in sd.line_ids():
			var text := SceneLines.find(sd.lines_file, id, lid)
			if text == "":
				missing.append(lid)
				continue
			if raw.contains(text):
				leaked.append(lid)
			if ScenePlayer._wrap(text, View.W - 2 * ScenePlayer.TEXT_X).size() > 2:
				long.append(lid)
			if md != "" and not md.contains("«%s»" % text) and not md.contains("\"%s\"" % text):
				differ.append(lid)
		check(missing.is_empty(), "Scene: ogni battuta del copione %s ha il suo testo nel file privato" % id, ", ".join(missing))
		check(leaked.is_empty(), "Scene: il copione pubblico %s non contiene il testo delle battute" % id, ", ".join(leaked))
		check(long.is_empty(), "Scene: le battute del copione %s stanno in due righe" % id, ", ".join(long))
		check(md != "" and differ.is_empty(), "Scene: le battute del copione %s sono quelle della sceneggiatura" % id, ", ".join(differ))


## La scena del pignoramento nel prologo: entrando nell'arena la simulazione ne applica l'esito e la
## chiede; recitata in automatico finisce da sola senza far avanzare la simulazione, con le comparse
## dove riprendono gli attori veri; poi le bande escono e la telecamera torna quella del gioco.
func _test_pignoramento() -> void:
	SceneData.clear_cache()
	var room := _prologue_room()
	var asked := false
	for t in 4000:
		room._sim_tick()
		room._follow_camera()
		if room.arena_phase == TestRoom.ArenaPhase.FIGHT:
			asked = str(room._scene_request.get("id", "")) == Prologue.PIGNORAMENTO
			break
	check(asked, "Pignoramento: allo scontro la stanza chiede la scena")
	if room.arena == null:
		_free_room(room)
		return
	var sd := SceneData.load_scene(Prologue.PIGNORAMENTO)
	var cam_x := float(room._arena_cam_x)
	var at := func(f: Fighter, who: String) -> bool:
		var e := sd.end_of(who)
		return not e.is_empty() and is_equal_approx(f.px - cam_x, float(e["x"])) and is_equal_approx(f.py, float(e["y"])) \
			and f.facing == int(e["verso"])
	var g := room.arena.player
	var messo: Messo = null
	var rider: Rider = null
	for f in room.arena.fighters:
		if f is Messo:
			messo = f
		elif f is Rider:
			rider = f
	check(at.call(g, "gig") and g.marked == Gig.MARK_TICKS and room.raining,
		"Pignoramento: GIG davanti al cancello, girato verso il viale, col segno sul braccio, e piove",
		"x %.0f y %.0f verso %d segno %d" % [g.px - cam_x, g.py, g.facing, g.marked])
	check(messo != null and rider != null and at.call(messo, "messo") and at.call(rider, "rider") and messo.state != Fighter.State.ENTER,
		"Pignoramento: il messo e il rider sono già al loro posto")
	var sim_tick := room.tick
	var arena_tick := room.arena.tick
	room._start_scene()
	var sp := room.scene
	check(sp != null and sp.holds_sim(), "Pignoramento: la scena parte")
	if sp == null:
		_free_room(room)
		return
	var last := {}
	var frames := 0
	while sp.holds_sim() and frames < 6000:
		for who: String in sp.puppets:
			var p: ScenePuppet = sp.puppets[who]
			last[who] = Vector2(p.px - cam_x, p.py)
		room._scene_frame()
		frames += 1
	check(not sp.holds_sim() and frames > 600 and frames < 4000, "Pignoramento: la scena finisce da sola, in automatico", "%d fotogrammi" % frames)
	check(room.tick == sim_tick and room.arena.tick == arena_tick, "Pignoramento: durante la scena la simulazione resta ferma")
	var off: Array[String] = []
	for who: String in sd.outcome:
		var e := sd.end_of(who)
		if not last.has(who) or (last[who] as Vector2).distance_to(Vector2(float(e["x"]), float(e["y"]))) > 1.0:
			off.append("%s %s" % [who, last.get(who, "?")])
	check(off.is_empty(), "Pignoramento: a fine scena le comparse sono dove riprendono gli attori veri", ", ".join(off))
	check(sp.events_sent.has("pioggia") and sp.puppets.has("gig") and (sp.puppets["gig"] as ScenePuppet).marked,
		"Pignoramento: nella scena il laser lascia il segno e il cielo si chiude")
	for i in ScenePlayer.OUTRO + 2:
		sp.tick()
	check(room.scene == null and is_equal_approx(room.zoom, 1.0), "Pignoramento: le bande escono e la telecamera torna quella del gioco")
	_free_room(room)
