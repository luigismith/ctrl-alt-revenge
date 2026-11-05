extends RefCounted
## Test automatici del gameplay. Si lanciano con run_tests.gd (vedi lì).
## Ogni check stampa "ok   - nome" oppure "FAIL - nome (dettagli)".

const Harness := preload("res://tests/harness.gd")
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
	_test_replay_end()
	_test_credits_glyphs()
	_test_json_files()
	_test_replays()
	_test_platform()
	_test_room_arena()
	_test_room_hacking()
	_test_rider()
	return failures == 0


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
	var texts := PackedStringArray()
	for l: Array in c._lines:
		texts.append(str(l[0]))
	var expected := Music.credit_lines()
	var music_ok := texts.has("MUSICA")
	if expected.is_empty():
		music_ok = music_ok and texts.has(CreditsScreen.NO_MUSIC)
	else:
		# Un titolo lungo va a capo come ogni riga dei crediti: si cercano i suoi pezzi.
		for t in expected:
			for part in CreditsScreen.word_wrap(UiFont.safe_text(t, true), CreditsScreen.MAX_CHARS):
				music_ok = music_ok and texts.has(part)
	check(music_ok, "Crediti: la sezione MUSICA elenca i brani caricati", "%d brani" % expected.size())
	c.free()


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


## Le animazioni d'attacco ritemporizzate hanno esattamente i tempi dell'AttackData.
func _check_attack_timing(s: SpriteSheet) -> void:
	for f in DirAccess.get_files_at("res://data/attacks"):
		var a := load("res://data/attacks/" + f) as AttackData
		if a == null or a.anim == &"" or not String(a.id).begins_with(String(s.id) + "_"):
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

	# Sporgenza: saltando verso un muro alto 6 blocchi ci si aggrappa e si sale.
	var gl := _room(40, 20, 16)
	_box(gl, 14, 20, 10, 15)
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
	check(p.state == PlatformPlayer.State.GROUND and p.py == 10 * T and p.px > 14 * T, "Platform: dalla sporgenza si sale in cima al muro",
		"stato %s, x %d, y %d" % [p.state_name(), p.px, p.py])

	# Muro alto 5 blocchi (100 px), oltre il salto: lo spigolo arriva all'altezza del petto e,
	# senza posto per stare appesi, GIG scavalca. Non ci sono muri impossibili fra 80 e 120 px.
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
	_box(gk, 14, 22, 10, 15)
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
	var corner := Vector2i(14 * T, 10 * T)
	check(rec["hang"] > 0 and absi(rec["grip"].x - corner.x) <= 3 and absi(rec["grip"].y - corner.y) <= 3,
		"Platform: appeso, le mani di GIG sono sullo spigolo", "mani %s, spigolo %s" % [str(rec["grip"]), str(corner)])
	check(p.state == PlatformPlayer.State.GROUND and p.py == 10 * T and rec["jump"] <= 7.5,
		"Platform: a fine salita lo sprite non scatta", "stato %s, scatto di busto e piedi %.1f px, x %d" % [p.state_name(), rec["jump"], p.px])

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
