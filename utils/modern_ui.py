import pygame
import pygame_gui
from pygame_gui.elements import UICheckBox
import sys
import os
import json
from typing import List, Tuple, Optional, Dict, Any

def create_font_sample_surface(width: int,
                               height: int,
                               font_path: str,
                               sample_text: str) -> pygame.Surface:
    """Return an opaque surface with the rendered sample text."""

    # -------- Surface ----------------------------------------------
    surface = pygame.Surface((width, height), flags=pygame.SRCALPHA)
    surface = surface.convert_alpha()          # <- IMPORTANT
    surface.fill((255, 255, 255, 255))         # solid white, opaque

    pygame.draw.rect(surface, (200, 200, 200), surface.get_rect(), 1)

    # -------- Load Font --------------------------------------------
    try:
        font = pygame.font.Font(font_path, 32) if os.path.isfile(font_path) \
               else pygame.font.SysFont(font_path, 32)

        text_surf = font.render(sample_text, True, (0, 0, 0))  # black text
    except Exception:
        err_font = pygame.font.Font(None, 20)
        text_surf = err_font.render("Font Error", True, (200, 0, 0))

    # -------- Scale if wider than panel ----------------------------
    if text_surf.get_width() > width - 20:
        scale = (width - 20) / text_surf.get_width()
        new_size = (max(1, int(text_surf.get_width()*scale)),
                    max(1, int(text_surf.get_height()*scale)))
        text_surf = pygame.transform.smoothscale(text_surf, new_size)

    # -------- Center ------------------------------------------------
    rect = text_surf.get_rect(center=surface.get_rect().center)
    surface.blit(text_surf, rect)

    return surface.convert()   # opaque RGB surface (no unexpected alpha)

class ModernUIManager:
    """Modern UI manager using pygame_gui for professional-looking interfaces."""
    
    def __init__(self, screen_size: Tuple[int, int], theme_path: Optional[str] = None):
        self.screen_size = screen_size
        self.manager = pygame_gui.UIManager(screen_size, theme_path)
        self.active_windows = []  # Store custom windows that need updates
        
        # Load a dark theme for better visual appeal
        self._setup_theme()
        
    def _setup_theme(self):
        """Setup a modern dark theme for the UI."""
        # Try to load theme from file first, fall back to embedded theme
        theme_file = 'theme.json'
        if os.path.exists(theme_file):
            try:
                with open(theme_file, 'r') as f:
                    theme_data = json.load(f)
                self.manager.get_theme().load_theme(theme_data)
                return
            except Exception:
                pass  # Fall back to embedded theme
        
        # Embedded theme as fallback
        theme_data = self._get_default_theme()
        self.manager.get_theme().load_theme(theme_data)
    
    def _get_default_theme(self) -> Dict:
        """Get the default embedded theme."""
        return {
            'defaults': {
                'colours': {
                    'normal_bg': '#25292e',
                    'hovered_bg': '#35393e', 
                    'disabled_bg': '#25292e',
                    'selected_bg': '#193754',
                    'dark_bg': '#15191e',
                    'normal_text': '#c5c6c7',
                    'hovered_text': '#FFFFFF',
                    'selected_text': '#FFFFFF',
                    'disabled_text': '#6d6d6d',
                    'link_text': '#0000EE',
                    'link_hover': '#2020FF',
                    'link_selected': '#551A8B',
                    'text_shadow': '#777777',
                    'normal_border': '#DDDDDD',
                    'hovered_border': '#B0B0B0',
                    'disabled_border': '#808080',
                    'selected_border': '#193754',
                    'active_border': '#193754',
                    'filled_bar': '#f4d58d',
                    'unfilled_bar': '#CCCCCC'
                }
            },
            'window': {
                'colours': {
                    'normal_bg': '#25292e',
                    'normal_border': '#DDDDDD',
                    'normal_text': '#c5c6c7'
                },
                'misc': {
                    'shape': 'rounded_rectangle',
                    'shape_corner_radius': '10',
                    'border_width': '2'
                }
            },
            'button': {
                'colours': {
                    'normal_bg': '#c5c6c7',
                    'hovered_bg': '#45a049',
                    'disabled_bg': '#cccccc',
                    'selected_bg': '#193754',
                    'normal_text': '#25292e',
                    'hovered_text': '#FFFFFF',
                    'selected_text': '#FFFFFF',
                    'disabled_text': '#999999'
                },
                'misc': {
                    'shape': 'rounded_rectangle',
                    'shape_corner_radius': '5',
                    'border_width': '1'
                }
            },
            '#light_panel': {
                'colours': {
                    'normal_bg': '#f8f9fa',
                    'normal_border': '#dee2e6'
                },
                'misc': {
                    'border_width': '1'
                }
            }
        }

    def update(self, time_delta: float):
        """Update the UI manager and custom windows."""
        self.manager.update(time_delta)
        
        # Update custom windows and remove closed ones
        self.active_windows = [w for w in self.active_windows if w.is_alive]
        for window in self.active_windows:
            if hasattr(window, 'update'):
                window.update(time_delta)
    
    def draw(self, screen: pygame.Surface):
        """Draw the UI manager to the screen."""
        self.manager.draw_ui(screen)
    
    def process_events(self, event: pygame.event.Event) -> bool:
        """Process events and return True if event was consumed by UI."""
        # Let custom windows handle events first
        for window in self.active_windows:
            if hasattr(window, 'handle_event'):
                window.handle_event(event)
        
        return self.manager.process_events(event)

class BatchSaveDialog:
    """Modern batch save dialog using pygame_gui."""
    
    def __init__(self, ui_manager: pygame_gui.UIManager, screen_size: Tuple[int, int], 
                 image_count: int):
        self.ui_manager = ui_manager
        self.image_count = image_count
        self.result = None
        self.is_alive = True
        
        # Dialog dimensions
        dialog_width = 500
        dialog_height = 400
        dialog_x = (screen_size[0] - dialog_width) // 2
        dialog_y = (screen_size[1] - dialog_height) // 2
        
        # Create main window
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height),
            manager=ui_manager,
            window_display_title='Batch Save Settings',
            object_id='#batch_save_window'
        )
        
        # Container for all elements
        container_rect = pygame.Rect(0, 0, dialog_width - 40, dialog_height - 80)
        self.container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=container_rect,
            manager=ui_manager,
            container=self.window
        )
        
        self._create_elements(dialog_width)
    
    def _create_elements(self, dialog_width: int):
        """Create all UI elements for the dialog."""
        y_pos = 10
        element_width = dialog_width - 80
        
        # Info label
        self.info_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_pos, element_width, 30),
            text=f'Process images from directory ({self.image_count} available)',
            manager=self.ui_manager,
            container=self.container
        )
        y_pos += 50
        
        # Number of images section
        self.count_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_pos, element_width, 25),
            text='Number of images to process:',
            manager=self.ui_manager,
            container=self.container
        )
        y_pos += 30
        
        # Slider for image count
        self.image_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(10, y_pos, element_width - 100, 20),
            start_value=min(10, self.image_count),
            value_range=(1, self.image_count),
            manager=self.ui_manager,
            container=self.container
        )
        
        # Value display
        self.value_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(element_width - 80, y_pos - 5, 70, 30),
            text=f'{int(self.image_slider.get_current_value())}',
            manager=self.ui_manager,
            container=self.container
        )
        y_pos += 50
        
        # Resize options section
        self.resize_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, y_pos, element_width, 25),
            text='Image resize options:',
            manager=self.ui_manager,
            container=self.container
        )
        y_pos += 30
        
        # Resize checkbox
        self.resize_checkbox = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, y_pos, 200, 30),
            text='☐ Resize Images',
            manager=self.ui_manager,
            container=self.container,
            object_id='#checkbox_button'
        )
        self.resize_enabled = False
        y_pos += 40
        
        # Megapixel dropdown
        self.megapixel_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=['Original', '1 MP', '2 MP', '4 MP', '8 MP'],
            starting_option='Original',
            relative_rect=pygame.Rect(10, y_pos, 200, 30),
            manager=self.ui_manager,
            container=self.container
        )
        self.megapixel_dropdown.disable()
        y_pos += 70
        
        # Buttons
        button_width = 100
        button_height = 35
        spacing = 20
        total_button_width = 2 * button_width + spacing
        button_start_x = (dialog_width - total_button_width) // 2 - 20
        
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_start_x, y_pos, button_width, button_height),
            text='Start',
            manager=self.ui_manager,
            container=self.container,
            object_id='#start_button'
        )
        
        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_start_x + button_width + spacing, y_pos, 
                                    button_width, button_height),
            text='Cancel',
            manager=self.ui_manager,
            container=self.container,
            object_id='#cancel_button'
        )
    
    def handle_event(self, event: pygame.event.Event):
        """Handle UI events."""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.start_button:
                    # Get selected values
                    image_count = int(self.image_slider.get_current_value())
                    megapixels = None
                    if self.resize_enabled:
                        mp_text = self.megapixel_dropdown.selected_option
                        # Handle case where selected_option might be a tuple
                        if isinstance(mp_text, tuple):
                            mp_text = mp_text[0] if mp_text else 'Original'
                        elif mp_text is None:
                            mp_text = 'Original'
                        if mp_text != 'Original':
                            megapixels = int(mp_text.split()[0])
                    
                    self.result = (image_count, megapixels)
                    self.close()
                    
                elif event.ui_element == self.cancel_button:
                    self.result = None
                    self.close()
                    
                elif event.ui_element == self.resize_checkbox:
                    self.resize_enabled = not self.resize_enabled
                    if self.resize_enabled:
                        self.resize_checkbox.set_text('☑ Resize Images')
                        self.megapixel_dropdown.enable()
                    else:
                        self.resize_checkbox.set_text('☐ Resize Images')
                        self.megapixel_dropdown.disable()
            
            elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.image_slider:
                    self.value_label.set_text(f'{int(self.image_slider.get_current_value())}')
            
            elif event.user_type == pygame_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.window:
                    self.result = None
                    self.close()
    
    def close(self):
        """Close the dialog."""
        self.is_alive = False
        self.window.kill()
    
    def get_result(self):
        """Get the dialog result."""
        return self.result

# ---------------------------------------------------------------------------
# Directory Picker (uses pygame_gui.UIFileDialog)
# ---------------------------------------------------------------------------


class DirectoryDialog:
    """Directory selection dialog wrapper that integrates with ModernUIManager."""

    def __init__(self, ui_manager: pygame_gui.UIManager, screen_size: Tuple[int, int],
                 title: str = "Select Directory", start_path: str = os.getcwd(),
                 callback=None):
        """Create a directory picking dialog.

        Args:
            ui_manager: The pygame_gui.UIManager instance.
            screen_size: Current screen size (width, height).
            title: Window title.
            start_path: Initial directory.
            callback: Optional callable invoked with the chosen directory when the
                      dialog is accepted.
        """

        self.ui_manager = ui_manager
        self.callback = callback  # function to call with selected dir
        self.result: Optional[str] = None
        self.is_alive = True

        # Reasonable default size & positioning
        width, height = 700, 500
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (screen_size[0] // 2, screen_size[1] // 2)

        self.window = pygame_gui.windows.UIFileDialog(
            rect=rect,
            manager=ui_manager,
            window_title=title,
            initial_file_path=start_path,
            allow_picking_directories=True,
            allow_existing_files_only=True,
        )

    # ------------------------------------------------------------------
    # Event handling & lifecycle
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED and event.ui_element == self.window:
                # User chose a directory
                self.result = event.text
                if self.callback:
                    self.callback(self.result)
                self.close()
            elif event.user_type == pygame_gui.UI_WINDOW_CLOSE and event.ui_element == self.window:
                # User closed the window without choosing
                self.result = None
                self.close()

    def update(self, time_delta: float):
        pass  # UIFileDialog updates internally via ui_manager

    def close(self):
        self.is_alive = False
        self.window.kill()

    def get_result(self):
        return self.result


# ---------------------------------------------------------------------------
# Font Catalog Window
# ---------------------------------------------------------------------------

class FontCatalogWindow:
    """Modern font catalog window using pygame_gui best practices with lazy loading."""
    
    def __init__(self, ui_manager: pygame_gui.UIManager, screen_size: Tuple[int, int],
                 font_list: List[str], title: str):
        self.ui_manager = ui_manager
        self.is_alive = True
        self.font_list = font_list
        
        # Pagination settings
        self.fonts_per_page = 50  # Load fonts in batches for better performance
        self.current_page = 0
        self.total_pages = (len(font_list) + self.fonts_per_page - 1) // self.fonts_per_page
        
        # Window dimensions
        window_width = 900
        window_height = 700
        window_x = (screen_size[0] - window_width) // 2
        window_y = (screen_size[1] - window_height) // 2
        
        # Create main window
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(window_x, window_y, window_width, window_height),
            manager=ui_manager,
            window_display_title=title,
            object_id='#font_catalog_window'
        )
        
        # Navigation panel
        nav_height = 40
        self.nav_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(10, 10, window_width - 40, nav_height),
            manager=ui_manager,
            container=self.window
        )
        
        # Navigation buttons
        self.prev_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 5, 80, 30),
            text='Previous',
            manager=ui_manager,
            container=self.nav_panel
        )
        
        self.next_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(100, 5, 80, 30),
            text='Next',
            manager=ui_manager,
            container=self.nav_panel
        )
        
        # Page info label
        self.page_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(200, 5, 200, 30),
            text=self._get_page_text(),
            manager=ui_manager,
            container=self.nav_panel
        )
        
        # Create scrolling container for font samples
        scroll_y = 10 + nav_height + 5
        scroll_height = window_height - 80 - nav_height - 5
        self.scroll_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect(10, scroll_y, window_width - 40, scroll_height),
            manager=ui_manager,
            container=self.window
        )
        
        # Create font sample panels for current page
        self._create_current_page()
        
        # Close button
        self.close_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(window_width - 100, window_height - 60, 80, 30),
            text='Close',
            manager=ui_manager,
            container=self.window
        )
        
        self._update_navigation_buttons()
    
    def _get_page_text(self) -> str:
        """Get the current page information text."""
        if self.total_pages == 0:
            return "No fonts available"
        return f"Page {self.current_page + 1} of {self.total_pages} ({len(self.font_list)} total fonts)"
    
    def _update_navigation_buttons(self):
        """Update the state of navigation buttons."""
        # Enable/disable buttons based on current page
        if self.current_page <= 0:
            self.prev_button.disable()
        else:
            self.prev_button.enable()
            
        if self.current_page >= self.total_pages - 1:
            self.next_button.disable()
        else:
            self.next_button.enable()
            
        self.page_label.set_text(self._get_page_text())
    
    def _clear_current_page(self):
        """Clear all elements from the scroll container."""
        # Kill all child elements
        for element in list(self.scroll_container.get_container().elements):
            element.kill()
    
    def _create_current_page(self):
        """Create font sample panels for the current page only."""
        self._clear_current_page()
        
        panel_height = 80
        panel_width = self.scroll_container.rect.width - 40
        y_offset = 0
        sample_text = "The quick brown fox jumps over lazy dog 1234567890"
        
        # Calculate font range for current page
        start_idx = self.current_page * self.fonts_per_page
        end_idx = min(start_idx + self.fonts_per_page, len(self.font_list))
        
        for local_i, font_idx in enumerate(range(start_idx, end_idx)):
            font_path = self.font_list[font_idx]
            global_i = font_idx  # Global index for numbering
            
            # Create panel for this font with light background
            panel = pygame_gui.elements.UIPanel(
                relative_rect=pygame.Rect(10, y_offset, panel_width, panel_height),
                manager=self.ui_manager,
                container=self.scroll_container,
                object_id='#light_panel'
            )
            
            # Font name and index
            font_name = os.path.basename(font_path) if os.path.isfile(font_path) else font_path
            if len(font_name) > 35:
                font_name = font_name[:32] + "..."
            
            # Font index and name
            index_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(5, 5, 50, 25),
                text=f"{global_i + 1:3d}.",
                manager=self.ui_manager,
                container=panel
            )
            
            name_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(60, 5, 300, 25),
                text=font_name,
                manager=self.ui_manager,
                container=panel
            )
            
            # Create font sample surface and display via UIImage
            try:
                sample_surface = create_font_sample_surface(
                    panel_width - 15,
                    40,
                    font_path,
                    sample_text
                )
                pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect(5, 35, panel_width - 15, 40),
                    image_surface=sample_surface,
                    manager=self.ui_manager,
                    container=panel
                )
            except Exception as e:
                # Fallback error label if any issue creating surface
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(5, 35, panel_width - 15, 40),
                    text=f"Failed to load font: {str(e)[:30]}...",
                    manager=self.ui_manager,
                    container=panel
                )
            
            y_offset += panel_height + 5
        
        # Set the scrolling container's scrollable area
        self.scroll_container.set_scrollable_area_dimensions((panel_width + 20, max(y_offset, self.scroll_container.rect.height)))
    
    def _next_page(self):
        """Go to the next page of fonts."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._create_current_page()
            self._update_navigation_buttons()
    
    def _prev_page(self):
        """Go to the previous page of fonts."""
        if self.current_page > 0:
            self.current_page -= 1
            self._create_current_page()
            self._update_navigation_buttons()
    
    def update(self, time_delta):
        """Update the window - no need for manual rendering with custom elements."""
        # Custom UIFontSample elements handle their own rendering
        pass
    
    def handle_event(self, event: pygame.event.Event):
        """Handle UI events."""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.close_button:
                    self.close()
                elif event.ui_element == self.next_button:
                    self._next_page()
                elif event.ui_element == self.prev_button:
                    self._prev_page()
            elif event.user_type == pygame_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.window:
                    self.close()
    
    def close(self):
        """Close the window."""
        self.is_alive = False
        self.window.kill()

class ControlsHelpWindow:
    """Modern controls help window using pygame_gui."""
    
    def __init__(self, ui_manager: pygame_gui.UIManager, screen_size: Tuple[int, int]):
        self.ui_manager = ui_manager
        self.is_alive = True
        
        # Window dimensions
        window_width = 800
        window_height = 700
        window_x = (screen_size[0] - window_width) // 2
        window_y = (screen_size[1] - window_height) // 2
        
        # Create main window
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(window_x, window_y, window_width, window_height),
            manager=ui_manager,
            window_display_title='Controls & Shortcuts',
            object_id='#controls_window'
        )
        
        # Create controls content
        html_content = self._create_controls_html()
        
        self.text_box = pygame_gui.elements.UITextBox(
            html_text=html_content,
            relative_rect=pygame.Rect(10, 10, window_width - 40, window_height - 80),
            manager=ui_manager,
            container=self.window
        )
        
        # Close button
        self.close_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(window_width - 100, window_height - 60, 80, 30),
            text='Close',
            manager=ui_manager,
            container=self.window
        )
    
    def _create_controls_html(self) -> str:
        """Create HTML content for controls help."""
        controls_data = [
            ("General Controls", [
                ("SPACE", "Generate new layout + next image"),
                ("S", "Save current layout and mask"),
                ("O", "Batch save multiple layouts"),
                ("H", "Show this help window"),
                ("ESC", "Quit application")
            ]),
            ("View Controls", [
                ("Mouse Wheel", "Zoom in/out"),
                ("Left Click + Drag", "Pan around image"),
                ("Z / Q", "Reset zoom and pan")
            ]),
            ("Font Controls", [
                ("F", "Show font catalog"),
                ("C", "Set custom font directory"),
                ("R", "Reload fonts from default directory"),
                ("Y", "Switch to system fonts")
            ]),
            ("Image Controls", [
                ("I", "Set image directory"),
                ("N", "Next image (manual)"),
                ("P", "Previous image (manual)"),
                ("X", "Clear background image")
            ]),
            ("Debug Controls", [
                ("M", "Toggle mask view"),
                ("D", "Toggle region debug view"),
                ("G", "Toggle region constraint"),
                ("E", "Edit region templates"),
                ("T", "Switch between templates")
            ])
        ]
        
        html = "<font color='#c5c6c7'>"
        
        for section_title, controls in controls_data:
            html += f"<p><font size=5 color='#f4d58d'><b>{section_title}</b></font></p>"
            
            for key, description in controls:
                html += f"<p><font color='#45a049'><b>{key:15}</b></font> {description}</p>"
            
            html += "<br>"
        
        html += "</font>"
        return html
    
    def handle_event(self, event: pygame.event.Event):
        """Handle UI events."""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.close_button:
                    self.close()
            elif event.user_type == pygame_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.window:
                    self.close()
    
    def close(self):
        """Close the window."""
        self.is_alive = False
        self.window.kill()

class MultiTemplateSelectionDialog:
    """Modern template selection dialog using pygame_gui."""
    
    def __init__(self, ui_manager: pygame_gui.UIManager, screen_size: Tuple[int, int],
                 templates: List[str], active_templates: List[str]):
        self.ui_manager = ui_manager
        self.templates = templates
        self.result = None
        self.is_alive = True
        
        # Dialog dimensions
        dialog_width = 400
        dialog_height = min(500, 200 + len(templates) * 40)
        dialog_x = (screen_size[0] - dialog_width) // 2
        dialog_y = (screen_size[1] - dialog_height) // 2
        
        # Create main window
        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height),
            manager=ui_manager,
            window_display_title='Select Region Templates',
            object_id='#template_dialog'
        )
        
        # Selection list with multi-select enabled
        self.selection_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(20, 20, dialog_width - 60, dialog_height - 120),
            item_list=templates,
            manager=ui_manager,
            container=self.window,
            allow_multi_select=True,
            default_selection=active_templates if active_templates else None
        )
        
        # Randomize checkbox
        checkbox_y = dialog_height - 90
        self.randomize_checkbox = UICheckBox(
            relative_rect=pygame.Rect(20, checkbox_y, 30, 30),
            text='Randomize selected',
            manager=ui_manager,
            container=self.window,
            initial_state=False,
            object_id='#randomize_checkbox'
        )

        # Buttons
        button_y = dialog_height - 80
        self.ok_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(dialog_width - 180, button_y, 70, 30),
            text='OK',
            manager=ui_manager,
            container=self.window
        )
        
        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(dialog_width - 100, button_y, 70, 30),
            text='Cancel',
            manager=ui_manager,
            container=self.window
        )
    
    def handle_event(self, event: pygame.event.Event):
        """Handle UI events."""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.ok_button:
                    # Capture checkbox state when confirming
                    self.result = (self.selection_list.get_multi_selection(), self.randomize_checkbox.is_checked)
                    self.close()
                elif event.ui_element == self.cancel_button:
                    self.result = None
                    self.close()
            elif event.user_type == pygame_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.window:
                    self.result = None
                    self.close()
    
    def close(self):
        """Close the dialog."""
        self.is_alive = False
        self.window.kill()
    
    def get_result(self):
        """Get the dialog result. Returns tuple (templates_list, randomize_bool) or None."""
        return self.result

# Convenience functions to replace the old UI system
def show_modern_batch_save_popup(ui_manager: ModernUIManager, screen_size: Tuple[int, int], 
                                image_count: int) -> Optional[Tuple[int, Optional[int]]]:
    """Show modern batch save dialog and return result."""
    dialog = BatchSaveDialog(ui_manager.manager, screen_size, image_count)
    
    clock = pygame.time.Clock()
    while dialog.is_alive:
        time_delta = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # The dialog and the main UI manager need to process events
            dialog.handle_event(event)
            ui_manager.process_events(event)
        
        # Update the UI
        ui_manager.update(time_delta)
        
        # We must draw the screen and the UI manager to see the dialog
        screen = pygame.display.get_surface()
        screen.fill((30, 30, 30))  # Background during dialog
        ui_manager.draw(screen)
        pygame.display.flip()
    
    return dialog.get_result()

def show_modern_font_catalog(ui_manager: ModernUIManager, screen_size: Tuple[int, int],
                           font_list: List[str], title: str):
    """Show modern font catalog window."""
    window = FontCatalogWindow(ui_manager.manager, screen_size, font_list, title)
    
    # Store the window for updates
    ui_manager.active_windows.append(window)
    
    return window

def show_modern_controls(ui_manager: ModernUIManager, screen_size: Tuple[int, int]):
    """Show modern controls help window."""
    window = ControlsHelpWindow(ui_manager.manager, screen_size)
    
    # Window will be handled by the main UI manager
    ui_manager.active_windows.append(window)
    return window

def show_modern_template_selection(ui_manager: ModernUIManager, screen_size: Tuple[int, int],
                                 templates: List[str], active_templates: List[str]) -> MultiTemplateSelectionDialog:
    """Show modern template selection dialog and return the dialog instance."""
    dialog = MultiTemplateSelectionDialog(ui_manager.manager, screen_size, templates, active_templates)
    ui_manager.active_windows.append(dialog)
    return dialog 

# ---------------------------------------------------------------------------
# Directory Picker (uses pygame_gui.UIFileDialog)
# ---------------------------------------------------------------------------


def show_modern_directory_selection(ui_manager: 'ModernUIManager', screen_size: Tuple[int, int],
                                    title: str, start_path: str, callback=None) -> DirectoryDialog:
    """Open a directory selection dialog and return the wrapper instance."""
    dialog = DirectoryDialog(ui_manager.manager, screen_size, title, start_path, callback)
    ui_manager.active_windows.append(dialog)
    return dialog 