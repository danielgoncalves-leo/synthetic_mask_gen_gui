import pygame
from PIL import Image, ImageFilter
import numpy as np

def pil_to_pygame_surface(pil_image):
    """Convert PIL Image to pygame surface."""
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    img_string = pil_image.tobytes()
    surface = pygame.image.fromstring(img_string, pil_image.size, pil_image.mode)
    return surface

def fit_image_to_canvas(pil_image, canvas_width, canvas_height):
    """Resize PIL image to fit within canvas while maintaining aspect ratio."""
    img_width, img_height = pil_image.size
    
    scale_x = canvas_width / img_width
    scale_y = canvas_height / img_height
    scale = min(scale_x, scale_y)
    
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    
    fitted_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return fitted_image

def grow_binary_mask_pil(mask_surface, grow_pixels):
    """
    Grow the white regions of a binary mask using PIL's MaxFilter (dilation).
    This is the standard approach for expanding white regions in binary images.
    
    Args:
        mask_surface: pygame Surface with black (0,0,0) and white (255,255,255) pixels
        grow_pixels: number of pixels to grow the white regions by
    
    Returns:
        pygame Surface with grown white regions
    """
    if grow_pixels <= 0:
        return mask_surface
    
    try:
        surface_data = pygame.image.tostring(mask_surface, 'RGB')
        pil_image = Image.frombytes('RGB', mask_surface.get_size(), surface_data)
        gray_image = pil_image.convert('L')
        
        filter_size = grow_pixels * 2 + 1
        dilated_image = gray_image.filter(ImageFilter.MaxFilter(filter_size))
        
        binary_array = np.array(dilated_image)
        binary_array = np.where(binary_array > 128, 255, 0).astype(np.uint8)
        binary_image = Image.fromarray(binary_array, mode='L')
        rgb_image = binary_image.convert('RGB')
        
        rgb_data = rgb_image.tobytes()
        new_surface = pygame.image.fromstring(rgb_data, rgb_image.size, 'RGB')
        
        return new_surface
        
    except Exception as e:
        print(f"WARNING: Failed to grow mask using PIL method: {e}")
        print("Falling back to original surface")
        return mask_surface

def create_final_mask_surface(placed_sprites, canvas_width, canvas_height, canvas_offset_x, canvas_offset_y):
    """Creates a clean, black and white surface of the mask, perfectly sized to the canvas."""
    mask_surface = pygame.Surface((canvas_width, canvas_height))
    mask_surface.fill((0, 0, 0))
    
    for sprite in placed_sprites:
        relative_pos = (sprite.rect.x - canvas_offset_x, sprite.rect.y - canvas_offset_y)
        mask_surf = sprite.mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
        mask_surf.set_colorkey((0, 0, 0))
        mask_surface.blit(mask_surf, relative_pos)
        
    return mask_surface 