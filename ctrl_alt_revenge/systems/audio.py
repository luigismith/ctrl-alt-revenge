# systems/audio.py — High-quality procedural synthwave audio
# All music and SFX generated at runtime with proper ADSR, mixing, pentatonic scales
import math
import array
import random

try:
    import pygame
except ImportError:
    pygame = None


SAMPLE_RATE = 22050


def _clamp16(v):
    if v > 32767: return 32767
    if v < -32768: return -32768
    return int(v)


# ── Mixing helpers ──────────────────────────────────────────────────

def _mix(*buffers):
    """Mix multiple buffers by adding samples. Clamps to 16-bit range."""
    if not buffers:
        return array.array('h')
    max_len = max(len(b) for b in buffers)
    out = array.array('h', [0] * max_len)
    for buf in buffers:
        for i in range(len(buf)):
            out[i] = _clamp16(out[i] + buf[i])
    return out


def _add_to(dest, src, offset_samples):
    """Add src buffer into dest at offset. Mutates dest in place."""
    for i, v in enumerate(src):
        idx = offset_samples + i
        if idx >= len(dest):
            break
        dest[idx] = _clamp16(dest[idx] + v)


def _apply_adsr(buf, attack=0.005, decay=0.05, sustain=0.7, release=0.1,
                sample_rate=SAMPLE_RATE):
    """Apply ADSR envelope in place."""
    n = len(buf)
    if n == 0:
        return
    a_samples = int(attack * sample_rate)
    d_samples = int(decay * sample_rate)
    r_samples = int(release * sample_rate)
    s_samples = max(0, n - a_samples - d_samples - r_samples)

    idx = 0
    # Attack: 0 -> 1
    for i in range(min(a_samples, n)):
        env = i / max(a_samples, 1)
        buf[idx] = _clamp16(buf[idx] * env)
        idx += 1
    # Decay: 1 -> sustain
    for i in range(min(d_samples, n - idx)):
        env = 1.0 - (1.0 - sustain) * (i / max(d_samples, 1))
        buf[idx] = _clamp16(buf[idx] * env)
        idx += 1
    # Sustain
    for i in range(min(s_samples, n - idx)):
        buf[idx] = _clamp16(buf[idx] * sustain)
        idx += 1
    # Release: sustain -> 0
    for i in range(min(r_samples, n - idx)):
        env = sustain * (1.0 - (i / max(r_samples, 1)))
        buf[idx] = _clamp16(buf[idx] * env)
        idx += 1


# ── Waveforms ───────────────────────────────────────────────────────

def _triangle(freq, duration, volume=0.15, sample_rate=SAMPLE_RATE):
    """Warm triangle wave — much softer than square."""
    n = int(sample_rate * duration)
    buf = array.array('h', [0] * n)
    amp = volume * 32767
    period = sample_rate / max(freq, 1)
    for i in range(n):
        # Triangle: abs((t*2/period) mod 2 - 1) * 2 - 1
        t = (i * 2.0 / period) % 2.0
        val = abs(t - 1.0) * 2.0 - 1.0
        buf[i] = _clamp16(amp * val)
    return buf


def _pulse(freq, duration, duty=0.25, volume=0.15, sample_rate=SAMPLE_RATE):
    """Pulse wave with configurable duty cycle (25% = punchy bass)."""
    n = int(sample_rate * duration)
    buf = array.array('h', [0] * n)
    amp = volume * 32767
    period = sample_rate / max(freq, 1)
    for i in range(n):
        phase = (i % period) / period
        buf[i] = _clamp16(amp if phase < duty else -amp)
    return buf


def _saw(freq, duration, volume=0.12, sample_rate=SAMPLE_RATE):
    """Sawtooth wave for melodic leads."""
    n = int(sample_rate * duration)
    buf = array.array('h', [0] * n)
    amp = volume * 32767
    period = sample_rate / max(freq, 1)
    for i in range(n):
        phase = (i % period) / period
        buf[i] = _clamp16(amp * (2 * phase - 1))
    return buf


def _chorus_saw(freq, duration, volume=0.1, detune=0.008, sample_rate=SAMPLE_RATE):
    """Two sawtooth waves slightly detuned for chorus/thickness."""
    a = _saw(freq, duration, volume, sample_rate)
    b = _saw(freq * (1 + detune), duration, volume, sample_rate)
    return _mix(a, b)


def _noise(duration, volume=0.15, sample_rate=SAMPLE_RATE):
    """Random noise for drums."""
    n = int(sample_rate * duration)
    buf = array.array('h', [0] * n)
    amp = int(volume * 32767)
    for i in range(n):
        buf[i] = random.randint(-amp, amp)
    return buf


def _sweep(f_start, f_end, duration, volume=0.2, waveform='sine',
           sample_rate=SAMPLE_RATE):
    """Frequency sweep — for kicks, jump sounds, etc."""
    n = int(sample_rate * duration)
    buf = array.array('h', [0] * n)
    amp = volume * 32767
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f_start + (f_end - f_start) * t
        phase += 2.0 * math.pi * freq / sample_rate
        if waveform == 'sine':
            val = math.sin(phase)
        elif waveform == 'triangle':
            val = 2.0 / math.pi * math.asin(math.sin(phase))
        else:
            val = math.sin(phase)
        buf[i] = _clamp16(amp * val)
    return buf


# ── Drum sounds ─────────────────────────────────────────────────────

def _kick(duration=0.08, volume=0.35):
    """Kick drum: sine sweep from 120Hz to 40Hz."""
    buf = _sweep(120, 40, duration, volume, 'sine')
    _apply_adsr(buf, attack=0.002, decay=0.03, sustain=0.4, release=0.04)
    return buf


def _snare(duration=0.06, volume=0.25):
    """Snare: short noise burst + 200Hz body."""
    noise = _noise(duration, volume)
    body = _sine(200, duration * 0.5, volume * 0.5)
    out = _mix(noise, body)
    _apply_adsr(out, attack=0.001, decay=0.02, sustain=0.2, release=0.03)
    return out


def _hihat(duration=0.025, volume=0.12):
    """Hi-hat: very short noise."""
    buf = _noise(duration, volume)
    _apply_adsr(buf, attack=0.0, decay=0.008, sustain=0.15, release=0.01)
    return buf


def _sine(freq, duration, volume=0.2, sample_rate=SAMPLE_RATE):
    """Sine wave."""
    n = int(sample_rate * duration)
    buf = array.array('h', [0] * n)
    amp = volume * 32767
    two_pi_f = 2.0 * math.pi * freq
    for i in range(n):
        t = i / sample_rate
        buf[i] = _clamp16(amp * math.sin(two_pi_f * t))
    return buf


# ── Note helpers ────────────────────────────────────────────────────

# MIDI note to frequency: 440 * 2^((n-69)/12)
NOTES = {
    'A2': 110.00, 'A#2': 116.54, 'B2': 123.47,
    'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81,
    'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00,
    'A#3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63,
    'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00,
    'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'G5': 783.99, 'A5': 880.00,
}


def _note(name, duration, waveform='triangle', volume=0.12):
    """Create a note with ADSR envelope."""
    freq = NOTES.get(name, 440.0)
    if waveform == 'triangle':
        buf = _triangle(freq, duration, volume)
    elif waveform == 'pulse':
        buf = _pulse(freq, duration, 0.25, volume)
    elif waveform == 'saw':
        buf = _chorus_saw(freq, duration, volume)
    else:
        buf = _sine(freq, duration, volume)
    _apply_adsr(buf, attack=0.005, decay=0.04, sustain=0.65, release=0.08)
    return buf


# ── Music tracks ────────────────────────────────────────────────────

def _build_menu_track():
    """Menu: slow ambient pad with pentatonic arpeggio. 75 BPM, 8s loop."""
    bpm = 75
    beat = 60.0 / bpm  # 0.8s per beat
    bar = beat * 4     # 3.2s per bar
    total_duration = bar * 2.5  # 8 seconds
    total_samples = int(total_duration * SAMPLE_RATE)
    track = array.array('h', [0] * total_samples)

    # Chord progression: Am - F - C - G (dark synthwave)
    chords = [
        ['A3', 'C4', 'E4'],   # Am
        ['F3', 'A3', 'C4'],   # F
        ['C4', 'E4', 'G4'],   # C
        ['G3', 'B3', 'D4'],   # G
    ]

    # Pad: hold each chord for half a bar
    for i, chord in enumerate(chords):
        t_start = i * (bar / 2)
        for note_name in chord:
            pad = _note(note_name, bar / 2, 'saw', 0.06)
            _apply_adsr(pad, attack=0.15, decay=0.1, sustain=0.8, release=0.2)
            _add_to(track, pad, int(t_start * SAMPLE_RATE))

    # Arpeggio: cycle through chord tones at 8th notes
    arp_dur = beat / 2  # eighth note
    for i in range(16):  # 16 eighth notes = 2 bars
        chord_idx = (i // 4) % len(chords)
        chord = chords[chord_idx]
        note_idx = i % 3
        # Octave up for arpeggio
        note_name = chord[note_idx]
        # Transpose up one octave
        if note_name[-1].isdigit():
            octave = int(note_name[-1])
            note_name = note_name[:-1] + str(octave + 1)
        if note_name in NOTES:
            arp = _note(note_name, arp_dur, 'triangle', 0.07)
            _add_to(track, arp, int(i * arp_dur * SAMPLE_RATE))

    return track


def _build_level_track():
    """Level: driving bass + drums + melodic lead. 120 BPM, ~8s loop."""
    bpm = 120
    beat = 60.0 / bpm  # 0.5s per beat
    bar = beat * 4     # 2s per bar
    total_duration = bar * 4  # 8 seconds = 4 bars
    total_samples = int(total_duration * SAMPLE_RATE)
    track = array.array('h', [0] * total_samples)

    # Bass: Em - C - G - D progression (one chord per bar)
    bass_notes = ['E2', 'C3', 'G2', 'D3']
    # Wait — E2 isn't in NOTES, use E3 lower bound
    bass_notes = ['E3', 'C3', 'G3', 'D3']

    # Bass pattern: 8th notes, root + octave jumps
    for bar_idx in range(4):
        root = bass_notes[bar_idx]
        for eighth in range(8):
            t = bar_idx * bar + eighth * (beat / 2)
            vol = 0.18 if eighth % 2 == 0 else 0.12
            b = _pulse(NOTES[root], beat / 2 * 0.9, 0.25, vol)
            _apply_adsr(b, attack=0.003, decay=0.03, sustain=0.5, release=0.05)
            _add_to(track, b, int(t * SAMPLE_RATE))

    # Drums
    for bar_idx in range(4):
        # Kick on beat 1 and 3
        for kick_beat in [0, 2]:
            t = bar_idx * bar + kick_beat * beat
            _add_to(track, _kick(0.1, 0.35), int(t * SAMPLE_RATE))
        # Snare on beat 2 and 4
        for snare_beat in [1, 3]:
            t = bar_idx * bar + snare_beat * beat
            _add_to(track, _snare(0.08, 0.22), int(t * SAMPLE_RATE))
        # Hi-hat on 8ths
        for hh in range(8):
            t = bar_idx * bar + hh * (beat / 2)
            _add_to(track, _hihat(0.025, 0.08), int(t * SAMPLE_RATE))

    # Lead melody — pentatonic minor phrase
    lead_pattern = [
        # bar 1 (Em)
        ('E4', 0.5), ('G4', 0.25), ('B4', 0.25), ('E5', 0.5), ('D5', 0.5),
        # bar 2 (C)
        ('C4', 0.5), ('E4', 0.25), ('G4', 0.25), ('C5', 1.0),
        # bar 3 (G)
        ('G4', 0.5), ('B4', 0.25), ('D5', 0.25), ('G5', 0.5), ('A5', 0.5),
        # bar 4 (D)
        ('D4', 0.5), ('F#4', 0.25), ('A4', 0.25), ('D5', 1.0),
    ]
    t = 0.0
    for note_name, dur in lead_pattern:
        if note_name in NOTES:
            n = _note(note_name, dur * beat, 'saw', 0.08)
            _add_to(track, n, int(t * SAMPLE_RATE))
        t += dur * beat

    return track


def _build_boss_track():
    """Boss: aggressive 140 BPM, dissonant minor."""
    bpm = 140
    beat = 60.0 / bpm
    bar = beat * 4
    total_duration = bar * 4  # ~6.8s
    total_samples = int(total_duration * SAMPLE_RATE)
    track = array.array('h', [0] * total_samples)

    bass_notes = ['A3', 'E3', 'A3', 'F3']  # Am - E - Am - F

    # Aggressive 16th-note bass with octave jumps
    for bar_idx in range(4):
        root_name = bass_notes[bar_idx]
        root_freq = NOTES[root_name]
        oct_freq = root_freq * 2
        for sixteenth in range(16):
            t = bar_idx * bar + sixteenth * (beat / 4)
            # Alternate root / octave
            freq = root_freq if sixteenth % 2 == 0 else oct_freq
            b = _pulse(freq, beat / 4 * 0.85, 0.25, 0.16)
            _apply_adsr(b, attack=0.001, decay=0.02, sustain=0.5, release=0.03)
            _add_to(track, b, int(t * SAMPLE_RATE))

    # Double-time drums
    for bar_idx in range(4):
        # Kick every beat + extra on 2.5 and 4.5
        for k_time in [0, 1, 2, 2.5, 3]:
            t = bar_idx * bar + k_time * beat
            _add_to(track, _kick(0.07, 0.38), int(t * SAMPLE_RATE))
        # Snare on 2 and 4
        for s_time in [1, 3]:
            t = bar_idx * bar + s_time * beat
            _add_to(track, _snare(0.07, 0.24), int(t * SAMPLE_RATE))
        # 16th note hihats
        for h in range(16):
            t = bar_idx * bar + h * (beat / 4)
            _add_to(track, _hihat(0.02, 0.07), int(t * SAMPLE_RATE))

    # Fast arpeggio lead
    for bar_idx in range(4):
        chord_root = bass_notes[bar_idx]
        if chord_root not in NOTES:
            continue
        root_freq = NOTES[chord_root]
        # Minor arpeggio: root, min3 (6/5), fifth (3/2), octave
        arp_freqs = [root_freq * 2, root_freq * 2.4, root_freq * 3, root_freq * 4]
        for sixteenth in range(16):
            t = bar_idx * bar + sixteenth * (beat / 4)
            freq = arp_freqs[sixteenth % 4]
            a = _chorus_saw(freq, beat / 4 * 0.9, 0.07)
            _apply_adsr(a, attack=0.002, decay=0.02, sustain=0.4, release=0.03)
            _add_to(track, a, int(t * SAMPLE_RATE))

    return track


# ── SFX ─────────────────────────────────────────────────────────────

def _sfx_punch():
    noise = _noise(0.06, 0.2)
    blip = _sweep(150, 50, 0.05, 0.2, 'square' if False else 'sine')
    out = _mix(noise, blip)
    _apply_adsr(out, attack=0.001, decay=0.02, sustain=0.3, release=0.03)
    return out


def _sfx_jump():
    return _sweep(300, 700, 0.1, 0.15, 'triangle')


def _sfx_hurt():
    noise = _noise(0.15, 0.15)
    sweep = _sweep(500, 100, 0.15, 0.2, 'sine')
    out = _mix(noise, sweep)
    _apply_adsr(out, attack=0.001, decay=0.05, sustain=0.5, release=0.07)
    return out


def _sfx_hack_success():
    buf = array.array('h', [0] * int(0.3 * SAMPLE_RATE))
    for i, note_name in enumerate(['E4', 'G4', 'B4', 'E5']):
        n = _note(note_name, 0.08, 'triangle', 0.18)
        _add_to(buf, n, int(i * 0.06 * SAMPLE_RATE))
    return buf


def _sfx_hack_fail():
    return _sweep(400, 80, 0.25, 0.2, 'sine')


def _sfx_menu_select():
    return _note('A4', 0.04, 'triangle', 0.15)


def _sfx_parry():
    noise = _noise(0.05, 0.12)
    hi = _sine(2500, 0.06, 0.18)
    out = _mix(noise, hi)
    _apply_adsr(out, attack=0.0, decay=0.015, sustain=0.4, release=0.04)
    return out


# ── AudioManager ────────────────────────────────────────────────────

class AudioManager:
    def __init__(self):
        if pygame is None:
            self.available = False
            self.music_tracks = {}
            self.sfx = {}
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            self.available = True
        except Exception:
            self.available = False
            self.music_tracks = {}
            self.sfx = {}
            return

        try:
            self.music_tracks = {
                'menu': self._buf_to_sound(_build_menu_track()),
                'level': self._buf_to_sound(_build_level_track()),
                'boss': self._buf_to_sound(_build_boss_track()),
            }
            self.sfx = {
                'punch': self._buf_to_sound(_sfx_punch()),
                'jump': self._buf_to_sound(_sfx_jump()),
                'hurt': self._buf_to_sound(_sfx_hurt()),
                'hack_success': self._buf_to_sound(_sfx_hack_success()),
                'hack_fail': self._buf_to_sound(_sfx_hack_fail()),
                'menu_select': self._buf_to_sound(_sfx_menu_select()),
                'parry': self._buf_to_sound(_sfx_parry()),
            }
        except Exception as e:
            print(f"[audio] Error generating audio: {e}")
            self.music_tracks = {}
            self.sfx = {}

        self.current_music = None
        self.music_volume = 0.45
        self.sfx_volume = 0.7
        self._music_channel = None

    def _buf_to_sound(self, buf):
        """Convert an array.array('h') into pygame.mixer.Sound."""
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play_music(self, track_name):
        if not self.available or track_name not in self.music_tracks:
            return
        if self.current_music == track_name:
            return
        self.stop_music()
        sound = self.music_tracks[track_name]
        sound.set_volume(self.music_volume)
        self._music_channel = sound.play(loops=-1)
        self.current_music = track_name

    def stop_music(self):
        if self._music_channel:
            try:
                self._music_channel.fadeout(300)
            except Exception:
                pass
            self._music_channel = None
        self.current_music = None

    def play_sfx(self, sfx_name):
        if not self.available or sfx_name not in self.sfx:
            return
        try:
            s = self.sfx[sfx_name]
            s.set_volume(self.sfx_volume)
            s.play()
        except Exception:
            pass

    def set_music_volume(self, vol):
        self.music_volume = max(0.0, min(1.0, vol))
        if self._music_channel:
            try:
                self._music_channel.set_volume(self.music_volume)
            except Exception:
                pass

    def set_sfx_volume(self, vol):
        self.sfx_volume = max(0.0, min(1.0, vol))
