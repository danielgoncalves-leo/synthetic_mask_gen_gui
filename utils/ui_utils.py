# import pygame
# import sys
# import os

# # Deprecated legacy UI helpers (generate_font_catalog, show_controls, show_template_selection_popup) were removed in favour of Modern UI equivalents.
# # Only show_batch_save_popup remains exported from this module.

# def show_batch_save_popup(screen, W, H, current_image_directory):
#     """Show a pygame-based slider interface for batch save settings."""
#     popup_width = 500
#     popup_height = 470  # Increased height to accommodate all elements comfortably
#     popup_x = (W - popup_width) // 2
#     popup_y = (H - popup_height) // 2

#     # Create popup surface
#     popup_surface = pygame.Surface((popup_width, popup_height))

#     # Fonts
#     title_font = pygame.font.Font(None, 32)
#     text_font = pygame.font.Font(None, 24)
#     value_font = pygame.font.Font(None, 28)

#     # --- Layout & Constants ---
#     x_margin = 50
    
#     # --- State Variables ---
#     resize_enabled = False
#     selected_megapixels = 0
#     dropdown_expanded = False
#     min_value = 1
#     max_value = len(current_image_directory) if current_image_directory else 1
#     current_value = min(10, max_value)

#     # Megapixel Dropdown
#     megapixel_options = ["Original", "1 MP", "2 MP", "4 MP", "8 MP"]
#     dropdown_values = [0, 1, 2, 4, 8]  # Corresponding MP values, 0 for original

#     # Slider configuration
#     slider_width = popup_width - 2 * x_margin
#     slider_height = 8
    
#     # Slider track colors
#     track_color = (180, 180, 180)
#     filled_color = (100, 150, 255)
#     handle_color = (50, 100, 200)
#     handle_hover_color = (70, 120, 220)
    
#     # Buttons
#     ok_button_rect = pygame.Rect(popup_width//2 - 80, popup_height - 60, 70, 35)
#     cancel_button_rect = pygame.Rect(popup_width//2 + 10, popup_height - 60, 70, 35)
    
#     # Slider interaction variables
#     is_dragging_slider = False
#     handle_hover = False
    
#     while True:
#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 pygame.quit()
#                 sys.exit()
            
#             elif event.type == pygame.MOUSEBUTTONDOWN:
#                 mouse_pos = event.pos
#                 popup_mouse_x = mouse_pos[0] - popup_x
#                 popup_mouse_y = mouse_pos[1] - popup_y
                
#                 # --- Dynamic element positions ---
#                 y_pos = 80 # Starting Y for controls
                
#                 # Resize Checkbox
#                 resize_checkbox_rect = pygame.Rect(x_margin, y_pos, 20, 20)
#                 y_pos += 35

#                 # Dropdown
#                 dropdown_rect = pygame.Rect(x_margin, y_pos, 200, 30)
                
#                 # Checkbox click
#                 if resize_checkbox_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                     resize_enabled = not resize_enabled
#                     dropdown_expanded = False
                
#                 # Dropdown click
#                 if resize_enabled:
#                     if dropdown_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                         dropdown_expanded = not dropdown_expanded
#                     elif dropdown_expanded:
#                         for idx in range(len(megapixel_options)):
#                             option_rect = pygame.Rect(dropdown_rect.x, dropdown_rect.y + (idx + 1) * 30, dropdown_rect.width, 30)
#                             if option_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                                 selected_megapixels = dropdown_values[idx]
#                                 dropdown_expanded = False
#                                 break
                
#                 # --- Slider positions are calculated dynamically during the draw loop ---
#                 # We need to calculate slider_y here for collision detection
#                 y_pos_slider = 80 # Start after title
#                 if resize_enabled:
#                     y_pos_slider += 35 # space for checkbox
#                     if dropdown_expanded:
#                         y_pos_slider += 35 + (len(megapixel_options) * 30)
#                     else:
#                         y_pos_slider += 35 # space for collapsed dropdown
#                 y_pos_slider += 80 # space before slider

#                 slider_y = y_pos_slider

#                 # Check button clicks
#                 if ok_button_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                     return current_value, selected_megapixels if resize_enabled else None
                
#                 elif cancel_button_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                     return None, None
                
#                 # Check if clicking on slider
#                 handle_x = x_margin + (current_value - min_value) / (max_value - min_value) * slider_width
#                 handle_rect = pygame.Rect(handle_x - 8, slider_y - 8, 16, 24)
#                 if handle_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                     is_dragging_slider = True
                
#                 # Check if clicking on slider track
#                 track_rect = pygame.Rect(x_margin, slider_y - 4, slider_width, slider_height + 8)
#                 if track_rect.collidepoint(popup_mouse_x, popup_mouse_y):
#                     # Calculate new value based on click position
#                     click_ratio = (popup_mouse_x - x_margin) / slider_width
#                     new_value = min_value + click_ratio * (max_value - min_value)
#                     current_value = max(min_value, min(max_value, int(new_value)))
            
#             elif event.type == pygame.MOUSEBUTTONUP:
#                 if event.button == 1:  # Left mouse button
#                     is_dragging_slider = False
            
#             elif event.type == pygame.MOUSEMOTION:
#                 mouse_pos = event.pos
#                 popup_mouse_x = mouse_pos[0] - popup_x
#                 popup_mouse_y = mouse_pos[1] - popup_y
                
#                 # Check handle hover - requires dynamic slider_y
#                 y_pos_slider = 80
#                 if resize_enabled:
#                     y_pos_slider += 35
#                     if dropdown_expanded:
#                         y_pos_slider += 35 + (len(megapixel_options) * 30)
#                     else:
#                         y_pos_slider += 35
#                 y_pos_slider += 80
#                 slider_y = y_pos_slider
                
#                 handle_x = x_margin + (current_value - min_value) / (max_value - min_value) * slider_width
#                 handle_rect = pygame.Rect(handle_x - 8, slider_y - 8, 16, 24)
#                 handle_hover = handle_rect.collidepoint(popup_mouse_x, popup_mouse_y)
                
#                 # Handle dragging
#                 if is_dragging_slider:
#                     # Calculate new value based on mouse position
#                     mouse_ratio = (popup_mouse_x - x_margin) / slider_width
#                     mouse_ratio = max(0, min(1, mouse_ratio))  # Clamp to 0-1
#                     new_value = min_value + mouse_ratio * (max_value - min_value)
#                     current_value = max(min_value, min(max_value, int(new_value)))
            
#             elif event.type == pygame.KEYDOWN:
#                 if event.key == pygame.K_RETURN:
#                     return current_value, selected_megapixels if resize_enabled else None
#                 elif event.key == pygame.K_ESCAPE:
#                     return None, None
#                 elif event.key == pygame.K_LEFT:
#                     current_value = max(min_value, current_value - 1)
#                 elif event.key == pygame.K_RIGHT:
#                     current_value = min(max_value, current_value + 1)
#                 elif event.key == pygame.K_UP:
#                     current_value = min(max_value, current_value + 5)
#                 elif event.key == pygame.K_DOWN:
#                     current_value = max(min_value, current_value - 5)
        
#         # Clear popup surface
#         popup_surface.fill((240, 240, 240))
#         pygame.draw.rect(popup_surface, (100, 100, 100), (0, 0, popup_width, popup_height), 3)
        
#         # --- Redraw all elements sequentially ---
#         y_pos = 30 # Reset y_pos for drawing

#         # Title
#         title_text = title_font.render(f"Batch Save Settings ({len(current_image_directory)} images available)", True, (0, 0, 0))
#         title_rect = title_text.get_rect(center=(popup_width // 2, y_pos))
#         popup_surface.blit(title_text, title_rect)
#         y_pos += 50

#         # Resize Checkbox
#         resize_checkbox_rect = pygame.Rect(x_margin, y_pos, 20, 20)
#         resize_text = text_font.render("Resize Images", True, (0, 0, 0))
#         pygame.draw.rect(popup_surface, (0, 0, 0), resize_checkbox_rect, 2)
#         if resize_enabled:
#             pygame.draw.line(popup_surface, (0, 0, 0), (resize_checkbox_rect.left + 3, resize_checkbox_rect.centery), (resize_checkbox_rect.centerx - 1, resize_checkbox_rect.bottom - 3), 2)
#             pygame.draw.line(popup_surface, (0, 0, 0), (resize_checkbox_rect.centerx - 1, resize_checkbox_rect.bottom - 3), (resize_checkbox_rect.right - 3, resize_checkbox_rect.top + 3), 2)
#         popup_surface.blit(resize_text, (resize_checkbox_rect.x + 30, resize_checkbox_rect.y))
#         y_pos += 35
        
#         # Megapixel Dropdown
#         dropdown_rect = pygame.Rect(x_margin, y_pos, 200, 30)
#         if resize_enabled:
#             current_option = megapixel_options[dropdown_values.index(selected_megapixels)]
#             dropdown_text_surf = text_font.render(current_option, True, (0, 0, 0))
#             pygame.draw.rect(popup_surface, (200, 200, 200), dropdown_rect)
#             pygame.draw.rect(popup_surface, (0, 0, 0), dropdown_rect, 1) # border
#             popup_surface.blit(dropdown_text_surf, (dropdown_rect.x + 10, dropdown_rect.y + 5))
            
#             if dropdown_expanded:
#                 for idx, option in enumerate(megapixel_options):
#                     option_rect = pygame.Rect(dropdown_rect.x, dropdown_rect.y + (idx + 1) * 30, dropdown_rect.width, 30)
#                     pygame.draw.rect(popup_surface, (220, 220, 220), option_rect)
#                     pygame.draw.rect(popup_surface, (0, 0, 0), option_rect, 1) # border
#                     option_text = text_font.render(option, True, (0, 0, 0))
#                     popup_surface.blit(option_text, (option_rect.x + 10, option_rect.y + 5))
#                 y_pos += (len(megapixel_options) + 1) * 30
#             else:
#                  y_pos += 35
        
#         y_pos += 40 # Padding before slider

#         # Slider for number of images
#         slider_y = y_pos
#         instruction_text = text_font.render("Select number of images to process:", True, (0, 0, 0))
#         instruction_rect = instruction_text.get_rect(center=(popup_width // 2, slider_y - 20))
#         popup_surface.blit(instruction_text, instruction_rect)
        
#         # Draw slider track
#         pygame.draw.rect(popup_surface, track_color, (x_margin, slider_y, slider_width, slider_height))
        
#         # Draw filled portion
#         if max_value > min_value:
#             fill_width = (current_value - min_value) / (max_value - min_value) * slider_width
#         else:
#             fill_width = 0
#         pygame.draw.rect(popup_surface, filled_color, (x_margin, slider_y, fill_width, slider_height))
        
#         # Draw slider handle
#         if max_value > min_value:
#             handle_x = x_margin + (current_value - min_value) / (max_value - min_value) * slider_width
#         else:
#             handle_x = x_margin
#         handle_color_to_use = handle_hover_color if handle_hover else handle_color
#         pygame.draw.rect(popup_surface, handle_color_to_use, (handle_x - 8, slider_y - 8, 16, 24))
        
#         # Draw value display
#         value_text = value_font.render(f"{current_value} images", True, (0, 0, 0))
#         value_rect = value_text.get_rect(center=(popup_width//2, slider_y + 40))
#         popup_surface.blit(value_text, value_rect)
        
#         # Draw min/max labels
#         min_text = text_font.render(str(min_value), True, (100, 100, 100))
#         max_text = text_font.render(str(max_value), True, (100, 100, 100))
#         popup_surface.blit(min_text, (x_margin, slider_y + 15))
#         popup_surface.blit(max_text, (x_margin + slider_width - max_text.get_width(), slider_y + 15))
        
#         # Draw buttons
#         pygame.draw.rect(popup_surface, (100, 200, 100), ok_button_rect)
#         pygame.draw.rect(popup_surface, (200, 100, 100), cancel_button_rect)
        
#         ok_text = text_font.render("Start", True, (255, 255, 255))
#         cancel_text = text_font.render("Cancel", True, (255, 255, 255))
        
#         ok_text_rect = ok_text.get_rect(center=ok_button_rect.center)
#         cancel_text_rect = cancel_text.get_rect(center=cancel_button_rect.center)
        
#         popup_surface.blit(ok_text, ok_text_rect)
#         popup_surface.blit(cancel_text, cancel_text_rect)
        
#         # Draw keyboard hints
#         hint_text = text_font.render("Use arrow keys or drag slider • Enter to confirm • Esc to cancel", True, (120, 120, 120))
#         hint_rect = hint_text.get_rect(center=(popup_width//2, popup_height - 20))
#         popup_surface.blit(hint_text, hint_rect)
        
#         # Draw popup on screen
#         screen.blit(popup_surface, (popup_x, popup_y))
#         pygame.display.flip()
        
#         # Cap frame rate
#         pygame.time.wait(16)  # ~60 FPS 