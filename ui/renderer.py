from __future__ import annotations

import pygame

from body.cells import CellType
from simworld.terrain import Terrain
from ui import colors
from ui.panels import build_lines
from ui.input_handler import InputHandler


class Renderer:
    def __init__(self, runtime) -> None:
        pygame.init()
        self.runtime = runtime
        self.cfg = runtime.cfg
        width = self.cfg.grid_w * self.cfg.cell_px + self.cfg.hud_width
        height = self.cfg.grid_h * self.cfg.cell_px
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(self.cfg.window_title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('consolas', 18)
        self.small_font = pygame.font.SysFont('consolas', 14)
        self.paused = False
        self.input_handler = InputHandler(runtime, self)

    def mouse_to_grid(self, pos):
        x, y = pos
        grid_px_w = self.cfg.grid_w * self.cfg.cell_px
        if x >= grid_px_w:
            return None, None
        gx = x // self.cfg.cell_px
        gy = y // self.cfg.cell_px
        if not (0 <= gx < self.cfg.grid_w and 0 <= gy < self.cfg.grid_h):
            return None, None
        return gx, gy

    def _world_color(self, cell):
        if cell.terrain == Terrain.WALL:
            return colors.WALL
        if cell.terrain == Terrain.RESOURCE:
            return colors.RESOURCE
        if cell.terrain == Terrain.HAZARD:
            return colors.HAZARD
        nutrient = max(0, min(255, int(cell.nutrient * 120)))
        toxin = max(0, min(255, int(cell.toxin * 130)))
        return (20 + toxin // 4, 24 + nutrient // 3, 28 + nutrient // 5)

    def _body_color(self, cell):
        if cell.cell_type == CellType.STEM:
            return colors.BODY_STEM
        if cell.cell_type == CellType.MEMBRANE:
            return colors.BODY_MEMBRANE
        return colors.BODY_STORAGE

    def draw(self) -> None:
        self.screen.fill(colors.BACKGROUND)
        cell_px = self.cfg.cell_px
        grid_px_w = self.cfg.grid_w * cell_px

        for y in range(self.cfg.grid_h):
            for x in range(self.cfg.grid_w):
                wcell = self.runtime.world.grid[y][x]
                rect = pygame.Rect(x * cell_px, y * cell_px, cell_px, cell_px)
                pygame.draw.rect(self.screen, self._world_color(wcell), rect)
                pygame.draw.rect(self.screen, colors.GRID, rect, 1)

                bcell = self.runtime.body.grid[y][x]
                if bcell.alive:
                    inner = rect.inflate(-2, -2)
                    pygame.draw.rect(self.screen, self._body_color(bcell), inner)

        hud_rect = pygame.Rect(grid_px_w, 0, self.cfg.hud_width, self.cfg.grid_h * cell_px)
        pygame.draw.rect(self.screen, colors.HUD_BG, hud_rect)

        title = self.font.render('AEGIS EMBRYO', True, colors.TEXT)
        self.screen.blit(title, (grid_px_w + 12, 12))

        for idx, line in enumerate(build_lines(self.runtime)):
            surf = self.small_font.render(line, True, colors.TEXT)
            self.screen.blit(surf, (grid_px_w + 12, 50 + idx * 20))

        if self.paused:
            surf = self.font.render('PAUSED', True, (255, 200, 100))
            self.screen.blit(surf, (grid_px_w + 12, self.cfg.grid_h * cell_px - 40))

        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.input_handler.handle(event)

            if not self.paused:
                alive = self.runtime.step()
                if not alive:
                    self.paused = True

            self.draw()
            self.clock.tick(self.cfg.fps)

        pygame.quit()
