from __future__ import annotations

from collections import Counter
import random
from pathlib import Path

import pygame
from pygame.math import Vector2

from core.config import (
    ACCENT,
    BACKGROUND,
    BELT_RECT,
    CONTAINER_HEIGHT,
    CONTAINER_TOP,
    DANGER,
    DESTINATION_COLORS,
    FPS,
    INK,
    MUTED,
    PANEL,
    PANEL_2,
    PANEL_BORDER,
    PHASES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SUCCESS,
    TITLE,
    WARNING,
)
from core.enums import Destination, GameState, HandlingTag, PackageState
from entities.package import CargoPackage, draw_destination_symbol
from entities.player import PlayerStats
from infrastructure.audio import AudioManager
from infrastructure.storage import HighScoreStore
from interactables.conveyor import ConveyorBelt
from interactables.scanner import ScannerConsole
from interactables.shipping_container import ShippingContainer
from managers.difficulty_manager import DifficultyManager
from managers.feedback_manager import FeedbackManager
from managers.score_manager import ScoreManager
from managers.spawn_manager import SpawnManager


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    font = pygame.font.SysFont("segoeui,arial", size, bold=bold)
    return font if font is not None else pygame.font.Font(None, size)


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int] = PANEL,
    border: tuple[int, int, int] = PANEL_BORDER,
    radius: int = 12,
    width: int = 2,
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)


class CargoPanicGame:
    def __init__(self, seed: int | None = None, headless: bool = False) -> None:
        pygame.init()
        pygame.font.init()
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.TITLE
        self.seed = seed if seed is not None else random.randrange(1, 999_999)
        self.rng = random.Random(self.seed)
        self.headless = headless

        self.fonts = {
            "tiny": load_font(14),
            "small": load_font(18),
            "medium": load_font(23, True),
            "large": load_font(34, True),
            "title": load_font(70, True),
            "hero": load_font(100, True),
        }

        self.audio = AudioManager()
        self.storage = HighScoreStore(Path.home() / ".cargo_panic_highscore.json")
        self.high_score = self.storage.load()
        self.feedback = FeedbackManager()

        self.game_time = 0.0
        self.phase_index = 0
        self.phase_elapsed = 0.0
        self.phase_intro_until = 0.0
        self.emergency_until: float | None = None
        self.result_saved = False

        self.score = ScoreManager()
        self.stats = PlayerStats()
        self.strikes = 3
        self.packages: list[CargoPackage] = []
        self.held_package: CargoPackage | None = None
        self.scanning_package: CargoPackage | None = None
        self.hovered_package: CargoPackage | None = None
        self.mouse_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        self.belt = ConveyorBelt(PHASES[0].belt_speed)
        self.spawn_manager = SpawnManager(self.rng)
        self.difficulty = DifficultyManager(self.rng)
        self.containers = self._create_containers()
        self.scanner = ScannerConsole(pygame.Rect(885, 151, 350, 74))

        self.screen_shake = 0.0
        self.flash_color: tuple[int, int, int] | None = None
        self.flash_alpha = 0.0

    @staticmethod
    def _create_containers() -> list[ShippingContainer]:
        margin = 42
        gap = 24
        width = (SCREEN_WIDTH - margin * 2 - gap * 2) // 3
        return [
            ShippingContainer(
                destination=destination,
                rect=pygame.Rect(margin + index * (width + gap), CONTAINER_TOP, width, CONTAINER_HEIGHT),
            )
            for index, destination in enumerate(Destination)
        ]

    def start_new_game(self) -> None:
        self.seed = random.randrange(1, 999_999) if self.seed is None else self.seed
        self.rng.seed(self.seed)
        self.state = GameState.PLAYING
        self.game_time = 0.0
        self.phase_index = 0
        self.phase_elapsed = 0.0
        self.phase_intro_until = 2.4
        self.emergency_until = None
        self.result_saved = False
        self.score = ScoreManager()
        self.stats = PlayerStats()
        self.strikes = 3
        self.packages.clear()
        self.held_package = None
        self.scanning_package = None
        self.hovered_package = None
        self.feedback.reset()
        self.belt.base_speed = PHASES[0].belt_speed
        self.belt.surge_multiplier = 1.0
        self.spawn_manager.reset(self.game_time)
        self.spawn_manager.next_spawn_at = self.phase_intro_until + 0.4
        self.difficulty.reset(self.game_time)
        for container in self.containers:
            container.closed_until = 0.0
            container.warning_until = 0.0
        self.feedback.banner(PHASES[0].name, ACCENT, self.game_time, 2.2)
        self.audio.play("phase")

    def run(self) -> None:
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                self.mouse_position = event.pos

            if self.state is GameState.TITLE:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.start_new_game()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_new_game()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                continue

            if self.state is GameState.RESULTS:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                    self.start_new_game()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = GameState.TITLE
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_new_game()
                continue

            if self.state is GameState.PAUSED:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    self.state = GameState.PLAYING
                continue

            if self.state is not GameState.PLAYING:
                continue

            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                if self.held_package is not None:
                    self._reattach(self.held_package)
                    self.held_package = None
                if self.scanning_package is not None:
                    self.scanning_package.state = PackageState.ON_BELT
                    self.scanning_package.scan_progress = 0.0
                    self.scanning_package = None
                self.state = GameState.PAUSED
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._try_grab(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._release_held(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self._try_start_scan(event.pos)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self._try_start_scan(self.mouse_position)

    def _active_packages(self) -> list[CargoPackage]:
        return [
            package
            for package in self.packages
            if package.state in (PackageState.ON_BELT, PackageState.HELD, PackageState.SCANNING)
        ]

    def _package_at(self, position: tuple[int, int]) -> CargoPackage | None:
        candidates = [
            package
            for package in self._active_packages()
            if package.state is PackageState.ON_BELT and package.rect.collidepoint(position)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda package: (package.position.x, package.package_id))

    def _try_grab(self, position: tuple[int, int]) -> None:
        if self.held_package is not None or self.scanning_package is not None:
            return
        package = self._package_at(position)
        if package is None:
            return
        package.state = PackageState.HELD
        package.held_offset = Vector2(position) - package.position
        package.reset_drag_metrics()
        self.held_package = package
        self.audio.play("grab")

    def _try_start_scan(self, position: tuple[int, int]) -> None:
        if self.held_package is not None or self.scanning_package is not None:
            return
        package = self._package_at(position)
        if package is None or package.tag is not HandlingTag.DAMAGED or package.label_revealed:
            return
        package.state = PackageState.SCANNING
        package.scan_progress = 0.0
        self.scanning_package = package
        self.feedback.add_text("HOLD TO SCAN", (package.position.x, package.position.y - 58), (92, 214, 235))

    def _release_held(self, position: tuple[int, int]) -> None:
        package = self.held_package
        if package is None:
            return
        self.held_package = None

        target = next((container for container in self.containers if container.contains(position)), None)
        if target is None:
            self._reattach(package)
            if package.tag is HandlingTag.FRAGILE and package.peak_drag_speed > 1025:
                self.score.fragile_penalty()
                self.stats.fragile_mishandled += 1
                self.feedback.add_text("ROUGH HANDLING -50", package.position, DANGER)
                self.audio.play("wrong")
            return

        if target.is_closed(self.game_time):
            package.rejected_until = self.game_time + 0.7
            self._reattach(package)
            self.feedback.add_text("BAY CLOSED", (target.rect.centerx, target.rect.y - 18), DANGER, 1.2)
            self.audio.play("wrong")
            return

        if target.destination is package.destination:
            self._correct_delivery(package, target)
        else:
            self._wrong_delivery(package, target)

    def _reattach(self, package: CargoPackage) -> None:
        package.state = PackageState.ON_BELT
        belt = pygame.Rect(BELT_RECT)
        package.position.x = max(30.0, min(float(SCREEN_WIDTH - 145), package.position.x))
        package.position.y = belt.centery
        package.reset_drag_metrics()

    def _correct_delivery(self, package: CargoPackage, target: ShippingContainer) -> None:
        fragile_clean = package.tag is not HandlingTag.FRAGILE or package.peak_drag_speed <= 1025
        gained, labels = self.score.award_delivery(package, self.game_time, fragile_clean)
        package.state = PackageState.DELIVERED
        self.stats.total_sorted += 1
        self.stats.correct_sorted += 1
        self.stats.total_sort_time += package.age(self.game_time)

        color = DESTINATION_COLORS[target.destination.value]
        self.feedback.burst(target.rect.center, color, 28)
        self.feedback.add_text(f"+{gained}", (target.rect.centerx, target.rect.y - 20), SUCCESS, 1.2)
        for index, label in enumerate(labels[:2]):
            self.feedback.add_text(label, (target.rect.centerx, target.rect.y - 48 - index * 22), ACCENT)
        self.audio.play("correct")

        if package.tag is HandlingTag.FRAGILE and not fragile_clean:
            self.score.fragile_penalty()
            self.stats.fragile_mishandled += 1
            self.feedback.add_text("ROUGH HANDLING -50", (target.rect.centerx, target.rect.y - 76), DANGER)

        if self.score.combo in (5, 10, 20):
            self.feedback.banner(f"COMBO x{self.score.multiplier:g}", ACCENT, self.game_time, 1.5)
            self.audio.play("combo")

    def _wrong_delivery(self, package: CargoPackage, target: ShippingContainer) -> None:
        self.score.wrong_delivery()
        self.stats.total_sorted += 1
        self.stats.wrong += 1
        self._lose_strike("Wrong destination")
        package.rejected_until = self.game_time + 0.8
        self._reattach(package)
        package.position.x = min(package.position.x, SCREEN_WIDTH - 250)
        self.feedback.add_text("WRONG BAY", (target.rect.centerx, target.rect.y - 18), DANGER, 1.2)
        self.feedback.add_text(
            f"→ {package.destination.value.upper()}",
            (package.position.x, package.position.y - 70),
            DESTINATION_COLORS[package.destination.value],
        )
        self.audio.play("wrong")

    def _lose_strike(self, reason: str) -> None:
        if self.emergency_until is not None:
            return
        self.strikes = max(0, self.strikes - 1)
        self.flash_color = DANGER
        self.flash_alpha = 120.0
        self.screen_shake = 7.0
        self.feedback.banner(reason.upper(), DANGER, self.game_time, 1.2)
        if self.strikes <= 0:
            self.emergency_until = self.game_time + 10.0
            self.feedback.banner("EMERGENCY MODE — 10 SECONDS", DANGER, self.game_time, 2.6)

    def update(self, dt: float) -> None:
        if self.state is not GameState.PLAYING:
            return

        self.game_time += dt
        self.phase_elapsed += dt
        self.feedback.update(dt)
        self.screen_shake = max(0.0, self.screen_shake - 20.0 * dt)
        self.flash_alpha = max(0.0, self.flash_alpha - 180.0 * dt)

        if self.emergency_until is not None and self.game_time >= self.emergency_until:
            self._finish_game()
            return

        self._update_phase()
        if self.state is not GameState.PLAYING:
            return

        spec = PHASES[self.phase_index]
        self.belt.base_speed = spec.belt_speed
        multiplier, message = self.difficulty.update(self.game_time, self.phase_index, self.containers)
        self.belt.surge_multiplier = multiplier
        if message:
            color = DANGER if "offline" in message.lower() or "surge" in message.lower() else WARNING
            self.feedback.banner(message.upper(), color, self.game_time, 1.8)
            self.audio.play("warning")

        if self.held_package is not None:
            self.held_package.update_drag(self.mouse_position, dt)

        self._update_scanner(dt)
        self.belt.update(self.packages, dt)
        self._update_packages()

        if self.game_time >= self.phase_intro_until:
            active_count = len(self._active_packages())
            if self.spawn_manager.can_spawn(self.game_time, active_count, self.phase_index):
                package = self.spawn_manager.spawn(self.game_time, self.phase_index, pygame.Rect(BELT_RECT).centery)
                self.packages.append(package)

        self.packages = [package for package in self.packages if package.state not in (PackageState.DELIVERED, PackageState.MISSED)]
        self.hovered_package = self._package_at(self.mouse_position) if self.held_package is None else None

    def _update_phase(self) -> None:
        spec = PHASES[self.phase_index]
        if self.phase_elapsed < spec.duration:
            return
        self.phase_index += 1
        self.phase_elapsed = 0.0
        if self.phase_index >= len(PHASES):
            self._finish_game()
            return

        next_spec = PHASES[self.phase_index]
        self.phase_intro_until = self.game_time + 2.4
        self.spawn_manager.next_spawn_at = self.phase_intro_until + 0.3
        self.feedback.banner(next_spec.name.upper(), ACCENT, self.game_time, 2.2)
        self.audio.play("phase")

        if self.phase_index == 3:
            self.rng.shuffle(self.containers)
            ordered_rects = sorted((container.rect.copy() for container in self.containers), key=lambda rect: rect.x)
            for container, rect in zip(self.containers, ordered_rects, strict=True):
                container.rect = rect
            self.feedback.add_text("BAY ORDER CHANGED", (SCREEN_WIDTH / 2, 485), WARNING, 1.2)

    def _update_scanner(self, dt: float) -> None:
        package = self.scanning_package
        if package is None:
            return
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed(3)
        held = bool(keys[pygame.K_SPACE] or mouse_buttons[2])
        pointer_inside = package.rect.inflate(30, 30).collidepoint(self.mouse_position)

        if not held or not pointer_inside:
            package.state = PackageState.ON_BELT
            package.scan_progress = 0.0
            self.scanning_package = None
            return

        package.scan_progress += dt / 1.1
        if package.scan_progress >= 1.0:
            package.scan_progress = 1.0
            package.label_revealed = True
            package.state = PackageState.ON_BELT
            self.scanning_package = None
            self.feedback.add_text("LABEL RESTORED", (package.position.x, package.position.y - 62), SUCCESS, 1.2)
            self.feedback.burst(package.position, (92, 214, 235), 16)
            self.audio.play("scan")

    def _update_packages(self) -> None:
        for package in list(self.packages):
            if package.state not in (PackageState.ON_BELT, PackageState.SCANNING):
                continue

            if package.tag is HandlingTag.REFRIGERATED and package.age(self.game_time) >= 10.5:
                package.state = PackageState.MISSED
                self.stats.expired += 1
                self.score.miss()
                self._lose_strike("Refrigerated cargo expired")
                self.feedback.add_text("EXPIRED", package.position, DANGER, 1.2)
                self.audio.play("wrong")
                if self.scanning_package is package:
                    self.scanning_package = None
                continue

            if package.position.x - package.width / 2 > SCREEN_WIDTH:
                package.state = PackageState.MISSED
                self.stats.missed += 1
                self.score.miss()
                self._lose_strike("Package missed")
                self.feedback.add_text("MISSED", (SCREEN_WIDTH - 100, pygame.Rect(BELT_RECT).centery - 70), DANGER, 1.2)
                self.audio.play("wrong")
                if self.scanning_package is package:
                    self.scanning_package = None

    def _finish_game(self) -> None:
        self.phase_index = min(self.phase_index, len(PHASES) - 1)
        self.state = GameState.RESULTS
        self.held_package = None
        self.scanning_package = None
        if not self.result_saved:
            self.high_score = self.storage.save_if_higher(self.score.score)
            self.result_saved = True

    def _remaining_phase_time(self) -> float:
        return max(0.0, PHASES[self.phase_index].duration - self.phase_elapsed)

    def _rank(self) -> str:
        accuracy = self.stats.accuracy
        score = self.score.score
        if accuracy >= 94 and score >= 9000:
            return "S"
        if accuracy >= 88 and score >= 6000:
            return "A"
        if accuracy >= 75 and score >= 3000:
            return "B"
        return "C"

    def _common_mistake(self) -> str:
        mistakes = Counter(
            {
                "Wrong destination": self.stats.wrong,
                "Missed package": self.stats.missed,
                "Expired refrigerated cargo": self.stats.expired,
                "Rough fragile handling": self.stats.fragile_mishandled,
            }
        )
        label, count = mistakes.most_common(1)[0]
        return label if count > 0 else "No major mistakes"

    def draw(self) -> None:
        self._draw_warehouse()

        if self.state is GameState.TITLE:
            self._draw_title()
            return
        if self.state is GameState.RESULTS:
            self._draw_results()
            return

        self._draw_hud()
        self.belt.draw(self.screen, self.fonts)

        active_scan_progress = self.scanning_package.scan_progress if self.scanning_package else 0.0
        self.scanner.draw(self.screen, self.fonts, self.scanning_package is not None, active_scan_progress)

        hovered_container = None
        if self.held_package is not None:
            hovered_container = next(
                (container for container in self.containers if container.contains(self.mouse_position)),
                None,
            )

        for container in self.containers:
            container.draw(
                self.screen,
                self.fonts,
                self.game_time,
                highlighted=container is hovered_container and not container.is_closed(self.game_time),
            )

        ordered = sorted(self.packages, key=lambda package: package.state is PackageState.HELD)
        for package in ordered:
            package.draw(
                self.screen,
                self.fonts,
                self.game_time,
                highlight=package is self.hovered_package,
            )

        self.feedback.draw(self.screen, self.fonts, self.game_time)
        self._draw_cursor_hint()

        if self.state is GameState.PAUSED:
            self._draw_pause()

        if self.flash_alpha > 0 and self.flash_color is not None:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((*self.flash_color, round(self.flash_alpha)))
            self.screen.blit(overlay, (0, 0))

    def _draw_warehouse(self) -> None:
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, (25, 32, 44), pygame.Rect(0, 0, SCREEN_WIDTH, 492))
        for x in range(0, SCREEN_WIDTH, 128):
            pygame.draw.line(self.screen, (35, 44, 58), (x, 0), (x, 492), 2)
        for y in range(0, 492, 82):
            pygame.draw.line(self.screen, (32, 40, 53), (0, y), (SCREEN_WIDTH, y), 2)

        for x in (90, 350, 610, 870, 1130):
            pygame.draw.line(self.screen, (92, 101, 114), (x, 0), (x - 45, 72), 5)
            pygame.draw.circle(self.screen, (236, 211, 143), (x - 45, 76), 17)
            glow = pygame.Surface((90, 55), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (246, 221, 150, 38), glow.get_rect())
            self.screen.blit(glow, (x - 90, 64))

        floor = pygame.Rect(0, 492, SCREEN_WIDTH, SCREEN_HEIGHT - 492)
        pygame.draw.rect(self.screen, (17, 22, 29), floor)
        for x in range(-SCREEN_HEIGHT, SCREEN_WIDTH, 72):
            pygame.draw.line(self.screen, (33, 39, 49), (x, SCREEN_HEIGHT), (x + 220, 492), 2)

    def _draw_hud(self) -> None:
        top = pygame.Rect(22, 16, SCREEN_WIDTH - 44, 118)
        draw_panel(self.screen, top, fill=(19, 25, 35), radius=14)

        title = self.fonts["large"].render("CARGO PANIC", True, ACCENT)
        self.screen.blit(title, (42, 29))
        subtitle = self.fonts["tiny"].render("NIGHT SHIFT LOGISTICS CONTROL", True, MUTED)
        self.screen.blit(subtitle, (45, 70))

        phase = PHASES[self.phase_index]
        phase_text = self.fonts["medium"].render(phase.name.upper(), True, INK)
        self.screen.blit(phase_text, phase_text.get_rect(midtop=(SCREEN_WIDTH // 2, 28)))
        phase_subtitle = self.fonts["small"].render(phase.subtitle, True, MUTED)
        self.screen.blit(phase_subtitle, phase_subtitle.get_rect(midtop=(SCREEN_WIDTH // 2, 60)))

        bar_rect = pygame.Rect(382, 96, 516, 9)
        pygame.draw.rect(self.screen, PANEL_2, bar_rect, border_radius=5)
        progress = min(1.0, self.phase_elapsed / phase.duration)
        fill = bar_rect.copy()
        fill.width = round(bar_rect.width * progress)
        pygame.draw.rect(self.screen, ACCENT, fill, border_radius=5)

        score_text = self.fonts["medium"].render(f"SCORE  {self.score.score:06d}", True, INK)
        self.screen.blit(score_text, (922, 28))
        combo_color = ACCENT if self.score.combo >= 5 else MUTED
        combo = self.fonts["small"].render(
            f"COMBO {self.score.combo}  ×{self.score.multiplier:g}",
            True,
            combo_color,
        )
        self.screen.blit(combo, (924, 61))

        timer = self.fonts["small"].render(f"{self._remaining_phase_time():04.1f}s", True, INK)
        self.screen.blit(timer, (827, 28))

        for index in range(3):
            x = 1110 + index * 34
            active = index < self.strikes
            color = DANGER if active else (68, 73, 84)
            pygame.draw.rect(self.screen, color, pygame.Rect(x, 91, 24, 12), border_radius=4)
        label = self.fonts["tiny"].render("STRIKES", True, MUTED)
        self.screen.blit(label, (1110, 72))

        if self.emergency_until is not None:
            remaining = max(0.0, self.emergency_until - self.game_time)
            warning = self.fonts["medium"].render(f"EMERGENCY {remaining:04.1f}s", True, DANGER)
            self.screen.blit(warning, warning.get_rect(midtop=(SCREEN_WIDTH // 2, 108)))

    def _draw_cursor_hint(self) -> None:
        package = self.hovered_package
        if package is None or self.held_package is not None:
            return
        if package.tag is HandlingTag.DAMAGED and not package.label_revealed:
            text = "Hold SPACE or right mouse to scan"
            color = (92, 214, 235)
        else:
            text = "Left-drag to a matching shipping bay"
            color = INK
        rendered = self.fonts["tiny"].render(text, True, color)
        rect = rendered.get_rect(midbottom=(self.mouse_position[0], self.mouse_position[1] - 16))
        panel = rect.inflate(12, 7)
        pygame.draw.rect(self.screen, (10, 14, 21), panel, border_radius=5)
        self.screen.blit(rendered, rect)

    def _draw_title(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 12, 19, 176))
        self.screen.blit(overlay, (0, 0))

        hero = self.fonts["hero"].render("CARGO PANIC", True, ACCENT)
        self.screen.blit(hero, hero.get_rect(midtop=(SCREEN_WIDTH // 2, 72)))
        night = self.fonts["large"].render("NIGHT SHIFT", True, INK)
        self.screen.blit(night, night.get_rect(midtop=(SCREEN_WIDTH // 2, 177)))

        pitch = self.fonts["medium"].render(
            "Sort destination cargo while the warehouse system collapses around you.",
            True,
            MUTED,
        )
        self.screen.blit(pitch, pitch.get_rect(midtop=(SCREEN_WIDTH // 2, 225)))

        info = pygame.Rect(188, 285, 904, 236)
        draw_panel(self.screen, info, fill=(17, 23, 33), border=(73, 88, 112), radius=18)

        columns = (
            ("1  READ", "Use the destination name, color and symbol."),
            ("2  PRIORITIZE", "Express and refrigerated cargo cannot wait."),
            ("3  ROUTE", "Drag cargo into Northport, Eastvale or Westhaven."),
            ("4  SURVIVE", "Three strikes. Five escalating shift phases."),
        )
        for index, (heading, body) in enumerate(columns):
            row_y = info.y + 26 + index * 50
            head = self.fonts["medium"].render(heading, True, ACCENT)
            detail = self.fonts["small"].render(body, True, INK)
            self.screen.blit(head, (info.x + 28, row_y))
            self.screen.blit(detail, (info.x + 260, row_y + 3))

        scan = self.fonts["small"].render(
            "Damaged label: hover the package and hold SPACE or right mouse to scan.",
            True,
            (92, 214, 235),
        )
        self.screen.blit(scan, scan.get_rect(midtop=(SCREEN_WIDTH // 2, 540)))

        start = self.fonts["large"].render("PRESS SPACE OR CLICK TO START", True, SUCCESS)
        self.screen.blit(start, start.get_rect(midtop=(SCREEN_WIDTH // 2, 585)))
        footer = self.fonts["small"].render(
            f"High score {self.high_score:06d}   •   Mouse-first playable demo   •   Seed {self.seed}",
            True,
            MUTED,
        )
        self.screen.blit(footer, footer.get_rect(midtop=(SCREEN_WIDTH // 2, 643)))

    def _draw_pause(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 13, 205))
        self.screen.blit(overlay, (0, 0))
        pause = self.fonts["hero"].render("PAUSED", True, INK)
        self.screen.blit(pause, pause.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        hint = self.fonts["medium"].render("Press Esc or P to resume", True, MUTED)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 390)))

    def _draw_results(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 9, 15, 222))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(190, 55, 900, 610)
        draw_panel(self.screen, panel, fill=(18, 24, 34), border=(83, 99, 126), radius=20, width=3)

        complete = self.fonts["large"].render("SHIFT REPORT", True, ACCENT)
        self.screen.blit(complete, complete.get_rect(midtop=(panel.centerx, panel.y + 22)))

        rank = self._rank()
        rank_text = self.fonts["hero"].render(rank, True, SUCCESS if rank in ("S", "A") else ACCENT)
        self.screen.blit(rank_text, rank_text.get_rect(center=(panel.x + 145, panel.y + 155)))
        rank_label = self.fonts["small"].render("PERFORMANCE RANK", True, MUTED)
        self.screen.blit(rank_label, rank_label.get_rect(midtop=(panel.x + 145, panel.y + 215)))

        metrics = (
            ("Total score", f"{self.score.score:06d}"),
            ("High score", f"{self.high_score:06d}"),
            ("Correct packages", str(self.stats.correct_sorted)),
            ("Accuracy", f"{self.stats.accuracy:.1f}%"),
            ("Highest combo", str(self.score.highest_combo)),
            ("Average sort time", f"{self.stats.average_sort_time:.2f}s"),
            ("Missed / expired", f"{self.stats.missed} / {self.stats.expired}"),
            ("Most common mistake", self._common_mistake()),
        )
        start_x = panel.x + 300
        for index, (label, value) in enumerate(metrics):
            y = panel.y + 96 + index * 51
            label_render = self.fonts["small"].render(label.upper(), True, MUTED)
            value_render = self.fonts["medium"].render(value, True, INK)
            self.screen.blit(label_render, (start_x, y))
            self.screen.blit(value_render, (start_x + 290, y - 3))
            pygame.draw.line(self.screen, (48, 58, 75), (start_x, y + 30), (panel.right - 35, y + 30), 1)

        retry = self.fonts["large"].render("R / SPACE / CLICK — RETRY", True, SUCCESS)
        self.screen.blit(retry, retry.get_rect(midtop=(panel.centerx, panel.bottom - 93)))
        exit_hint = self.fonts["small"].render("Esc — return to title", True, MUTED)
        self.screen.blit(exit_hint, exit_hint.get_rect(midtop=(panel.centerx, panel.bottom - 43)))
