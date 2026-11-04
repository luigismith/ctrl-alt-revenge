class_name StageCamera
extends RefCounted
## Telecamera del livello (§6): segue GIG in orizzontale su posizioni intere, con zona morta
## di ±24 px e al massimo 4 px per tick; l'altezza è fissa. I limiti li calcola il livello
## (non si usano i limiti di Camera2D). Il tremolio segue il modello a trauma: solo traslazione,
## al massimo 5 px, decadimento 1,5 al secondo, con rumore da un generatore con seme.

const VIEW_W := 384
const VIEW_H := 216
const DEADZONE := 24
const MAX_STEP := 4
const SHAKE_MAX := 5.0
const TRAUMA_DECAY := 1.5 / 60.0

## Bordo sinistro della vista nel mondo.
var x: int = 0
var min_x: int = 0
var max_x: int = 1536
var trauma: float = 0.0
var shake: Vector2i = Vector2i.ZERO
var rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(rng_seed: int = 1) -> void:
	rng.seed = rng_seed


## Centra subito la vista su `target_x` (inizio livello, rientro).
func snap_to(target_x: float) -> void:
	x = clampi(roundi(target_x) - VIEW_W / 2, min_x, max_x)


func follow(target_x: float) -> void:
	var center := x + VIEW_W / 2
	var d := roundi(target_x) - center
	var step := 0
	if d > DEADZONE:
		step = d - DEADZONE
	elif d < -DEADZONE:
		step = d + DEADZONE
	step = clampi(step, -MAX_STEP, MAX_STEP)
	x = clampi(x + step, min_x, max_x)


## Fa scorrere la vista verso i limiti nuovi alla velocità massima (dopo un blocco).
func settle() -> void:
	if x < min_x:
		x = mini(x + MAX_STEP, min_x)
	elif x > max_x:
		x = maxi(x - MAX_STEP, max_x)


func add_trauma(t: float) -> void:
	trauma = clampf(trauma + t, 0.0, 1.0)


## Un tick di tremolio (anche durante i congelamenti: è solo visivo).
func tick_shake() -> void:
	if trauma <= 0.0:
		shake = Vector2i.ZERO
		return
	var amp := SHAKE_MAX * trauma * trauma
	shake = Vector2i(roundi(amp * rng.randf_range(-1.0, 1.0)), roundi(amp * rng.randf_range(-1.0, 1.0)))
	trauma = maxf(trauma - TRAUMA_DECAY, 0.0)
