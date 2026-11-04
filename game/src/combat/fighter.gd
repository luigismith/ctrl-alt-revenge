class_name Fighter
extends Entity

## Maschera delle luci dinamiche: la ricevono solo gli sprite con la normal map (§4 normal_image).
const LIGHT_MASK_ACTORS := 2
## Base dei combattenti (GIG e i Thug): stato in pseudo-profondità, macchina a stati,
## hitstop per attore, lampo bianco, tremolio dello sprite, invulnerabilità, ordinamento per y.
##
## Ogni tick (Level.step → sim_tick):
##   1. hitstop: se attivo, l'attore resta fermo (anche l'animazione);
##   2. l'animazione avanza di un tick: un'animazione avviata nei passi 3-5 parte dal suo
##      fotogramma 0 e avanza solo dal tick seguente, quindi i tempi restano esatti;
##   3. transizioni automatiche (fine attacco, fine stordimento...);
##   4. _think(): ingressi del giocatore o intelligenza dei nemici;
##   5. fisica dello stato (camminata, salto, volo dopo un colpo, atterraggio);
##   6. eventi dei fotogrammi (suoni, effetti, passi) e root motion (dx);
##   7. limiti della fascia calpestabile e dei muri.

enum State { IDLE, WALK, RUN, JUMP, LAND, ATTACK, GRAB, GRABBED, HURT, KNOCK_AIR, KNOCK_DOWN, GETUP, THROWN, ENTER, DEAD }

const FLASH_TICKS := 2
const JUGGLE_POINTS := 3
## Lancio di base (px/s) per gli atterramenti senza lancio proprio e per i KO.
const DEFAULT_LAUNCH := Vector2(90.0, 170.0)
const KO_LAUNCH := Vector2(120.0, 210.0)
## Rimbalzo dopo il primo impatto con il suolo, in px/tick.
const BOUNCE_VH := 1.7
const BLINK_PERIOD := 4

static var _flash_shader: Shader

var data: FighterData
var sheet: SpriteSheet
var anim: FrameAnim
## +1 a destra, -1 a sinistra. Lo sprite è disegnato rivolto a destra e si specchia.
var facing: int = 1
var hp: int = 1
var state: State = State.IDLE
var state_ticks: int = 0
## Velocità in px per tick: vx orizzontale, vy profondità, vh altezza (verso l'alto).
var vx: float = 0.0
var vy: float = 0.0
var vh: float = 0.0
## Gravità del volo corrente, px per tick².
var grav: float = 0.26
var hitstop: int = 0
var flash: int = 0
var invuln: int = 0
var blink: bool = false
var juggle: int = JUGGLE_POINTS
var stun: int = 0
var dead: bool = false
var down_timer: int = 0
var vanish_timer: int = 0

var attack: AttackData
var attack_tick: int = 0
var attack_serial: int = 0
## uid delle vittime già colpite da questa istanza d'attacco.
var hit_registry: Dictionary[int, bool] = {}
## L'attacco corrente è andato a segno.
var connected: bool = false

## Presa: il partner (vittima per chi prende, chi prende per la vittima).
var grab_partner: Fighter
var grab_ticks: int = 0
## Scostamento verticale di disegno (vittima di una presa) e disegno dietro al partner.
var draw_dy: int = 0
var draw_bias: int = 0

## Corpo proiettato: colpisce i nemici di chi l'ha lanciato.
var body_attack: AttackData
var body_team: Team = Team.NEUTRAL
var bounced: bool = false

var _step_parity: bool = false
var _push_ticks: int = 0
var _push_v: float = 0.0
var _shake_ticks: int = 0

var body: Sprite2D
var _mat: ShaderMaterial


func setup(fighter_data: FighterData, lvl: Level, id: int, fighter_team: Team) -> void:
	data = fighter_data
	level = lvl
	uid = id
	team = fighter_team
	name = "%s_%d" % [data.id, uid]
	hp = data.max_hp
	grav = data.gravity
	sheet = SpriteSheet.get_sheet(data.sprite_id)
	anim = FrameAnim.new(sheet)
	body = Sprite2D.new()
	body.centered = false
	body.region_enabled = true
	body.texture = sheet.texture
	if sheet.has_normals:
		body.light_mask = LIGHT_MASK_ACTORS
	_mat = ShaderMaterial.new()
	_mat.shader = _get_flash_shader()
	body.material = _mat
	add_child(body)
	play_anim(&"idle")


## Lampo bianco dei colpi e luci dinamiche. La luce è "a gradini" (3 bande di n·L, come le ombre della pixel art);
## sul bordo della sagoma (normali di taglio) arriva il colore della luce, riflesso del neon; dentro schiarisce
## senza cambiare tinta, così l'ocra di GIG non vira verso il colore della luce.
const FLASH_SHADER := """shader_type canvas_item;
uniform float flash = 0.0;
void fragment() {
	COLOR.rgb = mix(COLOR.rgb, vec3(1.0), flash);
}
void light() {
	float d = max(dot(NORMAL, LIGHT_DIRECTION), 0.0);
	d = floor(d * 3.0 + 0.35) / 3.0;
	float rim = clamp((1.0 - NORMAL.z) * 1.6, 0.0, 1.0);
	float lum = dot(LIGHT_COLOR.rgb, vec3(0.299, 0.587, 0.114));
	vec3 inner = COLOR.rgb * lum * 0.45;
	vec3 edge = LIGHT_COLOR.rgb * 0.6;
	LIGHT = vec4(mix(inner, edge, rim) * LIGHT_ENERGY * d, LIGHT_COLOR.a);
}
"""


static func _get_flash_shader() -> Shader:
	if _flash_shader == null:
		_flash_shader = Shader.new()
		_flash_shader.code = FLASH_SHADER
	return _flash_shader


# --- Ciclo del tick -------------------------------------------------------------------------

func sim_tick() -> void:
	if removed:
		return
	if flash > 0:
		flash -= 1
	if hitstop > 0:
		hitstop -= 1
		if _shake_ticks > 0:
			_shake_ticks -= 1
		return
	_shake_ticks = 0
	if invuln > 0:
		invuln -= 1
	state_ticks += 1
	if anim.clip != null:
		anim.advance()
	if state == State.ATTACK:
		attack_tick += 1
	_auto_transitions()
	_think()
	_physics()
	_anim_output()
	_clamp_position()
	blink = _compute_blink()


## Transizioni comuni dovute al tempo o alla fine dell'animazione.
func _auto_transitions() -> void:
	match state:
		State.ATTACK:
			if anim.finished and not is_airborne():
				_end_attack()
		State.LAND:
			if anim.finished or state_ticks >= _land_ticks:
				set_state(State.IDLE)
		State.HURT:
			stun -= 1
			if stun <= 0:
				set_state(State.IDLE)
		State.KNOCK_DOWN:
			down_timer -= 1
			if down_timer <= 0:
				if dead:
					_on_down_while_dead()
				else:
					set_state(State.GETUP)
		State.GETUP:
			if anim.finished:
				invuln = data.getup_invuln
				juggle = JUGGLE_POINTS
				set_state(State.IDLE)
		State.DEAD:
			vanish_timer -= 1
			if vanish_timer <= 0:
				removed = true


## Decisioni: ingressi del giocatore o intelligenza artificiale. Da ridefinire.
func _think() -> void:
	pass


func _physics() -> void:
	match state:
		State.IDLE, State.WALK, State.RUN, State.ENTER:
			px += vx
			py += vy
		State.JUMP:
			_fly(false)
		State.ATTACK:
			if is_airborne() or vh != 0.0:
				_fly(false)
		State.HURT:
			if _push_ticks > 0:
				px += _push_v
				_push_ticks -= 1
		State.KNOCK_AIR, State.THROWN:
			_fly(true)


## Volo balistico; `bounce` = rimbalzo sui muri dell'arena e una volta sul suolo.
func _fly(bounce: bool) -> void:
	px += vx
	py += vy
	vh -= grav
	ph += vh
	if bounce:
		var cx := level.clamp_x(self, px)
		if cx != px:
			px = cx
			vx = -vx * 0.5
	if ph <= 0.0 and vh < 0.0:
		ph = 0.0
		_on_landed()


func _on_landed() -> void:
	match state:
		State.JUMP:
			vx = 0.0
			vy = 0.0
			vh = 0.0
			enter_land(sheet.clip(&"land").total_ticks())
			_sfx_unless_anim(&"land")
			_fx_unless_anim(&"dust_land")
		State.ATTACK:
			# Calcio in salto: recupero all'atterraggio.
			vx = 0.0
			vy = 0.0
			vh = 0.0
			enter_land(attack.recovery if attack != null else 6)
			_sfx_unless_anim(&"land")
			_fx_unless_anim(&"dust_land")
		State.KNOCK_AIR, State.THROWN:
			if not bounced and vh < -1.2:
				bounced = true
				vh = BOUNCE_VH
				vx *= 0.5
				ph = 0.01
				_sfx(&"body_thud")
				_fx(&"dust_land", 0)
				if state == State.THROWN:
					body_attack = null
				level.add_shake(0.12)
			else:
				vx = 0.0
				vh = 0.0
				body_attack = null
				set_state(State.KNOCK_DOWN)
				_sfx_unless_anim(&"body_fall")
				_fx_unless_anim(&"dust_land")


var _land_ticks: int = 4


func enter_land(ticks: int) -> void:
	_land_ticks = maxi(ticks, 1)
	set_state(State.LAND)


func _anim_output() -> void:
	for e in anim.take_events():
		_on_anim_event(e)
	var d := anim.take_dx()
	if d != 0:
		px += d * facing
	if state == State.ATTACK and attack != null and attack.glint_tick >= 0 and attack_tick == attack.glint_tick and not _clip_has_event(anim.clip, "glint"):
		_on_glint()


func _on_anim_event(e: String) -> void:
	if e.begins_with("sfx:"):
		_sfx(StringName(e.substr(4)))
	elif e.begins_with("fx:"):
		_fx_event(StringName(e.substr(3)))
	elif e == "glint":
		_on_glint()
	elif e == "step":
		_step_parity = not _step_parity
		if level != null and level.sound_enabled:
			# I passi dei nemici più bassi di quelli di GIG, per non coprire i colpi.
			Sfx.play_at(&"step_a" if _step_parity else &"step_b", px, 0.05, 0.0 if team == Team.PLAYER else -6.0)


## Effetto chiesto da un fotogramma: polvere ai piedi, il resto sulla hitbox (o all'altezza del petto).
## Con "nome@punto" (§4) l'effetto nasce nel punto del fotogramma (per esempio la scarica al pugno).
func _fx_event(fx_name: StringName) -> void:
	var fs := String(fx_name)
	if fs.contains("@"):
		var point := fs.get_slice("@", 1)
		var base := StringName(fs.get_slice("@", 0))
		var pf := anim.frame()
		if pf.points.has(point):
			var pt: Vector2i = pf.points[point]
			level.fx.spawn(base, px + pt.x * facing, py - ph + pt.y, facing, depth_z(2) + 2)
		else:
			_fx(base, -50)
		return
	if fs.begins_with("dust"):
		_fx(fx_name, 0)
		return
	var f := anim.frame()
	if not f.hit.is_empty():
		var c := to_world(f.hit[0]).get_center()
		level.fx.spawn(fx_name, c.x, c.y, facing, depth_z(2) + 2)
	else:
		_fx(fx_name, -50)


## Lampo che annuncia un attacco caricato: sul davanti in alto della posa di carica,
## dove sta il pugno alzato (il fotogramma di carica non ha una box per il pugno).
func _on_glint() -> void:
	_sfx(&"glint")
	var main := Rect2i(-11, -86, 22, 86)
	for b in anim.frame().hurt:
		if b.get_area() > main.get_area() or main == Rect2i(-11, -86, 22, 86):
			main = b
	var p := Vector2(main.end.x - 2, main.position.y + 4)
	level.fx.spawn(&"glint", px + p.x * facing, py - ph + p.y, facing, depth_z(1) + 4)


func _clamp_position() -> void:
	if state != State.ENTER and state != State.GRABBED:
		px = level.clamp_x(self, px)
	py = clampf(py, level.band_top, level.band_bottom)


func _compute_blink() -> bool:
	if state == State.DEAD:
		return (vanish_timer / BLINK_PERIOD) % 2 == 1
	if invuln > 0 and state != State.KNOCK_DOWN:
		return (invuln / BLINK_PERIOD) % 2 == 1
	return false


# --- Stati e animazioni ---------------------------------------------------------------------

func set_state(s: State, anim_name: StringName = &"") -> void:
	var prev := state
	state = s
	state_ticks = 0
	if s != State.ATTACK:
		attack = null
	match s:
		State.IDLE:
			vx = 0.0
			vy = 0.0
			play_anim(anim_name if anim_name != &"" else &"idle")
		State.WALK:
			play_anim(anim_name if anim_name != &"" else &"walk", true)
		State.RUN:
			play_anim(anim_name if anim_name != &"" else &"run", true)
		State.LAND:
			play_anim(anim_name if anim_name != &"" else &"land")
		State.KNOCK_DOWN:
			ph = 0.0
			down_timer = data.down_ticks if not dead else 30
			juggle = JUGGLE_POINTS
			play_anim(&"knock_down")
		State.GETUP:
			play_anim(&"getup")
		State.DEAD:
			vanish_timer = 48
		_:
			if anim_name != &"":
				play_anim(anim_name)
	_on_state_changed(prev, s)


func _on_state_changed(_prev: State, _next: State) -> void:
	pass


func play_anim(anim_name: StringName, keep_if_same: bool = false) -> void:
	if keep_if_same and anim.name == anim_name and anim.clip != null:
		return
	anim.play(anim_name)


func is_airborne() -> bool:
	return ph > 0.0


func is_down() -> bool:
	return state == State.KNOCK_DOWN or state == State.GETUP or state == State.DEAD


func is_free() -> bool:
	return state == State.IDLE or state == State.WALK or state == State.RUN


func is_attacking() -> bool:
	return state == State.ATTACK


func is_alive() -> bool:
	return not dead and not removed


# --- Attacchi -------------------------------------------------------------------------------

func start_attack(atk: AttackData, serial: int) -> void:
	set_state(State.ATTACK)
	attack = atk
	attack_tick = 0
	attack_serial = serial
	hit_registry.clear()
	connected = false
	var c := sheet.attack_clip(atk.anim, atk)
	anim.play(atk.anim, c)
	if atk.sfx_whoosh != &"" and not _clip_has_sfx(c):
		_sfx(atk.sfx_whoosh)


func _end_attack() -> void:
	set_state(State.IDLE)


static func _clip_has_event(c: AnimClip, ev: String) -> bool:
	for f in c.frames:
		if ev in f.events:
			return true
	return false


static func _clip_has_sfx(c: AnimClip) -> bool:
	for f in c.frames:
		for e in f.events:
			if e.begins_with("sfx:"):
				return true
	return false


## Hitbox attive in questo tick, in coordinate del mondo.
func active_hitboxes() -> Array[Rect2]:
	var out: Array[Rect2] = []
	if hitstop > 0 or removed:
		return out
	if state == State.THROWN and body_attack != null:
		return world_hurtboxes()
	if state != State.ATTACK or attack == null or not anim.has_tag(AnimFrame.TAG_ACTIVE):
		return out
	var f := anim.frame()
	if f.hit.is_empty():
		out.append(to_world(attack.hitbox))
	else:
		for b in f.hit:
			out.append(to_world(b))
	return out


## Attacco con cui questo combattente sta colpendo adesso (attacco o corpo proiettato).
func current_hit_attack() -> AttackData:
	if state == State.THROWN:
		return body_attack
	return attack


func to_world(b: Rect2i) -> Rect2:
	var x := px + (b.position.x if facing > 0 else -(b.position.x + b.size.x))
	return Rect2(x, py - ph + b.position.y + draw_dy, b.size.x, b.size.y)


func world_hurtboxes() -> Array[Rect2]:
	var out: Array[Rect2] = []
	var f := anim.frame()
	if f.hurt.is_empty():
		out.append(to_world(Rect2i(-11, -86, 22, 86)))
	else:
		for b in f.hurt:
			out.append(to_world(b))
		var legs := _legs_box(f.hurt)
		if legs.size.x > 0:
			out.append(to_world(legs))
	# Durante lo stordimento e la presa la hurtbox non segue la posa piegata: resta anche il
	# volume in piedi (il fotogramma 0 di idle), così una combo iniziata non si interrompe.
	if state == State.HURT or state == State.GRABBED:
		for b in _standing_hurt():
			out.append(to_world(b))
	return out


## In piedi si è colpibili fino ai piedi: se le box del fotogramma coprono solo busto e testa,
## si aggiunge sotto il busto un riquadro per le gambe (altrimenti un colpo basso, come
## l'haymaker in affondo del punk, passerebbe sotto la hurtbox).
func _legs_box(boxes: Array[Rect2i]) -> Rect2i:
	match state:
		State.KNOCK_AIR, State.THROWN, State.KNOCK_DOWN, State.GETUP, State.DEAD:
			return Rect2i()
	var lowest := -1000
	var main := Rect2i()
	for b in boxes:
		lowest = maxi(lowest, b.end.y)
		if b.get_area() > main.get_area():
			main = b
	if lowest >= -10 or main.size.x <= 0:
		return Rect2i()
	return Rect2i(main.position.x + 2, lowest, maxi(4, main.size.x - 4), -lowest)


func _standing_hurt() -> Array[Rect2i]:
	var idle := sheet.clip(&"idle")
	if idle.frames.is_empty() or idle.frames[0].hurt.is_empty():
		return [Rect2i(-11, -86, 22, 86)]
	return idle.frames[0].hurt


func can_be_hit_by(attacker: Entity, atk: AttackData) -> bool:
	if removed or invuln > 0 or anim.has_tag(AnimFrame.TAG_INVULN):
		return false
	match state:
		State.KNOCK_DOWN, State.GETUP, State.DEAD:
			return false
		State.GRABBED:
			return attacker == grab_partner
		State.KNOCK_AIR, State.THROWN:
			return juggle >= atk.juggle_cost and not dead
		State.ENTER:
			# Chi entra da fuori schermo diventa colpibile solo dentro i muri invisibili: colpito
			# prima, dopo l'hitstop scatterebbe di colpo fino al muro.
			var inside := px >= level.view_left() + Level.WALL_MARGIN and px <= level.view_right() - Level.WALL_MARGIN
			return not dead and inside
	return not dead


## Armatura attiva: fotogramma "armor" oppure avvio di un attacco con armor.
func has_armor() -> bool:
	if anim.has_tag(AnimFrame.TAG_ARMOR):
		return true
	return state == State.ATTACK and attack != null and attack.armor and attack_tick < attack.startup


func receive_hit(attacker: Entity, atk: AttackData, info: HitInfo) -> void:
	hp = maxi(hp - atk.damage, 0)
	flash = FLASH_TICKS
	hitstop = atk.hitstop_victim
	_shake_ticks = hitstop
	var was_dead := dead
	if hp == 0:
		dead = true
	if state != State.GRABBED and state != State.THROWN:
		facing = -info.dir if info.dir != 0 else facing
	if state == State.KNOCK_AIR or state == State.THROWN:
		# Giocoleria: ogni colpo in aria consuma punti e rilancia un poco.
		juggle -= atk.juggle_cost
		vh = maxf(vh, 2.2)
		vx = info.dir * maxf(absf(vx), 1.3)
		ph = maxf(ph, 1.0)
	elif state == State.GRABBED:
		if dead:
			# Vittima KO in presa: si liberano tutti e due, anche chi la tiene (che altrimenti
			# la rimetterebbe in posa accanto a sé nello stesso tick).
			var holder := grab_partner
			_release_from_grab()
			if holder != null and holder.grab_partner == self:
				holder.grab_partner = null
			launch(KO_LAUNCH, 900.0, info.dir)
	elif dead:
		launch(atk.launch if atk.launch.length() > KO_LAUNCH.length() else KO_LAUNCH, atk.launch_gravity, info.dir)
	elif atk.knockdown or atk.launch != Vector2.ZERO or is_airborne():
		# Un colpo che prende in aria (salto, calcio volante) atterra sempre, come in Streets of
		# Rage: negli stati a terra non c'è gravità e il combattente resterebbe sospeso.
		launch(atk.launch if atk.launch != Vector2.ZERO else DEFAULT_LAUNCH, atk.launch_gravity, info.dir)
	elif has_armor() and atk.is_light():
		pass
	else:
		_enter_hurt(atk, info)
	_on_hit_taken(attacker, atk)
	if dead and not was_dead:
		level.on_fighter_ko(self, attacker)


func _enter_hurt(atk: AttackData, info: HitInfo) -> void:
	if grab_partner != null and state == State.GRAB:
		release_grab(false)
	set_state(State.HURT, &"hurt_high" if info.high else &"hurt_low")
	stun = maxi(atk.stun, 1)
	_push_ticks = 4
	_push_v = info.dir * atk.push / 4.0
	vx = 0.0
	vy = 0.0


## Lancia in aria: `v` in px/s (x in avanti nella direzione `dir`, y in alto), gravità in px/s².
func launch(v: Vector2, gravity_px_s2: float, dir: int) -> void:
	if grab_partner != null:
		if state == State.GRAB:
			release_grab(false)
		elif state == State.GRABBED:
			_release_from_grab()
	draw_dy = 0
	draw_bias = 0
	set_state(State.KNOCK_AIR, &"knock_air")
	vx = dir * v.x / 60.0
	vy = 0.0
	vh = v.y / 60.0
	grav = gravity_px_s2 / 3600.0
	ph = maxf(ph, 0.5)
	bounced = false


## Chiamata dopo ogni colpo subito (i Thug cedono il turno d'attacco).
func _on_hit_taken(_attacker: Entity, _atk: AttackData) -> void:
	pass


## A terra dopo il KO: i nemici lampeggiano e spariscono, GIG perde una vita.
func _on_down_while_dead() -> void:
	set_state(State.DEAD)


## Diventa vittima di una presa: la posizione la decide chi prende.
func become_grabbed(grabber: Fighter) -> void:
	grab_partner = grabber
	set_state(State.GRABBED)
	vx = 0.0
	vy = 0.0
	vh = 0.0
	ph = 0.0
	_on_grabbed()


## Chiamata quando si viene presi (i Thug cedono il turno d'attacco).
func _on_grabbed() -> void:
	pass


## Dopo una proiezione il corpo vola e colpisce i nemici di `thrower_team`.
func become_thrown(body_atk: AttackData, thrower_team: Team, serial: int) -> void:
	if state != State.KNOCK_AIR:
		return
	set_state(State.THROWN, &"thrown")
	body_attack = body_atk
	body_team = thrower_team
	attack_serial = serial
	hit_registry.clear()
	hit_registry[uid] = true
	bounced = false


## Chi prende lascia la vittima (che resta in piedi, leggermente spinta).
func release_grab(push_victim: bool) -> void:
	var v := grab_partner
	grab_partner = null
	if v != null and v.state == State.GRABBED:
		v._release_from_grab()
		if push_victim:
			v._push_ticks = 6
			v._push_v = facing * 2.0
			v.set_state(State.HURT, &"hurt_low")
			v.stun = 10


func _release_from_grab() -> void:
	grab_partner = null
	draw_dy = 0
	draw_bias = 0
	if state == State.GRABBED:
		set_state(State.IDLE)


# --- Aiuti -------------------------------------------------------------------------------------

func _sfx(sfx_name: StringName) -> void:
	if level != null and level.sound_enabled:
		Sfx.play_at(sfx_name, px)


func _fx(fx_name: StringName, dy: int) -> void:
	level.fx.spawn(fx_name, px, py - ph + dy, facing, depth_z(1))


## Suono suonato dal codice solo se l'animazione corrente non lo ha già fra i suoi eventi.
func _sfx_unless_anim(sfx_name: StringName) -> void:
	if not _clip_has_event(anim.clip, "sfx:" + String(sfx_name)):
		_sfx(sfx_name)


func _fx_unless_anim(fx_name: StringName) -> void:
	if not _clip_has_event(anim.clip, "fx:" + String(fx_name)):
		_fx(fx_name, 0)


func shadow_width() -> int:
	return 0 if removed else data.shadow_width


# --- Disegno ---------------------------------------------------------------------------------

func sync_visual() -> void:
	position = Vector2(roundf(px), roundf(py))
	var f := anim.frame()
	if body.texture != sheet.texture:
		body.texture = sheet.texture
	body.region_rect = Rect2(f.rect)
	body.offset = Vector2(-f.anchor)
	var sx := 0
	var sy := 0
	if _shake_ticks > 0:
		var amp := 2 if _shake_ticks > 3 else 1
		var sign_v := 1 if _shake_ticks % 2 == 0 else -1
		if is_airborne():
			sy = amp * sign_v
		else:
			sx = amp * sign_v
	body.position = Vector2(sx, -roundf(ph) + draw_dy + sy)
	body.scale = Vector2(facing, 1)
	z_index = depth_z(draw_bias)
	# Durante la sequenza del KO finale (congelamento e rallentatore) il lampeggio
	# (invulnerabilità, sparizione) resta fermo o rallenta, magari sulla fase invisibile:
	# in quel momento si vedono tutti.
	visible = not removed and not (blink and not level.ko_sequence_active())
	_mat.set_shader_parameter(&"flash", 1.0 if _flash_shown() else 0.0)


## Lampo bianco. Nel congelamento del KO finale gli attori non avanzano e il lampo resterebbe
## acceso per tutti i 26 tick: la vittima è bianca per i primi 4 tick, poi alterna colori
## normali e bianco ogni 4 tick.
func _flash_shown() -> bool:
	if flash <= 0:
		return false
	var k := level.ko_freeze_elapsed()
	return k < 0 or (k / 4) % 2 == 0
