import pygame

def is_within_canvas(rect, canvas_width, canvas_height, CANVAS_PADDING, canvas_offset_x=0, canvas_offset_y=0):
    """Check if rectangle is completely within the padded canvas boundaries"""
    # Adjust rect position relative to canvas offset
    adjusted_rect = pygame.Rect(
        rect.left - canvas_offset_x,
        rect.top - canvas_offset_y,
        rect.width,
        rect.height
    )
    
    return (adjusted_rect.left >= CANVAS_PADDING and 
            adjusted_rect.right <= canvas_width - CANVAS_PADDING and 
            adjusted_rect.top >= CANVAS_PADDING and 
            adjusted_rect.bottom <= canvas_height - CANVAS_PADDING)

def check_padded_collision(sprite1, sprite2):
    """Fast padded-mask collision.

    1. Quick reject with bounding-box test – almost free.
    2. Only if rects overlap do we pay the costlier Mask.overlap call.
    This typically eliminates ~80-90 % of the expensive calls seen in profiling.
    """

    # 1) Broad-phase: axis-aligned bounding boxes
    r1, r2 = sprite1.rect, sprite2.rect
    if not r1.colliderect(r2):
        return False

    # 2) Narrow-phase: exact mask test with padding
    offset_x = r2.x - r1.x
    offset_y = r2.y - r1.y
    return sprite1.padded_mask.overlap(sprite2.padded_mask, (offset_x, offset_y)) is not None 