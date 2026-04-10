# data/dialogs/level_03_dialogs.py — Dialoghi del livello 3: "Il Tetto del Mondo"

DIALOG_INTRO = [
    {
        "id": "start",
        "speaker": "SISTEMA",
        "text": "Superficie raggiunta. Altitudine: 340 metri. Vento: 80 km/h. La vista e' quasi bella, se ignori i cecchini.",
        "next": "intro2"
    },
    {
        "id": "intro2",
        "speaker": "GIG",
        "text": "Non guardare giu'. Non guardare giu'. Ho guardato giu'.",
        "next": "intro3"
    },
    {
        "id": "intro3",
        "speaker": "SISTEMA",
        "text": "Il segnale che cerchi viene trasmesso dall'eliporto tre edifici piu' avanti. Dovrai saltare. Spesso.",
        "choices": [
            {"text": "I miei innesti reggono il vento?", "next": "wind_info", "flag": "asked_wind"},
            {"text": "Saltare tra grattacieli. Normale giovedi' sera.", "next": "move_on"}
        ]
    },
    {
        "id": "wind_info",
        "speaker": "SISTEMA",
        "text": "Il giroscopio interno compensa. Ma se cadi, nessun innesto ti salva da 340 metri. La gravita' non si hackera.",
        "next": "move_on"
    },
    {
        "id": "move_on",
        "speaker": "SISTEMA",
        "text": "Droni di sorveglianza ovunque. Un terminale sul terzo edificio puo' disabilitare i riflettori. In bocca al lupo.",
        "next": None
    }
]

DIALOG_BOSS_INTRO = [
    {
        "id": "start",
        "speaker": "SISTEMA",
        "text": "Warden v3.0 in posizione sull'eliporto. Questa versione ha ali. Perche' no.",
        "next": "boss2"
    },
    {
        "id": "boss2",
        "speaker": "GIG",
        "text": "Ali. Ovviamente. E noi siamo su una piattaforma larga tre metri sopra il vuoto.",
        "next": "boss3"
    },
    {
        "id": "boss3",
        "speaker": "WARDEN",
        "text": "Spazio di combattimento ottimale. Per me. Per te e' una bara con vista panoramica.",
        "choices": [
            {"text": "Almeno moriro' con una bella vista.", "next": "dark_humor", "flag": "gallows_humor"},
            {"text": "Le ali si possono strappare.", "next": "threat"}
        ]
    },
    {
        "id": "dark_humor",
        "speaker": "SISTEMA",
        "text": "Spirito ammirevole. Inadeguato, ma ammirevole. Combatti.",
        "next": None
    },
    {
        "id": "threat",
        "speaker": "WARDEN",
        "text": "Prova. Attivazione protocollo di volo.",
        "next": None
    }
]
