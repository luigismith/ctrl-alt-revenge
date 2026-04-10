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


def _noise(duration, volume=0.3, sample_rate=SAMPLE_RATE):
    """Generate white noise buffer."""
    n = int(sample_rate * duration)
    buf = array.array('h')
    amp = volume * 32767
    rng = random.Random(42)
    for _ in range(n):
        buf.append(_clamp16(amp * (rng.random() * 2.0 - 1.0)))
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
    """Dark ambient synthwave pad — slow arpeggiated minor progression.

    Chord progression: Am - F - C - G (i - VI - III - VII in A minor)
    Each chord lasts ~2s, total loop ~8s at ~90 BPM.
    """
    bpm = 90
    beat_dur = 60.0 / bpm  # ~0.667s per beat
    # 3 beats per chord, 4 chords = 12 beats total = ~8s
    beats_per_chord = 3
    chord_dur = beat_dur * beats_per_chord

    # Arpeggiated notes for each chord (root, 3rd, 5th in low octave)
    chords = [
        # Am: A2, C3, E3
        [_note_freq('A', 2), _note_freq('C', 3), _note_freq('E', 3)],
        # F:  F2, A2, C3
        [_note_freq('F', 2), _note_freq('A', 2), _note_freq('C', 3)],
        # C:  C2, E2, G2
        [_note_freq('C', 2), _note_freq('E', 2), _note_freq('G', 2)],
        # G:  G2, B2, D3
        [_note_freq('G', 2), _note_freq('B', 2), _note_freq('D', 3)],
    ]

    note_dur = chord_dur / 3.0  # each arpeggio note
    total_dur = chord_dur * len(chords)
    total_samples = int(SAMPLE_RATE * total_dur)
    result = array.array('h', [0] * total_samples)

    for ci, chord_notes in enumerate(chords):
        for ni, freq in enumerate(chord_notes):
            start_t = ci * chord_dur + ni * note_dur
            start_s = int(start_t * SAMPLE_RATE)
            # Use square wave at low volume for that retro pad feel
            note_buf = _square(freq, note_dur * 0.9, volume=0.12)
            # Apply fade-in/fade-out envelope
            fade_samples = min(int(SAMPLE_RATE * 0.05), len(note_buf) // 4)
            for j in range(fade_samples):
                env = j / fade_samples
                note_buf[j] = _clamp16(note_buf[j] * env)
                note_buf[-(j + 1)] = _clamp16(note_buf[-(j + 1)] * env)
            _overlay_at(result, note_buf, start_s)

    # Add a slow sine pad underneath for warmth
    pad = _sine(_note_freq('A', 1), total_dur, volume=0.06)
    result = _mix_buffers(result, pad)

    return _make_sound(result)


def _build_level_music():
    """Driving beat-em-up energy — bass, drums, lead synth.

    Tempo: ~130 BPM, 16 beats = ~7.4s loop.
    Bass: 8th-note square wave pattern
    Drums: kick 1&3, snare 2&4, hi-hat on 8ths
    Lead: 4-bar synth riff with sawtooth
    """
    bpm = 130
    beat_dur = 60.0 / bpm  # ~0.462s
    num_beats = 16  # 4 bars of 4/4
    total_dur = beat_dur * num_beats
    total_samples = int(SAMPLE_RATE * total_dur)
    eighth_dur = beat_dur / 2.0

    # ── Bass line (square wave, 8th notes) ──
    bass_notes = [
        'A', 'A', 'C', 'C', 'D', 'D', 'E', 'E',  # bar 1-2
        'A', 'A', 'G', 'G', 'F', 'F', 'E', 'E',  # bar 3-4
        'A', 'A', 'C', 'C', 'D', 'D', 'E', 'E',
        'F', 'F', 'G', 'G', 'A', 'A', 'E', 'E',
    ]
    bass_buf = array.array('h', [0] * total_samples)
    for i, note_name in enumerate(bass_notes):
        freq = _note_freq(note_name, 2)
        start_s = int(i * eighth_dur * SAMPLE_RATE)
        note = _square(freq, eighth_dur * 0.85, volume=0.18)
        # Quick decay envelope
        decay_len = len(note)
        for j in range(decay_len):
            env = max(0, 1.0 - (j / decay_len) * 0.4)
            note[j] = _clamp16(note[j] * env)
        _overlay_at(bass_buf, note, start_s)

    # ── Drums ──
    kick = _sine_decay(60, 0.15, volume=0.35)
    snare = _noise_decay(0.12, volume=0.20, decay=18.0)
    hihat = _noise_decay(0.05, volume=0.10, decay=50.0)

    drum_buf = array.array('h', [0] * total_samples)
    for beat in range(num_beats):
        beat_start = int(beat * beat_dur * SAMPLE_RATE)
        # Hi-hat on every 8th note
        for sub in range(2):
            hh_start = beat_start + int(sub * eighth_dur * SAMPLE_RATE)
            _overlay_at(drum_buf, hihat, hh_start)
        # Kick on beats 1 and 3 (of each bar)
        bar_beat = beat % 4
        if bar_beat == 0 or bar_beat == 2:
            _overlay_at(drum_buf, kick, beat_start)
        # Snare on beats 2 and 4
        if bar_beat == 1 or bar_beat == 3:
            _overlay_at(drum_buf, snare, beat_start)

    # ── Lead melody (sawtooth, 4-bar riff) ──
    # Each entry: (note, octave, duration_in_eighths)
    lead_pattern = [
        ('A', 4, 2), ('C', 5, 1), ('E', 5, 1),
        ('D', 5, 2), ('C', 5, 2),
        ('A', 4, 1), ('G', 4, 1), ('E', 4, 2),
        ('rest', 0, 4),
        ('A', 4, 2), ('C', 5, 1), ('E', 5, 1),
        ('G', 5, 2), ('E', 5, 1), ('D', 5, 1),
        ('C', 5, 2), ('A', 4, 2),
        ('rest', 0, 4),
    ]
    lead_buf = array.array('h', [0] * total_samples)
    pos = 0  # position in 8th notes
    for note_name, octave, dur_eighths in lead_pattern:
        if note_name == 'rest':
            pos += dur_eighths
            continue
        freq = _note_freq(note_name, octave)
        note_dur_s = dur_eighths * eighth_dur
        start_s = int(pos * eighth_dur * SAMPLE_RATE)
        note = _sawtooth(freq, note_dur_s * 0.8, volume=0.10)
        # Fade in/out
        fade = min(int(SAMPLE_RATE * 0.02), len(note) // 4)
        for j in range(fade):
            env = j / fade
            note[j] = _clamp16(note[j] * env)
            note[-(j + 1)] = _clamp16(note[-(j + 1)] * env)
        _overlay_at(lead_buf, note, start_s)
        pos += dur_eighths

    result = _mix_buffers(bass_buf, drum_buf, lead_buf)
    return _make_sound(result)


def _build_boss_music():
    """Intense boss fight music — aggressive bass, double-time drums,
    dissonant lead with minor 2nds and tritones.

    Tempo: ~150 BPM, 16 beats = ~6.4s loop.
    """
    bpm = 150
    beat_dur = 60.0 / bpm
    num_beats = 16
    total_dur = beat_dur * num_beats
    total_samples = int(SAMPLE_RATE * total_dur)
    eighth_dur = beat_dur / 2.0
    sixteenth_dur = beat_dur / 4.0

    # ── Aggressive bass (16th note pattern) ──
    bass_pattern = [
        'E', 'E', 'E', 'E',   'Bb', 'Bb', 'E', 'E',
        'F', 'F', 'E', 'E',   'Bb', 'Bb', 'B', 'B',
        'E', 'E', 'E', 'E',   'F', 'F', 'E', 'E',
        'Bb', 'Bb', 'B', 'B', 'E', 'E', 'Eb', 'Eb',
        'E', 'E', 'E', 'E',   'Bb', 'Bb', 'E', 'E',
        'F', 'F', 'E', 'E',   'Bb', 'Bb', 'B', 'B',
        'E', 'E', 'E', 'E',   'Gb', 'Gb', 'E', 'E',
        'F', 'F', 'Bb', 'Bb', 'E', 'E', 'E', 'E',
    ]
    bass_buf = array.array('h', [0] * total_samples)
    for i, note_name in enumerate(bass_pattern):
        freq = _note_freq(note_name, 2)
        start_s = int(i * sixteenth_dur * SAMPLE_RATE)
        note = _square(freq, sixteenth_dur * 0.8, volume=0.20)
        # Sharp attack envelope
        attack = min(int(SAMPLE_RATE * 0.005), len(note) // 2)
        for j in range(attack):
            note[j] = _clamp16(note[j] * (j / attack))
        _overlay_at(bass_buf, note, start_s)

    # ── Double-time drums ──
    kick = _sine_decay(55, 0.12, volume=0.38)
    snare = _noise_decay(0.10, volume=0.22, decay=20.0)
    hihat = _noise_decay(0.04, volume=0.12, decay=55.0)

    drum_buf = array.array('h', [0] * total_samples)
    for beat in range(num_beats):
        beat_start = int(beat * beat_dur * SAMPLE_RATE)
        # Hi-hat on every 16th note
        for sub in range(4):
            hh_start = beat_start + int(sub * sixteenth_dur * SAMPLE_RATE)
            _overlay_at(drum_buf, hihat, hh_start)
        # Kick on every beat + the "and" of 2 and 4
        bar_beat = beat % 4
        _overlay_at(drum_buf, kick, beat_start)
        if bar_beat == 1 or bar_beat == 3:
            _overlay_at(drum_buf, kick,
                        beat_start + int(eighth_dur * SAMPLE_RATE))
        # Snare on 2 and 4
        if bar_beat == 1 or bar_beat == 3:
            _overlay_at(drum_buf, snare, beat_start)

    # ── Dissonant lead (tritones, minor 2nds) ──
    lead_pattern = [
        ('E', 5, 2), ('F', 5, 1), ('Bb', 5, 1),  # E->F minor 2nd, E->Bb tritone
        ('B', 4, 2), ('C', 5, 2),
        ('E', 5, 1), ('Bb', 5, 1), ('A', 5, 2),
        ('rest', 0, 4),
        ('E', 5, 2), ('F', 5, 2),
        ('Bb', 5, 1), ('B', 5, 1), ('E', 5, 2),
        ('F', 5, 1), ('E', 5, 1), ('Eb', 5, 2),
        ('rest', 0, 4),
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
        note = _sawtooth(freq, note_dur_s * 0.75, volume=0.09)
        fade = min(int(SAMPLE_RATE * 0.01), len(note) // 4)
        for j in range(fade):
            env = j / fade
            note[j] = _clamp16(note[j] * env)
            note[-(j + 1)] = _clamp16(note[-(j + 1)] * env)
        _overlay_at(lead_buf, note, start_s)
        pos += dur_eighths

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
