from __future__ import annotations

import math
import random
import time
from collections import deque
from dataclasses import replace
from pathlib import Path

import pygame

from .constants import (
    ACCENT,
    ATTRIBUTE_VALUES,
    BELT_RECT,
    BELT_Y,
    CONTRACTS,
    DANGER,
    DESTINATIONS,
    DESTINATION_COLORS,
    FOCUS,
    MAX_ACTIVE_PACKAGES,
    SCREEN_HEIGHT,
    SCREEN_SIZE,
    SCREEN_WIDTH,
    SUCCESS,
    TARGET_FPS,
    TUTORIAL_CONTRACT,
    WARNING,
    ContractSpec,
)
from .models import (
    CampaignStats,
    ContractStats,
    InputMode,
    Parcel,
    ParcelState,
    ScreenState,
    build_mapping,
    destination_for,
    make_parcel_attributes,
)
from .rendering import (
    Button,
    FontBook,
    Theme,
    draw_background,
    draw_bay,
    draw_conveyor,
    draw_destination_icon,
    draw_mark_icon,
    draw_panel,
    draw_parcel,
)
from .webcam import WebcamHandInput


class CargoPanicGame:
    def __init__(
        self,
        *,
        seed: int | None = None,
        headless: bool = False,
        webcam: bool = False,
        camera_index: int = 0,
        hand_model_path: str | None = None,
        preview_path: str | None = None,
    ) -> None:
        if headless:
            import os

            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.display.set_caption("Cargo Panic")
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode(SCREEN_SIZE, flags)
        self.clock = pygame.time.Clock()
        self.fonts = FontBook()
        self.theme = Theme()
        self.rng = random.Random(seed)
        self.running = True
        self.headless = headless
        self.preview_path = Path(preview_path) if preview_path else None

        self.state = ScreenState.MENU
        self.return_state = ScreenState.MENU
        self.input_mode = InputMode.WEBCAM if webcam else InputMode.MOUSE
        self.webcam = WebcamHandInput(camera_index, hand_model_path)
        if webcam:
            self.webcam.start()

        self.reduced_motion = False
        self.assist_mode = False
        self.sound_enabled = True  # Reserved for asset-backed audio.
        self.focus_index = 0
        self.buttons: list[Button] = []

        self.contract_index = 0
        self.contract: ContractSpec = CONTRACTS[0]
        self.mapping: dict[str, str] = {}
        self.stats = ContractStats()
        self.campaign = CampaignStats()
        self.parcels: list[Parcel] = []
        self.next_parcel_id = 1
        self.spawned = 0
        self.spawn_timer = 0.0
        self.selected_parcel: Parcel | None = None
        self.selected_via_webcam = False
        self.hovered_bay: str | None = None
        self.is_tutorial_run = False
        self.tutorial_step = 0
        self.tutorial_complete = False

        self.feedback_text = ""
        self.feedback_detail = ""
        self.feedback_tone = "neutral"
        self.feedback_timer = 0.0
        self.shake_timer = 0.0
        self.flash_timer = 0.0
        self.belt_offset = 0.0
        self.elapsed = 0.0

        self.webcam_history: deque[str] = deque(maxlen=7)
        self.webcam_stable_closed = False
        self.webcam_last_seen = 0.0
        self.webcam_tracking_suspended_at: float | None = None
        self.webcam_cursor = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.webcam_status = "Mouse input ready"
        self.webcam_gesture = "NONE"

        self._set_menu_buttons()

    # ---------- lifecycle ----------
    def run(self) -> None:
        preview_done = False
        while self.running:
            dt = min(0.05, self.clock.tick(TARGET_FPS) / 1000.0)
            self.elapsed += dt
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
            if self.preview_path and not preview_done:
                self.preview_path.parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(self.screen, str(self.preview_path))
                preview_done = True
                if self.headless:
                    self.running = False
            if self.headless and not self.preview_path and self.elapsed > 0.25:
                self.running = False
        self.webcam.stop()
        pygame.quit()

    # ---------- state setup ----------
    def _start_campaign(self) -> None:
        self.campaign = CampaignStats()
        self.contract_index = 0
        self.is_tutorial_run = False
        self._prepare_contract(CONTRACTS[0])
        self.state = ScreenState.BRIEFING
        self._set_briefing_buttons()

    def _start_tutorial(self) -> None:
        self.is_tutorial_run = True
        self.tutorial_complete = False
        self.tutorial_step = 0
        self._prepare_contract(TUTORIAL_CONTRACT)
        # Stable mapping makes the tutorial instruction deterministic.
        self.mapping = dict(zip(ATTRIBUTE_VALUES["COLOR"], DESTINATIONS, strict=True))
        self.state = ScreenState.TUTORIAL
        self._set_tutorial_buttons()

    def _prepare_contract(self, contract: ContractSpec) -> None:
        self.contract = contract
        self.mapping = build_mapping(contract.rule_type, self.rng)
        self.stats = ContractStats()
        self.parcels.clear()
        self.selected_parcel = None
        self.selected_via_webcam = False
        self.hovered_bay = None
        self.spawned = 0
        self.spawn_timer = 0.15
        self.next_parcel_id = 1
        self.feedback_timer = 0.0
        self.shake_timer = 0.0
        self.flash_timer = 0.0
        self.webcam_tracking_suspended_at = None
        self.webcam_history.clear()
        self.webcam_stable_closed = False

    def _begin_contract(self) -> None:
        self.state = ScreenState.PLAYING
        self.buttons = []
        self.spawn_timer = 0.12
        if self.is_tutorial_run:
            self._toast("TRAINING ACTIVE", "Grab the highlighted parcel.", "neutral", 2.2)
        else:
            self._toast("SHIFT STARTED", f"Sort by {self.contract.rule_type.lower()}.", "neutral", 1.8)

    def _pause(self) -> None:
        if self.state != ScreenState.PLAYING:
            return
        self.state = ScreenState.PAUSED
        self._set_pause_buttons()

    def _resume(self) -> None:
        self.state = ScreenState.PLAYING
        self.buttons = []

    def _retry_contract(self) -> None:
        contract = self.contract
        self._prepare_contract(contract)
        if self.is_tutorial_run:
            self.state = ScreenState.PLAYING
            self.buttons = []
        else:
            self.state = ScreenState.BRIEFING
            self._set_briefing_buttons()

    def _continue_after_report(self) -> None:
        if self.is_tutorial_run:
            self.state = ScreenState.MENU
            self.is_tutorial_run = False
            self._set_menu_buttons()
            return
        self.campaign.contract_results.append(replace(self.stats))
        self.contract_index += 1
        if self.contract_index >= len(CONTRACTS):
            self.state = ScreenState.CAMPAIGN_REPORT
            self._set_campaign_report_buttons()
        else:
            self._prepare_contract(CONTRACTS[self.contract_index])
            self.state = ScreenState.BRIEFING
            self._set_briefing_buttons()

    def _return_to_menu(self) -> None:
        self.state = ScreenState.MENU
        self.is_tutorial_run = False
        self.selected_parcel = None
        self._set_menu_buttons()

    def _open_settings(self) -> None:
        self.return_state = self.state
        self.state = ScreenState.SETTINGS
        self._set_settings_buttons()

    def _close_settings(self) -> None:
        self.state = self.return_state
        if self.state == ScreenState.MENU:
            self._set_menu_buttons()
        elif self.state == ScreenState.PAUSED:
            self._set_pause_buttons()
        else:
            self.buttons = []

    # ---------- buttons ----------
    def _set_menu_buttons(self) -> None:
        x = 815
        self.buttons = [
            Button(pygame.Rect(x, 300, 330, 58), "PLAY CAMPAIGN", self._start_campaign, "primary", shortcut="ENTER"),
            Button(pygame.Rect(x, 372, 330, 54), "INTERACTIVE TUTORIAL", self._start_tutorial, "secondary"),
            Button(pygame.Rect(x, 440, 158, 52), f"INPUT: {self.input_mode.value.upper()}", self._toggle_input, "secondary"),
            Button(pygame.Rect(x + 172, 440, 158, 52), "SETTINGS", self._open_settings, "secondary"),
            Button(pygame.Rect(x, 506, 330, 48), "QUIT", self._quit, "danger"),
        ]
        self.focus_index = 0

    def _set_tutorial_buttons(self) -> None:
        self.buttons = [
            Button(pygame.Rect(462, 601, 356, 58), "START PRACTICE", self._begin_contract, "primary", shortcut="ENTER"),
            Button(pygame.Rect(44, 32, 126, 44), "BACK", self._return_to_menu, "secondary"),
        ]
        self.focus_index = 0

    def _set_briefing_buttons(self) -> None:
        self.buttons = [
            Button(pygame.Rect(465, 613, 350, 58), "START CONTRACT", self._begin_contract, "primary", shortcut="ENTER"),
            Button(pygame.Rect(44, 32, 126, 44), "MENU", self._return_to_menu, "secondary"),
        ]
        self.focus_index = 0

    def _set_pause_buttons(self) -> None:
        self.buttons = [
            Button(pygame.Rect(466, 308, 348, 56), "RESUME", self._resume, "primary", shortcut="ESC"),
            Button(pygame.Rect(466, 378, 348, 50), "RESTART CONTRACT", self._retry_contract, "secondary"),
            Button(pygame.Rect(466, 442, 348, 50), "SETTINGS", self._open_settings, "secondary"),
            Button(pygame.Rect(466, 506, 348, 50), "MAIN MENU", self._return_to_menu, "danger"),
        ]
        self.focus_index = 0

    def _set_report_buttons(self) -> None:
        passed = self.stats.correct >= self.contract.required_correct or self.is_tutorial_run
        primary_label = "COMPLETE TUTORIAL" if self.is_tutorial_run else ("NEXT CONTRACT" if passed else "RETRY CONTRACT")
        primary_action = self._continue_after_report if passed else self._retry_contract
        self.buttons = [
            Button(pygame.Rect(462, 601, 356, 58), primary_label, primary_action, "primary", shortcut="ENTER"),
            Button(pygame.Rect(44, 32, 126, 44), "MENU", self._return_to_menu, "secondary"),
        ]
        if passed and not self.is_tutorial_run:
            self.buttons.insert(1, Button(pygame.Rect(862, 610, 250, 44), "RETRY FOR SCORE", self._retry_contract, "secondary"))
        self.focus_index = 0

    def _set_campaign_report_buttons(self) -> None:
        self.buttons = [
            Button(pygame.Rect(462, 611, 356, 58), "PLAY AGAIN", self._start_campaign, "primary", shortcut="ENTER"),
            Button(pygame.Rect(44, 32, 126, 44), "MENU", self._return_to_menu, "secondary"),
        ]
        self.focus_index = 0

    def _set_settings_buttons(self) -> None:
        self.buttons = [
            Button(pygame.Rect(450, 270, 380, 52), f"HIGH CONTRAST: {'ON' if self.theme.high_contrast else 'OFF'}", self._toggle_contrast, "secondary"),
            Button(pygame.Rect(450, 336, 380, 52), f"REDUCED MOTION: {'ON' if self.reduced_motion else 'OFF'}", self._toggle_reduced_motion, "secondary"),
            Button(pygame.Rect(450, 402, 380, 52), f"ROUTING ASSIST: {'ON' if self.assist_mode else 'OFF'}", self._toggle_assist, "secondary"),
            Button(pygame.Rect(450, 484, 380, 56), "DONE", self._close_settings, "primary", shortcut="ESC"),
        ]
        self.focus_index = 0

    def _toggle_input(self) -> None:
        if self.input_mode == InputMode.MOUSE:
            self.input_mode = InputMode.WEBCAM
            self.webcam_history.clear()
            self.webcam_stable_closed = False
            self.webcam.start()
            self.webcam_status = "Starting camera… mouse fallback remains active"
        else:
            self.input_mode = InputMode.MOUSE
            self.webcam.stop()
            self.webcam_history.clear()
            self.webcam_stable_closed = False
            self.webcam_status = "Mouse input ready"
        if self.state == ScreenState.MENU:
            self._set_menu_buttons()

    def _toggle_contrast(self) -> None:
        self.theme.high_contrast = not self.theme.high_contrast
        self._set_settings_buttons()

    def _toggle_reduced_motion(self) -> None:
        self.reduced_motion = not self.reduced_motion
        self._set_settings_buttons()

    def _toggle_assist(self) -> None:
        self.assist_mode = not self.assist_mode
        self._set_settings_buttons()

    def _quit(self) -> None:
        self.running = False

    # ---------- input ----------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._activate_button_at(event.pos):
                    self._handle_pointer_down(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._handle_pointer_up(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_pointer_move(event.pos)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_TAB and self.buttons:
            self.focus_index = (self.focus_index + 1) % len(self.buttons)
            return
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.buttons:
                self.buttons[self.focus_index % len(self.buttons)].action()
            return
        if key == pygame.K_ESCAPE:
            if self.state == ScreenState.PLAYING:
                self._pause()
            elif self.state == ScreenState.PAUSED:
                self._resume()
            elif self.state == ScreenState.SETTINGS:
                self._close_settings()
            elif self.state in (ScreenState.BRIEFING, ScreenState.TUTORIAL, ScreenState.CONTRACT_REPORT, ScreenState.CAMPAIGN_REPORT):
                self._return_to_menu()
            else:
                self.running = False
            return
        if key == pygame.K_p:
            if self.state == ScreenState.PLAYING:
                self._pause()
            elif self.state == ScreenState.PAUSED:
                self._resume()
        elif key == pygame.K_r and self.state in (ScreenState.PLAYING, ScreenState.CONTRACT_REPORT):
            self._retry_contract()

    def _activate_button_at(self, point: tuple[int, int]) -> bool:
        for index, button in enumerate(self.buttons):
            if button.activate_at(point):
                self.focus_index = index
                return True
        return False

    def _handle_pointer_down(self, point: tuple[int, int]) -> None:
        if self.state != ScreenState.PLAYING:
            return
        pause_rect = pygame.Rect(1192, 18, 62, 42)
        if pause_rect.collidepoint(point):
            self._pause()
            return
        self._try_grab(point, source="mouse")

    def _try_grab(self, point: tuple[int, int], *, source: str = "mouse") -> None:
        if self.selected_parcel is not None:
            return
        candidates = [
            parcel
            for parcel in self.parcels
            if parcel.state in (ParcelState.ON_BELT, ParcelState.RETURNING) and parcel.contains(point)
        ]
        if not candidates:
            return
        parcel = candidates[-1]
        parcel.begin_drag(point)
        self.selected_parcel = parcel
        self.selected_via_webcam = source == "webcam"
        if self.is_tutorial_run and self.tutorial_step == 0:
            self.tutorial_step = 1
            self._toast("GRAB CONFIRMED", "Carry the parcel to its matching bay.", "success", 2.0)

    def _handle_pointer_move(self, point: tuple[int, int]) -> None:
        if self.state != ScreenState.PLAYING or self.selected_parcel is None:
            return
        self.selected_parcel.drag_to(point, SCREEN_SIZE)
        self.hovered_bay = self._bay_at(point)

    def _handle_pointer_up(self, point: tuple[int, int]) -> None:
        if self.state != ScreenState.PLAYING or self.selected_parcel is None:
            return
        self._release_selected(point)

    def _release_selected(self, point: tuple[int, int]) -> None:
        parcel = self.selected_parcel
        if parcel is None:
            return
        bay = self._bay_at(point)
        if bay is None:
            parcel.reattach(BELT_Y)
            self._toast("INVALID RELEASE", "Parcel returning to the conveyor.", "warning", 1.6)
        else:
            correct_destination = destination_for(parcel.attributes, self.contract.rule_type, self.mapping)
            if bay == correct_destination:
                parcel.state = ParcelState.SORTED
                points = self.stats.record_correct()
                self.flash_timer = 0.22
                self._toast(
                    f"SORTED +{points}",
                    f"{parcel.active_value(self.contract.rule_type)} → {correct_destination}",
                    "success",
                    1.45,
                )
                if self.is_tutorial_run:
                    self.tutorial_step = 2
            else:
                parcel.state = ParcelState.SORTED
                self.stats.record_wrong()
                self.shake_timer = 0.30
                self._toast(
                    "WRONG BAY",
                    f"{parcel.active_value(self.contract.rule_type)} parcels go to {correct_destination}.",
                    "danger",
                    2.25,
                )
        self.selected_parcel = None
        self.selected_via_webcam = False
        self.hovered_bay = None

    def _bay_at(self, point: tuple[int, int]) -> str | None:
        for name, rect in self._bay_rects().items():
            if rect.collidepoint(point):
                return name
        return None

    # ---------- update ----------
    def _update(self, dt: float) -> None:
        if self.feedback_timer > 0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)

        if self.state == ScreenState.PLAYING:
            self._update_webcam(dt)
            self._update_gameplay(dt)
        elif self.input_mode == InputMode.WEBCAM:
            snapshot = self.webcam.snapshot()
            self.webcam_status = snapshot.message

    def _update_gameplay(self, dt: float) -> None:
        motion_dt = 0.0 if self.reduced_motion else dt
        self.belt_offset += self.contract.belt_speed * motion_dt
        self.spawn_timer -= dt
        active_count = sum(
            parcel.state not in (ParcelState.SORTED, ParcelState.MISSED)
            for parcel in self.parcels
        )
        if (
            self.spawned < self.contract.package_count
            and self.spawn_timer <= 0.0
            and active_count < MAX_ACTIVE_PACKAGES
        ):
            self._spawn_parcel()
            self.spawn_timer = self.contract.spawn_interval

        for parcel in self.parcels:
            if parcel is self.selected_parcel:
                continue
            if parcel.update(dt, SCREEN_WIDTH):
                self.stats.record_missed()
                self.shake_timer = 0.25
                self._toast(
                    "PARCEL MISSED",
                    "It exited the conveyor before being sorted.",
                    "danger",
                    1.9,
                )

        self.parcels = [
            parcel
            for parcel in self.parcels
            if parcel.state not in (ParcelState.SORTED, ParcelState.MISSED)
        ]
        if self.stats.resolved >= self.contract.package_count and not self.parcels:
            self.state = ScreenState.CONTRACT_REPORT
            self._set_report_buttons()

    def _spawn_parcel(self) -> None:
        attrs = make_parcel_attributes(self.rng)
        y = BELT_Y - 44 + self.rng.uniform(-8, 8)
        parcel = Parcel(
            parcel_id=self.next_parcel_id,
            attributes=attrs,
            x=-128.0,
            y=y,
            speed=self.contract.belt_speed,
        )
        self.next_parcel_id += 1
        self.spawned += 1
        self.parcels.append(parcel)

    def _update_webcam(self, dt: float) -> None:
        if self.input_mode != InputMode.WEBCAM:
            return
        snapshot = self.webcam.snapshot()
        self.webcam_status = snapshot.message
        self.webcam_gesture = snapshot.gesture
        now = time.monotonic()
        if snapshot.detected:
            self.webcam_last_seen = now
            target_x = int(snapshot.x * SCREEN_WIDTH)
            target_y = int(snapshot.y * SCREEN_HEIGHT)
            smoothing = 1.0 - math.exp(-max(dt, 0.001) * 14.0)
            self.webcam_cursor = (
                int(self.webcam_cursor[0] + (target_x - self.webcam_cursor[0]) * smoothing),
                int(self.webcam_cursor[1] + (target_y - self.webcam_cursor[1]) * smoothing),
            )
            self.webcam_history.append(snapshot.gesture)
            closed_votes = sum(gesture == "CLOSED" for gesture in self.webcam_history)
            open_votes = sum(gesture == "OPEN" for gesture in self.webcam_history)
            stable_closed = closed_votes >= 3
            stable_open = open_votes >= 3

            if self.webcam_tracking_suspended_at is not None and self.selected_parcel is not None:
                self.selected_parcel.resume_tracking()
                self.webcam_tracking_suspended_at = None
                self._toast("TRACKING RESTORED", "Parcel control resumed.", "success", 1.2)

            if stable_closed and not self.webcam_stable_closed:
                self.webcam_stable_closed = True
                self._try_grab(self.webcam_cursor, source="webcam")
            elif stable_open and self.webcam_stable_closed:
                self.webcam_stable_closed = False
                if self.selected_parcel is not None and self.selected_via_webcam:
                    self._release_selected(self.webcam_cursor)

            if (
                self.selected_parcel is not None
                and self.selected_via_webcam
                and self.webcam_stable_closed
            ):
                self.selected_parcel.drag_to(self.webcam_cursor, SCREEN_SIZE)
                self.hovered_bay = self._bay_at(self.webcam_cursor)
        else:
            self.webcam_history.clear()
            lost_for = now - self.webcam_last_seen
            if self.selected_parcel is None and lost_for > 0.35:
                self.webcam_stable_closed = False
            if self.selected_parcel is not None and self.selected_via_webcam and lost_for > 0.65:
                if self.webcam_tracking_suspended_at is None:
                    self.webcam_tracking_suspended_at = now
                    self.selected_parcel.suspend_tracking()
                    self._toast("TRACKING LOST", "Parcel position preserved. Show your hand again.", "warning", 2.0)
                elif now - self.webcam_tracking_suspended_at > 2.2:
                    self.selected_parcel.reattach(BELT_Y)
                    self.selected_parcel = None
                    self.selected_via_webcam = False
                    self.hovered_bay = None
                    self.webcam_tracking_suspended_at = None
                    self.webcam_stable_closed = False
                    self._toast("MOUSE FALLBACK READY", "Parcel returned to the conveyor.", "warning", 2.0)

    def _toast(self, title: str, detail: str, tone: str, duration: float) -> None:
        self.feedback_text = title
        self.feedback_detail = detail
        self.feedback_tone = tone
        self.feedback_timer = duration

    # ---------- draw ----------
    def _draw(self) -> None:
        draw_background(self.screen, self.theme, self.elapsed)
        if self.state == ScreenState.MENU:
            self._draw_menu()
        elif self.state == ScreenState.TUTORIAL:
            self._draw_tutorial()
        elif self.state == ScreenState.BRIEFING:
            self._draw_briefing()
        elif self.state == ScreenState.PLAYING:
            self._draw_gameplay()
        elif self.state == ScreenState.PAUSED:
            self._draw_gameplay()
            self._draw_pause_overlay()
        elif self.state == ScreenState.CONTRACT_REPORT:
            self._draw_report()
        elif self.state == ScreenState.CAMPAIGN_REPORT:
            self._draw_campaign_report()
        elif self.state == ScreenState.SETTINGS:
            self._draw_settings()

        mouse = pygame.mouse.get_pos()
        for index, button in enumerate(self.buttons):
            button.draw(self.screen, self.fonts, self.theme, mouse, focused=index == self.focus_index)

    def _draw_brand(self, x: int, y: int, compact: bool = False) -> None:
        size = 42 if compact else 64
        title = self.fonts.get(size, True).render("CARGO", True, self.theme.ink)
        panic = self.fonts.get(size, True).render("PANIC", True, ACCENT)
        self.screen.blit(title, (x, y))
        self.screen.blit(panic, (x + title.get_width() + 14, y))
        subtitle = self.fonts.get(15 if compact else 18, True).render("NIGHT SHIFT ROUTING", True, self.theme.muted)
        self.screen.blit(subtitle, (x + 3, y + size + 4))

    def _draw_menu(self) -> None:
        self._draw_brand(92, 102)
        headline = self.fonts.get(30, True).render("SORT FAST. ROUTE CLEAN.", True, self.theme.ink)
        self.screen.blit(headline, (96, 222))
        body = [
            "Four contracts. Four changing rules.",
            "Read the parcel, grab it, and deliver it",
            "before the conveyor carries it away.",
        ]
        for index, line in enumerate(body):
            text = self.fonts.get(19).render(line, True, self.theme.muted)
            self.screen.blit(text, (98, 274 + index * 30))

        # Hero illustration.
        hero = pygame.Rect(96, 397, 602, 198)
        draw_panel(self.screen, hero, self.theme, fill=(19, 26, 39), border=(64, 82, 113))
        belt = pygame.Rect(hero.left + 18, hero.top + 66, hero.width - 36, 96)
        draw_conveyor(self.screen, belt, self.elapsed * 48)
        demo_attrs = make_parcel_attributes(random.Random(17))
        demo = Parcel(17, demo_attrs, hero.left + 238, hero.top + 71, 0)
        draw_parcel(self.screen, demo, "MARK", self.fonts, self.theme, selected=True)
        for i, name in enumerate(DESTINATIONS[:3]):
            draw_destination_icon(self.screen, name, (hero.left + 85 + i * 210, hero.top + 36), DESTINATION_COLORS[name], 0.52)

        panel = pygame.Rect(762, 152, 430, 454)
        draw_panel(self.screen, panel, self.theme, fill=self.theme.panel_2, border=(82, 100, 134), radius=20)
        label = self.fonts.get(15, True).render("SHIFT CONTROL", True, ACCENT)
        self.screen.blit(label, (panel.left + 52, panel.top + 54))
        title = self.fonts.get(30, True).render("READY FOR INTAKE", True, self.theme.ink)
        self.screen.blit(title, (panel.left + 50, panel.top + 84))
        mode = self.fonts.get(15).render(f"Current input: {self.input_mode.value}", True, self.theme.muted)
        self.screen.blit(mode, (panel.left + 52, panel.top + 132))
        self._draw_status_chip(panel.left + 52, panel.top + 166, self.webcam_status if self.input_mode == InputMode.WEBCAM else "Mouse drag-and-drop ready", "neutral")
        foot = self.fonts.get(13).render("TAB selects controls · ENTER activates", True, self.theme.dim)
        self.screen.blit(foot, foot.get_rect(center=(panel.centerx, panel.bottom - 28)))

    def _draw_tutorial(self) -> None:
        self._draw_brand(455, 52, compact=True)
        title = self.fonts.get(30, True).render("HOW A SORT WORKS", True, self.theme.ink)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 160)))
        steps = [
            ("1", "READ", "The active rule appears first.\nOnly that parcel attribute matters."),
            ("2", "GRAB", "Hold the mouse button over a parcel.\nWebcam: close your hand."),
            ("3", "DELIVER", "Carry it to the mapped bay and release.\nWebcam: open your hand."),
        ]
        for index, (number, heading, description) in enumerate(steps):
            rect = pygame.Rect(84 + index * 382, 214, 350, 260)
            draw_panel(self.screen, rect, self.theme, fill=self.theme.panel_2, radius=18)
            pygame.draw.circle(self.screen, ACCENT, (rect.left + 52, rect.top + 52), 25)
            number_surface = self.fonts.get(22, True).render(number, True, (22, 25, 31))
            self.screen.blit(number_surface, number_surface.get_rect(center=(rect.left + 52, rect.top + 52)))
            heading_surface = self.fonts.get(24, True).render(heading, True, self.theme.ink)
            self.screen.blit(heading_surface, (rect.left + 88, rect.top + 37))
            for line_index, line in enumerate(description.splitlines()):
                text = self.fonts.get(16).render(line, True, self.theme.muted)
                self.screen.blit(text, (rect.left + 28, rect.top + 104 + line_index * 25))
            if index == 0:
                chip = pygame.Rect(rect.left + 48, rect.top + 180, 254, 54)
                pygame.draw.rect(self.screen, (246, 242, 226), chip, border_radius=9)
                pygame.draw.rect(self.screen, ACCENT, chip, 3, border_radius=9)
                label = self.fonts.get(18, True).render("SORT BY COLOR", True, (25, 29, 37))
                self.screen.blit(label, label.get_rect(center=chip.center))
            elif index == 1:
                pygame.draw.circle(self.screen, FOCUS, (rect.centerx, rect.top + 202), 31, 4)
                pygame.draw.circle(self.screen, self.theme.ink, (rect.centerx, rect.top + 202), 9)
            else:
                bay = pygame.Rect(rect.centerx - 72, rect.top + 170, 144, 66)
                pygame.draw.rect(self.screen, (25, 57, 46), bay, border_radius=10)
                pygame.draw.rect(self.screen, SUCCESS, bay, 4, border_radius=10)
                okay = self.fonts.get(16, True).render("VALID DROP", True, SUCCESS)
                self.screen.blit(okay, okay.get_rect(center=bay.center))

    def _draw_briefing(self) -> None:
        self._draw_brand(475, 42, compact=True)
        contract_number = self.contract_index + 1
        kicker = self.fonts.get(15, True).render(f"CONTRACT {contract_number} OF {len(CONTRACTS)}", True, ACCENT)
        self.screen.blit(kicker, kicker.get_rect(center=(SCREEN_WIDTH // 2, 142)))
        title = self.fonts.get(38, True).render(self.contract.title, True, self.theme.ink)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 184)))
        description = self.fonts.get(18).render(self.contract.description, True, self.theme.muted)
        self.screen.blit(description, description.get_rect(center=(SCREEN_WIDTH // 2, 229)))

        rule_rect = pygame.Rect(92, 280, 330, 265)
        draw_panel(self.screen, rule_rect, self.theme, fill=self.theme.panel_2, radius=18)
        label = self.fonts.get(13, True).render("ACTIVE RULE", True, self.theme.muted)
        self.screen.blit(label, (rule_rect.left + 30, rule_rect.top + 26))
        rule = self.fonts.get(34, True).render(f"SORT BY {self.contract.rule_type}", True, ACCENT)
        self.screen.blit(rule, (rule_rect.left + 30, rule_rect.top + 53))
        details = [
            ("Batch", str(self.contract.package_count)),
            ("Required", f"{self.contract.required_correct} correct"),
            ("Conveyor", f"{int(self.contract.belt_speed)} px/s"),
        ]
        for index, (key, value) in enumerate(details):
            y = rule_rect.top + 126 + index * 38
            key_surface = self.fonts.get(15).render(key, True, self.theme.muted)
            value_surface = self.fonts.get(16, True).render(value, True, self.theme.ink)
            self.screen.blit(key_surface, (rule_rect.left + 30, y))
            self.screen.blit(value_surface, value_surface.get_rect(topright=(rule_rect.right - 30, y)))

        mapping_rect = pygame.Rect(454, 280, 734, 265)
        draw_panel(self.screen, mapping_rect, self.theme, fill=self.theme.panel_2, radius=18)
        label = self.fonts.get(13, True).render("ROUTING MAP", True, self.theme.muted)
        self.screen.blit(label, (mapping_rect.left + 30, mapping_rect.top + 26))
        for index, value in enumerate(ATTRIBUTE_VALUES[self.contract.rule_type]):
            row = pygame.Rect(mapping_rect.left + 28, mapping_rect.top + 58 + index * 45, mapping_rect.width - 56, 36)
            pygame.draw.rect(self.screen, self.theme.panel, row, border_radius=8)
            self._draw_attribute_symbol(value, self.contract.rule_type, (row.left + 23, row.centery), 0.72)
            value_surface = self.fonts.get(16, True).render(self._value_label(value), True, self.theme.ink)
            self.screen.blit(value_surface, (row.left + 48, row.top + 8))
            arrow = self.fonts.get(18, True).render("→", True, self.theme.dim)
            self.screen.blit(arrow, arrow.get_rect(center=(row.centerx, row.centery)))
            destination = self.mapping[value]
            dest_surface = self.fonts.get(16, True).render(destination, True, DESTINATION_COLORS[destination])
            self.screen.blit(dest_surface, dest_surface.get_rect(midright=(row.right - 18, row.centery)))

    def _draw_gameplay(self) -> None:
        shake_x = 0
        if self.shake_timer > 0 and not self.reduced_motion:
            shake_x = int(math.sin(self.elapsed * 70) * 5)
        canvas = pygame.Surface(SCREEN_SIZE)
        draw_background(canvas, self.theme, self.elapsed)
        original = self.screen
        self.screen = canvas

        self._draw_hud()
        belt_rect = pygame.Rect(BELT_RECT)
        draw_conveyor(self.screen, belt_rect, self.belt_offset)

        # Bays and drop previews.
        correct_for_selected = None
        if self.selected_parcel is not None:
            correct_for_selected = destination_for(self.selected_parcel.attributes, self.contract.rule_type, self.mapping)
        for name, rect in self._bay_rects().items():
            hovered = name == self.hovered_bay
            valid = None
            if hovered and correct_for_selected is not None:
                valid = name == correct_for_selected
            guided = bool(
                self.selected_parcel is not None
                and name == correct_for_selected
                and (self.assist_mode or self.is_tutorial_run)
            )
            draw_bay(
                self.screen,
                rect,
                name,
                self.fonts,
                self.theme,
                hovered=hovered,
                valid=valid,
                guided=guided,
                pulse=self.elapsed,
            )

        for parcel in self.parcels:
            draw_parcel(
                self.screen,
                parcel,
                self.contract.rule_type,
                self.fonts,
                self.theme,
                selected=parcel is self.selected_parcel,
                suspended=parcel.state == ParcelState.TRACKING_SUSPENDED,
            )

        if self.is_tutorial_run:
            self._draw_tutorial_prompt()
        self._draw_feedback()
        self._draw_input_status()
        self._draw_pause_button()
        if self.input_mode == InputMode.WEBCAM:
            self._draw_webcam_cursor()

        self.screen = original
        self.screen.blit(canvas, (shake_x, 0))
        if self.flash_timer > 0:
            overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
            overlay.fill((93, 228, 147, int(42 * self.flash_timer / 0.22)))
            self.screen.blit(overlay, (0, 0))

    def _draw_hud(self) -> None:
        header = pygame.Rect(20, 15, 1240, 244)
        draw_panel(self.screen, header, self.theme, fill=(18, 24, 36), border=(58, 74, 102), radius=16)

        rule_rect = pygame.Rect(38, 34, 260, 96)
        draw_panel(self.screen, rule_rect, self.theme, fill=self.theme.panel_2, border=ACCENT, radius=12, shadow=False)
        label = self.fonts.get(12, True).render("ACTIVE RULE", True, self.theme.muted)
        self.screen.blit(label, (rule_rect.left + 16, rule_rect.top + 12))
        rule = self.fonts.get(27, True).render(f"SORT BY {self.contract.rule_type}", True, ACCENT)
        self.screen.blit(rule, (rule_rect.left + 16, rule_rect.top + 34))
        sub = self.fonts.get(13).render(self.contract.title, True, self.theme.muted)
        self.screen.blit(sub, (rule_rect.left + 16, rule_rect.bottom - 23))

        # Mapping is the second visual priority.
        map_rect = pygame.Rect(316, 34, 642, 96)
        draw_panel(self.screen, map_rect, self.theme, fill=self.theme.panel_2, radius=12, shadow=False)
        cell_width = map_rect.width // 4
        for index, value in enumerate(ATTRIBUTE_VALUES[self.contract.rule_type]):
            cell = pygame.Rect(map_rect.left + index * cell_width, map_rect.top, cell_width, map_rect.height)
            if index:
                pygame.draw.line(self.screen, self.theme.border, (cell.left, cell.top + 14), (cell.left, cell.bottom - 14), 1)
            self._draw_attribute_symbol(value, self.contract.rule_type, (cell.centerx, cell.top + 28), 0.62)
            value_surface = self.fonts.get(12, True).render(self._value_label(value), True, self.theme.ink)
            self.screen.blit(value_surface, value_surface.get_rect(center=(cell.centerx, cell.top + 52)))
            dest = self.mapping[value]
            destination_surface = self.fonts.get(12, True).render(dest, True, DESTINATION_COLORS[dest])
            self.screen.blit(destination_surface, destination_surface.get_rect(center=(cell.centerx, cell.top + 75)))

        stats_rect = pygame.Rect(976, 34, 266, 96)
        draw_panel(self.screen, stats_rect, self.theme, fill=self.theme.panel_2, radius=12, shadow=False)
        score_label = self.fonts.get(12, True).render("CONTRACT SCORE", True, self.theme.muted)
        score = self.fonts.get(30, True).render(f"{self.stats.score:,}", True, self.theme.ink)
        self.screen.blit(score_label, (stats_rect.left + 18, stats_rect.top + 12))
        self.screen.blit(score, (stats_rect.left + 18, stats_rect.top + 31))
        combo = self.fonts.get(15, True).render(f"COMBO ×{self.stats.combo}", True, ACCENT if self.stats.combo else self.theme.dim)
        self.screen.blit(combo, combo.get_rect(midright=(stats_rect.right - 17, stats_rect.centery + 12)))

        progress_rect = pygame.Rect(38, 148, 1204, 88)
        draw_panel(self.screen, progress_rect, self.theme, fill=self.theme.panel_2, radius=12, shadow=False)
        resolved = self.stats.resolved
        progress = min(1.0, resolved / max(1, self.contract.package_count))
        bar = pygame.Rect(progress_rect.left + 18, progress_rect.top + 35, 730, 18)
        pygame.draw.rect(self.screen, (11, 15, 23), bar, border_radius=9)
        fill = bar.copy()
        fill.width = int(bar.width * progress)
        pygame.draw.rect(self.screen, FOCUS, fill, border_radius=9)
        batch = self.fonts.get(13, True).render(f"BATCH {resolved}/{self.contract.package_count}", True, self.theme.ink)
        self.screen.blit(batch, (bar.left, progress_rect.top + 13))
        required = self.fonts.get(13).render(f"Pass: {self.contract.required_correct} correct", True, self.theme.muted)
        self.screen.blit(required, required.get_rect(topright=(bar.right, progress_rect.top + 13)))

        metrics = [
            ("CORRECT", self.stats.correct, SUCCESS),
            ("WRONG", self.stats.wrong, DANGER),
            ("MISSED", self.stats.missed, WARNING),
        ]
        for index, (name, value, color) in enumerate(metrics):
            x = progress_rect.left + 790 + index * 127
            label = self.fonts.get(11, True).render(name, True, self.theme.muted)
            number = self.fonts.get(25, True).render(str(value), True, color)
            self.screen.blit(label, label.get_rect(center=(x + 45, progress_rect.top + 24)))
            self.screen.blit(number, number.get_rect(center=(x + 45, progress_rect.top + 55)))

    def _draw_feedback(self) -> None:
        if self.feedback_timer <= 0:
            return
        tone_colors = {
            "success": SUCCESS,
            "danger": DANGER,
            "warning": WARNING,
            "neutral": FOCUS,
        }
        color = tone_colors.get(self.feedback_tone, FOCUS)
        rect = pygame.Rect(394, 264, 492, 62)
        draw_panel(self.screen, rect, self.theme, fill=(20, 27, 39), border=color, radius=12, width=3)
        title = self.fonts.get(17, True).render(self.feedback_text, True, color)
        detail = self.fonts.get(14).render(self.feedback_detail, True, self.theme.ink)
        self.screen.blit(title, (rect.left + 18, rect.top + 10))
        self.screen.blit(detail, (rect.left + 18, rect.top + 34))

    def _draw_input_status(self) -> None:
        rect = pygame.Rect(20, 678, 420, 28)
        pygame.draw.rect(self.screen, (12, 17, 26), rect, border_radius=8)
        mode_color = FOCUS if self.input_mode == InputMode.WEBCAM else self.theme.muted
        mode = self.fonts.get(12, True).render(self.input_mode.value.upper(), True, mode_color)
        status = self.fonts.get(12).render(self.webcam_status if self.input_mode == InputMode.WEBCAM else "Hold left mouse to grab · release over a bay", True, self.theme.muted)
        self.screen.blit(mode, (rect.left + 10, rect.top + 6))
        self.screen.blit(status, (rect.left + 78, rect.top + 6))

    def _draw_pause_button(self) -> None:
        rect = pygame.Rect(1192, 18, 62, 42)
        pygame.draw.rect(self.screen, self.theme.panel_2, rect, border_radius=10)
        pygame.draw.rect(self.screen, self.theme.border, rect, 2, border_radius=10)
        pygame.draw.rect(self.screen, self.theme.ink, pygame.Rect(rect.left + 22, rect.top + 12, 5, 18), border_radius=2)
        pygame.draw.rect(self.screen, self.theme.ink, pygame.Rect(rect.left + 35, rect.top + 12, 5, 18), border_radius=2)

    def _draw_webcam_cursor(self) -> None:
        x, y = self.webcam_cursor
        color = ACCENT if self.webcam_stable_closed else FOCUS
        radius = 25 if self.webcam_stable_closed else 19
        pygame.draw.circle(self.screen, color, (x, y), radius, 4)
        pygame.draw.circle(self.screen, self.theme.ink, (x, y), 5)
        label = "GRAB" if self.webcam_stable_closed else "OPEN"
        text = self.fonts.get(11, True).render(label, True, color)
        self.screen.blit(text, text.get_rect(midtop=(x, y + radius + 4)))

    def _draw_tutorial_prompt(self) -> None:
        messages = [
            ("STEP 1", "Grab any parcel on the conveyor."),
            ("STEP 2", "Follow the green bay and release."),
            ("STEP 3", "Correct. Finish the remaining practice parcels."),
        ]
        step = min(self.tutorial_step, 2)
        kicker, instruction = messages[step]
        rect = pygame.Rect(872, 678, 388, 28)
        pygame.draw.rect(self.screen, (21, 35, 43), rect, border_radius=8)
        pygame.draw.rect(self.screen, SUCCESS, rect, 1, border_radius=8)
        first = self.fonts.get(11, True).render(kicker, True, SUCCESS)
        second = self.fonts.get(12).render(instruction, True, self.theme.ink)
        self.screen.blit(first, (rect.left + 10, rect.top + 7))
        self.screen.blit(second, (rect.left + 72, rect.top + 6))

    def _draw_pause_overlay(self) -> None:
        veil = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        veil.fill((4, 7, 12, 205))
        self.screen.blit(veil, (0, 0))
        rect = pygame.Rect(420, 188, 440, 406)
        draw_panel(self.screen, rect, self.theme, fill=(22, 29, 43), border=FOCUS, radius=20, width=2)
        title = self.fonts.get(38, True).render("SHIFT PAUSED", True, self.theme.ink)
        self.screen.blit(title, title.get_rect(center=(rect.centerx, rect.top + 66)))
        sub = self.fonts.get(16).render("The conveyor and parcel timers are stopped.", True, self.theme.muted)
        self.screen.blit(sub, sub.get_rect(center=(rect.centerx, rect.top + 107)))

    def _draw_report(self) -> None:
        passed = self.stats.correct >= self.contract.required_correct or self.is_tutorial_run
        color = SUCCESS if passed else DANGER
        status = "TRAINING COMPLETE" if self.is_tutorial_run else ("CONTRACT PASSED" if passed else "CONTRACT FAILED")
        kicker = self.fonts.get(15, True).render(status, True, color)
        self.screen.blit(kicker, kicker.get_rect(center=(SCREEN_WIDTH // 2, 96)))
        title = self.fonts.get(40, True).render(self.contract.title, True, self.theme.ink)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 141)))
        detail = self.fonts.get(17).render(
            "Every result includes the reason, so the next decision is clearer.",
            True,
            self.theme.muted,
        )
        self.screen.blit(detail, detail.get_rect(center=(SCREEN_WIDTH // 2, 184)))

        metrics = [
            ("CORRECT", self.stats.correct, SUCCESS),
            ("WRONG", self.stats.wrong, DANGER),
            ("MISSED", self.stats.missed, WARNING),
            ("BEST COMBO", self.stats.best_combo, ACCENT),
        ]
        for index, (label, value, tone) in enumerate(metrics):
            rect = pygame.Rect(84 + index * 286, 233, 254, 128)
            draw_panel(self.screen, rect, self.theme, fill=self.theme.panel_2, border=tone, radius=16)
            label_surface = self.fonts.get(13, True).render(label, True, self.theme.muted)
            value_surface = self.fonts.get(42, True).render(str(value), True, tone)
            self.screen.blit(label_surface, label_surface.get_rect(center=(rect.centerx, rect.top + 32)))
            self.screen.blit(value_surface, value_surface.get_rect(center=(rect.centerx, rect.top + 82)))

        summary = pygame.Rect(238, 398, 804, 158)
        draw_panel(self.screen, summary, self.theme, fill=self.theme.panel_2, radius=18)
        accuracy = self.stats.accuracy * 100
        score = self.fonts.get(30, True).render(f"{self.stats.score:,} POINTS", True, self.theme.ink)
        self.screen.blit(score, (summary.left + 34, summary.top + 26))
        accuracy_surface = self.fonts.get(20, True).render(f"{accuracy:.0f}% quality", True, color)
        self.screen.blit(accuracy_surface, (summary.left + 36, summary.top + 75))
        requirement = f"Required: {self.contract.required_correct} correct · Delivered: {self.stats.correct}"
        requirement_surface = self.fonts.get(15).render(requirement, True, self.theme.muted)
        self.screen.blit(requirement_surface, (summary.left + 36, summary.top + 111))
        verdict = "Ready for the next routing rule." if passed else "Review the routing map and retry this contract."
        verdict_surface = self.fonts.get(19, True).render(verdict, True, color)
        self.screen.blit(verdict_surface, verdict_surface.get_rect(midright=(summary.right - 38, summary.centery)))

    def _draw_campaign_report(self) -> None:
        grade = self.campaign.grade
        grade_color = SUCCESS if grade in ("S", "A") else ACCENT if grade in ("B", "C") else DANGER
        kicker = self.fonts.get(15, True).render("CAMPAIGN COMPLETE", True, grade_color)
        self.screen.blit(kicker, kicker.get_rect(center=(SCREEN_WIDTH // 2, 80)))
        title = self.fonts.get(40, True).render("NIGHT SHIFT REPORT", True, self.theme.ink)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 126)))

        grade_rect = pygame.Rect(92, 190, 330, 354)
        draw_panel(self.screen, grade_rect, self.theme, fill=self.theme.panel_2, border=grade_color, radius=22, width=3)
        label = self.fonts.get(14, True).render("FINAL GRADE", True, self.theme.muted)
        grade_surface = self.fonts.get(126, True).render(grade, True, grade_color)
        self.screen.blit(label, label.get_rect(center=(grade_rect.centerx, grade_rect.top + 45)))
        self.screen.blit(grade_surface, grade_surface.get_rect(center=(grade_rect.centerx, grade_rect.top + 154)))
        score = self.fonts.get(30, True).render(f"{self.campaign.total_score:,}", True, self.theme.ink)
        self.screen.blit(score, score.get_rect(center=(grade_rect.centerx, grade_rect.top + 268)))
        score_label = self.fonts.get(13, True).render("TOTAL SCORE", True, self.theme.muted)
        self.screen.blit(score_label, score_label.get_rect(center=(grade_rect.centerx, grade_rect.top + 304)))

        report = pygame.Rect(458, 190, 730, 354)
        draw_panel(self.screen, report, self.theme, fill=self.theme.panel_2, radius=22)
        metrics = [
            ("Overall quality", f"{self.campaign.accuracy * 100:.0f}%", SUCCESS),
            ("Correct parcels", str(self.campaign.correct), SUCCESS),
            ("Wrong bays", str(self.campaign.wrong), DANGER),
            ("Missed parcels", str(self.campaign.missed), WARNING),
            ("Best combo", f"×{self.campaign.best_combo}", ACCENT),
        ]
        for index, (label_text, value_text, tone) in enumerate(metrics):
            row = pygame.Rect(report.left + 34, report.top + 30 + index * 57, report.width - 68, 45)
            pygame.draw.rect(self.screen, self.theme.panel, row, border_radius=9)
            label_surface = self.fonts.get(16).render(label_text, True, self.theme.muted)
            value_surface = self.fonts.get(20, True).render(value_text, True, tone)
            self.screen.blit(label_surface, (row.left + 16, row.top + 12))
            self.screen.blit(value_surface, value_surface.get_rect(midright=(row.right - 16, row.centery)))

    def _draw_settings(self) -> None:
        veil = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        veil.fill((5, 8, 13, 145))
        self.screen.blit(veil, (0, 0))
        rect = pygame.Rect(392, 126, 496, 486)
        draw_panel(self.screen, rect, self.theme, fill=(21, 28, 41), border=FOCUS, radius=22)
        title = self.fonts.get(34, True).render("ACCESSIBILITY", True, self.theme.ink)
        self.screen.blit(title, title.get_rect(center=(rect.centerx, rect.top + 58)))
        sub = self.fonts.get(15).render("Changes apply immediately.", True, self.theme.muted)
        self.screen.blit(sub, sub.get_rect(center=(rect.centerx, rect.top + 96)))
        notes = [
            "High contrast strengthens borders and text.",
            "Reduced motion limits conveyor animation and shake.",
            "Routing assist reveals the correct bay while carrying.",
        ]
        for index, note in enumerate(notes):
            text = self.fonts.get(13).render(note, True, self.theme.dim)
            self.screen.blit(text, text.get_rect(center=(rect.centerx, rect.top + 158 + index * 66)))

    def _draw_status_chip(self, x: int, y: int, text: str, tone: str) -> None:
        color = {"success": SUCCESS, "warning": WARNING, "danger": DANGER}.get(tone, FOCUS)
        width = min(320, max(160, self.fonts.get(13).size(text)[0] + 36))
        rect = pygame.Rect(x, y, width, 32)
        pygame.draw.rect(self.screen, (20, 31, 43), rect, border_radius=9)
        pygame.draw.rect(self.screen, color, rect, 1, border_radius=9)
        pygame.draw.circle(self.screen, color, (rect.left + 14, rect.centery), 4)
        label = self.fonts.get(13).render(text, True, self.theme.ink)
        self.screen.blit(label, (rect.left + 26, rect.top + 8))

    def _draw_attribute_symbol(self, value: str, rule_type: str, center: tuple[int, int], scale: float) -> None:
        x, y = center
        if rule_type == "COLOR":
            pygame.draw.circle(self.screen, self._color_for_value(value), center, max(6, int(12 * scale)))
            pygame.draw.circle(self.screen, self.theme.ink, center, max(6, int(12 * scale)), 1)
        elif rule_type == "MARK":
            draw_mark_icon(self.screen, value, center, self.theme.ink, max(7, int(11 * scale)), 2)
        elif rule_type == "STATUS":
            color = self._color_for_value(value)
            pygame.draw.polygon(self.screen, color, ((x, y - 10), (x + 10, y), (x, y + 10), (x - 10, y)))
        else:
            pygame.draw.rect(self.screen, (234, 230, 214), pygame.Rect(x - 14, y - 9, 28, 18), border_radius=5)
            pygame.draw.rect(self.screen, ACCENT, pygame.Rect(x - 14, y - 9, 28, 18), 2, border_radius=5)

    def _color_for_value(self, value: str) -> tuple[int, int, int]:
        from .constants import PACKAGE_COLORS, STATUS_COLORS

        return PACKAGE_COLORS.get(value, STATUS_COLORS.get(value, ACCENT))

    def _value_label(self, value: str) -> str:
        from .constants import WEIGHT_LABELS

        return WEIGHT_LABELS.get(value, value)

    def _bay_rects(self) -> dict[str, pygame.Rect]:
        gap = 18
        margin = 24
        width = (SCREEN_WIDTH - margin * 2 - gap * 3) // 4
        y = 511
        height = 154
        return {
            name: pygame.Rect(margin + index * (width + gap), y, width, height)
            for index, name in enumerate(DESTINATIONS)
        }
