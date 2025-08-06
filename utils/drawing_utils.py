import pygame

def draw_mask_panel(screen, placed_sprites, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, current_background_surface, original_pil_image, MASK_GROW_PIXELS, grow_binary_mask_pil, zoom_level, pan_offset_x, pan_offset_y):
    """Draws a 1:1 black and white mask representation on the right side of the screen."""
    mask_area_x = MAIN_AREA_WIDTH
    
    # Create mask panel surface with a neutral gray background
    mask_panel_surface = pygame.Surface((MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT))
    mask_panel_surface.fill((50, 50, 50)) # Gray background for the whole panel

    if current_background_surface:
        # Create a combined mask surface with background + text masks as one unit
        img_rect = current_background_surface.get_rect()
        mask_surface = pygame.Surface((img_rect.width, img_rect.height))
        mask_surface.fill((0, 0, 0))  # Black background
        
        # Calculate base position (centered) - MUST be calculated before using it
        base_img_x = (MAIN_AREA_WIDTH - img_rect.width) // 2
        base_img_y = (MAIN_AREA_HEIGHT - img_rect.height) // 2
        
        # Draw all the letter masks (as white) onto the mask surface at their original positions
        for sprite in placed_sprites:
            # Calculate sprite position relative to the image (not the full canvas)
            sprite_x = sprite.rect.x - base_img_x
            sprite_y = sprite.rect.y - base_img_y
            mask_surf = sprite.mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
            mask_surf.set_colorkey((0, 0, 0))
            mask_surface.blit(mask_surf, (sprite_x, sprite_y))
        
        # Apply mask growing if enabled (scaled for preview resolution)
        if MASK_GROW_PIXELS > 0:
            try:
                # Calculate scaled growth amount for preview
                # If we have the original image, scale the growth proportionally
                if original_pil_image:
                    original_width, original_height = original_pil_image.size
                    preview_width, preview_height = img_rect.width, img_rect.height
                    scale_factor = min(preview_width / original_width, preview_height / original_height)
                    scaled_growth = max(1, int(MASK_GROW_PIXELS * scale_factor))
                else:
                    scaled_growth = MASK_GROW_PIXELS
                
                mask_surface = grow_binary_mask_pil(mask_surface, scaled_growth)
            except Exception as e:
                print(f"WARNING: Failed to grow mask in preview. Reason: {e}")
        
        # Apply zoom and pan to the entire mask surface
        if abs(zoom_level - 1.0) > 0.01:
            scaled_width = int(img_rect.width * zoom_level)
            scaled_height = int(img_rect.height * zoom_level)
            scaled_mask = pygame.transform.scale(mask_surface, (scaled_width, scaled_height))
            mask_panel_surface.blit(scaled_mask, (base_img_x + pan_offset_x, base_img_y + pan_offset_y))
        else:
            mask_panel_surface.blit(mask_surface, (base_img_x + pan_offset_x, base_img_y + pan_offset_y))
    else:
        # If no image, draw masks directly
        for sprite in placed_sprites:
            mask_surf = sprite.mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
            mask_surf.set_colorkey((0, 0, 0))
            mask_panel_surface.blit(mask_surf, sprite.rect.topleft)
    
    screen.blit(mask_panel_surface, (mask_area_x, 0))
    pygame.draw.line(screen, (100, 100, 100), (mask_area_x, 0), (mask_area_x, MAIN_AREA_HEIGHT), 2)

def draw_mask_overlay(screen, placed_sprites, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, current_background_surface, original_pil_image, MASK_GROW_PIXELS, grow_binary_mask_pil, zoom_level, pan_offset_x, pan_offset_y):
    """Draw a semi-transparent black and white mask overlay on top of the image + text for debugging."""
    if not current_background_surface:
        return
    
    # Create a combined mask surface with background + text masks as one unit
    img_rect = current_background_surface.get_rect()
    mask_surface = pygame.Surface((img_rect.width, img_rect.height))
    mask_surface.fill((0, 0, 0))  # Pure black background

    # Calculate base position (centered) - MUST be calculated before using it
    base_img_x = (MAIN_AREA_WIDTH - img_rect.width) // 2
    base_img_y = (MAIN_AREA_HEIGHT - img_rect.height) // 2
    
    # Draw all letter masks onto this surface as pure white at their original positions
    for sprite in placed_sprites:
        # Calculate sprite position relative to the image (not the full canvas)
        sprite_x = sprite.rect.x - base_img_x
        sprite_y = sprite.rect.y - base_img_y
        mask_surf = sprite.mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
        mask_surf.set_colorkey((0, 0, 0))
        mask_surface.blit(mask_surf, (sprite_x, sprite_y))
    
    # Apply mask growing if enabled (scaled for preview resolution)
    if MASK_GROW_PIXELS > 0:
        try:
            # Calculate scaled growth amount for preview
            # If we have the original image, scale the growth proportionally
            if original_pil_image:
                original_width, original_height = original_pil_image.size
                preview_width, preview_height = img_rect.width, img_rect.height
                scale_factor = min(preview_width / original_width, preview_height / original_height)
                scaled_growth = max(1, int(MASK_GROW_PIXELS * scale_factor))
            else:
                scaled_growth = MASK_GROW_PIXELS
            
            mask_surface = grow_binary_mask_pil(mask_surface, scaled_growth)
        except Exception as e:
            print(f"WARNING: Failed to grow mask in overlay. Reason: {e}")
    
    # Set the entire mask's opacity to 70%
    mask_surface.set_alpha(int(255 * 0.7))
    
    # Apply zoom and pan to the entire mask surface and blit it on top of the existing view
    # (which already has the image + text from redraw_layout)
    if abs(zoom_level - 1.0) > 0.01:
        scaled_width = int(img_rect.width * zoom_level)
        scaled_height = int(img_rect.height * zoom_level)
        scaled_mask = pygame.transform.scale(mask_surface, (scaled_width, scaled_height))
        screen.blit(scaled_mask, (base_img_x + pan_offset_x, base_img_y + pan_offset_y))
    else:
        screen.blit(mask_surface, (base_img_x + pan_offset_x, base_img_y + pan_offset_y))

def draw_debug_regions(screen, W, H, PLACEMENT_REGIONS, current_background_surface, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, zoom_level, pan_offset_x, pan_offset_y, placed_points_cache):
    """Draws semi-transparent polygons and placement anchors for debugging with zoom and pan support."""
    if not current_background_surface:
        return
    
    # Get the image dimensions and base position
    img_rect = current_background_surface.get_rect()
    base_img_x = (MAIN_AREA_WIDTH - img_rect.width) // 2
    base_img_y = (MAIN_AREA_HEIGHT - img_rect.height) // 2
    
    # Calculate the actual image area dimensions (for 'fit' mode calculations)
    design_canvas_size = min(img_rect.width, img_rect.height)
    design_canvas_offset_x = (img_rect.width - design_canvas_size) // 2
    design_canvas_offset_y = (img_rect.height - design_canvas_size) // 2

    for region in PLACEMENT_REGIONS:
        mode = region.get('rules', {}).get('placement_mode', 'stretch')

        # Convert relative points to coordinates relative to the image
        image_relative_points = []
        for rel_x, rel_y in region['shape']:
            if mode == 'fit':
                # For 'fit' mode, use the design canvas within the image
                img_x = int(rel_x * design_canvas_size + design_canvas_offset_x)
                img_y = int(rel_y * design_canvas_size + design_canvas_offset_y)
            else: # stretch
                # For 'stretch' mode, use the full image dimensions
                img_x = int(rel_x * img_rect.width)
                img_y = int(rel_y * img_rect.height)
            image_relative_points.append((img_x, img_y))

        if len(image_relative_points) > 2:
            # Apply zoom and pan transformations to get screen coordinates
            screen_points = []
            for img_x, img_y in image_relative_points:
                # Apply zoom
                zoomed_x = int(img_x * zoom_level)
                zoomed_y = int(img_y * zoom_level)
                # Apply pan and base position
                screen_x = zoomed_x + pan_offset_x + base_img_x
                screen_y = zoomed_y + pan_offset_y + base_img_y
                screen_points.append((screen_x, screen_y))

            # Create a temporary surface for transparency
            region_surface = pygame.Surface((W, H), pygame.SRCALPHA)
            
            # Draw the filled polygon with alpha
            region_color_fill = (255, 255, 0, 50) # Yellow, semi-transparent
            pygame.draw.polygon(region_surface, region_color_fill, screen_points)
            
            # Draw the outline
            region_color_outline = (255, 255, 0, 200) # Yellow, more opaque
            pygame.draw.polygon(region_surface, region_color_outline, screen_points, 2) # 2px width

            screen.blit(region_surface, (0, 0))

            # Draw region name
            info_font = pygame.font.Font(None, 20)
            text_surf = info_font.render(region['name'], True, (255, 255, 255))
            # Find rough center of polygon to place text
            avg_x = sum(p[0] for p in screen_points) / len(screen_points)
            avg_y = sum(p[1] for p in screen_points) / len(screen_points)
            text_rect = text_surf.get_rect(center=(avg_x, avg_y))
            screen.blit(text_surf, text_rect)

    # Draw the anchor points for successfully placed words with zoom and pan
    if 'placed_points_cache' in globals() and placed_points_cache:
        for point in placed_points_cache:
            # Convert anchor point from canvas coordinates to image-relative coordinates
            # The anchor points are stored in canvas coordinates, but we need them relative to the image
            img_relative_x = point[0] - base_img_x
            img_relative_y = point[1] - base_img_y
            
            # Apply zoom and pan to the image-relative coordinates
            zoomed_x = int(img_relative_x * zoom_level)
            zoomed_y = int(img_relative_y * zoom_level)
            screen_x = zoomed_x + pan_offset_x + base_img_x
            screen_y = zoomed_y + pan_offset_y + base_img_y
            pygame.draw.circle(screen, (255, 0, 0), (screen_x, screen_y), 5) # Red, 5px radius

def draw_info_bar(screen, W, MAIN_AREA_HEIGHT, INFO_BAR_HEIGHT, get_image_status, get_performance_stats, current_image_directory, FORCE_REGIONS_ONLY):
    """Draw the info bar at the bottom of the screen."""
    info_bar_rect = pygame.Rect(0, MAIN_AREA_HEIGHT, W, INFO_BAR_HEIGHT)
    pygame.draw.rect(screen, (40, 40, 40), info_bar_rect)  # Dark background
    pygame.draw.line(screen, (100, 100, 100), (0, MAIN_AREA_HEIGHT), (W, MAIN_AREA_HEIGHT), 1)  # Top border
    
    info_font = pygame.font.Font(None, 20)
    small_font = pygame.font.Font(None, 18)  # Slightly larger font for hints
    
    # --- Left Side: Image Status ---
    status_text = get_image_status()
    status_surf = info_font.render(status_text, True, (200, 200, 200))
    text_y = MAIN_AREA_HEIGHT + (INFO_BAR_HEIGHT - status_surf.get_height()) // 2
    screen.blit(status_surf, (10, text_y))

    # --- Center: Hints ---
    hint_text = "Press H for controls | F for fonts | Scroll to zoom | Drag to pan"
    hint_surf = small_font.render(hint_text, True, (255, 215, 0))  # Gold color
    hint_x = (W - hint_surf.get_width()) // 2
    hint_y = MAIN_AREA_HEIGHT + (INFO_BAR_HEIGHT - hint_surf.get_height()) // 2
    screen.blit(hint_surf, (hint_x, hint_y))

    # --- Right Side: Mode and Image Count ---
    right_x_pos = W - 10 # Start from the right edge with a margin

    # Display Image Count
    if current_image_directory:
        total_images_text = f"Total: {len(current_image_directory)} images"
        total_surf = info_font.render(total_images_text, True, (150, 150, 150))
        right_x_pos -= total_surf.get_width()
        screen.blit(total_surf, (right_x_pos, text_y))
        right_x_pos -= 20 # Add some padding

    # Display Placement Mode
    mode_text = "Mode: Regions Only" if FORCE_REGIONS_ONLY else "Mode: All Random"
    mode_surf = info_font.render(mode_text, True, (200, 200, 200)) # Use a bright color
    right_x_pos -= mode_surf.get_width()
    screen.blit(mode_surf, (right_x_pos, text_y))
    
    # Display Performance Stats (if available)
    perf_text = get_performance_stats()
    perf_surf = small_font.render(perf_text, True, (150, 255, 150))  # Green color for performance
    right_x_pos -= perf_surf.get_width() + 10  # Add some padding
    screen.blit(perf_surf, (right_x_pos, text_y)) 