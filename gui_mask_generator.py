import pygame, random, sys
import os
from PIL import Image
import datetime
import numpy as np
import threading
import queue
import math
import pygame_gui
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from utils.image_utils import pil_to_pygame_surface, fit_image_to_canvas, grow_binary_mask_pil
from utils.font_utils import get_cached_font, clear_font_cache, get_system_fonts, get_font
from utils.file_utils import get_images_from_directory
from utils.modern_ui import (
    ModernUIManager,
    show_modern_font_catalog,
    show_modern_controls,
    show_modern_template_selection,
    show_modern_directory_selection,
    MultiTemplateSelectionDialog,
    show_modern_batch_save_popup,
)
from utils.collision_utils import is_within_canvas, check_padded_collision
from utils.log_utils import AppLogger
from utils.sprite_utils import create_arc_sprites, create_normal_sprites, create_asset_sprite
from utils.config_manager import get_config
from utils.words_loader import get_words, reload_words
from utils.region_manager import RegionManager
from utils.region_editor import RegionEditor
from state import AppState

console = Console()

config = get_config()
logger = AppLogger(config)

# Instantiate the application state container.
app_state = AppState()

# --- Helper ---------------------------------------------------------------
# Reload configuration at runtime and update the global `config` reference so
# that other modules pick up the new values automatically.  This mirrors the
# existing Shift+R behaviour but also refreshes the cached `config` object.

def reload_configuration():
    """Reload the YAML configuration and update the global `config`."""
    global config

    from utils.config_manager import reload_config as _reload_cfg, get_config as _get_cfg

    _reload_cfg()
    config = _get_cfg()
    logger.success("Configuration reloaded")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMG_DIR = os.path.join(SCRIPT_DIR, config.paths.default_image_dir)
DEFAULT_FONT_DIR = os.path.join(SCRIPT_DIR, config.paths.default_font_dir)

IMG_DIR = DEFAULT_IMG_DIR
FONT_DIR = DEFAULT_FONT_DIR

config_table = Table(show_header=False, box=None, padding=(0, 1))
config_table.add_row("[cyan]Script directory[/]", SCRIPT_DIR)
config_table.add_row("[cyan]Image directory[/]", IMG_DIR)
config_table.add_row("[cyan]Font directory[/]", FONT_DIR)
logger.info(Panel(config_table, title="[bold magenta]Script Configuration[/bold magenta]", expand=False))

pygame.init()
W, H = config.display.window_width, config.display.window_height
INFO_BAR_HEIGHT = config.display.info_bar_height
MAIN_AREA_WIDTH = int(W * config.canvas.main_area_ratio)
MAIN_AREA_HEIGHT = H - INFO_BAR_HEIGHT
screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()

# Initialize modern UI manager
ui_manager = ModernUIManager((W, H))

# --- UI Elements ---
toggle_region_button = None

original_pil_image = None
current_background_image = None
current_background_surface = None
SUPPORTED_IMAGE_EXTENSIONS = set(config.supported_extensions.images)
DEFAULT_BACKGROUND_COLOR = tuple(config.display.default_background_color)

zoom_level = 1.0
pan_offset_x = 0
pan_offset_y = 0
is_dragging = False
last_mouse_pos = (0, 0)
MIN_ZOOM = config.zoom.min_level
MAX_ZOOM = config.zoom.max_level
ZOOM_SPEED = config.zoom.speed

SHOW_FONT_INFO = config.fonts.show_info
custom_font_paths = []

current_image_directory = []
current_image_index = -1

show_mask_overlay = config.debug.show_mask_overlay
show_debug_regions = config.debug.show_debug_regions
FORCE_REGIONS_ONLY = config.debug.force_regions_only

# --- Active Dialog State ---
active_dialog = None

if FONT_DIR and os.path.isdir(FONT_DIR):
    for root, _, files in os.walk(FONT_DIR):
        for fname in files:
            if any(fname.lower().endswith(ext) for ext in config.supported_extensions.fonts):
                custom_font_paths.append(os.path.join(root, fname))
    logger.success(f"Found {len(custom_font_paths)} custom fonts in '{FONT_DIR}' (recursive search)")
else:
    system_fonts = get_system_fonts()
    logger.warning(f"Custom font directory not found. Using {len(system_fonts)} system fonts.")

ASSET_DIR = os.path.join(SCRIPT_DIR, "assets")
ASSET_PATHS = []
if os.path.isdir(ASSET_DIR):
    for fname in os.listdir(ASSET_DIR):
        if fname.lower().endswith('.png'):
            ASSET_PATHS.append(os.path.join(ASSET_DIR, fname))
    logger.success(f"Found {len(ASSET_PATHS)} assets in '{ASSET_DIR}'")
else:
    logger.warning(f"Asset directory not found at '{ASSET_DIR}'")

WORDS = get_words()

TEXT_TYPES = config.text.types
TEXT_TYPE_WEIGHTS = config.text.type_weights
MIN_FONT_SIZE = config.fonts.min_size
MAX_FONT_SIZE = config.fonts.max_size

MAX_WORDS = config.layout.max_words
MAX_ATTEMPTS_PER_WORD = config.layout.max_attempts_per_word
MAX_ATTEMPTS_TOTAL = config.layout.max_attempts_total
CANVAS_PADDING = config.canvas.padding

PADDING = config.text.normal.padding

ARC_MIN_RADIUS = config.text.arc.min_radius
ARC_MAX_RADIUS = config.text.arc.max_radius
ROTATE_LETTERS_ON_ARC = config.fonts.rotate_letters_on_arc
MAX_ARC_LETTER_ROTATION = config.fonts.max_arc_letter_rotation

RANDOMIZE_TEMPLATES = False

# --- Region Template Management ---
region_manager = RegionManager()
ACTIVE_TEMPLATE_NAMES = ["Default"]  # Start with the default template

# after RANDOMIZE_TEMPLATES declaration
CURRENT_RANDOM_TEMPLATE_NAME = "Default"

def _refresh_placement_regions():
    global PLACEMENT_REGIONS
    global CURRENT_RANDOM_TEMPLATE_NAME
    if RANDOMIZE_TEMPLATES and ACTIVE_TEMPLATE_NAMES:
        CURRENT_RANDOM_TEMPLATE_NAME = random.choice(ACTIVE_TEMPLATE_NAMES)
        PLACEMENT_REGIONS = region_manager.get_template(CURRENT_RANDOM_TEMPLATE_NAME)
        logger.info(f"[Randomize ON] Selected template: {CURRENT_RANDOM_TEMPLATE_NAME} with {len(PLACEMENT_REGIONS)} regions")
    else:
        CURRENT_RANDOM_TEMPLATE_NAME = ', '.join(ACTIVE_TEMPLATE_NAMES)
        PLACEMENT_REGIONS = []
        for name in ACTIVE_TEMPLATE_NAMES:
            template_regions = region_manager.get_template(name)
            PLACEMENT_REGIONS.extend(template_regions)
            logger.info(f"[Randomize OFF] Added template '{name}' with {len(template_regions)} regions")
        logger.info(f"[Randomize OFF] Total regions: {len(PLACEMENT_REGIONS)}")

_refresh_placement_regions()

layout_generation_count = 0
last_layout_time = 0.0

BATCH_PROCESSING_MODE = False

MASK_GROW_PIXELS = config.mask.grow_pixels

padding_kernel_size = config.mask.padding_size
padding_kernel_mask = pygame.mask.Mask((padding_kernel_size, padding_kernel_size), fill=True)


def get_canvas_offsets(image_size):
    """Calculate canvas offsets based on image size."""
    img_width, img_height = image_size
    offset_x = (MAIN_AREA_WIDTH - img_width) // 2
    offset_y = (MAIN_AREA_HEIGHT - img_height) // 2
    return offset_x, offset_y

def load_background_image(image_path):
    """Load and process a background image."""
    global original_pil_image, current_background_image, current_background_surface
    
    try:
        pil_image = Image.open(image_path)
        original_pil_image = pil_image.copy()
        logger.info(f"🖼️  Loaded image: [bold]{os.path.basename(image_path)}[/bold] ({pil_image.size[0]}x{pil_image.size[1]})")
        
        fitted_image = fit_image_to_canvas(pil_image, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT)
        current_background_image = fitted_image
        
        if not BATCH_PROCESSING_MODE:
            current_background_surface = pil_to_pygame_surface(fitted_image)
        else:
            current_background_surface = None
        
        reset_zoom_and_pan()
        
        logger.info(f"Image fitted to: {fitted_image.size[0]}x{fitted_image.size[1]}")
        return True
        
    except Exception as e:
        logger.error(f"Error loading image [bold]{image_path}[/]: {str(e)}")
        return False

def clear_background_image():
    """Clear the current background image."""
    global original_pil_image, current_background_image, current_background_surface
    original_pil_image = None
    current_background_image = None
    current_background_surface = None
    logger.info("🖼️  [yellow]Background image cleared[/]")


def reset_zoom_and_pan():
    """Reset zoom and pan to default values."""
    global zoom_level, pan_offset_x, pan_offset_y
    zoom_level = 1.0
    pan_offset_x = 0
    pan_offset_y = 0
    
    if 'placed_sprites_cache' in globals() and placed_sprites_cache:
        if not BATCH_PROCESSING_MODE:
            redraw_layout()
            pygame.display.flip()


if IMG_DIR and os.path.isdir(IMG_DIR):
    current_image_directory = get_images_from_directory(IMG_DIR)
    if current_image_directory:
        logger.success(f"Found {len(current_image_directory)} images in '{IMG_DIR}'")
        # Load first image automatically
        if load_background_image(current_image_directory[0]):
            current_image_index = 0
            logger.info(f"Auto-loaded: [bold]{os.path.basename(current_image_directory[0])}[/bold]")
        else:
            logger.error(f"Failed to load first image")
            current_image_index = -1
    else:
        logger.warning(f"No supported images found in '{IMG_DIR}'")
        current_image_index = -1
else:
    logger.warning(f"No image directory found. Using solid background.")
    current_image_directory = []
    current_image_index = -1

logger.info(f"🚀 [bold green]Initialization complete:[/] {len(current_image_directory)} images loaded, index: {current_image_index}")

# --- Padding Configuration ---
PADDING = 5
# Create a kernel for convolution to expand masks for padding
padding_kernel_surf = pygame.Surface((PADDING * 2 + 1, PADDING * 2 + 1), pygame.SRCALPHA)
pygame.draw.circle(padding_kernel_surf, (255, 255, 255), (PADDING, PADDING), PADDING)
padding_kernel_mask = pygame.mask.from_surface(padding_kernel_surf)

# --- Placement Configuration ---
CANVAS_PADDING = 10

USE_RANDOM_COLORS = True
MIN_COLOR_VALUE = 50  # Avoid too dark colors for visibility
MAX_COLOR_VALUE = 255

MAX_PLACEMENT_TRIES = 800

master_letter_sprites = pygame.sprite.Group()
placed_sprites_cache = []
placed_points_cache = []
BATCH_PROCESSING_MODE = False

import math

def get_random_color():
    """Generate a random RGB color"""
    if USE_RANDOM_COLORS:
        return (
            random.randint(MIN_COLOR_VALUE, MAX_COLOR_VALUE),
            random.randint(MIN_COLOR_VALUE, MAX_COLOR_VALUE),
            random.randint(MIN_COLOR_VALUE, MAX_COLOR_VALUE)
        )
    else:
        return (255, 255, 255)  # Default white

def point_in_polygon(x, y, poly):
    """
    Checks if a point (x, y) is inside a polygon `poly`.
    `poly` is a list of (x, y) vertices.
    Uses the Ray-Casting algorithm.
    """
    n = len(poly)
    if n < 3: # A polygon must have at least 3 vertices
        return False
        
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


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
                logger.warning(f"Failed to grow mask in preview. Reason: {e}")
        
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
            logger.warning(f"Failed to grow mask in overlay. Reason: {e}")
    
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

def create_final_mask_surface(placed_sprites, canvas_width, canvas_height, canvas_offset_x, canvas_offset_y):
    """Creates a clean, black and white surface of the mask, perfectly sized to the canvas."""
    mask_surface = pygame.Surface((canvas_width, canvas_height))
    mask_surface.fill((0, 0, 0)) # Pure black background
    
    for sprite in placed_sprites:
        # Calculate position relative to the canvas, not the screen
        relative_pos = (sprite.rect.x - canvas_offset_x, sprite.rect.y - canvas_offset_y)
        
        # We only need the sprite's mask, rendered in pure white
        mask_surf = sprite.mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
        mask_surf.set_colorkey((0, 0, 0))
        mask_surface.blit(mask_surf, relative_pos)
        
    return mask_surface



def render_high_quality_layout(original_image, placed_sprites, preview_canvas_size, preview_canvas_offsets):
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

    # Group sprites by word for more efficient rendering, and separate assets
    word_groups = {}
    asset_sprites = []
    for sprite in placed_sprites:
        if sprite.text_type == 'asset':
            asset_sprites.append(sprite)
            continue
            
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
                logger.warning(f"Could not render high-res char '{sprite.char}' from font {sprite.font_path}. Reason: {e}")

    # --- New: Render asset sprites ---
    for sprite in asset_sprites:
        try:
            # 1. Load original asset
            asset_image = pygame.image.load(sprite.font_path).convert_alpha()

            # 2. Scale it to high resolution based on the preview size
            high_res_height = int(sprite.font_size * scale_factor)
            original_asset_width, original_asset_height = asset_image.get_size()
            
            if original_asset_height == 0: continue
            
            asset_scale_factor = high_res_height / original_asset_height
            high_res_width = int(original_asset_width * asset_scale_factor)

            scaled_asset = pygame.transform.smoothscale(asset_image, (high_res_width, high_res_height))

            # 3. Calculate high-res position
            relative_center_x = sprite.rect.centerx - preview_offset_x
            relative_center_y = sprite.rect.centery - preview_offset_y
            
            high_res_center_x = int(relative_center_x * scale_factor)
            high_res_center_y = int(relative_center_y * scale_factor)

            high_res_rect = scaled_asset.get_rect(center=(high_res_center_x, high_res_center_y))

            # 4. Blit to overlay and mask surfaces
            overlay_surface.blit(scaled_asset, high_res_rect)
            
            # For the mask, we create a white version of the asset
            asset_mask = pygame.mask.from_surface(scaled_asset, 127)
            mask_surf_for_asset = asset_mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0,0,0,0))
            mask_surf_for_asset.set_colorkey((0, 0, 0))
            mask_surface.blit(mask_surf_for_asset, high_res_rect)

        except Exception as e:
            logger.warning(f"Could not render high-res asset '{sprite.font_path}'. Reason: {e}")

    return overlay_surface, mask_surface

def save_output(placed_sprites, script_dir, current_background_image, current_image_index, current_image_directory, original_pil_image, get_canvas_dimensions, get_canvas_offsets, pil_to_pygame_surface, mask_grow_pixels, grow_binary_mask_pil, create_final_mask_surface, get_cached_font, rotate_letters_on_arc, max_arc_letter_rotation, screen, main_area_width, main_area_height, image_index=None):
    """Saves the current text overlay, mask, and a debug overlay to the 'out' directory with optimizations."""
    if not placed_sprites:
        # Don't save if there's nothing to save
        return False

    try:
        # 1. Define and create output directories
        out_dir = os.path.join(script_dir, "out")
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

        # --- High-Resolution Saving ---
        if original_pil_image:
            # 1. Render the high-quality layout using optimized function
            preview_canvas_size = get_canvas_dimensions()
            
            # Use the helper function to get offsets
            if current_background_image:
                canvas_offset_x, canvas_offset_y = get_canvas_offsets(current_background_image.size)
            else:
                canvas_offset_x, canvas_offset_y = 0, 0

            overlay_surf, mask_surf = render_high_quality_layout(original_pil_image, placed_sprites, preview_canvas_size, (canvas_offset_x, canvas_offset_y))

            # --- Grow the mask if requested ---
            if mask_grow_pixels > 0:
                try:
                    mask_surf = grow_binary_mask_pil(mask_surf, mask_grow_pixels)
                except Exception as e:
                    logger.warning(f"Failed to grow mask. Reason: {e}")

            # 2. Save the "after" mask (black and white)
            after_path = os.path.join(after_dir, f"{base_name}.png")
            pygame.image.save(mask_surf, after_path)

            # 3. Composite and save the "before" image (original with text overlay)
            base_image_surf = pil_to_pygame_surface(original_pil_image.copy())
            base_image_surf.blit(overlay_surf, (0, 0)) # Blit high-res text on top
            before_path = os.path.join(before_dir, f"{base_name}.png")
            pygame.image.save(base_image_surf, before_path)

            # 4. Composite and save the "debug" image (image with text + semi-transparent B&W mask overlay)
            debug_image_surf = base_image_surf.copy()
            debug_mask_overlay = mask_surf.copy()
            debug_mask_overlay.set_alpha(int(255 * 0.7)) # Set uniform 70% opacity
            debug_image_surf.blit(debug_mask_overlay, (0, 0))
            debug_path = os.path.join(debug_dir, f"{base_name}.png")
            pygame.image.save(debug_image_surf, debug_path)

            return True

        # --- Fallback to Low-Resolution Saving (if no background image) ---
        # 3. Save the "before" image (main canvas with text overlay)
        before_path = os.path.join(before_dir, f"{base_name}.png")
        main_area_surf = screen.subsurface(pygame.Rect(0, 0, main_area_width, main_area_height))
        pygame.image.save(main_area_surf, before_path)

        # 4. Save the "after" image (black and white mask)
        after_path = os.path.join(after_dir, f"{base_name}.png")
        canvas_width, canvas_height = get_canvas_dimensions()
        
        # Use the helper function to get offsets
        if current_background_image:
            canvas_offset_x, canvas_offset_y = get_canvas_offsets(current_background_image.size)
        else:
            canvas_offset_x, canvas_offset_y = 0, 0

        mask_to_save = create_final_mask_surface(placed_sprites, canvas_width, canvas_height, canvas_offset_x, canvas_offset_y)
        pygame.image.save(mask_to_save, after_path)
        
        return True

    except Exception as e:
        logger.error(f"Failed to save output: {e}")
        return False

def process_single_image(image_index, total_images, megapixels=None):
    """Process a single image in the batch - designed for parallel execution."""
    global current_image_index, current_background_image, current_background_surface, original_pil_image
    
    try:
        # Load the specific image
        if 0 <= image_index < len(current_image_directory):
            image_path = current_image_directory[image_index]
            if load_background_image(image_path):
                # Resize if megapixels is specified
                if megapixels and megapixels > 0:
                    # Calculate target size preserving aspect ratio
                    original_width, original_height = original_pil_image.size
                    original_mp = (original_width * original_height) / 1_000_000
                    if original_mp > megapixels:
                        scale_factor = math.sqrt(megapixels / original_mp)
                        new_width = int(original_width * scale_factor)
                        new_height = int(original_height * scale_factor)
                        original_pil_image = original_pil_image.resize((new_width, new_height), Image.LANCZOS)
                        logger.info(f"Resized image {image_index + 1} to {new_width}x{new_height} ({megapixels} MP)")
                
                # Generate layout without redrawing
                layout(auto_advance_image=False, skip_redraw=True)
                # Save the output
                success = save_output(placed_sprites_cache, SCRIPT_DIR, current_background_image, current_image_index, current_image_directory, original_pil_image, get_canvas_dimensions, get_canvas_offsets, pil_to_pygame_surface, MASK_GROW_PIXELS, grow_binary_mask_pil, create_final_mask_surface, get_cached_font, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION, screen, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, image_index=image_index)
                return success, f"Image {image_index + 1}/{total_images}: {os.path.basename(image_path)}"
            else:
                return False, f"Image {image_index + 1}/{total_images}: Failed to load {os.path.basename(image_path)}"
        else:
            return False, f"Image {image_index + 1}/{total_images}: Invalid index"
    except Exception as e:
        return False, f"Image {image_index + 1}/{total_images}: Error - {str(e)}"

def batch_save():
    """Optimized batch save with proper parallelization and progress tracking."""
    global current_image_index, zoom_level, pan_offset_x, pan_offset_y, BATCH_PROCESSING_MODE, show_mask_overlay, show_debug_regions
    
    if not current_image_directory:
        logger.info("💡 [cyan]INFO:[/] No image directory loaded. Please set an image directory first.")
        return
    
    # Use modern UI dialog
    result = show_modern_batch_save_popup(ui_manager, (W, H), len(current_image_directory))
    if result is None:
        logger.info("Batch save cancelled by user.")
        return
    
    num_images, selected_megapixels = result

    # --- Enter Batch Processing Mode ---
    BATCH_PROCESSING_MODE = True
    logger.info(Panel("Entering Batch Processing Mode", style="bold yellow", expand=False))

    # Store original state
    original_image_index = current_image_index
    original_zoom_level = zoom_level
    original_pan_offset_x = pan_offset_x
    original_pan_offset_y = pan_offset_y
    
    reset_zoom_and_pan()
    
    # Disable preview rendering during batch processing
    original_show_mask_overlay = show_mask_overlay
    original_show_debug_regions = show_debug_regions
    show_mask_overlay = False
    show_debug_regions = False
    
    # Clear font cache before starting to ensure fresh state
    clear_font_cache()
    
    # Use sequential processing to avoid pygame threading issues
    # pygame font rendering is not thread-safe, so we process one image at a time
    max_workers = 1  # Force sequential processing for accuracy
    
    successful_saves = 0
    failed_saves = 0
    
    logger.info(f"\n--- Starting Sequential Batch Processing ---")
    logger.info(f"Processing {num_images} images sequentially for accuracy")
    logger.info(f"Font cache enabled for performance")
    
    # Create a progress popup
    popup_width = 400
    popup_height = 200
    popup_x = (W - popup_width) // 2
    popup_y = (H - popup_height) // 2
    popup_surface = pygame.Surface((popup_width, popup_height))
    popup_surface.fill((240, 240, 240))
    pygame.draw.rect(popup_surface, (100, 100, 100), (0, 0, popup_width, popup_height), 3)
    
    title_font = pygame.font.Font(None, 32)
    text_font = pygame.font.Font(None, 24)
    
    # Process images sequentially to avoid pygame threading issues
    for i in range(num_images):
        try:
            success, message = process_single_image(i, num_images, megapixels=selected_megapixels)
            if success:
                successful_saves += 1
                logger.success(f"{message}")
            else:
                failed_saves += 1
                logger.error(f"{message}")
        except Exception as e:
            failed_saves += 1
            logger.error(f"EXCEPTION: {str(e)}")
        
        # Update progress bar
        done_count = i + 1
        
        # Handle events to keep UI responsive
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        # Draw progress popup
        popup_surface.fill((240, 240, 240))
        pygame.draw.rect(popup_surface, (100, 100, 100), (0, 0, popup_width, popup_height), 3)
        
        title_text = title_font.render("Batch Processing", True, (0, 0, 0))
        title_rect = title_text.get_rect(center=(popup_width//2, 40))
        popup_surface.blit(title_text, title_rect)
        
        progress_text = text_font.render(f"Progress: {done_count}/{num_images}", True, (0, 0, 0))
        progress_rect = progress_text.get_rect(center=(popup_width//2, 100))
        popup_surface.blit(progress_text, progress_rect)
        
        # Draw progress bar
        bar_width = popup_width - 80
        bar_height = 20
        bar_x = 40
        bar_y = 140
        pygame.draw.rect(popup_surface, (180, 180, 180), (bar_x, bar_y, bar_width, bar_height))
        fill_width = (done_count / num_images) * bar_width if num_images > 0 else 0
        pygame.draw.rect(popup_surface, (100, 150, 255), (bar_x, bar_y, fill_width, bar_height))
        
        screen.blit(popup_surface, (popup_x, popup_y))
        pygame.display.flip()
        
        pygame.time.wait(50)  # Small delay to show progress
    
    # --- Exit Batch Processing Mode ---
    BATCH_PROCESSING_MODE = False
    logger.info(Panel("Exiting Batch Processing Mode", style="bold yellow", expand=False))
    
    # Re-enable preview rendering
    show_mask_overlay = original_show_mask_overlay
    show_debug_regions = original_show_debug_regions
    
    # Restore original state
    current_image_index = original_image_index
    zoom_level = original_zoom_level
    pan_offset_x = original_pan_offset_x
    pan_offset_y = original_pan_offset_y
    
    if current_image_directory and 0 <= current_image_index < len(current_image_directory):
        load_background_image(current_image_directory[current_image_index])
    
    redraw_layout()
    
    logger.info(f"\n--- Batch Processing Complete ---")
    logger.info(f"✅ Successful: {successful_saves}")
    logger.info(f"❌ Failed: {failed_saves}")
    logger.info(f"Total: {num_images}")
    logger.info("=" * 40)

def draw_debug_regions(screen, W, H, PLACEMENT_REGIONS, current_background_surface, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, zoom_level, pan_offset_x, pan_offset_y, placed_points_cache):
    """Draws semi-transparent polygons and placement anchors for debugging with zoom and pan support."""
    if not current_background_surface:
        return
    
    # Debug info: Show which template is being displayed
    debug_font = pygame.font.Font(None, 16)
    debug_text = f"Debug: {len(PLACEMENT_REGIONS)} regions"
    if RANDOMIZE_TEMPLATES:
        debug_text += f" (Random: {CURRENT_RANDOM_TEMPLATE_NAME})"
    else:
        debug_text += f" (All: {CURRENT_RANDOM_TEMPLATE_NAME})"
    
    debug_surf = debug_font.render(debug_text, True, (255, 255, 0))
    screen.blit(debug_surf, (10, 10))
    
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

def draw_info_bar(screen, W, MAIN_AREA_HEIGHT, INFO_BAR_HEIGHT, FORCE_REGIONS_ONLY, current_background_image, current_image_index, current_image_directory, layout_generation_count, last_layout_time):
    """Draw the info bar at the bottom of the screen."""
    info_bar_rect = pygame.Rect(0, MAIN_AREA_HEIGHT, W, INFO_BAR_HEIGHT)
    pygame.draw.rect(screen, (40, 40, 40), info_bar_rect)  # Dark background
    pygame.draw.line(screen, (100, 100, 100), (0, MAIN_AREA_HEIGHT), (W, MAIN_AREA_HEIGHT), 1)  # Top border
    
    info_font = pygame.font.Font(None, 20)
    small_font = pygame.font.Font(None, 18)  # Slightly larger font for hints
    
    # --- Left Side: Image Status ---
    if current_background_image:
        if current_image_directory:
            current_name = os.path.basename(current_image_directory[current_image_index])
            status_text = f"Image: {current_name} ({current_image_index + 1}/{len(current_image_directory)})"
        else:
            status_text = "Image: Single image loaded"
    else:
        status_text = "Background: Solid color"
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
    right_x_pos -= 20 # Add some padding

    # Display Template Name
    if RANDOMIZE_TEMPLATES:
        template_text = f"Template: {CURRENT_RANDOM_TEMPLATE_NAME} (rand)"
    else:
        template_text = f"Template: {', '.join(ACTIVE_TEMPLATE_NAMES)}"
    template_surf = info_font.render(template_text, True, (150, 200, 255)) # Blue color for template
    right_x_pos -= template_surf.get_width()
    screen.blit(template_surf, (right_x_pos, text_y))
    
    # Display Performance Stats (if available)
    if layout_generation_count > 0:
        avg_time = last_layout_time if layout_generation_count == 1 else "N/A"
        perf_text = f"Layouts: {layout_generation_count}, Avg: {avg_time:.3f}s" if isinstance(avg_time, float) else f"Layouts: {layout_generation_count}"
    else:
        perf_text = "No layouts generated"
    perf_surf = small_font.render(perf_text, True, (150, 255, 150))  # Green color for performance
    right_x_pos -= perf_surf.get_width() + 10  # Add some padding
    screen.blit(perf_surf, (right_x_pos, text_y))


def set_font_directory(font_dir_path):
    """Set the font directory and reload custom fonts."""
    global FONT_DIR, custom_font_paths
    FONT_DIR = font_dir_path
    custom_font_paths = []
    
    if FONT_DIR and os.path.isdir(FONT_DIR):
        for root, _, files in os.walk(FONT_DIR):
            for fname in files:
                if any(fname.lower().endswith(ext) for ext in config.supported_extensions.fonts):
                    custom_font_paths.append(os.path.join(root, fname))
        logger.info(f"💡 [cyan]INFO:[/] Font directory set. Found {len(custom_font_paths)} custom fonts in '{FONT_DIR}'")
    else:
        if font_dir_path is None:
            # This is an intentional switch to system fonts
            logger.info("💡 [cyan]INFO:[/] Switched to system fonts. Press 'R' to restore default custom fonts.")
        else:
            # This is a warning that the specified path was not found
            logger.warning(f"Font directory '{font_dir_path}' not found or invalid. Using system fonts.")

def set_image_directory(img_dir_path):
    """Set the image directory and reload images."""
    global IMG_DIR, current_image_directory, current_image_index
    IMG_DIR = img_dir_path
    current_image_directory = []
    current_image_index = -1
    
    if IMG_DIR and os.path.isdir(IMG_DIR):
        current_image_directory = get_images_from_directory(IMG_DIR)
        if current_image_directory:
            logger.info(f"💡 [cyan]INFO:[/] Image directory updated: Found {len(current_image_directory)} images in '{IMG_DIR}'")
            # Load first image automatically
            if load_background_image(current_image_directory[0]):
                current_image_index = 0
                logger.info(f"Auto-loaded: {os.path.basename(current_image_directory[0])}")
        else:
            logger.warning(f"No supported images found in '{IMG_DIR}'")
    else:
        logger.warning(f"Image directory '{img_dir_path}' not found or invalid.")
        clear_background_image()

def reload_words():
    """Reload words from files."""
    global WORDS
    from utils.words_loader import WordsLoader
    loader = WordsLoader(WORDS_DIR)
    loader.reload_cache()
    WORDS = loader.load_all_words(config.text.fallback_words)
    logger.info(f"💡 [cyan]INFO:[/] Reloaded {len(WORDS)} words from files")

def toggle_mask_overlay():
    """Toggle the mask overlay debug mode."""
    global show_mask_overlay
    show_mask_overlay = not show_mask_overlay
    if show_mask_overlay:
        logger.info("💡 [cyan]INFO:[/] Mask overlay debug mode: ON (showing black/white masks on gray background)")
    else:
        logger.info("💡 [cyan]INFO:[/] Mask overlay debug mode: OFF (showing normal colored text on image)")
    return show_mask_overlay

def toggle_region_debug():
    """Toggle the region debug view."""
    global show_debug_regions
    show_debug_regions = not show_debug_regions
    if show_debug_regions:
        logger.info("💡 [cyan]INFO:[/] Region debug mode: ON (showing placement zones)")
    else:
        logger.info("💡 [cyan]INFO:[/] Region debug mode: OFF")
    return show_debug_regions

def toggle_force_regions_only():
    """Toggle the region constraint mode."""
    global FORCE_REGIONS_ONLY
    FORCE_REGIONS_ONLY = not FORCE_REGIONS_ONLY
    if FORCE_REGIONS_ONLY:
        logger.info("💡 [cyan]INFO:[/] Region constraint mode: ON (Text only in defined zones)")
    else:
        logger.info("💡 [cyan]INFO:[/] Region constraint mode: OFF (Text can appear anywhere)")
    return FORCE_REGIONS_ONLY

def advance_to_next_image():
    """Advance to the next image in the directory if available."""
    global current_image_index, current_image_directory, current_background_image, current_background_surface
    
    logger.debug(f"current_image_directory length: {len(current_image_directory) if current_image_directory else 0}")
    logger.debug(f"current_image_index: {current_image_index}")
    
    if current_image_directory and current_image_index >= 0:
        # Advance to next image (even if there's only 1 image, this will reload it)
        current_image_index = (current_image_index + 1) % len(current_image_directory)
        next_image = current_image_directory[current_image_index]
        logger.info(f"Auto-advancing to: {os.path.basename(next_image)} ({current_image_index + 1}/{len(current_image_directory)})")
        return load_background_image(next_image)
    else:
        logger.debug(f"Cannot advance - no image directory or invalid index")
    return False

def get_canvas_dimensions():
    """Get the canvas dimensions based on current image or default size."""
    if current_background_image:
        # Use actual image dimensions
        img_width, img_height = current_background_image.size
        return img_width, img_height
    else:
        # Use default dimensions when no image loaded
        return MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT

def handle_zoom(mouse_pos, zoom_direction):
    """Handle zoom in/out centered on mouse position."""
    global zoom_level, pan_offset_x, pan_offset_y
    
    if not current_background_image:
        return
    
    # Calculate zoom factor
    zoom_factor = 1.0 + (zoom_direction * ZOOM_SPEED)
    new_zoom = zoom_level * zoom_factor
    
    # Clamp zoom level
    if MIN_ZOOM <= new_zoom <= MAX_ZOOM:
        # Calculate mouse position relative to image center
        img_rect = current_background_surface.get_rect()
        img_center_x = (MAIN_AREA_WIDTH - img_rect.width) // 2
        img_center_y = (MAIN_AREA_HEIGHT - img_rect.height) // 2
        
        mouse_rel_x = mouse_pos[0] - img_center_x
        mouse_rel_y = mouse_pos[1] - img_center_y
        
        # Calculate how much the mouse position should change
        zoom_ratio = new_zoom / zoom_level
        new_mouse_rel_x = mouse_rel_x * zoom_ratio
        new_mouse_rel_y = mouse_rel_y * zoom_ratio
        
        # Adjust pan to keep mouse position fixed
        pan_offset_x += (mouse_rel_x - new_mouse_rel_x)
        pan_offset_y += (mouse_rel_y - new_mouse_rel_y)
        
        zoom_level = new_zoom
        
        # Redraw immediately to show zoom changes
        redraw_layout()
        pygame.display.flip()

def handle_pan(mouse_pos):
    """Handle panning when dragging."""
    global pan_offset_x, pan_offset_y, last_mouse_pos
    
    if not current_background_image:
        return
    
    # Calculate mouse movement
    dx = mouse_pos[0] - last_mouse_pos[0]
    dy = mouse_pos[1] - last_mouse_pos[1]
    
    # Update pan offset
    pan_offset_x += dx
    pan_offset_y += dy
    
    last_mouse_pos = mouse_pos
    
    # Redraw immediately to show pan changes
    redraw_layout()
    pygame.display.flip()

def redraw_layout():
    """Redraws the screen with the cached layout, without regenerating."""
    # 1. Draw background
    main_area_rect = pygame.Rect(0, 0, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT)
    pygame.draw.rect(screen, DEFAULT_BACKGROUND_COLOR, main_area_rect)

    if current_background_surface:
        # Create a combined preview surface with image + text as one unit
        img_rect = current_background_surface.get_rect()
        preview_surface = pygame.Surface((img_rect.width, img_rect.height), pygame.SRCALPHA)
        
        # Draw the background image onto the preview surface
        preview_surface.blit(current_background_surface, (0, 0))
        
        # Calculate base position (centered) - MUST be calculated before using it
        base_img_x = (MAIN_AREA_WIDTH - img_rect.width) // 2
        base_img_y = (MAIN_AREA_HEIGHT - img_rect.height) // 2
        
        # Draw all text sprites onto the preview surface at their original positions
        # Always draw text sprites (both for normal view and mask overlay view)
        if 'placed_sprites_cache' in globals() and placed_sprites_cache:
            for sprite in placed_sprites_cache:
                # Calculate sprite position relative to the image (not the full canvas)
                # The sprites are positioned relative to the canvas, but we need them relative to the image
                sprite_x = sprite.rect.x - base_img_x
                sprite_y = sprite.rect.y - base_img_y
                preview_surface.blit(sprite.image, (sprite_x, sprite_y))
        
        # Apply zoom and pan to the entire preview surface
        if abs(zoom_level - 1.0) > 0.01:
            scaled_width = int(img_rect.width * zoom_level)
            scaled_height = int(img_rect.height * zoom_level)
            scaled_preview = pygame.transform.scale(preview_surface, (scaled_width, scaled_height))
            screen.blit(scaled_preview, (base_img_x + pan_offset_x, base_img_y + pan_offset_y))
        else:
            screen.blit(preview_surface, (base_img_x + pan_offset_x, base_img_y + pan_offset_y))
        
        # Store canvas offset for other functions
        canvas_offset_x = base_img_x + pan_offset_x
        canvas_offset_y = base_img_y + pan_offset_y
    else:
        canvas_offset_x, canvas_offset_y = 0, 0
        # Draw sprites directly if no background image
        if 'placed_sprites_cache' in globals() and placed_sprites_cache:
            for sprite in placed_sprites_cache:
                screen.blit(sprite.image, sprite.rect)

    # 2. Draw mask overlay if enabled (separate from the combined preview)
    if show_mask_overlay and 'placed_sprites_cache' in globals() and placed_sprites_cache:
        draw_mask_overlay(screen, placed_sprites_cache, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, current_background_surface, original_pil_image, MASK_GROW_PIXELS, grow_binary_mask_pil, zoom_level, pan_offset_x, pan_offset_y)
    
    # 2a. Draw debug regions if enabled
    if show_debug_regions:
        canvas_width, canvas_height = get_canvas_dimensions()
        draw_debug_regions(screen, W, H, PLACEMENT_REGIONS, current_background_surface, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, zoom_level, pan_offset_x, pan_offset_y, placed_points_cache)

    # 3. Draw UI elements
    if 'placed_sprites_cache' in globals() and placed_sprites_cache:
        draw_mask_panel(screen, placed_sprites_cache, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT, current_background_surface, original_pil_image, MASK_GROW_PIXELS, grow_binary_mask_pil, zoom_level, pan_offset_x, pan_offset_y)
    else:
        # Draw empty mask panel if no sprites
        mask_area_x = MAIN_AREA_WIDTH
        mask_panel_surface = pygame.Surface((W - MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT))
        mask_panel_surface.fill((50, 50, 50))
        screen.blit(mask_panel_surface, (mask_area_x, 0))
        pygame.draw.line(screen, (100, 100, 100), (mask_area_x, 0), (mask_area_x, MAIN_AREA_HEIGHT), 2)
    
    draw_info_bar(screen, W, MAIN_AREA_HEIGHT, INFO_BAR_HEIGHT, FORCE_REGIONS_ONLY, current_background_image, current_image_index, current_image_directory, layout_generation_count, last_layout_time)

def setup_ui_elements():
    """Create and configure all persistent UI elements."""
    global toggle_region_button

    # This function should only be called once to create the elements
    if toggle_region_button is not None:
        return

    button_text = f"Regions: {'ON' if FORCE_REGIONS_ONLY else 'OFF'}"
    button_width = 140
    button_height = 40
    button_x = (MAIN_AREA_WIDTH - button_width) / 2
    button_y = 10

    toggle_region_button = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((button_x, button_y), (button_width, button_height)),
        text=button_text,
        manager=ui_manager.manager,
        object_id='#toggle_region_button'
    )


def update_toggle_region_button_text():
    """Updates the text of the toggle region button to reflect the current state."""
    if toggle_region_button:
        button_text = f"Regions: {'ON' if FORCE_REGIONS_ONLY else 'OFF'}"
        toggle_region_button.set_text(button_text)


def layout(auto_advance_image=False, skip_redraw=False):
    global placed_sprites_cache, placed_points_cache, current_image_index, current_image_directory, current_background_image, current_background_surface, show_mask_overlay, layout_generation_count, last_layout_time, PLACEMENT_REGIONS
    
    # Performance monitoring
    import time
    start_time = time.time()
    layout_generation_count += 1
    
    # Auto-advance to next image if directory is loaded and requested
    if auto_advance_image and current_image_directory:
        advance_to_next_image()
    
    # Reload the active template in case it was changed externally or needs resetting
    _refresh_placement_regions()
    
    master_letter_sprites.empty()
    all_sprites_to_draw = []
    placed_points_cache.clear()
    used_fonts = []
    
    # Get canvas dimensions and offsets for placement logic
    canvas_width, canvas_height = get_canvas_dimensions()
    if current_background_image:
        canvas_offset_x, canvas_offset_y = get_canvas_offsets(current_background_image.size)
    else:
        canvas_offset_x, canvas_offset_y = 0, 0
    
    # --- Define dimensions for both 'fit' and 'stretch' modes ---
    fit_canvas_size = min(canvas_width, canvas_height)
    fit_canvas_offset_x = canvas_offset_x + (canvas_width - fit_canvas_size) // 2
    fit_canvas_offset_y = canvas_offset_y + (canvas_height - fit_canvas_size) // 2
    
    if FORCE_REGIONS_ONLY:
        # --- Region-driven layout composition ---
        # Here we iterate through regions and populate them based on their rules
        total_placed_count = 0
        total_words_attempted = 0
        if not BATCH_PROCESSING_MODE:
            console.print("\n--- Region Placement Report ---", style="bold magenta")

        for region in PLACEMENT_REGIONS:
            rules = region.get('rules', {})
            if 'word_count_range' not in rules:
                continue
            
            min_words, max_words = rules['word_count_range']
            if min_words > max_words: min_words = max_words # safety check
            num_words_to_place = random.randint(min_words, max_words)
            total_words_attempted += num_words_to_place
            
            placed_in_this_region = 0
            for _ in range(num_words_to_place):
                word = random.choice(WORDS)

                # Generate word properties based on region rules
                min_size, max_size = rules.get('size_range', (MIN_FONT_SIZE, MAX_FONT_SIZE))
                if min_size > max_size: min_size = max_size # Safety check
                size = random.randint(min_size, max_size)
                
                text_type_rule = rules.get('text_type', 'any')
                if text_type_rule == 'any':
                    text_type = random.choices(TEXT_TYPES, weights=TEXT_TYPE_WEIGHTS, k=1)[0]
                else:
                    text_type = text_type_rule

                font, font_identifier, font_display_name = get_font(size, custom_font_paths)
                color = get_random_color()
                
                # Generate sprites for the word
                if text_type == "normal":
                    new_sprites, word_bbox = create_normal_sprites(word, font, color, font_identifier, size, PADDING, padding_kernel_mask, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION)
                elif text_type == "arc": # arc
                    new_sprites, word_bbox = create_arc_sprites(word, font, color, font_identifier, size, ARC_MIN_RADIUS, ARC_MAX_RADIUS, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION, padding_kernel_mask)
                elif text_type == "asset":
                    if not ASSET_PATHS:
                        new_sprites, word_bbox = [], None
                    else:
                        asset_path = random.choice(ASSET_PATHS)
                        new_sprites, word_bbox = create_asset_sprite(asset_path, size, padding_kernel_mask)
                else:
                    new_sprites, word_bbox = [], None

                if not new_sprites:
                    continue

                # Try to place the word inside the CURRENT region
                for _ in range(MAX_PLACEMENT_TRIES):
                    # 1. Get a test center position inside the region, respecting its placement mode
                    test_pos_center = None
                    placement_mode = region.get('rules', {}).get('placement_mode', 'stretch')
                    all_x = [p[0] for p in region['shape']]
                    all_y = [p[1] for p in region['shape']]
                    
                    for _ in range(10): # Try 10 times to find a point
                        rand_rel_x = random.uniform(min(all_x), max(all_x))
                        rand_rel_y = random.uniform(min(all_y), max(all_y))
                        
                        if point_in_polygon(rand_rel_x, rand_rel_y, region['shape']):
                            if placement_mode == 'fit':
                                center_x = rand_rel_x * fit_canvas_size + fit_canvas_offset_x
                                center_y = rand_rel_y * fit_canvas_size + fit_canvas_offset_y
                            else: # stretch
                                center_x = rand_rel_x * canvas_width + canvas_offset_x
                                center_y = rand_rel_y * canvas_height + canvas_offset_y
                            test_pos_center = (int(center_x), int(center_y))
                            break
                    
                    if not test_pos_center:
                        continue

                    # 2. Validate the Proposed Position
                    is_valid_pos = True
                    word_rect = word_bbox.copy()
                    word_rect.center = test_pos_center
                    top_left_offset = word_rect.topleft

                    # New: Check if word is fully inside the polygon if rule is enabled
                    enforce_boundaries = rules.get('enforce_boundaries', False)
                    if enforce_boundaries:
                        # Get all four corners of the word's bounding box
                        corners = [
                            word_rect.topleft,
                            word_rect.topright,
                            word_rect.bottomleft,
                            word_rect.bottomright
                        ]
                        
                        # Convert each corner to relative coordinates and check if it's in the polygon
                        for corner_x, corner_y in corners:
                            # Convert absolute corner coordinates to relative coordinates for the check
                            if placement_mode == 'fit':
                                if fit_canvas_size == 0:
                                    is_valid_pos = False; break
                                rel_corner_x = (corner_x - fit_canvas_offset_x) / fit_canvas_size
                                rel_corner_y = (corner_y - fit_canvas_offset_y) / fit_canvas_size
                            else: # stretch
                                if canvas_width == 0 or canvas_height == 0:
                                    is_valid_pos = False; break
                                rel_corner_x = (corner_x - canvas_offset_x) / canvas_width
                                rel_corner_y = (corner_y - canvas_offset_y) / canvas_height
                            
                            if not point_in_polygon(rel_corner_x, rel_corner_y, region['shape']):
                                is_valid_pos = False
                                break # One corner out is enough to invalidate
                        if not is_valid_pos:
                            continue # Try a new random point

                    # Check canvas boundaries
                    if not is_within_canvas(word_rect, canvas_width, canvas_height, CANVAS_PADDING, canvas_offset_x, canvas_offset_y):
                        is_valid_pos = False
                    
                    if not is_valid_pos:
                        continue

                    # Check collision with existing letters
                    proposed_rects = [s.rect.move(top_left_offset) for s in new_sprites]
                    for i, sprite in enumerate(new_sprites):
                        original_rect = sprite.rect
                        sprite.rect = proposed_rects[i]
                        if pygame.sprite.spritecollide(sprite, master_letter_sprites, False, check_padded_collision):
                            is_valid_pos = False
                        sprite.rect = original_rect
                        if not is_valid_pos: break
                    
                    if is_valid_pos:
                        for i, sprite in enumerate(new_sprites):
                            sprite.rect = proposed_rects[i]
                        master_letter_sprites.add(new_sprites)
                        all_sprites_to_draw.extend(new_sprites)
                        used_fonts.append(f"{word} ({font_display_name}, {size}px)")
                        placed_in_this_region += 1
                        placed_points_cache.append(test_pos_center)
                        break # Successfully placed, move to next word
            
            # Log the result for the current region
            total_placed_count += placed_in_this_region
            if not BATCH_PROCESSING_MODE:
                console.print(f"  - {region['name']}: Placed {placed_in_this_region} out of {num_words_to_place} attempted words.")
        
        if not BATCH_PROCESSING_MODE:
            console.print("---------------------------------", style="bold magenta")
            console.print(f"Total: Placed {total_placed_count} out of {total_words_attempted} attempted words across all regions.")

    else:
        # --- Freeform layout generation ---
        num_words = random.randint(5, 15)
        placed_words_count = 0
        total_attempts = 0

        for _ in range(MAX_ATTEMPTS_TOTAL):
            if placed_words_count >= num_words:
                break
            
            total_attempts += 1
            word = random.choice(WORDS)
            
            # --- Hotspot/Random generation (original logic) ---
            size = random.randint(MIN_FONT_SIZE, MAX_FONT_SIZE)
            text_type = random.choices(TEXT_TYPES, weights=TEXT_TYPE_WEIGHTS, k=1)[0]
            
            font, font_identifier, font_display_name = get_font(size, custom_font_paths)
            color = get_random_color()
            
            if text_type == "normal":
                new_sprites, word_bbox = create_normal_sprites(word, font, color, font_identifier, size, PADDING, padding_kernel_mask, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION)
            elif text_type == "arc": # arc
                new_sprites, word_bbox = create_arc_sprites(word, font, color, font_identifier, size, ARC_MIN_RADIUS, ARC_MAX_RADIUS, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION, padding_kernel_mask)
            elif text_type == "asset":
                if not ASSET_PATHS:
                    new_sprites, word_bbox = [], None
                else:
                    asset_path = random.choice(ASSET_PATHS)
                    new_sprites, word_bbox = create_asset_sprite(asset_path, size, padding_kernel_mask)
            else:
                new_sprites, word_bbox = [], None

            if not new_sprites:
                continue

            # Find a valid position for the entire word on the canvas
            for _ in range(MAX_ATTEMPTS_PER_WORD):
                # 1. Determine Placement Strategy & Get a Test Center Position
                half_w, half_h = word_bbox.width // 2, word_bbox.height // 2
                rand_x_min = CANVAS_PADDING + half_w
                rand_x_max = canvas_width - CANVAS_PADDING - half_w
                rand_y_min = CANVAS_PADDING + half_h
                rand_y_max = canvas_height - CANVAS_PADDING - half_h
                
                if rand_x_min >= rand_x_max or rand_y_min >= rand_y_max:
                    break

                test_pos_center = (
                    random.randint(rand_x_min, rand_x_max) + canvas_offset_x,
                    random.randint(rand_y_min, rand_y_max) + canvas_offset_y
                )

                # 2. Validate the Proposed Position
                is_valid_pos = True
                word_rect = word_bbox.copy()
                word_rect.center = test_pos_center
                top_left_offset = word_rect.topleft

                # Region Rule Enforcement - must check all regions, respecting their individual modes
                for check_region in PLACEMENT_REGIONS:
                    check_mode = check_region.get('rules', {}).get('placement_mode', 'stretch')
                    
                    # Convert absolute center to relative coords for the region being checked
                    if check_mode == 'fit':
                        if fit_canvas_size == 0: continue # Avoid division by zero
                        relative_center_x = (test_pos_center[0] - fit_canvas_offset_x) / fit_canvas_size
                        relative_center_y = (test_pos_center[1] - fit_canvas_offset_y) / fit_canvas_size
                    else: # stretch
                        if canvas_width == 0 or canvas_height == 0: continue # Avoid division by zero
                        relative_center_x = (test_pos_center[0] - canvas_offset_x) / canvas_width
                        relative_center_y = (test_pos_center[1] - canvas_offset_y) / canvas_height

                    # Only check rules if the point is within the region's shape
                    if 0 <= relative_center_x <= 1 and 0 <= relative_center_y <= 1:
                        if point_in_polygon(relative_center_x, relative_center_y, check_region['shape']):
                            rules = check_region['rules']
                            
                            # Check text type
                            allowed_text_types = rules.get('text_types', ['any'])
                            if 'any' not in allowed_text_types and text_type not in allowed_text_types:
                                is_valid_pos = False; break
                                
                            # Check font size
                            min_size_rule, max_size_rule = rules.get('font_size_range', (MIN_FONT_SIZE, MAX_FONT_SIZE))
                            if not (min_size_rule <= size <= max_size_rule):
                                is_valid_pos = False; break
                if not is_valid_pos: continue

                # Canvas boundaries
                if not is_within_canvas(word_rect, canvas_width, canvas_height, CANVAS_PADDING, canvas_offset_x, canvas_offset_y):
                    is_valid_pos = False
                if not is_valid_pos: continue

                # Collision with existing letters
                proposed_rects = [s.rect.move(top_left_offset) for s in new_sprites]
                for i, sprite in enumerate(new_sprites):
                    original_rect = sprite.rect
                    sprite.rect = proposed_rects[i]
                    if pygame.sprite.spritecollide(sprite, master_letter_sprites, False, check_padded_collision):
                        is_valid_pos = False
                    sprite.rect = original_rect
                    if not is_valid_pos: break
                
                # 3. Success! Commit the placement
                if is_valid_pos:
                    for i, sprite in enumerate(new_sprites):
                        sprite.rect = proposed_rects[i]
                    master_letter_sprites.add(new_sprites)
                    all_sprites_to_draw.extend(new_sprites)
                    used_fonts.append(f"{word} ({font_display_name}, {size}px)")
                    placed_words_count += 1
                    placed_points_cache.append(test_pos_center)
                    break 
        
        if not BATCH_PROCESSING_MODE:
            logger.info(f"Placement Report: Placed {placed_words_count} out of {num_words} attempted words in {total_attempts} tries.")

    # --- Store the newly generated layout in the cache ---
    placed_sprites_cache = all_sprites_to_draw
    
    # --- Drawing Phase ---
    # Call the dedicated redraw function to put the new layout on screen
    if not skip_redraw and not BATCH_PROCESSING_MODE:
        redraw_layout()

    # Performance monitoring - end
    end_time = time.time()
    last_layout_time = end_time - start_time
    
    # Display used fonts information if enabled
    if SHOW_FONT_INFO and used_fonts and not BATCH_PROCESSING_MODE:
        font_text = Text()
        font_text.append("--- Font Usage for this layout ---\n", style="bold magenta")
        for font_entry in used_fonts:
            font_text.append(f"  {font_entry}\n")
        font_text.append(f"Total fonts used: {len(set(f.split('(')[1].split(',')[0] for f in used_fonts))}\n")
        font_text.append(f"Layout generation time: {last_layout_time:.3f}s\n")
        font_text.append("=" * 35, style="bold magenta")
        logger.info(Panel(font_text, expand=False, border_style="magenta"))

    update_toggle_region_button_text()

layout()                                            # draw once; call again if you want a new arrangement
setup_ui_elements()
controls_text = Text()
controls_text.append("--- TEXT OVERLAY DEMO CONTROLS ---\n", style="bold cyan")
controls_text.append("SPACE: Generate new layout + next image\n\n", style="green")
controls_text.append("--- Font Controls ---\n", style="bold yellow")
controls_text.append("F: Show font catalog\n")
controls_text.append("C: Set custom font directory\n")
controls_text.append("R: Reload fonts from default directory\n")
controls_text.append("Y: Switch to system fonts\n\n")
controls_text.append("--- Image Controls ---\n", style="bold yellow")
controls_text.append("I: Set image directory (IMG_DIR)\n")
controls_text.append("N: Next image (manual)\n")
controls_text.append("P: Previous image (manual)\n")
controls_text.append("X: Clear background image\n\n")
controls_text.append("--- Debug Controls ---\n", style="bold yellow")
controls_text.append("M: Toggle mask view (black/white masks on gray background)\n")
controls_text.append("D: Toggle region debug view (shows rule-based zones)\n")
controls_text.append("G: Toggle region constraint (force text only in zones)\n")
controls_text.append("E: Edit region templates\n")
controls_text.append("T: Switch between region templates\n\n")
controls_text.append("--- General ---\n", style="bold yellow")
controls_text.append("S: Save current layout and mask\n")
controls_text.append("O: Batch save multiple layouts (parallel processing)\n")
controls_text.append("ESC: Quit\n\n")
controls_text.append(f"Font source: {'Custom fonts' if custom_font_paths else 'System fonts'}\n")
if current_background_image:
    if current_image_directory:
        current_name = os.path.basename(current_image_directory[current_image_index])
        controls_text.append(f"Image: {current_name} ({current_image_index + 1}/{len(current_image_directory)})\n")
    else:
        controls_text.append("Image: Single image loaded\n")
else:
    controls_text.append("Background: Solid color\n")
if IMG_DIR:
    controls_text.append(f"IMG_DIR: {IMG_DIR}\n")
else:
    controls_text.append("IMG_DIR: Not set (edit script to add image directory)\n")
controls_text.append(f"Active Templates: {', '.join(ACTIVE_TEMPLATE_NAMES)}\n")
controls_text.append("Canvas: Using actual image dimensions for text placement")
logger.info(Panel(controls_text, expand=False, border_style="cyan"))

# Ensure first click that focuses the window is also delivered as a normal click (requires SDL ≥2.0.22)
os.environ.setdefault("SDL_MOUSE_FOCUS_CLICKTHROUGH", "1")

while True:
    time_delta = clock.tick(config.display.fps) / 1000.0
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT: 
            pygame.quit()
            sys.exit()
        
        # Allow active dialog to close itself
        if active_dialog and not active_dialog.is_alive:
            # Handle dialog results based on dialog type
            from utils.modern_ui import MultiTemplateSelectionDialog

            result = active_dialog.get_result()

            # Template selection handling
            if isinstance(active_dialog, MultiTemplateSelectionDialog):
                if result is not None:
                    selected, randomize = result
                    ACTIVE_TEMPLATE_NAMES = selected if selected else ["Default"]
                    RANDOMIZE_TEMPLATES = randomize
                    logger.info(f"Switched to templates: [bold cyan]{', '.join(ACTIVE_TEMPLATE_NAMES)}[/bold cyan] | Randomize: {RANDOMIZE_TEMPLATES}")
                    _refresh_placement_regions()
                    layout()
                    setup_ui_elements()

            # For other dialog types any necessary action was done via callback
            active_dialog = None  # Clear the dialog reference
            
        # Process UI events first
        ui_consumed = ui_manager.process_events(e)
        
        if ui_consumed:
            # Handle specific UI element events
            if e.type == pygame_gui.UI_BUTTON_PRESSED:
                if e.ui_element == toggle_region_button:
                    toggle_force_regions_only()
                    update_toggle_region_button_text()
                    layout()
        
        # Always clear dragging state on mouse button release (even if UI consumed the event)
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            is_dragging = False
        
        # Only process application events if UI didn't consume them
        if not ui_consumed:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    # Start panning only if click occurs inside the main canvas (avoid UI windows)
                    if e.pos[0] < MAIN_AREA_WIDTH:
                        is_dragging = True
                        last_mouse_pos = e.pos
            elif e.type == pygame.MOUSEBUTTONUP:
                if e.button == 1:
                    is_dragging = False
            elif e.type == pygame.MOUSEMOTION:
                if is_dragging:
                    handle_pan(e.pos)
            elif e.type == pygame.MOUSEWHEEL:
                zoom_direction = 1 if e.y > 0 else -1
                mouse_pos = pygame.mouse.get_pos()
                handle_zoom(mouse_pos, zoom_direction)
            
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    logger.debug("SPACE key pressed - generating new layout with auto-advance")
                    logger.debug(f"Before layout - current_image_index: {current_image_index}, directory length: {len(current_image_directory) if current_image_directory else 0}")
                    layout(auto_advance_image=True)
                    logger.debug(f"After layout - current_image_index: {current_image_index}")
                    if current_background_image:
                        if current_image_directory:
                            current_name = os.path.basename(current_image_directory[current_image_index])
                            logger.debug(f"Current image status: Image: {current_name} ({current_image_index + 1}/{len(current_image_directory)})")
                        else:
                            logger.debug("Current image status: Image: Single image loaded")
                    else:
                        logger.debug("Current image status: Background: Solid color")
                elif e.key == pygame.K_s:
                    save_output(placed_sprites_cache, SCRIPT_DIR, current_background_image, current_image_index, current_image_directory, original_pil_image, get_canvas_dimensions, get_canvas_offsets, pil_to_pygame_surface, MASK_GROW_PIXELS, grow_binary_mask_pil, create_final_mask_surface, get_cached_font, ROTATE_LETTERS_ON_ARC, MAX_ARC_LETTER_ROTATION, screen, MAIN_AREA_WIDTH, MAIN_AREA_HEIGHT)
                elif e.key == pygame.K_o:
                    batch_save()
                elif e.key == pygame.K_f:
                    # Use modern font catalog
                    if custom_font_paths:
                        font_list = custom_font_paths
                        title = f"Custom Fonts ({len(custom_font_paths)} total)"
                    else:
                        font_list = get_system_fonts()
                        title = f"System Fonts ({len(font_list)} total)"
                    show_modern_font_catalog(ui_manager, (W, H), font_list, title)
                elif e.key == pygame.K_h:
                    # Use modern controls help
                    show_modern_controls(ui_manager, (W, H))
                elif e.key == pygame.K_c:
                    logger.info("\n=== SET CUSTOM FONT DIRECTORY ===")
                    logger.info("Enter path to folder containing .ttf/.otf files")
                    logger.info("Example Windows: C:\\Windows\\Fonts")
                    logger.info("Example macOS: /System/Library/Fonts")
                    logger.info("Example Linux: /usr/share/fonts")
                    if not active_dialog:
                        def _on_font_dir_selected(dir_path):
                            set_font_directory(dir_path)
                            layout()

                        active_dialog = show_modern_directory_selection(
                            ui_manager,
                            (W, H),
                            title="Select Font Directory",
                            start_path=FONT_DIR or os.getcwd(),
                            callback=_on_font_dir_selected,
                        )
                elif e.key == pygame.K_r and pygame.key.get_pressed()[pygame.K_LSHIFT]:
                    reload_configuration()
                    logger.success("Configuration reloaded!")
                    layout()
                elif e.key == pygame.K_r:
                    logger.info("💡 [cyan]INFO:[/] Resetting to default font directory.")
                    set_font_directory(DEFAULT_FONT_DIR)
                    layout()
                elif e.key == pygame.K_y:
                    set_font_directory(None)
                    layout()
                elif e.key == pygame.K_x:
                    clear_background_image()
                    current_image_directory.clear()
                    current_image_index = -1
                    layout()
                elif e.key == pygame.K_m:
                    toggle_mask_overlay()
                    redraw_layout()
                elif e.key == pygame.K_d:
                    toggle_region_debug()
                    redraw_layout()
                elif e.key == pygame.K_g:
                    toggle_force_regions_only()
                    update_toggle_region_button_text()
                    layout()
                elif e.key == pygame.K_e:
                    # Open region editor
                    editor = RegionEditor(screen, region_manager, pygame.font.Font(None, 24), ACTIVE_TEMPLATE_NAMES[0])
                    editor.run()
                    # After editor exits, reload the template and redraw
                    # ACTIVE_TEMPLATE_NAMES = editor.get_active_template_name() # Get the latest template name
                    _refresh_placement_regions()
                    layout()
                elif e.key == pygame.K_t:
                    # Use modern template selection dialog
                    if not active_dialog: # Prevent opening multiple dialogs
                        all_templates = region_manager.get_template_names()
                        active_dialog = show_modern_template_selection(ui_manager, (W, H), all_templates, ACTIVE_TEMPLATE_NAMES)

                elif e.key == pygame.K_w:
                    reload_words()
                    layout()
                elif e.key == pygame.K_i:
                    logger.info("\n=== SET IMAGE DIRECTORY ===")
                    logger.info("Enter path to folder containing images (jpg, jpeg, png, bmp, tiff, tif, webp)")
                    logger.info("Example Windows: C:\\Users\\YourUsername\\Pictures")
                    logger.info("Example macOS: /Users/YourUsername/Pictures")
                    logger.info("Example Linux: /home/YourUsername/Pictures")
                    if not active_dialog:
                        def _on_img_dir_selected(dir_path):
                            set_image_directory(dir_path)
                            layout()

                        active_dialog = show_modern_directory_selection(
                            ui_manager,
                            (W, H),
                            title="Select Image Directory",
                            start_path=IMG_DIR or os.getcwd(),
                            callback=_on_img_dir_selected,
                        )
                elif e.key == pygame.K_n:
                    if current_image_directory and current_image_index >= 0:
                        current_image_index = (current_image_index + 1) % len(current_image_directory)
                        next_image = current_image_directory[current_image_index]
                        logger.info(f"Loading next image: {os.path.basename(next_image)} ({current_image_index + 1}/{len(current_image_directory)})")
                        if load_background_image(next_image):
                            layout()  # Redraw with new background
                    else:
                        logger.warning("No IMG_DIR loaded or no images found. Set IMG_DIR in the script.")
                elif e.key == pygame.K_p:
                    # Previous image in directory
                    if current_image_directory and current_image_index >= 0:
                        current_image_index = (current_image_index - 1) % len(current_image_directory)
                        prev_image = current_image_directory[current_image_index]
                        logger.info(f"Loading previous image: {os.path.basename(prev_image)} ({current_image_index + 1}/{len(current_image_directory)})")
                        if load_background_image(prev_image):
                            layout()
                    else:
                        logger.warning("No IMG_DIR loaded or no images found. Set IMG_DIR in the script.")
                elif e.key == pygame.K_z:
                    reset_zoom_and_pan()
                    redraw_layout()
                elif e.key == pygame.K_q:
                    reset_zoom_and_pan()
                    redraw_layout()
                elif e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
    
    # Update UI manager
    ui_manager.update(time_delta)
    
    # Draw application content
    redraw_layout()
    
    # Draw UI on top
    ui_manager.draw(screen)
    
    pygame.display.flip()
