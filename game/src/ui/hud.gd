class_name Hud
extends Control
## HUD in stile Streets of Rage 2 (§7), con la disposizione di game/assets/ui/ui.json:
## - in alto a sinistra ritratto, nome, barra della vita e vite di GIG;
## - sotto, nome e barra dell'ultimo nemico colpito;
## - in alto a destra il punteggio a 6 cifre.
## Ogni pezzo grafico che manca viene disegnato con rettangoli puliti.

const TARGET_SHOW_TICKS := 180

var level: Level
var _gig_trail: float = 1.0
var _enemy_trail: float = 1.0
var _target: Thug
var _target_ticks: int = 0
var _portrait: Texture2D
var _text := Color8(247, 232, 189)
var _gold := Color8(255, 226, 122)


func _ready() -> void:
	size = View.SIZE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_portrait = UiArt.portrait(&"gig")
	_text = UiArt.color("text", _text)
	_gold = UiArt.color("score", _gold)


func show_target(t: Thug) -> void:
	if t != _target:
		_enemy_trail = float(t.hp) / t.data.max_hp
	_target = t
	_target_ticks = TARGET_SHOW_TICKS


## Un tick di interfaccia: le scie del danno scendono piano verso la vita vera.
func tick() -> void:
	var p := level.player
	if p != null:
		var r := float(p.hp) / p.data.max_hp
		_gig_trail = r if r > _gig_trail else move_toward(_gig_trail, r, 0.012)
	if _target != null and not is_instance_valid(_target):
		_target = null
	if _target != null:
		if _target_ticks > 0:
			_target_ticks -= 1
		var er := float(_target.hp) / _target.data.max_hp
		_enemy_trail = er if er > _enemy_trail else move_toward(_enemy_trail, er, 0.015)
		if _target_ticks == 0 or (_target.removed and _enemy_trail <= er):
			_target = null
	queue_redraw()


func _draw() -> void:
	var p := level.player if level != null else null
	var pf := UiArt.layout("portrait_frame", [6, 4])
	var pp := UiArt.layout("portrait", [7, 5])
	var back := UiArt.texture("portrait_back")
	if back != null:
		draw_texture(back, Vector2(pf[0], pf[1]))
	else:
		draw_rect(Rect2(pf[0], pf[1], 34, 34), Color8(28, 20, 52))
	if _portrait != null:
		draw_texture_rect(_portrait, Rect2(pp[0], pp[1], 32, 32), false)
	var frame := UiArt.texture("portrait_frame")
	if frame != null:
		draw_texture(frame, Vector2(pf[0], pf[1]))
	else:
		UiFont.draw_frame(self, Rect2(pf[0], pf[1], 34, 34), _gold)
	var gn := UiArt.layout("gig_name", [44, 2])
	UiFont.draw_text(self, Vector2(gn[0], gn[1]), "GIG", _text)
	var lv := UiArt.layout("gig_lives_right", [152, 2])
	UiFont.draw_text(self, Vector2(lv[0], lv[1]), "×%d" % maxi(Game.lives, 0), UiArt.color("lives", _gold), 1, 2)
	var gb := UiArt.layout("gig_bar", [46, 15, 104, 6])
	var ratio := float(p.hp) / p.data.max_hp if p != null else 0.0
	_bar(Rect2(gb[0], gb[1], gb[2], gb[3]), ratio, _gig_trail, "", Color8(244, 196, 64))
	if _target != null and is_instance_valid(_target):
		var en := UiArt.layout("enemy_name", [44, 21])
		UiFont.draw_text(self, Vector2(en[0], en[1]), _target.data.display_name, _text)
		var eb := UiArt.layout("enemy_bar", [46, 34, 104, 4])
		_bar(Rect2(eb[0], eb[1], eb[2], eb[3]), float(_target.hp) / _target.data.max_hp, _enemy_trail, "_enemy", Color8(222, 54, 52))
	var sc := UiArt.layout("score_right", [378, 2])
	UiFont.draw_text(self, Vector2(sc[0], sc[1]), "%06d" % Game.score, _gold, 1, 2)
	if p is Gig:
		_draw_pignoramento(p as Gig)


## Il pignoramento del rider: DIVINCOLATI! sopra GIG afferrato, con le tacche delle pressioni,
## e BRACCIO SOSPESO accanto alla barra della vita finché il braccio non torna (lampeggia
## nell'ultimo secondo).
func _draw_pignoramento(g: Gig) -> void:
	var red := UiArt.color("accent_red", Color8(122, 23, 15))
	if g.state == Fighter.State.GRABBED and g.grab_partner is Rider:
		var sx := g.px - level.camera.x
		var sy := g.py - 150.0
		if (level.tick / 8) % 2 == 0:
			UiFont.draw_text(self, Vector2(sx, sy), "DIVINCOLATI!", _gold, 1, 1, red)
		var n := Gig.ESCAPE_PRESSES
		var x0 := sx - n * 3 + 1
		for i in n:
			var on := i < g.escape_presses
			draw_rect(Rect2(x0 + i * 6, sy + 12, 4, 4), _gold if on else Color(0.1, 0.06, 0.15, 0.8))
	if g.arm_off > 0 and (g.arm_off > 60 or (g.arm_off / 6) % 2 == 0):
		var gb := UiArt.layout("gig_bar", [46, 15, 104, 6])
		UiFont.draw_text(self, Vector2(gb[0] + gb[2] + 8, gb[1] - 2), "BRACCIO SOSPESO", Color8(170, 170, 178), 1, 0, red)


## Barra della vita: fondo, scia del danno, vita, cornice (in quest'ordine, come da README).
func _bar(r: Rect2, ratio: float, trail: float, suffix: String, fill: Color) -> void:
	var fw := int(round(r.size.x * clampf(ratio, 0.0, 1.0)))
	var tw := int(round(r.size.x * clampf(trail, 0.0, 1.0)))
	var back := UiArt.texture("bar_back" + suffix)
	var ghost := UiArt.texture("bar_ghost" + suffix)
	var fill_tex := UiArt.texture("bar_fill" + suffix)
	var frame := UiArt.texture("bar_frame" + suffix)
	if back != null:
		draw_texture_rect_region(back, r, Rect2(0, 0, r.size.x, r.size.y))
	else:
		draw_rect(r, Color8(40, 22, 52))
	if tw > fw:
		if ghost != null:
			draw_texture_rect_region(ghost, Rect2(r.position.x, r.position.y, tw, r.size.y), Rect2(0, 0, tw, r.size.y))
		else:
			draw_rect(Rect2(r.position.x + fw, r.position.y, tw - fw, r.size.y), Color8(250, 240, 220))
	if fw > 0:
		if fill_tex != null:
			draw_texture_rect_region(fill_tex, Rect2(r.position.x, r.position.y, fw, r.size.y), Rect2(0, 0, fw, r.size.y))
		else:
			draw_rect(Rect2(r.position.x, r.position.y, fw, r.size.y), fill)
			draw_rect(Rect2(r.position.x, r.position.y, fw, 1), fill.lightened(0.4))
	if frame != null:
		draw_texture(frame, r.position - Vector2(2, 2))
	else:
		UiFont.draw_frame(self, Rect2(r.position - Vector2(2, 2), r.size + Vector2(4, 4)), Color8(20, 12, 30))
		UiFont.draw_frame(self, Rect2(r.position - Vector2(1, 1), r.size + Vector2(2, 2)), Color8(247, 232, 189))
