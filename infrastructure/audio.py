from __future__ import annotations

from array import array
import math

import pygame


class AudioManager:
    """Small procedural sound bank; no external audio assets required."""

    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.sounds = {
                "grab": self._tone(420, 0.06, 0.18),
                "correct": self._sequence(((620, 0.07), (820, 0.10)), 0.22),
                "wrong": self._sequence(((210, 0.11), (155, 0.16)), 0.25),
                "scan": self._tone(880, 0.08, 0.15),
                "combo": self._sequence(((740, 0.06), (960, 0.06), (1180, 0.10)), 0.20),
                "phase": self._sequence(((360, 0.08), (520, 0.08), (700, 0.12)), 0.20),
                "warning": self._tone(260, 0.12, 0.18),
            }
            self.enabled = True
        except Exception:
            self.enabled = False

    @staticmethod
    def _samples(frequency: float, duration: float, volume: float) -> array:
        sample_rate = 22050
        count = max(1, int(sample_rate * duration))
        data = array("h")
        for index in range(count):
            t = index / sample_rate
            envelope = min(1.0, index / max(1, int(sample_rate * 0.01)))
            envelope *= max(0.0, 1.0 - index / count)
            value = int(32767 * volume * envelope * math.sin(math.tau * frequency * t))
            data.append(value)
        return data

    def _tone(self, frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(buffer=self._samples(frequency, duration, volume))

    def _sequence(self, notes: tuple[tuple[float, float], ...], volume: float) -> pygame.mixer.Sound:
        combined = array("h")
        for frequency, duration in notes:
            combined.extend(self._samples(frequency, duration, volume))
        return pygame.mixer.Sound(buffer=combined)

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()
