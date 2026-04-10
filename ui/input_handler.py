import pygame


class InputHandler:
    def __init__(self, runtime, renderer) -> None:
        self.runtime = runtime
        self.renderer = renderer

    def handle(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.renderer.paused = not self.renderer.paused
            elif event.key == pygame.K_r:
                self.runtime.reset()
            elif event.key == pygame.K_s:
                self.runtime.save_snapshot_now()

        if event.type == pygame.MOUSEBUTTONDOWN:
            gx, gy = self.renderer.mouse_to_grid(event.pos)
            if gx is None:
                return
            if event.button == 1:
                self.runtime.maybe_help_from_user(gx, gy, 0.45)
            elif event.button == 3:
                self.runtime.inject_toxin(gx, gy, 0.35)
