import pygame
import math
import random

class Letter(pygame.sprite.Sprite):
    """A sprite for a single letter to handle placement and collision."""
    def __init__(self, char_surf, color, text_type, char, font_path, font_size, padding_kernel_mask, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION):
        super().__init__()
        self.original_image = char_surf # Store for rotation
        self.image = char_surf
        self.mask = pygame.mask.from_surface(self.image, 10)
        # Create a padded version of the mask for collision detection
        self.padded_mask = self.mask.convolve(padding_kernel_mask)
        self.rect = self.image.get_rect()
        self.color = color
        self.text_type = text_type
        # --- Data for high-res rendering ---
        self.char = char # For text, this is the character. For assets, can be None or a path.
        self.font_path = font_path # For assets, this will be the asset path
        self.font_size = font_size # The size used for the preview layout
        self.ROTATE_LETTERS_ON_ARC = ROTATE_LETTERS_ON_ARC
        self.MAX_ARC_LETTER_ROTATION = MAX_ARC_LETTER_ROTATION
        # angle_rad is set externally for arc letters

    def move_along_arc(self, radius, angle_offset_rad):
        """Move the sprite along its circular path by a given angle offset."""
        self.angle_rad += angle_offset_rad

        new_center_x = radius * math.cos(self.angle_rad)
        new_center_y = radius * math.sin(self.angle_rad)

        if self.ROTATE_LETTERS_ON_ARC:
            rotation_deg = -math.degrees(self.angle_rad) - 90
            
            # --- Clamp rotation to avoid upside-down letters ---
            # Normalize to -180 to 180 to handle angle wrapping correctly
            normalized_rotation = (rotation_deg + 180) % 360 - 180
            clamped_rotation = max(-self.MAX_ARC_LETTER_ROTATION, min(self.MAX_ARC_LETTER_ROTATION, normalized_rotation))

            # Update image and rect, but not mask, for performance during nudging
            self.image = pygame.transform.rotate(self.original_image, clamped_rotation)
            self.rect = self.image.get_rect(center=(self.rect.center)) # Keep center

        self.rect.center = (new_center_x, new_center_y)

def _trim_and_normalize_sprites(letter_sprites):
    """
    Calculates the tightest bounding box around the actual pixels of the sprites,
    then moves the sprites to be relative to that new box's top-left corner.
    This "trims" unnecessary transparent space around the word.
    """
    if not letter_sprites:
        return letter_sprites, pygame.Rect(0, 0, 0, 0)

    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    for sprite in letter_sprites:
        try:
            # The mask contains the actual pixel data. Get its bounding box.
            mask_brect = sprite.mask.get_bounding_rects()[0]
            # Convert the mask's local bounding box to "world" coordinates relative to the word layout
            sprite_abs_x = sprite.rect.x + mask_brect.x
            sprite_abs_y = sprite.rect.y + mask_brect.y
            sprite_abs_right = sprite.rect.x + mask_brect.right
            sprite_abs_bottom = sprite.rect.y + mask_brect.bottom

            min_x = min(min_x, sprite_abs_x)
            min_y = min(min_y, sprite_abs_y)
            max_x = max(max_x, sprite_abs_right)
            max_y = max(max_y, sprite_abs_bottom)
        except IndexError:
            # This can happen if a character is all whitespace (e.g., space character)
            # and has no pixels in its mask. We can safely ignore it for bounding box calculation.
            continue
    
    # If no pixels were found in any sprites (e.g., word is just spaces)
    if min_x == float('inf'):
        return letter_sprites, pygame.Rect(0, 0, 0, 0)

    # Normalize all sprites by shifting them by the top-left of the tight bounding box
    for sprite in letter_sprites:
        sprite.rect.move_ip(-min_x, -min_y)

    # The new, tight bounding box for the whole word
    tight_bbox_width = max_x - min_x
    tight_bbox_height = max_y - min_y
    new_word_bbox = pygame.Rect(0, 0, tight_bbox_width, tight_bbox_height)
    
    return letter_sprites, new_word_bbox

def create_arc_sprites(word, font, color, font_path, font_size, ARC_MIN_RADIUS, ARC_MAX_RADIUS, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION, padding_kernel_mask):
    """
    Generates a list of Letter sprites for an arc word, with internal collisions resolved.
    Returns the list of sprites and the word's final bounding box.
    """
    
    def check_internal_collision(sprite1, sprite2):
        """Checks sprite1's normal mask against sprite2's padded mask."""
        offset_x = sprite2.rect.x - sprite1.rect.x
        offset_y = sprite2.rect.y - sprite1.rect.y
        # Note: The padded mask is not offset here as the rects are already absolute within their own space
        return bool(sprite1.mask.overlap(sprite2.padded_mask, (offset_x, offset_y)))

    # --- Master loop to handle dynamic resizing of the arc ---
    max_radius_attempts = 15
    for radius_attempt in range(max_radius_attempts):
        # Arc parameters - start with a random radius and increase it if needed
        if radius_attempt == 0:
            radius = random.randint(ARC_MIN_RADIUS, ARC_MAX_RADIUS)
        else:
            radius += 10 # Increase the radius to make the arc gentler

        start_angle_deg = random.randint(0, 360)
        is_reversed = random.choice([False, True])
        
        word_to_render = word if not is_reversed else word[::-1]
        
        letter_surfs = [font.render(char, True, color) for char in word_to_render]
        if not letter_surfs:
            return [], pygame.Rect(0,0,0,0)

        # --- 1. Initial placement of letters as sprites ---
        letter_sprites = []
        current_angle_rad = math.radians(start_angle_deg)
        spacing_rad = (font.get_height() * 0.3) / radius

        for char, surf in zip(word_to_render, letter_surfs):
            char_width = surf.get_width()
            half_char_angle_rad = (char_width / 2) / radius
            center_angle_rad = current_angle_rad + half_char_angle_rad
            
            sprite = Letter(surf, color, "arc", char, font_path, font_size, padding_kernel_mask, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION)
            sprite.angle_rad = center_angle_rad # Store for movement
            sprite.rect.center = (radius * math.cos(center_angle_rad), radius * math.sin(center_angle_rad))

            if ROTATE_LETTERS_ON_ARC:
                # Rotate the letter to match the arc tangent
                rotation_deg = -math.degrees(center_angle_rad) - 90
                
                # --- Clamp rotation to avoid upside-down letters ---
                # Normalize to -180 to 180 to handle angle wrapping correctly
                normalized_rotation = (rotation_deg + 180) % 360 - 180
                clamped_rotation = max(-MAX_ARC_LETTER_ROTATION, min(MAX_ARC_LETTER_ROTATION, normalized_rotation))

                original_center = sprite.rect.center
                sprite.image = pygame.transform.rotate(sprite.original_image, clamped_rotation)
                sprite.rect = sprite.image.get_rect(center=original_center)
                # The mask must be updated after rotation for accurate collision checks
                sprite.mask = pygame.mask.from_surface(sprite.image)
                sprite.padded_mask = sprite.mask.convolve(padding_kernel_mask)

            letter_sprites.append(sprite)
            
            current_angle_rad += (char_width / radius) + spacing_rad

        # --- 2. Sequential internal collision resolution ---
        internal_collisions_resolved = True
        for i in range(1, len(letter_sprites)):
            max_loops = 150 # Increased safety break
            loop_count = 0
            collision_in_loop = False
            while loop_count < max_loops:
                collision_found_in_pass = False
                for j in range(i):
                    if check_internal_collision(letter_sprites[i], letter_sprites[j]):
                        nudge_angle_rad = 0.01 
                        for k in range(i, len(letter_sprites)):
                            letter_sprites[k].move_along_arc(radius, nudge_angle_rad)
                        collision_found_in_pass = True
                        collision_in_loop = True
                        break 
                if not collision_found_in_pass:
                    break
                loop_count += 1
            
            # If the loop timed out, it means we couldn't resolve it by nudging
            if loop_count >= max_loops:
                internal_collisions_resolved = False
                break
        
        # If all internal collisions were resolved, we are done with this word.
        if internal_collisions_resolved:
            # --- 3. Finalize sprites (update masks if they were deferred) and normalize positions ---
            if ROTATE_LETTERS_ON_ARC:
                for s in letter_sprites:
                    # The mask is now always updated during move_along_arc,
                    # but we need to ensure the padded mask is also up-to-date for the *next* word's collision check
                    s.mask = pygame.mask.from_surface(s.image)
                    s.padded_mask = s.mask.convolve(padding_kernel_mask)

            # --- 3. Trim the entire group of sprites to a tight bounding box ---
            return _trim_and_normalize_sprites(letter_sprites)

    # If we exit the master loop, it means we failed even after resizing the radius
    print(f"CRITICAL WARNING: Failed to place '{word}' without overlaps even after {max_radius_attempts} radius increases.")
    return [], pygame.Rect(0,0,0,0)

def create_normal_sprites(word, font, color, font_path, font_size, PADDING, padding_kernel_mask, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION):
    """Generates a list of Letter sprites for a normal, straight word."""
    letter_sprites = []
    x_offset = 0
    max_h = 0
    padding_between_letters = PADDING
    
    for char in word:
        char_surf = font.render(char, True, color)
        sprite = Letter(char_surf, color, "normal", char, font_path, font_size, padding_kernel_mask, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION)
        sprite.rect.topleft = (x_offset, 0)
        letter_sprites.append(sprite)
        x_offset += sprite.rect.width + padding_between_letters
        max_h = max(max_h, sprite.rect.height)
    
    # After initial placement, trim the group to a tight bounding box
    return _trim_and_normalize_sprites(letter_sprites) 

def create_asset_sprite(asset_path, size, padding_kernel_mask):
    """
    Creates a single sprite from a PNG asset.
    'size' is used to determine the height of the scaled asset.
    """
    try:
        # Load the asset image
        asset_image = pygame.image.load(asset_path).convert_alpha()
        
        # Scale the image based on the desired 'size' (height)
        original_width, original_height = asset_image.get_size()
        if original_height == 0: return [], None
        
        scale_factor = size / original_height
        new_width = int(original_width * scale_factor)
        new_height = int(size)
        
        scaled_image = pygame.transform.smoothscale(asset_image, (new_width, new_height))
        
        # The color argument is not used for assets, so we pass a dummy value
        color = (0, 0, 0) 
        
        # Create a single sprite. Note that ROTATE_LETTERS_ON_ARC and MAX_ARC_LETTER_ROTATION are not relevant for assets.
        sprite = Letter(scaled_image, color, "asset", None, asset_path, size, padding_kernel_mask, False, 0)
        
        # The 'word_bbox' is simply the rect of the single scaled image.
        word_bbox = scaled_image.get_rect()
        
        # Return as a list containing the single sprite and its bounding box
        return [sprite], word_bbox
        
    except Exception as e:
        print(f"Error creating asset sprite from {asset_path}: {e}")
        return [], None 