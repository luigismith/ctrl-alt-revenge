# systems/audio.py — Procedural synthwave audio engine
# Generates all music and SFX at runtime using pure Python (no numpy)
import math
import array
import random

try:
    import pygame
except ImportError:
    pygame = None


SAMPLE_RATE = 22050


def _clamp16(val):
    """Clamp to signed 16-bit range."""
    if val > 32767:
        return 32767
    if val < -32768:
        return -32768
    return int(val)


# ── Waveform generators ──────────────────────────────────────────────

def _sine(freq, duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate a sine wave buffer."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    two_pi_f = 2.0 * math.pi * freq
    amp = volume * 32767
    for i in range(n):
        t = i / sample_rate
        buf.append(_clamp16(amp * math.sin(two_pi_f * t)))
    return buf


def _square(freq, duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate a square wave buffer."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    two_pi_f = 2.0 * math.pi * freq
    amp = volume * 32767
    for i in range(n):
        t = i / sample_rate
        val = amp if math.sin(two_pi_f * t) >= 0 else -amp
        buf.append(_clamp16(val))
    return buf


def _pulse(freq, duration, duty=0.25, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate a pulse wave buffer with variable duty cycle."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    period = sample_rate / freq if freq > 0 else sample_rate
    for i in range(n):
        phase = (i % int(period)) / period
        val = amp if phase < duty else -amp
        buf.append(_clamp16(val))
    return buf


def _sawtooth(freq, duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate a sawtooth wave buffer."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    period = sample_rate / freq if freq > 0 else sample_rate
    for i in range(n):
        phase = (i % int(period)) / period
        val = amp * (2.0 * phase - 1.0)
        buf.append(_clamp16(val))
    return buf


def _chorus_saw(freq, duration, detune=0.005, volume=0.3, sample_rate=SAMPLE_RATE):
    """Sawtooth with detuned copy for chorus effect."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767 * 0.5  # halved since we mix two
    freq2 = freq * (1.0 + detune)
    period1 = sample_rate / freq if freq > 0 else sample_rate
    period2 = sample_rate / freq2 if freq2 > 0 else sample_rate
    for i in range(n):
        phase1 = (i % int(period1)) / period1
        phase2 = (i % int(period2)) / period2
        v1 = 2.0 * phase1 - 1.0
        v2 = 2.0 * phase2 - 1.0
        buf.append(_clamp16(amp * (v1 + v2)))
    return buf


def _noise(duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate white noise buffer."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    rng = random.Random(42)
    for _ in range(n):
        buf.append(_clamp16(amp * (rng.random() * 2.0 - 1.0)))
    return buf


def _kick_drum(duration=0.12, volume=0.4, sample_rate=SAMPLE_RATE):
    """Proper kick: sine sweep 150Hz->40Hz over 80ms + body."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    for i in range(n):
        t = i / sample_rate
        # Pitch sweep: 150->40 Hz exponentially
        freq = 40.0 + 110.0 * math.exp(-t * 30.0)
        # Phase accumulation would be better but this is close enough
        phase = 2.0 * math.pi * freq * t
        env = math.exp(-t * 15.0)
        buf.append(_clamp16(amp * env * math.sin(phase)))
    return buf


def _snare_drum(duration=0.12, volume=0.3, sample_rate=SAMPLE_RATE):
    """Snare: noise burst + pitched body."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    rng = random.Random(77)
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t * 18.0)
        noise_val = rng.random() * 2.0 - 1.0
        body = math.sin(2.0 * math.pi * 180.0 * t)
        buf.append(_clamp16(amp * env * (noise_val * 0.7 + body * 0.3)))
    return buf


def _hihat(duration=0.04, volume=0.15, sample_rate=SAMPLE_RATE):
    """Hi-hat: short noise burst with fast decay."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    rng = random.Random(55)
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t * 60.0)
        buf.append(_clamp16(amp * env * (rng.random() * 2.0 - 1.0)))
    return buf


def _sine_decay(freq, duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Sine wave with exponential amplitude decay (for kick drums)."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    two_pi_f = 2.0 * math.pi * freq
    amp = volume * 32767
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t * 12.0)
        buf.append(_clamp16(amp * env * math.sin(two_pi_f * t)))
    return buf


def _noise_decay(duration, volume=0.3, decay=20.0, sample_rate=SAMPLE_RATE):
    """Noise burst with exponential decay (for snare / hi-hat)."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    rng = random.Random(123)
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t * decay)
        buf.append(_clamp16(amp * env * (rng.random() * 2.0 - 1.0)))
    return buf


def _apply_adsr(buf, attack=0.01, decay=0.05, sustain=0.7, release=0.05,
                sample_rate=SAMPLE_RATE):
    """Apply ADSR envelope to a buffer in-place."""
    n = len(buf)
    a_samples = int(attack * sample_rate)
    d_samples = int(decay * sample_rate)
    r_samples = int(release * sample_rate)
    s_start = a_samples + d_samples
    r_start = max(s_start, n - r_samples)
    for i in range(n):
        if i < a_samples:
            # Attack: ramp up
            env = i / a_samples if a_samples > 0 else 1.0
        elif i < s_start:
            # Decay: ramp down to sustain
            progress = (i - a_samples) / d_samples if d_samples > 0 else 1.0
            env = 1.0 - (1.0 - sustain) * progress
        elif i < r_start:
            # Sustain
            env = sustain
        else:
            # Release: ramp down
            progress = (i - r_start) / r_samples if r_samples > 0 else 1.0
            env = sustain * (1.0 - progress)
        buf[i] = _clamp16(buf[i] * env)
    return buf


def _mix_buffers(*buffers):
    """Mix multiple equal-length buffers by summing and clamping."""
    if not buffers:
        return array.array('h')
    length = max(len(b) for b in buffers)
    result = array.array('h', [0] * length)
    for buf in buffers:
        for i in range(len(buf)):
            result[i] = _clamp16(result[i] + buf[i])
    return result


def _overlay_at(base, overlay, offset):
    """Overlay a buffer onto base at sample offset."""
    for i in range(len(overlay)):
        pos = offset + i
        if pos < len(base):
            base[pos] = _clamp16(base[pos] + overlay[i])


def _make_sound(buf):
    """Convert array buffer to pygame Sound."""
    return pygame.mixer.Sound(buffer=buf)


# ── Note frequencies (A4 = 440 Hz) ───────────────────────────────────

def _note_freq(note, octave):
    """Get frequency for a note name and octave."""
    semitones = {
        'C': -9, 'C#': -8, 'Db': -8,
        'D': -7, 'D#': -6, 'Eb': -6,
        'E': -5,
        'F': -4, 'F#': -3, 'Gb': -3,
        'G': -2, 'G#': -1, 'Ab': -1,
        'A': 0, 'A#': 1, 'Bb': 1,
        'B': 2,
    }
    n = semitones[note] + (octave - 4) * 12
    return 440.0 * (2.0 ** (n / 12.0))


# ── Music track builders ─────────────────────────────────────────────

def _build_menu_music():
    """Dark cinematic synthwave — Cm - Ab - Eb - Bb progression.

    Layered: pulse bass + chorus saw pad + arpeggiated lead.
    ~8s seamless loop at 85 BPM.
    """
    bpm = 85
    beat_dur = 60.0 / bpm
    beats_per_chord = 4
    chord_dur = beat_dur * beats_per_chord
    num_chords = 4
    total_dur = chord_dur * num_chords
    total_samples = int(SAMPLE_RATE * total_dur)

    # Cm - Ab - Eb - Bb (root notes)
    roots = [
        _note_freq('C', 2),   # Cm
        _note_freq('Ab', 1),  # Ab
        _note_freq('Eb', 2),  # Eb
        _note_freq('Bb', 1),  # Bb
    ]
    # Minor chord intervals: root, minor 3rd (6/5), 5th (3/2)
    def minor_chord(root):
        return [root, root * 6.0 / 5.0, root * 3.0 / 2.0]

    # ── Bass: pulse wave (25% duty), whole notes ──
    bass_buf = array.array('h', [0] * total_samples)
    for ci, root in enumerate(roots):
        start_s = int(ci * chord_dur * SAMPLE_RATE)
        note = _pulse(root, chord_dur * 0.95, duty=0.25, volume=0.20)
        _apply_adsr(note, attack=0.02, decay=0.1, sustain=0.6, release=0.15)
        _overlay_at(bass_buf, note, start_s)

    # ── Pad: chorus sawtooth playing chord tones ──
    pad_buf = array.array('h', [0] * total_samples)
    for ci, root in enumerate(roots):
        chord_tones = minor_chord(root * 2)  # one octave up
        start_s = int(ci * chord_dur * SAMPLE_RATE)
        for freq in chord_tones:
            tone = _chorus_saw(freq, chord_dur * 0.92, detune=0.006, volume=0.06)
            _apply_adsr(tone, attack=0.15, decay=0.1, sustain=0.7, release=0.2)
            _overlay_at(pad_buf, tone, start_s)

    # ── Lead: arpeggiated minor chord, 8th notes ──
    lead_buf = array.array('h', [0] * total_samples)
    eighth_dur = beat_dur / 2.0
    for ci, root in enumerate(roots):
        chord_tones = minor_chord(root * 4)  # two octaves up
        arp_pattern = [0, 1, 2, 1, 0, 2, 1, 0]  # arpeggio indices
        for ni, idx in enumerate(arp_pattern):
            freq = chord_tones[idx]
            start_t = ci * chord_dur + ni * eighth_dur
            start_s = int(start_t * SAMPLE_RATE)
            note = _chorus_saw(freq, eighth_dur * 0.7, detune=0.004, volume=0.08)
            _apply_adsr(note, attack=0.008, decay=0.04, sustain=0.5, release=0.04)
            _overlay_at(lead_buf, note, start_s)

    # ── Subtle kick on beats 1 and 3 for pulse ──
    drum_buf = array.array('h', [0] * total_samples)
    kick = _kick_drum(duration=0.10, volume=0.18)
    for ci in range(num_chords):
        for b in [0, 2]:
            pos = int((ci * chord_dur + b * beat_dur) * SAMPLE_RATE)
            _overlay_at(drum_buf, kick, pos)

    result = _mix_buffers(bass_buf, pad_buf, lead_buf, drum_buf)
    return _make_sound(result)


def _build_level_music():
    """Driving synthwave energy — Em - C - G - D progression.

    Layered: 16th-note pulse bass + full drums + chorus saw lead.
    ~7.4s seamless loop at 130 BPM.
    """
    bpm = 130
    beat_dur = 60.0 / bpm
    num_beats = 16  # 4 bars of 4/4
    total_dur = beat_dur * num_beats
    total_samples = int(SAMPLE_RATE * total_dur)
    eighth_dur = beat_dur / 2.0
    sixteenth_dur = beat_dur / 4.0

    # Em - C - G - D (each chord = 1 bar = 4 beats)
    chord_roots = [
        _note_freq('E', 2),
        _note_freq('C', 2),
        _note_freq('G', 2),
        _note_freq('D', 2),
    ]

    # ── Bass: 16th-note pulse wave pattern ──
    bass_buf = array.array('h', [0] * total_samples)
    # Pattern per bar: root in 16ths with rhythmic gaps
    bass_rhythm = [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1]
    for ci, root in enumerate(chord_roots):
        bar_start = ci * 4 * beat_dur
        for si, hit in enumerate(bass_rhythm):
            if not hit:
                continue
            freq = root
            start_s = int((bar_start + si * sixteenth_dur) * SAMPLE_RATE)
            note = _pulse(freq, sixteenth_dur * 0.75, duty=0.25, volume=0.22)
            _apply_adsr(note, attack=0.003, decay=0.02, sustain=0.6, release=0.01)
            _overlay_at(bass_buf, note, start_s)

    # ── Drums: kick, snare, hihat ──
    kick = _kick_drum(duration=0.12, volume=0.38)
    snare = _snare_drum(duration=0.10, volume=0.25)
    hh = _hihat(duration=0.04, volume=0.14)
    hh_open = _hihat(duration=0.08, volume=0.10)

    drum_buf = array.array('h', [0] * total_samples)
    for beat in range(num_beats):
        beat_start = int(beat * beat_dur * SAMPLE_RATE)
        bar_beat = beat % 4
        # Kick on 1 and 3, plus syncopated kick on "and" of 4
        if bar_beat == 0 or bar_beat == 2:
            _overlay_at(drum_buf, kick, beat_start)
        if bar_beat == 3:
            _overlay_at(drum_buf, kick,
                        beat_start + int(eighth_dur * SAMPLE_RATE))
        # Snare on 2 and 4
        if bar_beat == 1 or bar_beat == 3:
            _overlay_at(drum_buf, snare, beat_start)
        # Hi-hat on every 8th, open on "and" of 2
        for sub in range(2):
            hh_start = beat_start + int(sub * eighth_dur * SAMPLE_RATE)
            if bar_beat == 1 and sub == 1:
                _overlay_at(drum_buf, hh_open, hh_start)
            else:
                _overlay_at(drum_buf, hh, hh_start)

    # ── Lead melody: chorus sawtooth riff ──
    lead_pattern = [
        # Bar 1 (Em): driving 8th notes
        ('E', 4, 1), ('G', 4, 1), ('B', 4, 1), ('E', 5, 1),
        ('D', 5, 1), ('B', 4, 1), ('G', 4, 1), ('A', 4, 1),
        # Bar 2 (C): melodic phrase
        ('C', 5, 2), ('E', 5, 1), ('G', 5, 1),
        ('E', 5, 2), ('C', 5, 2),
        # Bar 3 (G): ascending run
        ('G', 4, 1), ('B', 4, 1), ('D', 5, 1), ('G', 5, 1),
        ('rest', 0, 2), ('D', 5, 2),
        # Bar 4 (D): resolving phrase
        ('D', 5, 2), ('F#', 5, 1), ('A', 5, 1),
        ('F#', 5, 1), ('D', 5, 1), ('rest', 0, 2),
    ]
    lead_buf = array.array('h', [0] * total_samples)
    pos = 0
    for note_name, octave, dur_eighths in lead_pattern:
        if note_name == 'rest':
            pos += dur_eighths
            continue
        freq = _note_freq(note_name, octave)
        note_dur_s = dur_eighths * eighth_dur
        start_s = int(pos * eighth_dur * SAMPLE_RATE)
        note = _chorus_saw(freq, note_dur_s * 0.85, detune=0.005, volume=0.10)
        _apply_adsr(note, attack=0.005, decay=0.03, sustain=0.6, release=0.03)
        _overlay_at(lead_buf, note, start_s)
        pos += dur_eighths

    result = _mix_buffers(bass_buf, drum_buf, lead_buf)
    return _make_sound(result)


def _build_boss_music():
    """Intense boss fight — Am - E - Am - F progression.

    Fast arpeggios, aggressive bass, double-time drums.
    ~6.4s seamless loop at 150 BPM.
    """
    bpm = 150
    beat_dur = 60.0 / bpm
    num_beats = 16
    total_dur = beat_dur * num_beats
    total_samples = int(SAMPLE_RATE * total_dur)
    eighth_dur = beat_dur / 2.0
    sixteenth_dur = beat_dur / 4.0

    # Am - E - Am - F (each = 1 bar = 4 beats)
    chord_roots = [
        _note_freq('A', 2),
        _note_freq('E', 2),
        _note_freq('A', 2),
        _note_freq('F', 2),
    ]

    # ── Aggressive bass: 16th note pulse wave ──
    bass_buf = array.array('h', [0] * total_samples)
    # Driving pattern with octave jumps
    bass_rhythm = [1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0]
    for ci, root in enumerate(chord_roots):
        bar_start = ci * 4 * beat_dur
        for si, hit in enumerate(bass_rhythm):
            if not hit:
                continue
            # Alternate between root and octave for punch
            freq = root if si % 3 != 0 else root * 2
            start_s = int((bar_start + si * sixteenth_dur) * SAMPLE_RATE)
            note = _pulse(freq, sixteenth_dur * 0.7, duty=0.25, volume=0.24)
            _apply_adsr(note, attack=0.002, decay=0.01, sustain=0.7, release=0.005)
            _overlay_at(bass_buf, note, start_s)

    # ── Double-time drums ──
    kick = _kick_drum(duration=0.10, volume=0.40)
    snare = _snare_drum(duration=0.08, volume=0.28)
    hh = _hihat(duration=0.03, volume=0.13)

    drum_buf = array.array('h', [0] * total_samples)
    for beat in range(num_beats):
        beat_start = int(beat * beat_dur * SAMPLE_RATE)
        bar_beat = beat % 4
        # Kick on every beat + "and" of 2 and 4
        _overlay_at(drum_buf, kick, beat_start)
        if bar_beat == 1 or bar_beat == 3:
            _overlay_at(drum_buf, kick,
                        beat_start + int(eighth_dur * SAMPLE_RATE))
        # Snare on 2 and 4
        if bar_beat == 1 or bar_beat == 3:
            _overlay_at(drum_buf, snare, beat_start)
        # Hi-hat on every 16th note
        for sub in range(4):
            hh_start = beat_start + int(sub * sixteenth_dur * SAMPLE_RATE)
            _overlay_at(drum_buf, hh, hh_start)

    # ── Fast arpeggiated lead ──
    # Arpeggiate each chord as fast 16th notes
    def minor_chord_freqs(root_freq):
        return [root_freq, root_freq * 6.0 / 5.0, root_freq * 3.0 / 2.0]

    def major_chord_freqs(root_freq):
        return [root_freq, root_freq * 5.0 / 4.0, root_freq * 3.0 / 2.0]

    lead_buf = array.array('h', [0] * total_samples)
    chord_types = [minor_chord_freqs, major_chord_freqs,
                   minor_chord_freqs, major_chord_freqs]
    for ci, (root, chord_fn) in enumerate(zip(chord_roots, chord_types)):
        freqs = chord_fn(root * 4)  # two octaves up for lead
        # Fast arpeggio: cycle through chord tones in 16ths
        arp_seq = [0, 1, 2, 1, 0, 2, 1, 2, 0, 1, 2, 0, 2, 1, 0, 1]
        bar_start = ci * 4 * beat_dur
        for si, idx in enumerate(arp_seq):
            freq = freqs[idx]
            start_s = int((bar_start + si * sixteenth_dur) * SAMPLE_RATE)
            note = _chorus_saw(freq, sixteenth_dur * 0.65, detune=0.007,
                               volume=0.09)
            _apply_adsr(note, attack=0.003, decay=0.015, sustain=0.5,
                        release=0.01)
            _overlay_at(lead_buf, note, start_s)

    result = _mix_buffers(bass_buf, drum_buf, lead_buf)
    return _make_sound(result)


# ── SFX builders ─────────────────────────────────────────────────────

def _build_sfx_punch():
    """Short noise burst + low square blip (~50ms)."""
    noise = _noise_decay(0.05, volume=0.40, decay=40.0)
    blip = _square(80, 0.05, volume=0.25)
    # Decay the blip
    for i in range(len(blip)):
        env = max(0, 1.0 - i / len(blip))
        blip[i] = _clamp16(blip[i] * env)
    return _make_sound(_mix_buffers(noise, blip))


def _build_sfx_jump():
    """Rising pitch sweep (~100ms)."""
    n = int(SAMPLE_RATE * 0.1)
    buf = array.array('h')
    amp = 0.30 * 32767
    for i in range(n):
        t = i / SAMPLE_RATE
        progress = i / n
        freq = 200 + 800 * progress  # sweep 200 -> 1000 Hz
        env = 1.0 - progress * 0.5
        val = amp * env * math.sin(2 * math.pi * freq * t)
        buf.append(_clamp16(val))
    return _make_sound(buf)


def _build_sfx_hurt():
    """Descending noise sweep (~150ms)."""
    n = int(SAMPLE_RATE * 0.15)
    buf = array.array('h')
    amp = 0.35 * 32767
    rng = random.Random(999)
    for i in range(n):
        progress = i / n
        env = 1.0 - progress
        # Mix noise with descending square
        noise_val = rng.random() * 2.0 - 1.0
        freq = 400 - 300 * progress
        t = i / SAMPLE_RATE
        square_val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        val = amp * env * (noise_val * 0.5 + square_val * 0.5)
        buf.append(_clamp16(val))
    return _make_sound(buf)


def _build_sfx_hack_success():
    """Ascending arpeggio — 3 quick notes up (~200ms)."""
    freqs = [
        _note_freq('C', 5),
        _note_freq('E', 5),
        _note_freq('G', 5),
    ]
    note_dur = 0.065
    total = note_dur * 3
    total_samples = int(SAMPLE_RATE * total)
    buf = array.array('h', [0] * total_samples)
    for i, freq in enumerate(freqs):
        start_s = int(i * note_dur * SAMPLE_RATE)
        note = _square(freq, note_dur * 0.9, volume=0.25)
        # Quick fade
        fade = min(int(SAMPLE_RATE * 0.008), len(note) // 3)
        for j in range(fade):
            note[-(j + 1)] = _clamp16(note[-(j + 1)] * (j / fade))
        _overlay_at(buf, note, start_s)
    return _make_sound(buf)


def _build_sfx_hack_fail():
    """Descending buzzer (~200ms)."""
    n = int(SAMPLE_RATE * 0.2)
    buf = array.array('h')
    amp = 0.30 * 32767
    for i in range(n):
        t = i / SAMPLE_RATE
        progress = i / n
        freq = 300 - 200 * progress  # descend 300 -> 100
        env = 1.0 - progress * 0.6
        val = amp * env * (1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0)
        buf.append(_clamp16(val))
    return _make_sound(buf)


def _build_sfx_menu_select():
    """Short blip (~50ms)."""
    note = _square(_note_freq('A', 5), 0.05, volume=0.20)
    fade = min(int(SAMPLE_RATE * 0.01), len(note) // 3)
    for j in range(fade):
        note[-(j + 1)] = _clamp16(note[-(j + 1)] * (j / fade))
    return _make_sound(note)


def _build_sfx_parry():
    """Metallic clash — noise + high square (~80ms)."""
    noise = _noise_decay(0.08, volume=0.30, decay=30.0)
    tone = _square(1200, 0.08, volume=0.20)
    for i in range(len(tone)):
        env = max(0, 1.0 - (i / len(tone)) * 1.5)
        tone[i] = _clamp16(tone[i] * env)
    return _make_sound(_mix_buffers(noise, tone))


# ── AudioManager ─────────────────────────────────────────────────────

class AudioManager:
    """Procedural synthwave audio engine.

    Generates all music and SFX at runtime using pure Python waveform
    synthesis. No external audio files needed.
    """

    def __init__(self):
        self.enabled = False
        self.music_tracks = {}
        self.sfx = {}
        self._current_music = None
        self._current_channel = None
        self._music_volume = 0.3
        self._sfx_volume = 0.5

        try:
            # Build all music tracks
            self.music_tracks = {
                "menu": _build_menu_music(),
                "level": _build_level_music(),
                "boss": _build_boss_music(),
            }

            # Build all SFX
            self.sfx = {
                "punch": _build_sfx_punch(),
                "jump": _build_sfx_jump(),
                "hurt": _build_sfx_hurt(),
                "hack_success": _build_sfx_hack_success(),
                "hack_fail": _build_sfx_hack_fail(),
                "menu_select": _build_sfx_menu_select(),
                "parry": _build_sfx_parry(),
            }

            # Apply default volumes
            for snd in self.music_tracks.values():
                snd.set_volume(self._music_volume)
            for snd in self.sfx.values():
                snd.set_volume(self._sfx_volume)

            # Reserve channel 0 for music
            if pygame.mixer.get_num_channels() < 4:
                pygame.mixer.set_num_channels(8)

            self.enabled = True
        except Exception as e:
            print(f"[AudioManager] Init failed: {e}")
            self.enabled = False

    def play_music(self, track_name):
        """Play a music track on loop. Stops any current music first."""
        if not self.enabled:
            return
        try:
            self.stop_music()
            snd = self.music_tracks.get(track_name)
            if snd:
                self._current_channel = snd.play(loops=-1)
                self._current_music = track_name
        except Exception:
            pass

    def stop_music(self):
        """Fade out current music over 500ms."""
        if not self.enabled:
            return
        try:
            if self._current_music and self._current_music in self.music_tracks:
                self.music_tracks[self._current_music].fadeout(500)
            self._current_music = None
            self._current_channel = None
        except Exception:
            pass

    def play_sfx(self, sfx_name):
        """Play a sound effect once."""
        if not self.enabled:
            return
        try:
            snd = self.sfx.get(sfx_name)
            if snd:
                snd.play()
        except Exception:
            pass

    def set_music_volume(self, vol):
        """Set music volume (0.0 - 1.0)."""
        self._music_volume = max(0.0, min(1.0, vol))
        if not self.enabled:
            return
        try:
            for snd in self.music_tracks.values():
                snd.set_volume(self._music_volume)
        except Exception:
            pass

    def set_sfx_volume(self, vol):
        """Set SFX volume (0.0 - 1.0)."""
        self._sfx_volume = max(0.0, min(1.0, vol))
        if not self.enabled:
            return
        try:
            for snd in self.sfx.values():
                snd.set_volume(self._sfx_volume)
        except Exception:
            pass
