import pygame
import os
import random
import threading

font_cache = {}  # Cache for loaded fonts to avoid repeated disk I/O
font_cache_lock = threading.Lock()  # Thread-safe access to font cache

def get_cached_font(font_path, font_size):
    """Get a font from cache or load it if not cached."""
    cache_key = (font_path, font_size)
    
    with font_cache_lock:
        if cache_key in font_cache:
            return font_cache[cache_key]
        
        # Load the font
        try:
            if font_path and os.path.isfile(font_path):
                font = pygame.font.Font(font_path, font_size)
            elif font_path:  # It's not a file, so it must be a system font name
                font = pygame.font.SysFont(font_path, font_size)
            else:  # It's the default font
                font = pygame.font.Font(None, font_size)
            
            # Cache the font
            font_cache[cache_key] = font
            return font
        except Exception as e:
            print(f"Warning: Failed to load font '{font_path}' at size {font_size}: {str(e)}. Falling back to default.")
            fallback_font = pygame.font.Font(None, font_size)
            font_cache[cache_key] = fallback_font
            return fallback_font

def clear_font_cache():
    """Clear the font cache to free memory."""
    global font_cache
    with font_cache_lock:
        font_cache.clear()
    print("Font cache cleared")

def get_system_fonts():
    """Get available system fonts using Pygame"""
    return pygame.font.get_fonts()

def get_font(size, custom_font_paths):
    """Get a random font with specified size using Pygame and return its identifier and display name."""
    # Prioritize custom fonts from FONT_DIR if provided.
    if custom_font_paths:
        candidates = custom_font_paths
    else:
        candidates = get_system_fonts()
    
    if not candidates:
        print("Warning: No custom fonts in FONT_DIR and no system fonts found. Using default.")
        font = pygame.font.Font(None, size)
        return font, None, "Default"
    
    chosen = random.choice(candidates)
    try:
        if os.path.isfile(chosen):
            # It's a path to a custom font
            font = get_cached_font(chosen, size)
            return font, chosen, os.path.basename(chosen)
        else:
            # It's a system font name
            font = get_cached_font(chosen, size)
            return font, chosen, chosen
    except Exception as e:
        print(f"Warning: Failed to load font '{chosen}': {str(e)}. Falling back to default.")
        font = pygame.font.Font(None, size)
        return font, None, "Default" 