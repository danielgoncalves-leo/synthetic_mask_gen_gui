from dataclasses import dataclass, field
from typing import List, Tuple
import pygame


@dataclass
class AppState:
    """Container for all mutable application state.

    This is an initial subset of what will eventually replace the many global
    variables scattered throughout the codebase.  Additional fields should be
    added incrementally as refactors proceed.
    """

    zoom_level: float = 1.0
    pan_offset: Tuple[int, int] = (0, 0)

    # Caches
    placed_sprites: List[pygame.sprite.Sprite] = field(default_factory=list)
    placed_points: List[Tuple[int, int]] = field(default_factory=list)

    # Image tracking
    current_image_index: int = -1 