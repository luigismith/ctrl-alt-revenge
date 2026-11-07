class_name ArmMark
extends RefCounted
## Il segno del laser del messo (decisione 63): un puntino rosso che pulsa sul braccio sinistro di
## GIG, quello di MANODOPERA. Lo disegnano allo stesso modo la comparsa delle scene e GIG nell'arena,
## così nel passaggio dalla scena al gioco il puntino non salta.

const C_MARK := Color8(255, 52, 64)
const C_CORE := Color8(255, 214, 214)
## Il nucleo del laser, bianco caldo, e il colore del suo alone.
const C_HOT := Color8(255, 242, 218)
const C_HOT_GLOW := Color8(255, 168, 120)
## Ogni quanti tick l'impulso corre dalla penna al bersaglio.
const PULSE := 22


## Dove sta il segno rispetto ai piedi, nel fotogramma `f`: un terzo della strada dalla spalla
## sinistra (sotto la testa) al pugno sinistro.
static func offset(f: AnimFrame, facing: int) -> Vector2:
	var head := Vector2(f.points["head"]) if f.points.has("head") else Vector2(4, -95)
	var fist := Vector2(f.points["fist_l"]) if f.points.has("fist_l") else Vector2(17, -51)
	var p := (head + Vector2(4, 22)).lerp(fist, 0.35)
	return Vector2(roundf(p.x) * facing, roundf(p.y))


## Il puntino in `at`, con un alone che pulsa (`t`: tick per la pulsazione, solo disegno).
static func draw(ci: CanvasItem, at: Vector2, t: int, glow: Glow = null) -> void:
	var pulse := 0.5 + 0.5 * sin(t * 0.22)
	ci.draw_rect(Rect2(at - Vector2(2, 2), Vector2(5, 5)), Color(C_MARK, 0.16 + 0.22 * pulse))
	ci.draw_rect(Rect2(at - Vector2(1, 1), Vector2(3, 3)), Color(C_MARK, 0.6 + 0.35 * pulse))
	ci.draw_rect(Rect2(at, Vector2(1, 1)), C_CORE)
	if glow != null:
		glow.halo(at, 4, Color(C_MARK, 0.25 + 0.3 * pulse))


## La linea del laser da `a` a `b` mentre mira (`k` da 0 a 1): il nucleo bianco caldo con i bordi rossi
## che sfarfallano, un impulso che corre dalla penna al bersaglio e l'impatto sul bersaglio, che si
## stringe. Con `glow`, gli aloni additivi. Solo disegno.
static func draw_beam(ci: CanvasItem, a: Vector2, b: Vector2, t: int, k: float, glow: Glow = null) -> void:
	var flick := 0.8 + 0.2 * float(((t * 7) % 5) != 0)
	var pa := a.round()
	var pb := b.round()
	ci.draw_line(pa, pb, Color(C_MARK, 0.42 * flick), 3.0)
	ci.draw_line(pa, pb, Color(C_HOT, 0.95 * flick), 1.0)
	var dir := (pb - pa).normalized()
	var p := (pa.lerp(pb, float(t % PULSE) / PULSE)).round()
	ci.draw_line(p - dir * 4.0, p + dir * 4.0, Color(C_MARK, 0.85), 3.0)
	ci.draw_line(p - dir * 3.0, p + dir * 3.0, Color.WHITE, 1.0)
	_impact(ci, pb, t, k, flick)
	if glow != null:
		glow.band(pa, pb, 3, Color(C_MARK, 0.32 * flick))
		glow.halo(p, 5, Color(C_HOT_GLOW, 0.55))
		glow.halo(pa, 3, Color(C_MARK, 0.6))
		glow.halo(pb, 6 + (t * 5) % 2, Color(C_MARK, 0.6 * flick))


## Il colpo partito (dopo la mira): la linea piena che sbiadisce (`k` da 1 a 0).
static func draw_shot(ci: CanvasItem, a: Vector2, b: Vector2, k: float, glow: Glow = null) -> void:
	var pa := a.round()
	var pb := b.round()
	ci.draw_line(pa, pb, Color(C_MARK, 0.6 * k), 3.0)
	ci.draw_line(pa, pb, Color(C_HOT, k), 1.0)
	if glow != null:
		glow.band(pa, pb, 4, Color(C_MARK, 0.5 * k))
		glow.halo(pa, 4, Color(C_HOT_GLOW, 0.6 * k))


## L'impatto sul bersaglio: il quadrato della mira che si stringe e una stella di quattro raggi che
## cambiano lunghezza a ogni tick.
static func _impact(ci: CanvasItem, at: Vector2, t: int, k: float, flick: float) -> void:
	var r := roundf(lerpf(5.0, 2.0, clampf(k, 0.0, 1.0)))
	ci.draw_rect(Rect2(at - Vector2(r, r), Vector2(2 * r + 1, 2 * r + 1)), Color(C_MARK, 0.18 * flick))
	var ray := float(2 + (t * 5) % 3)
	var c := Color(C_MARK, 0.75 * flick)
	ci.draw_rect(Rect2(at.x - 1 - ray, at.y, ray, 1), c)
	ci.draw_rect(Rect2(at.x + 2, at.y, ray, 1), c)
	ci.draw_rect(Rect2(at.x, at.y - 1 - ray, 1, ray), c)
	ci.draw_rect(Rect2(at.x, at.y + 2, 1, ray), c)
	ci.draw_rect(Rect2(at - Vector2(1, 1), Vector2(3, 3)), Color(C_MARK, 0.9))
	ci.draw_rect(Rect2(at, Vector2(1, 1)), C_HOT)


## Il lampo del segno appena dato: un quadrato che si allarga e sbiadisce (`left`: tick che restano, da 10).
static func draw_flash(ci: CanvasItem, at: Vector2, left: int, glow: Glow = null) -> void:
	var u := 1.0 - float(left) / 10.0
	var r := roundf(2.0 + 9.0 * u)
	var c := Color(C_CORE.lerp(C_MARK, u), 1.0 - u)
	var p := at.round()
	ci.draw_rect(Rect2(p.x - r, p.y, 2 * r + 1, 1), c)
	ci.draw_rect(Rect2(p.x, p.y - r, 1, 2 * r + 1), c)
	ci.draw_rect(Rect2(p - Vector2(2, 2), Vector2(5, 5)), Color(C_MARK, 0.5 * (1.0 - u)))
	if glow != null:
		glow.halo(p, roundi(4.0 + 8.0 * u), Color(C_HOT_GLOW.lerp(C_MARK, u), 0.8 * (1.0 - u)))
