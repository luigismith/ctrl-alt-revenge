extends Node
## Crea le azioni di input da codice (più affidabile che scriverle a mano in project.godot)
## e campiona gli ingressi di gioco in un InputFrame una volta per tick.
## Nessuna azione usa Shift: in Godot 4.7.2 può restare "premuto" (bug #122554).

const KEYS := {
	"move_left": [KEY_LEFT, KEY_A],
	"move_right": [KEY_RIGHT, KEY_D],
	"move_up": [KEY_UP, KEY_W],
	"move_down": [KEY_DOWN, KEY_S],
	"attack": [KEY_J, KEY_Z],
	"jump": [KEY_K, KEY_X],
	"pause": [KEY_ESCAPE, KEY_ENTER],
	"menu_confirm": [KEY_ENTER, KEY_SPACE, KEY_J, KEY_Z],
	"menu_back": [KEY_ESCAPE, KEY_BACKSPACE],
	"debug_boxes": [KEY_F1],
	"debug_slow": [KEY_F2],
	"debug_freeze": [KEY_F3],
	"debug_step": [KEY_F4],
}

const PAD_BUTTONS := {
	"move_left": [JOY_BUTTON_DPAD_LEFT],
	"move_right": [JOY_BUTTON_DPAD_RIGHT],
	"move_up": [JOY_BUTTON_DPAD_UP],
	"move_down": [JOY_BUTTON_DPAD_DOWN],
	"attack": [JOY_BUTTON_X, JOY_BUTTON_Y],
	"jump": [JOY_BUTTON_A, JOY_BUTTON_B],
	"pause": [JOY_BUTTON_START],
	"menu_confirm": [JOY_BUTTON_A, JOY_BUTTON_START],
	"menu_back": [JOY_BUTTON_B],
}

const PAD_AXES := {
	"move_left": [JOY_AXIS_LEFT_X, -1.0],
	"move_right": [JOY_AXIS_LEFT_X, 1.0],
	"move_up": [JOY_AXIS_LEFT_Y, -1.0],
	"move_down": [JOY_AXIS_LEFT_Y, 1.0],
}

## Azioni di gioco nello stesso ordine dei bit di InputFrame.
const GAME_ACTIONS: Array[StringName] = [&"move_left", &"move_right", &"move_up", &"move_down", &"attack", &"jump"]


func _ready() -> void:
	# Gli input arrivano una volta per tick di fisica, senza accumulo: serve ai replay deterministici.
	Input.use_accumulated_input = false
	for action: String in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.35)
		for key: int in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
		for button: int in PAD_BUTTONS.get(action, []):
			var jb := InputEventJoypadButton.new()
			jb.button_index = button
			InputMap.action_add_event(action, jb)
		if PAD_AXES.has(action):
			var jm := InputEventJoypadMotion.new()
			jm.axis = PAD_AXES[action][0]
			jm.axis_value = PAD_AXES[action][1]
			InputMap.action_add_event(action, jm)


## Tasti di gioco tenuti adesso, come bit di InputFrame. Un tocco più breve di un tick conta come tenuto.
func sample_held() -> int:
	var bits := 0
	for i in GAME_ACTIONS.size():
		if Input.is_action_pressed(GAME_ACTIONS[i]) or Input.is_action_just_pressed(GAME_ACTIONS[i]):
			bits |= 1 << i
	return bits


## Tasti di gioco premuti in questo tick di fisica.
func sample_just_pressed() -> int:
	var bits := 0
	for i in GAME_ACTIONS.size():
		if Input.is_action_just_pressed(GAME_ACTIONS[i]):
			bits |= 1 << i
	return bits
