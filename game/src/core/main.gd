extends Node
## Scena principale. Per ora mostra solo un segnaposto: il flusso vero
## (titolo → livello → fine demo) arriva con lo slice verticale.


func _ready() -> void:
	var label := Label.new()
	label.text = "CTRL+ALT REVENGE\nscheletro del progetto"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.size = Vector2(384, 216)
	add_child(label)
