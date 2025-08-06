import pygame
import os
import datetime
import math
from PIL import Image
import cv2
import numpy as np

def pygame_surface_to_pil_image(surface):
    """
    Convert a pygame surface to a PIL image.
    This is optimized to use views and avoid extra memory copies.
    """
    # Pygame and PIL use different coordinate systems. A raw view
    # would be vertically flipped. Creating a string buffer handles the
    # conversion correctly and is still faster than older methods.
    if surface.get_alpha():
        return Image.frombytes('RGBA', surface.get_size(), pygame.image.tobytes(surface, 'RGBA', mirrored=True))
    else:
        return Image.frombytes('RGB', surface.get_size(), pygame.image.tobytes(surface, 'RGB', mirrored=True))

def render_high_quality_layout(original_image, placed_sprites, preview_canvas_size, preview_canvas_offsets, get_cached_font, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION):
    """Renders the final layout at full resolution onto a new surface with font caching and word-level rendering."""
    
    original_width, original_height = original_image.size
    preview_width, preview_height = preview_canvas_size
    preview_offset_x, preview_offset_y = preview_canvas_offsets

    # Use width for scaling factor to handle different aspect ratios consistently
    scale_factor = original_width / preview_width

    # Create new, large surfaces for drawing the high-res output
    overlay_surface = pygame.Surface(original_image.size, pygame.SRCALPHA)
    mask_surface = pygame.Surface(original_image.size)
    mask_surface.fill((0, 0, 0))

    # Group sprites by word for more efficient rendering
    word_groups = {}
    for sprite in placed_sprites:
        # Create a word identifier based on position and properties
        word_key = (sprite.font_path, sprite.font_size, sprite.color, sprite.text_type)
        if word_key not in word_groups:
            word_groups[word_key] = []
        word_groups[word_key].append(sprite)

    # Render each word group
    for word_key, sprites in word_groups.items():
        font_path, font_size, color, text_type = word_key
        
        # Load font once for the entire word
        high_res_font_size = int(font_size * scale_factor)
        if high_res_font_size < 1: 
            high_res_font_size = 1
        
        high_res_font = get_cached_font(font_path, high_res_font_size)
        
        # Render each character in the word
        for sprite in sprites:
            try:
                # 3. Render the character for both overlay and mask
                overlay_char_surf = high_res_font.render(sprite.char, True, color)
                mask_char_surf = high_res_font.render(sprite.char, True, (255, 255, 255))
                
                # 4. Scale position and apply rotation if it's an arc letter
                relative_center_x = sprite.rect.centerx - preview_offset_x
                relative_center_y = sprite.rect.centery - preview_offset_y
                
                high_res_center_x = int(relative_center_x * scale_factor)
                high_res_center_y = int(relative_center_y * scale_factor)

                # Get the rect of the newly rendered high-res character, centered on the new scaled position
                high_res_rect = overlay_char_surf.get_rect(center=(high_res_center_x, high_res_center_y))

                final_overlay_surf = overlay_char_surf
                final_mask_surf = mask_char_surf

                # Re-apply rotation for arc letters at high resolution
                if sprite.text_type == 'arc' and ROTATE_LETTERS_ON_ARC:
                    rotation_deg = -math.degrees(sprite.angle_rad) - 90
                    normalized_rotation = (rotation_deg + 180) % 360 - 180
                    clamped_rotation = max(-MAX_ARC_LETTER_ROTATION, min(MAX_ARC_LETTER_ROTATION, normalized_rotation))
                    
                    # Rotate the high-res surfaces
                    final_overlay_surf = pygame.transform.rotate(overlay_char_surf, clamped_rotation)
                    final_mask_surf = pygame.transform.rotate(mask_char_surf, clamped_rotation)
                    
                    # Update rect to keep it centered after rotation
                    high_res_rect = final_overlay_surf.get_rect(center=high_res_rect.center)

                # 5. Blit the final character onto the large surfaces
                overlay_surface.blit(final_overlay_surf, high_res_rect)
                mask_surface.blit(final_mask_surf, high_res_rect)

            except Exception as e:
                print(f"Warning: Could not render high-res char '{sprite.char}' from font {sprite.font_path}. Reason: {e}")

    return overlay_surface, mask_surface

def save_output(placed_sprites_cache, SCRIPT_DIR, current_background_image, current_image_index, current_image_directory, original_pil_image, get_canvas_dimensions, get_canvas_offsets, pil_to_pygame_surface, MASK_GROW_PIXELS, grow_binary_mask_pil, create_final_mask_surface, get_cached_font, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION, screen, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, image_index=None):
    """Saves the current text overlay, mask, and a debug overlay to the 'out' directory with optimizations."""
    if not placed_sprites_cache:
        # Don't save if there's nothing to save
        return False

    try:
        # 1. Define and create output directories
        out_dir = os.path.join(SCRIPT_DIR, "out")
        before_dir = os.path.join(out_dir, "before")
        after_dir = os.path.join(out_dir, "after")
        debug_dir = os.path.join(out_dir, "debug")
        os.makedirs(before_dir, exist_ok=True)
        os.makedirs(after_dir, exist_ok=True)
        os.makedirs(debug_dir, exist_ok=True)

        # 2. Determine a base filename with a shared timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if current_background_image and current_image_index != -1:
            image_part = os.path.splitext(os.path.basename(current_image_directory[current_image_index]))[0]
        else:
            image_part = "layout"
        
        # Add image index if provided for batch processing
        if image_index is not None:
            base_name = f"{timestamp}_{image_part}_{image_index:03d}"
        else:
            base_name = f"{timestamp}_{image_part}"

        # --- High-Resolution Saving with OpenCV ---
        if original_pil_image:
            # 1. Render the high-quality layout using the existing Pygame-based function
            preview_canvas_size = get_canvas_dimensions()
            if current_background_image:
                canvas_offset_x, canvas_offset_y = get_canvas_offsets(current_background_image.size)
            else:
                canvas_offset_x, canvas_offset_y = 0, 0

            overlay_surf, mask_surf = render_high_quality_layout(original_pil_image, placed_sprites_cache, preview_canvas_size, (canvas_offset_x, canvas_offset_y), get_cached_font, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION)

            # --- Convert all assets to OpenCV/NumPy format upfront ---
            
            # Original image (PIL to NumPy, RGB to BGR)
            original_cv = cv2.cvtColor(np.array(original_pil_image), cv2.COLOR_RGB2BGR)

            # Mask surface (Pygame to NumPy grayscale)
            mask_bytes = pygame.image.tobytes(mask_surf, 'L')
            mask_cv = np.frombuffer(mask_bytes, dtype=np.uint8).reshape(mask_surf.get_height(), mask_surf.get_width())

            # Overlay surface (Pygame to NumPy RGBA, then to BGRA for OpenCV)
            overlay_bytes = pygame.image.tobytes(overlay_surf, 'RGBA')
            overlay_np_rgba = np.frombuffer(overlay_bytes, dtype=np.uint8).reshape(overlay_surf.get_height(), overlay_surf.get_width(), 4)
            overlay_cv_bgra = cv2.cvtColor(overlay_np_rgba, cv2.COLOR_RGBA2BGRA)

            # --- Grow the mask with OpenCV (replaces slow PIL filter) ---
            if MASK_GROW_PIXELS > 0:
                kernel = np.ones((MASK_GROW_PIXELS * 2 + 1, MASK_GROW_PIXELS * 2 + 1), np.uint8)
                mask_cv = cv2.dilate(mask_cv, kernel, iterations=1)

            # 2. Save the "after" mask using fast cv2.imwrite
            after_path = os.path.join(after_dir, f"{base_name}.png")
            cv2.imwrite(after_path, mask_cv)

            # 3. Composite and save the "before" image using NumPy
            # Extract BGR and alpha channels from overlay
            overlay_bgr = overlay_cv_bgra[:, :, :3]
            alpha = overlay_cv_bgra[:, :, 3:] / 255.0 # Normalize alpha to 0-1 range

            # Perform alpha blending
            before_cv = original_cv * (1 - alpha) + overlay_bgr * alpha
            before_cv = before_cv.astype(np.uint8)
            
            before_path = os.path.join(before_dir, f"{base_name}.png")
            cv2.imwrite(before_path, before_cv)

            # 4. Composite and save the "debug" image
            debug_cv = before_cv.copy()
            tint_alpha = 0.7  # ~70% opacity for the mask overlay
            mask_area = mask_cv > 0
            
            # Darken the areas under the mask
            debug_cv[mask_area] = debug_cv[mask_area] * (1.0 - tint_alpha)
            debug_cv = debug_cv.astype(np.uint8)
            
            debug_path = os.path.join(debug_dir, f"{base_name}.png")
            cv2.imwrite(debug_path, debug_cv)

            return True

        # --- Fallback to Low-Resolution Saving (if no background image) ---
        # This part remains the same as it's already fast enough for screen-resolution images.
        before_path = os.path.join(before_dir, f"{base_name}.png")
        main_area_surf = screen.subsurface(pygame.Rect(0, 0, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT))
        pygame.image.save(main_area_surf, before_path)

        # 4. Save the "after" image (black and white mask)
        after_path = os.path.join(after_dir, f"{base_name}.png")
        canvas_width, canvas_height = get_canvas_dimensions()
        
        # Use the helper function to get offsets
        if current_background_image:
            canvas_offset_x, canvas_offset_y = get_canvas_offsets(current_background_image.size)
        else:
            canvas_offset_x, canvas_offset_y = 0, 0

        mask_to_save = create_final_mask_surface(placed_sprites_cache, canvas_width, canvas_height, canvas_offset_x, canvas_offset_y)
        pygame.image.save(mask_to_save, after_path)
        
        return True

    except Exception as e:
        print(f"ERROR: Failed to save output: {e}")
        return False 