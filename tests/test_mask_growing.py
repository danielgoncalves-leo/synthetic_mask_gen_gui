#!/usr/bin/env python3
"""
Test script for the mask growing functionality
"""

import pygame
import numpy as np
from PIL import Image, ImageFilter
import os

# Initialize pygame
pygame.init()

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
        print(f"DEBUG: Starting mask growth process...")
        print(f"DEBUG: Original mask size: {mask_surface.get_size()}")
        
        # Convert pygame surface to PIL Image
        # Get the surface data as a string
        surface_data = pygame.image.tostring(mask_surface, 'RGB')
        
        # Create PIL Image from the data
        pil_image = Image.frombytes('RGB', mask_surface.get_size(), surface_data)
        print(f"DEBUG: Converted to PIL Image: {pil_image.size}, mode: {pil_image.mode}")
        
        # Convert to grayscale for binary processing
        gray_image = pil_image.convert('L')
        print(f"DEBUG: Converted to grayscale: {gray_image.size}, mode: {gray_image.mode}")
        
        # Apply MaxFilter (dilation) to grow white regions
        # MaxFilter size should be grow_pixels * 2 + 1 for proper dilation
        filter_size = grow_pixels * 2 + 1
        print(f"DEBUG: Applying MaxFilter with size {filter_size}")
        dilated_image = gray_image.filter(ImageFilter.MaxFilter(filter_size))
        
        # Convert back to binary (ensure pure black/white)
        # Threshold at 128 to ensure binary output
        binary_array = np.array(dilated_image)
        print(f"DEBUG: Binary array shape: {binary_array.shape}, dtype: {binary_array.dtype}")
        print(f"DEBUG: Binary array min: {binary_array.min()}, max: {binary_array.max()}")
        
        binary_array = np.where(binary_array > 128, 255, 0).astype(np.uint8)
        print(f"DEBUG: After thresholding - min: {binary_array.min()}, max: {binary_array.max()}")
        
        binary_image = Image.fromarray(binary_array, 'L')
        
        # Convert back to RGB for pygame
        rgb_image = binary_image.convert('RGB')
        
        # Convert PIL Image back to pygame Surface
        rgb_data = rgb_image.tobytes()
        new_surface = pygame.image.fromstring(rgb_data, rgb_image.size, 'RGB')
        
        print(f"DEBUG: Successfully created new surface: {new_surface.get_size()}")
        return new_surface
        
    except Exception as e:
        print(f"WARNING: Failed to grow mask using PIL method: {e}")
        import traceback
        traceback.print_exc()
        print("Falling back to original surface")
        return mask_surface

def create_test_mask():
    """Create a simple test mask with some white text on black background"""
    # Create a surface
    surface = pygame.Surface((200, 100))
    surface.fill((0, 0, 0))  # Black background
    
    # Add some white text
    font = pygame.font.Font(None, 36)
    text_surface = font.render("TEST", True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(100, 50))
    surface.blit(text_surface, text_rect)
    
    return surface

def main():
    print("=== Testing Mask Growing Functionality ===")
    
    # Create test mask
    print("Creating test mask...")
    test_mask = create_test_mask()
    
    # Save original
    pygame.image.save(test_mask, "test_original_mask.png")
    print("Saved original mask as test_original_mask.png")
    
    # Test growing by different amounts
    for grow_pixels in [1, 2, 3, 5]:
        print(f"\n--- Testing growth by {grow_pixels} pixels ---")
        grown_mask = grow_binary_mask_pil(test_mask, grow_pixels)
        
        # Save grown mask
        filename = f"test_grown_mask_{grow_pixels}px.png"
        pygame.image.save(grown_mask, filename)
        print(f"Saved grown mask as {filename}")
    
    print("\n=== Test Complete ===")
    print("Check the generated PNG files to verify the mask growing works correctly.")

if __name__ == "__main__":
    main() 