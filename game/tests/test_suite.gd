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
	return failures == 0


# --- Impostazioni ----------------------------------------------------------------------------------

func _test_settings() -> void:
	check(ProjectSettings.get_setting("display/window/size/viewport_width") == 384, "risoluzione interna larga 384")
	check(ProjectSettings.get_setting("display/window/size/viewport_height") == 216, "risoluzione interna alta 216")
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
	var lvl := Harness.make_level(root, input, 300.0, 180.0)
	var punk := lvl.spawn_thug(&"thug_punk", 1, 180.0, "")
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
	var d := _duel(_taps(2, 4, 30), 30.0)
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
	var d := _duel(_taps(2, 4, 12), 120.0)
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
	d = _duel({start: InputFrame.ATTACK, start + 7: InputFrame.ATTACK}, 120.0)
	lvl = d["level"]
	log = _attack_log(lvl, 40)
	check(log.size() == 2 and int(log[1][0]) == int(log[0][0]) + 14, "Buffer: un tocco 7 tick prima della fine viene tenuto", str(log))
	Harness.free_level(lvl)

	d = _duel({start: InputFrame.ATTACK, start + 6: InputFrame.ATTACK}, 120.0)
	lvl = d["level"]
	log = _attack_log(lvl, 40)
	check(log.size() == 1, "Buffer: un tocco 8 tick prima della fine scade", str(log))
	Harness.free_level(lvl)


func _test_hitstop() -> void:
	var d := _duel({2: InputFrame.ATTACK}, 30.0)
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
	# Presa: entro 18 px e 4 px di profondità, camminando contro il nemico.
	var held := {}
	for t in 40:
		held[t] = InputFrame.RIGHT
	var d := _duel(held, 30.0)
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
	var want_dx := float(e[0]) if not e.is_empty() else 18.0
	check(absf((punk.px - lvl.player.px) * lvl.player.facing - want_dx) < 0.01, "La vittima arriva all'offset del campo victim", "%.1f invece di %.1f" % [(punk.px - lvl.player.px) * lvl.player.facing, want_dx])
	check(worst_step <= 4.0, "Presa: la vittima si avvicina senza scatti (al massimo 4 px per tick)", "%.1f px" % worst_step)
	# Fuori corsia di 6 px: nessuna presa.
	Harness.free_level(lvl)
	d = _duel(held, 30.0)
	lvl = d["level"]
	punk = d["punk"]
	punk.py += 6.0
	var any := false
	for i in 40:
		lvl.step()
		any = any or lvl.player.state == Fighter.State.GRAB
	check(not any, "Nessuna presa fuori dai 4 px di profondità")
	Harness.free_level(lvl)
	# La vittima si libera dopo 90 tick.
	d = _duel(held, 30.0)
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
	var d := _duel(held, 30.0)
	var lvl: Level = d["level"]
	var a: Thug = d["punk"]
	var b := lvl.spawn_thug(&"thug_punk", 1, 180.0, "")
	b.ai_enabled = false
	b.px = lvl.player.px + 110.0
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
		var d := _duel(held, 30.0)
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
		var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 300.0, 180.0)
		var g := lvl.player
		var t := lvl.spawn_thug(spec[0], 1, 180.0, "")
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
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 300.0, 180.0)
	var g := lvl.player
	var b := lvl.spawn_thug(&"thug_bruiser", 1, 180.0, "")
	b.ai_enabled = false
	b.px = g.px + 40.0
	b.py = g.py
	b.facing = -1
	b.set_state(Fighter.State.IDLE)
	var punch := load("res://data/attacks/thug_bruiser_punch.tres") as AttackData
	b.start_attack(punch, lvl.next_attack_serial())
	for i in 4:
		lvl.step()
	var hp0 := b.hp
	lvl.combat.apply_hit(g, b, g.attacks[&"gig_jab1"], Vector2(b.px, b.py - 60), 1)
	check(b.state == Fighter.State.ATTACK and b.hp == hp0 - 4, "Bruto con armatura: il jab fa danno ma non lo ferma")
	lvl.combat.apply_hit(g, b, g.attacks[&"gig_hook"], Vector2(b.px, b.py - 60), 1)
	check(b.state == Fighter.State.HURT, "Bruto con armatura: il gancio lo ferma")
	Harness.free_level(lvl)


func _test_lives() -> void:
	var d := _duel({}, 200.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	var hay := load("res://data/attacks/thug_punk_haymaker.tres") as AttackData
	g.hp = 1
	lvl.combat.apply_hit(punk, g, hay, Vector2(g.px, g.py - 60), -1)
	check(g.dead and g.state == Fighter.State.KNOCK_AIR, "GIG a 0 di vita vola a terra")
	var respawned_at := -1
	for i in 400:
		lvl.step()
		if Game.lives == 2 and g.state != Fighter.State.DEAD and not g.dead:
			respawned_at = i
			break
	check(respawned_at > 0 and g.hp == g.data.max_hp and g.invuln > 60, "Una vita in meno, poi rientra con la vita piena e invulnerabile", "tick %d, vita %d, invuln %d" % [respawned_at, g.hp, g.invuln])
	check(g.ph > 100.0, "Il rientro avviene dall'alto")
	# Ultima vita: CONTINUA?
	for i in 200:
		lvl.step()
	Game.lives = 1
	g.invuln = 0
	g.hp = 1
	lvl.combat.apply_hit(punk, g, hay, Vector2(g.px, g.py - 60), -1)
	for i in 400:
		lvl.step()
		if lvl.phase == Level.Phase.CONTINUE:
			break
	check(lvl.phase == Level.Phase.CONTINUE and Game.lives == 0, "Senza vite si passa a CONTINUA?")
	Harness.free_level(lvl)


# --- AttackDirector --------------------------------------------------------------------------------

func _test_attack_director() -> void:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 1560.0, 184.0)
	AttackDirector.keep_log = true
	var thugs: Array[Thug] = []
	thugs.append(lvl.spawn_thug(&"thug_punk", 1, 170.0, "prova"))
	thugs.append(lvl.spawn_thug(&"thug_punk", -1, 196.0, "prova"))
	thugs.append(lvl.spawn_thug(&"thug_bruiser", 1, 190.0, "prova"))
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
			if releases.has(id) and tick - int(releases[id]) < 72:
				same_ok = false
			starts[id] = tick
		elif e[2] == "release":
			releases[id] = tick
	check(attacks_seen >= 6, "AttackDirector: i nemici attaccano davvero", str(attacks_seen))
	check(worst <= 1, "AttackDirector: mai due nemici in attacco attivo insieme", str(worst))
	check(min_gap >= AttackDirector.GLOBAL_GAP, "AttackDirector: almeno 0,35 s fra due attacchi nemici", str(min_gap))
	check(same_ok, "AttackDirector: almeno 1,2 s fra due attacchi dello stesso nemico")
	AttackDirector.keep_log = false
	Harness.free_level(lvl)


func _test_ko_freeze() -> void:
	# L'ultimo KO di un'ondata congela tutto per 26 tick, poi 0,4 s al 35%.
	var d := _duel({}, 30.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	lvl.active_wave = {"id": "prova"}
	punk.wave_id = "prova"
	punk.hp = 4
	var g := lvl.player
	var atk: AttackData = g.attacks[&"gig_jab1"]
	lvl.combat.apply_hit(g, punk, atk, Vector2(punk.px, punk.py - 60), 1)
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
	var d := _duel({}, 30.0)
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
	lvl.combat.apply_hit(g, punk, g.attacks[&"gig_jab1"], Vector2(punk.px, punk.py - 60), 1)
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
	var d := _duel({2: InputFrame.JUMP}, 200.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	var jab := load("res://data/attacks/thug_punk_jab.tres") as AttackData
	var hit := false
	var seen_down := false
	for i in 220:
		lvl.step()
		if not hit and g.ph > 18.0:
			punk.px = g.px + 30.0
			lvl.combat.apply_hit(punk, g, jab, Vector2(g.px, g.py - g.ph - 60), 0)
			hit = true
		seen_down = seen_down or g.state == Fighter.State.KNOCK_DOWN
	check(hit and seen_down, "Jab su GIG in salto: GIG viene atterrato", "stato %d" % g.state)
	check(g.ph == 0.0 and g.state != Fighter.State.KNOCK_AIR, "Jab su GIG in salto: GIG torna a terra", "ph %.1f" % g.ph)
	Harness.free_level(lvl)


## GIG perde l'ultima vita quasi insieme al KO dell'ultimo nemico: niente CONTINUA? sopra
## ZONA LIBERATA e il livello finisce lo stesso (prima restava bloccato dopo il continue).
func _test_clear_and_last_life() -> void:
	for gap in [0, 8]:
		var d := _duel({}, 30.0)
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
		lvl.combat.apply_hit(punk, g, hay, Vector2(g.px, g.py - 60), -1)
		for i in gap:
			lvl.step()
		lvl.combat.apply_hit(g, punk, g.attacks[&"gig_jab1"], Vector2(punk.px, punk.py - 60), 1)
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
	var d := _duel(held, 30.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	lvl.camera.min_x = lvl.camera.x
	lvl.camera.max_x = lvl.camera.x
	var wall := lvl.view_right() - Level.WALL_MARGIN
	punk.px = wall
	g.px = wall - 40.0
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
	var d := _duel(held, 30.0)
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
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 300.0, 180.0)
	var g := lvl.player
	var b := lvl.spawn_thug(&"thug_bruiser", 1, 180.0, "")
	b.ai_enabled = false
	b.px = g.px + 40.0
	b.py = g.py
	b.facing = -1
	b.set_state(Fighter.State.IDLE)
	check(lvl.director.request(b, lvl.tick), "Armatura: il bruto ottiene il turno")
	lvl.director.on_attack_start(b, lvl.tick)
	b.start_attack(load("res://data/attacks/thug_bruiser_punch.tres") as AttackData, lvl.next_attack_serial())
	for i in 4:
		lvl.step()
	lvl.combat.apply_hit(g, b, g.attacks[&"gig_jab1"], Vector2(b.px, b.py - 60), 1)
	check(b.state == Fighter.State.ATTACK and lvl.director.is_holder(b), "Armatura: dopo il jab il bruto tiene il turno finché il pugno non finisce")
	Harness.free_level(lvl)


## Un nemico che entra da fuori schermo non si può colpire finché non supera il muro.
func _test_enter_not_hittable() -> void:
	var lvl := Harness.make_level(root, PlayerInput.from_provider(func(_t: int) -> int: return 0), 300.0, 180.0)
	var t := lvl.spawn_thug(&"thug_punk", 1, 180.0, "")
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
	var d := _duel(_taps(2, 4, 3), 30.0)
	var lvl: Level = d["level"]
	var punk: Thug = d["punk"]
	var g := lvl.player
	for i in 24:
		lvl.step()
	var step_before := g.combo_step
	var jab := load("res://data/attacks/thug_punk_jab.tres") as AttackData
	lvl.combat.apply_hit(punk, g, jab, Vector2(g.px, g.py - 60), -1)
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
		for t in expected:
			music_ok = music_ok and texts.has(t)
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
	check(lv is Dictionary and int(lv.get("width", 0)) == 1920 and (lv["waves"] as Array).size() == 2, "Dati del livello leggibili")
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
		check(res["cam_locked_at"] == 576, "Replay combo: la telecamera si blocca sull'ondata 1", str(res["cam_locked_at"]))
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
		check(st.get(&"cable_zaps_gig", 0) == 0 and lvl.player.hp == 120 and lvl.player.px > 1270.0, "Replay cavo saltato: nessun danno, GIG oltre il cavo", "x %.0f, vita %d" % [lvl.player.px, lvl.player.hp])
		Harness.free_level(lvl)
	res = _play("arena.json")
	if not res.is_empty():
		var lvl: Level = res["level"]
		var st: Dictionary = res["stats"]
		check(res["cam_locked_at"] == 1536, "Replay arena: la telecamera si blocca sull'arena", str(res["cam_locked_at"]))
		check(st.get(&"ko_thug_punk", 0) >= 1 and st.get(&"ko_thug_bruiser", 0) == 1, "Replay arena: KO del punk e del bruto")
		check(lvl.zone_cleared and lvl.active_wave.is_empty(), "Replay arena: dopo i KO la zona è liberata")
		var cams: Array[int] = res["cam_after_clear"]
		check(not cams.is_empty() and cams.all(func(x: int) -> bool: return x == 1536), "Replay arena: dopo ZONA LIBERATA la telecamera resta sull'arena", str(cams.slice(0, 3)))
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
