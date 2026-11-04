class_name PropBin
extends Prop
## Bidone dell'immondizia: si rompe con i colpi di GIG e lascia cadere una mela (+30 di vita).

const HITS_TO_BREAK := 3
const HIT_SHOW_TICKS := 8

var hits: int = 0
var broken: bool = false
var _hit_timer: int = 0
var _anim_intact: StringName
var _anim_hit: StringName
var _anim_broken: StringName


func setup_bin(lvl: Level, id: int, x: float, y: float) -> void:
	setup_prop(&"bin", lvl, id)
	team = Team.NEUTRAL
	px = x
	py = y
	shadow_w = 26
	_anim_intact = pick_anim([&"intact", &"intero", &"idle"])
	_anim_hit = pick_anim([&"hit", &"colpito", &"intact"])
	_anim_broken = pick_anim([&"break", &"broken", &"rotto", &"intact"])
	anim.play(_anim_intact)
	anim.take_events()


## Il bidone si colpisce anche con i pugni: la sua hurtbox di gioco va dal suolo a 80 px,
## qualunque sia l'altezza del disegno.
func world_hurtboxes() -> Array[Rect2]:
	var f := anim.frame()
	var w := float(f.rect.size.x - 6)
	return [Rect2(px - w / 2.0, py - 80.0, w, 82.0)]


func sim_tick() -> void:
	advance_anim()
	if _hit_timer > 0:
		_hit_timer -= 1
		if _hit_timer == 0 and not broken:
			anim.play(_anim_intact)


func can_be_hit_by(attacker: Entity, _atk: AttackData) -> bool:
	return not broken and attacker.team == Team.PLAYER


func receive_hit(_attacker: Entity, atk: AttackData, info: HitInfo) -> void:
	hits += 1
	if hits >= HITS_TO_BREAK or atk.knockdown:
		broken = true
		anim.play(_anim_broken)
		if not clip_has_sfx(anim.clip) and level.sound_enabled:
			Sfx.play_at(&"bin_break", px)
		play_events()
		level.fx.spawn(&"dust_land", px, py, 1, depth_z(1))
		level.spawn_pickup(px + info.dir * 10.0, py + 2.0, 22.0)
		Game.count(&"bins_broken")
	else:
		anim.play(_anim_hit)
		_hit_timer = maxi(HIT_SHOW_TICKS, anim.clip.total_ticks())
		if not clip_has_sfx(anim.clip) and level.sound_enabled:
			Sfx.play_at(&"bin_hit", px)
		play_events()
