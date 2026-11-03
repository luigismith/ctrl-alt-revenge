extends Node
## Crea le azioni di input da codice (più affidabile che scriverle a mano in project.godot).
## Nessuna azione usa Shift: in Godot 4.7.2 può restare "premuto" (bug #122554).

const KEYS := {
	"move_left": [KEY_LEFT, KEY_A],
	"move_right": [KEY_RIGHT, KEY_D],
	"move_up": [KEY_UP, KEY_W],
	"move_down": [KEY_DOWN, KEY_S],
	"attack": [KEY_J, KEY_Z],
	"jump": [KEY_K, KEY_X],
	"pause": [KEY_ESCAPE, KEY_ENTER],
}

const PAD_BUTTONS := {
	"move_left": [JOY_BUTTON_DPAD_LEFT],
	"move_right": [JOY_BUTTON_DPAD_RIGHT],
	"move_up": [JOY_BUTTON_DPAD_UP],
	"move_down": [JOY_BUTTON_DPAD_DOWN],
	"attack": [JOY_BUTTON_X, JOY_BUTTON_Y],
	"jump": [JOY_BUTTON_A, JOY_BUTTON_B],
	"pause": [JOY_BUTTON_START],
}

const PAD_AXES := {
	"move_left": [JOY_AXIS_LEFT_X, -1.0],
	"move_right": [JOY_AXIS_LEFT_X, 1.0],
	"move_up": [JOY_AXIS_LEFT_Y, -1.0],
	"move_down": [JOY_AXIS_LEFT_Y, 1.0],
}


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
