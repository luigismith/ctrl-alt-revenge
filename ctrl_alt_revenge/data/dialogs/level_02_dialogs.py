# data/dialogs/level_02_dialogs.py — Dialoghi del livello 2: "La Rete"

DIALOG_INTRO = [
    {
        "id": "start",
        "speaker": "SISTEMA",
        "text": "Sei entrato nella server farm della MegaCorpo. Temperatura interna: 8 gradi. Umidita': 12%. Posto accogliente.",
        "next": "intro2"
    },
    {
        "id": "intro2",
        "speaker": "GIG",
        "text": "Quanti dati passano da qui?",
        "next": "intro3"
    },
    {
        "id": "intro3",
        "speaker": "SISTEMA",
        "text": "Abbastanza per controllare mezza citta'. Telecamere, droni, semafori, contratti... tutto passa da questi rack.",
        "choices": [
            {"text": "Allora facciamo casino.", "next": "chaos", "flag": "chose_chaos"},
            {"text": "Procediamo in silenzio.", "next": "stealth"}
        ]
    },
    {
        "id": "chaos",
        "speaker": "SISTEMA",
        "text": "Approccio diretto. Come sempre. I terminali in fondo possono disabilitare i droni di pattuglia. Se riesci ad arrivarci.",
        "next": None
    },
    {
        "id": "stealth",
        "speaker": "SISTEMA",
        "text": "Saggio. Ci sono condotti verticali piu' avanti. Sali in alto e usa i terminali per aprirti la strada. Cerca di non toccare niente di costoso.",
        "next": None
    }
]

DIALOG_BOSS_INTRO = [
    {
        "id": "start",
        "speaker": "SISTEMA",
        "text": "Attenzione: Warden v2.1 rilevato. Variante potenziata. Tempo di reazione migliorato del 40%.",
        "next": "boss2"
    },
    {
        "id": "boss2",
        "speaker": "GIG",
        "text": "2.1? Non avevano detto che la 2.0 era l'ultima versione?",
        "next": "boss3"
    },
    {
        "id": "boss3",
        "speaker": "WARDEN",
        "text": "Hotfix di emergenza. Rilasciato dopo che hai smontato il mio predecessore. Stavolta niente bug.",
        "choices": [
            {"text": "Ogni software ha bug.", "next": "taunt", "flag": "taunted_warden"},
            {"text": "Vediamo il changelog.", "next": "fight"}
        ]
    },
    {
        "id": "taunt",
        "speaker": "GIG",
        "text": "E io sono molto bravo a trovare exploit.",
        "next": None
    },
    {
        "id": "fight",
        "speaker": "WARDEN",
        "text": "Changelog: correzione critica — eliminazione soggetto GIG. Inizio deploy.",
        "next": None
    }
]
