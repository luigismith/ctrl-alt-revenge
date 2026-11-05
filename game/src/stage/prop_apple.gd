class_name PropApple
extends Prop
## Mela: salta fuori dal bidone e ridà 30 di vita a GIG quando ci passa sopra.

const HEAL := 30
const PICK_RANGE := Vector2(17.5, 8.75)

var _vh: float = 0.0
var _vx: float = 0.0


func setup_apple(lvl: Level, id: int, x: float, y: float, pop_height: float) -> void:
	setup_prop(&"apple", lvl, id)
	team = Team.NEUTRAL
	px = x
	py = y
	ph = 1.0
	_vh = sqrt(2.0 * 0.3125 * pop_height)
	_vx = 0.75
	shadow_w = 10
	anim.play(pick_anim([&"idle", &"mela", &"apple"]))


func sim_tick() -> void:
	advance_anim()
	if ph > 0.0 or _vh > 0.0:
		_vh -= 0.3125
		ph += _vh
		px += _vx
		if ph <= 0.0:
			ph = 0.0
			_vh = 0.0
			_vx = 0.0
		return
	var p := level.player
	if p == null or not p.is_alive() or p.is_airborne():
		return
	if absf(p.px - px) <= PICK_RANGE.x and absf(p.py - py) <= PICK_RANGE.y:
		p.hp = mini(p.hp + HEAL, p.data.max_hp)
		removed = true
		if level.sound_enabled:
			Sfx.play(&"pickup")
		Game.count(&"apples")
		level.fx.spawn(&"glint", px, py - 10.0, 1, depth_z(2))
