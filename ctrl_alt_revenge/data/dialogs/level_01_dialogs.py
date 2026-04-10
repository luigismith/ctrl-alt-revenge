# data/dialogs/level_01_dialogs.py — Dialoghi del livello 1

DIALOG_INTRO = [
    {
        "id": "start",
        "speaker": "SISTEMA",
        "text": "Connessione neurale ristabilita. Benvenuto, GIG. O quello che ne resta.",
        "next": "intro2"
    },
    {
        "id": "intro2",
        "speaker": "GIG",
        "text": "Dove diavolo sono? L'ultimo ricordo e' un taser e una risata.",
        "next": "intro3"
    },
    {
        "id": "intro3",
        "speaker": "SISTEMA",
        "text": "Sei sotto la Linea. Zona C-7. I tuoi innesti sono ancora funzionanti... piu' o meno.",
        "choices": [
            {"text": "Analizza innesti", "next": "implants_info", "flag": "checked_implants"},
            {"text": "Non me ne frega. Muoviamoci.", "next": "move_on"}
        ]
    },
    {
        "id": "implants_info",
        "speaker": "SISTEMA",
        "text": "Braccio cyber sinistro: operativo. Visione termica: online. EMP: ricarica in corso. Il doppio salto e' calibrato. Sei un museo ambulante di ferraglia.",
        "next": "move_on"
    },
    {
        "id": "move_on",
        "speaker": "SISTEMA",
        "text": "Procedi. Il terminale davanti a te controlla il cancello. Hackalo con E. Cerca di non fare troppo rumore.",
        "next": None
    }
]

DIALOG_BOSS_INTRO = [
    {
        "id": "start",
        "speaker": "WARDEN",
        "text": "Protocollo di contenimento attivato. Soggetto GIG identificato.",
        "next": "boss2"
    },
    {
        "id": "boss2",
        "speaker": "GIG",
        "text": "Ah, un Warden. Pensavo li avessero dismessi dopo il bug del 2024.",
        "next": "boss3"
    },
    {
        "id": "boss3",
        "speaker": "WARDEN",
        "text": "Versione 2.0. Aggiornato. Letale. La tua fuga termina qui.",
        "choices": [
            {"text": "Vediamo se reggi un EMP.", "next": "fight", "flag": "taunted_boss"},
            {"text": "Possiamo parlarne?", "next": "no_talk"}
        ]
    },
    {
        "id": "no_talk",
        "speaker": "WARDEN",
        "text": "Negativo. Inizia lo smantellamento.",
        "next": None
    },
    {
        "id": "fight",
        "speaker": "GIG",
        "text": "Non era una domanda.",
        "next": None
    }
]
