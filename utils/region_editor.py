import pygame
import pygame_gui
import sys
import math
from .geometry_utils import point_in_polygon
from pygame_gui.elements import UIWindow, UIButton, UILabel, UITextEntryLine, UISelectionList, UIPanel, UIDropDownMenu
from pygame_gui.windows import UIConfirmationDialog, UIMessageWindow

class RegionEditor:
    def __init__(self, screen, region_manager, font, template_name="Default"):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.region_manager = region_manager
        self.font = font
        self.clock = pygame.time.Clock()

        # UI constants
        self.SIDEBAR_WIDTH = 300
        self.TOP_TOOLBAR_HEIGHT = 60
        self.BOTTOM_TOOLBAR_HEIGHT = 40
        
        # Initialize pygame-gui
        self.ui_manager = pygame_gui.UIManager((self.w, self.h), 'theme.json')
        
        # Editor state
        self.running = True
        self.active_template_name = template_name
        self.regions = self.region_manager.get_template(self.active_template_name)
        self.selected_region_idx = None
        self.selected_point_idx = None
        self.hovered_point_idx = None
        self.hovered_region_idx = None
        self.dragging_point = False
        self.dragging_region = False
        self.drag_start_mouse_pos = (0, 0)
        self.original_points_on_drag_start = []
        self.grid_snap_enabled = False
        self.snap_grid_size = 25
        self.aspect_mode = 'horizontal' # 'horizontal' or 'vertical'
        self.POINT_SELECTION_RADIUS = 15

        # UI Elements
        self.sidebar_panel = None
        self.property_ui_elements = {}
        self.toggle_aspect_button = None
        self.bottom_toolbar = None
        
        # Calculate canvas geometry
        self.setup_canvas_rect()

        # Colors
        self.colors = {
            'bg': (20, 20, 30), 'grid': (40, 40, 50), 'canvas_bg': (30, 30, 40),
            'region_fill': (100, 100, 200, 100), 'region_outline': (150, 150, 255),
            'selected_region_fill': (120, 180, 255, 120), 'selected_region_outline': (255, 255, 0),
            'point': (255, 255, 255), 'selected_point': (255, 0, 0), 'hovered_point': (255, 255, 0), 'text': (220, 220, 220),
        }

        self.setup_ui()

    def get_active_template_name(self):
        return self.active_template_name

    def setup_canvas_rect(self):
        """Calculates the canvas rect based on the current aspect mode to fit available space."""
        available_w = self.w - self.SIDEBAR_WIDTH
        available_h = self.h - self.TOP_TOOLBAR_HEIGHT - self.BOTTOM_TOOLBAR_HEIGHT
        
        if self.aspect_mode == 'horizontal':
            ratio = 16 / 9
            canvas_w = available_w
            canvas_h = canvas_w / ratio
            if canvas_h > available_h:
                canvas_h = available_h
                canvas_w = canvas_h * ratio
        else:  # vertical
            ratio = 9 / 16
            canvas_h = available_h
            canvas_w = canvas_h * ratio
            if canvas_w > available_w:
                canvas_w = available_w
                canvas_h = canvas_w / ratio

        offset_x = (available_w - canvas_w) / 2
        offset_y = self.TOP_TOOLBAR_HEIGHT + (available_h - canvas_h) / 2
        self.canvas_rect = pygame.Rect(offset_x, offset_y, canvas_w, canvas_h)

    def setup_ui(self):
        """Setup the main UI layout: top toolbar and sidebar."""
        # --- Top Toolbar ---
        self.top_toolbar = UIPanel(pygame.Rect(0, 0, self.w, self.TOP_TOOLBAR_HEIGHT), manager=self.ui_manager, object_id='#top_toolbar')
        
        button_y = 10
        button_h = self.TOP_TOOLBAR_HEIGHT - 20
        
        # Left-aligned buttons
        x_pos = 10
        self.new_template_button = UIButton(pygame.Rect(x_pos, button_y, 120, button_h), 'New Template', self.ui_manager, self.top_toolbar)
        x_pos += 130
        self.switch_template_button = UIButton(pygame.Rect(x_pos, button_y, 130, button_h), 'Switch Template', self.ui_manager, self.top_toolbar)
        x_pos += 140
        self.rename_template_button = UIButton(pygame.Rect(x_pos, button_y, 130, button_h), 'Rename Template', self.ui_manager, self.top_toolbar)
        x_pos += 140
        self.delete_template_button = UIButton(pygame.Rect(x_pos, button_y, 130, button_h), 'Delete Template', self.ui_manager, self.top_toolbar, object_id='#delete_button')
        x_pos += 140
        self.reload_button = UIButton(pygame.Rect(x_pos, button_y, 100, button_h), 'Reload', self.ui_manager, self.top_toolbar)
        
        # Center template name label - calculate available space to avoid overlap
        left_buttons_end = x_pos + 100 + 20  # End of reload button + padding
        right_buttons_start = self.w - 10 - 120 - 90 - 140 - 140 - 20  # Start of right buttons - padding
        available_center_width = max(200, right_buttons_start - left_buttons_end)  # Minimum 200px width
        
        template_label_rect = pygame.Rect(0, button_y, min(300, available_center_width), button_h)
        template_label_rect.centerx = (left_buttons_end + right_buttons_start) // 2
        self.template_name_label = UILabel(template_label_rect, f"Current: {self.active_template_name}", self.ui_manager, self.top_toolbar, object_id='#template_label')
        
        # Right-aligned buttons
        x_pos = self.w - 10
        x_pos -= 120
        self.save_exit_button = UIButton(pygame.Rect(x_pos, button_y, 120, button_h), 'Save & Exit', self.ui_manager, self.top_toolbar, object_id='#save_button')
        x_pos -= 90
        self.save_button = UIButton(pygame.Rect(x_pos, button_y, 80, button_h), 'Save', self.ui_manager, self.top_toolbar, object_id='#save_button')
        x_pos -= 140
        self.add_region_button = UIButton(pygame.Rect(x_pos, button_y, 130, button_h), 'Add New Region', self.ui_manager, self.top_toolbar)
        x_pos -= 140
        self.toggle_aspect_button = UIButton(pygame.Rect(x_pos, button_y, 130, button_h), 'Aspect: Horizontal', self.ui_manager, self.top_toolbar)

        # --- Sidebar ---
        sidebar_height = self.h - self.TOP_TOOLBAR_HEIGHT - self.BOTTOM_TOOLBAR_HEIGHT
        self.sidebar_panel = UIPanel(
            pygame.Rect(self.w - self.SIDEBAR_WIDTH, self.TOP_TOOLBAR_HEIGHT, self.SIDEBAR_WIDTH, sidebar_height),
            manager=self.ui_manager,
            object_id='#sidebar'
        )
        self.redraw_sidebar()

        # --- Bottom Toolbar ---
        self.bottom_toolbar = UIPanel(pygame.Rect(0, self.h - self.BOTTOM_TOOLBAR_HEIGHT, self.w , self.BOTTOM_TOOLBAR_HEIGHT), manager=self.ui_manager, object_id='#top_toolbar')

    def run(self):
        """Main loop for the editor."""
        while self.running:
            time_delta = self.clock.tick(60) / 1000.0
            
            self.handle_events()
            
            self.ui_manager.update(time_delta)
            self.draw()
            
            pygame.display.flip()
    
    def handle_events(self):
        """Process all pygame and pygame-gui events."""
        for event in pygame.event.get():
            handled_by_gui = self.ui_manager.process_events(event)

            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                self.handle_button_press(event.ui_element)
            
            if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                # Handle dropdown changes immediately
                pass

            # --- Explicit Mouse Handling for Canvas ---
            # We process canvas clicks directly to avoid conflicts where a UI panel 
            # might consume the event, forcing a user to click twice.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if the click is on the canvas and not on any UI element
                if self.canvas_rect.collidepoint(event.pos) and not handled_by_gui:
                    self.handle_mouse_down(event.pos)
                    continue # Skip further processing for this event
            
            self.handle_keyboard_events(event)

            if not handled_by_gui:
                self.handle_mouse_events(event)
    
    def handle_keyboard_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                self.grid_snap_enabled = True
            elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                if self.selected_region_idx is not None and self.selected_point_idx is not None:
                    self.delete_selected_point()
                elif self.selected_region_idx is not None:
                    self.delete_selected_region()
            elif event.key == pygame.K_a:
                 self.add_point_to_selected_region()
            elif event.key == pygame.K_ESCAPE:
                self.running = False

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                self.grid_snap_enabled = False

    def handle_mouse_events(self, event):
        mouse_pos = pygame.mouse.get_pos()
        
        if not self.canvas_rect.collidepoint(mouse_pos):
            return

        # MOUSEBUTTONDOWN is now handled in the main event loop to avoid the double-click issue.
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_point = False
            self.dragging_region = False

        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(mouse_pos)
            
    def handle_mouse_down(self, mouse_pos):
        """Handle mouse clicks on the canvas for selection and dragging."""
        canvas_x, canvas_y = mouse_pos[0] - self.canvas_rect.x, mouse_pos[1] - self.canvas_rect.y
        rel_x, rel_y = canvas_x / self.canvas_rect.width, canvas_y / self.canvas_rect.height

        # Check for point selection first
        if self.select_point_at(mouse_pos):
            self.dragging_point = True
            return

        # Then check for region selection
        if self.select_region_at(rel_x, rel_y):
            self.dragging_region = True
            self.drag_start_mouse_pos = mouse_pos
            self.original_points_on_drag_start = [list(p) for p in self.regions[self.selected_region_idx]['shape']]
            return

        # If click is on empty space, deselect
        self.selected_region_idx = None
        self.selected_point_idx = None
        self.redraw_sidebar()
    
    def select_point_at(self, mouse_pos):
        """Selects a vertex if the mouse is close enough."""
        # Check all regions, starting from the top-most one.
        for region_idx in range(len(self.regions) - 1, -1, -1):
            region = self.regions[region_idx]
            mode = region.get('rules', {}).get('placement_mode', 'stretch')
            
            fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
            fit_offset_x = (self.canvas_rect.width - fit_size) / 2
            fit_offset_y = (self.canvas_rect.height - fit_size) / 2
            
            for point_idx, point in enumerate(region['shape']):
                if mode == 'fit':
                    px = self.canvas_rect.x + fit_offset_x + point[0] * fit_size
                    py = self.canvas_rect.y + fit_offset_y + point[1] * fit_size
                else: # stretch
                    px = self.canvas_rect.x + point[0] * self.canvas_rect.width
                    py = self.canvas_rect.y + point[1] * self.canvas_rect.height
                
                if math.hypot(px - mouse_pos[0], py - mouse_pos[1]) < self.POINT_SELECTION_RADIUS:
                    self.selected_region_idx = region_idx
                    self.selected_point_idx = point_idx
                    self.redraw_sidebar()
                    return True
        return False

    def select_region_at(self, rel_x, rel_y):
        """Selects the top-most region at a given relative position."""
        fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
        fit_offset_x = (self.canvas_rect.width - fit_size) / 2 if fit_size > 0 else 0
        fit_offset_y = (self.canvas_rect.height - fit_size) / 2 if fit_size > 0 else 0
        
        for i in range(len(self.regions) - 1, -1, -1):
            region = self.regions[i]
            mode = region.get('rules', {}).get('placement_mode', 'stretch')
            if isinstance(mode, list) and mode:
                mode = mode[0]
            if not isinstance(mode, str) or mode not in ['stretch', 'fit']:
                mode = 'stretch'
            
            if mode == 'fit':
                # Transform canvas-relative to fit-relative
                canvas_x = rel_x * self.canvas_rect.width
                canvas_y = rel_y * self.canvas_rect.height
                fit_rel_x = (canvas_x - fit_offset_x) / fit_size if fit_size > 0 else rel_x
                fit_rel_y = (canvas_y - fit_offset_y) / fit_size if fit_size > 0 else rel_y
                check_x, check_y = fit_rel_x, fit_rel_y
            else:
                check_x, check_y = rel_x, rel_y
            
            if point_in_polygon(check_x, check_y, region['shape']):
                if self.selected_region_idx != i:
                    self.selected_region_idx = i
                    self.selected_point_idx = None
                    self.redraw_sidebar()
                return True
        return False
        
    def handle_mouse_motion(self, mouse_pos):
        """Handle dragging points or regions."""
        if self.dragging_point:
            self.drag_point(mouse_pos)
        elif self.dragging_region:
            self.drag_region(mouse_pos)
        else:
            self.handle_hover(mouse_pos)

    def drag_point(self, mouse_pos):
        if self.selected_region_idx is None or self.selected_point_idx is None:
            return

        region = self.regions[self.selected_region_idx]
        mode = region.get('rules', {}).get('placement_mode', 'stretch')
        if isinstance(mode, list) and mode:
            mode = mode[0]
        if not isinstance(mode, str) or mode not in ['stretch', 'fit']:
            mode = 'stretch'

        canvas_x = mouse_pos[0] - self.canvas_rect.x
        canvas_y = mouse_pos[1] - self.canvas_rect.y
        
        if self.grid_snap_enabled:
            canvas_x = round(canvas_x / self.snap_grid_size) * self.snap_grid_size
            canvas_y = round(canvas_y / self.snap_grid_size) * self.snap_grid_size

        if mode == 'fit':
            fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
            fit_offset_x = (self.canvas_rect.width - fit_size) / 2
            fit_offset_y = (self.canvas_rect.height - fit_size) / 2
            rel_x = (canvas_x - fit_offset_x) / fit_size if fit_size > 0 else 0
            rel_y = (canvas_y - fit_offset_y) / fit_size if fit_size > 0 else 0
        else: # stretch
            rel_x = canvas_x / self.canvas_rect.width if self.canvas_rect.width > 0 else 0
            rel_y = canvas_y / self.canvas_rect.height if self.canvas_rect.height > 0 else 0

        rel_x = max(0, min(1, rel_x))
        rel_y = max(0, min(1, rel_y))

        self.regions[self.selected_region_idx]['shape'][self.selected_point_idx] = [rel_x, rel_y]

    def drag_region(self, mouse_pos):
        if self.selected_region_idx is None:
            return

        region = self.regions[self.selected_region_idx]
        mode = region.get('rules', {}).get('placement_mode', 'stretch')
        if isinstance(mode, list) and mode:
            mode = mode[0]
        if not isinstance(mode, str) or mode not in ['stretch', 'fit']:
            mode = 'stretch'

        delta_x_px = mouse_pos[0] - self.drag_start_mouse_pos[0]
        delta_y_px = mouse_pos[1] - self.drag_start_mouse_pos[1]
        
        if mode == 'fit':
            fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
            delta_x_rel = delta_x_px / fit_size if fit_size > 0 else 0
            delta_y_rel = delta_y_px / fit_size if fit_size > 0 else 0
        else: # stretch
            delta_x_rel = delta_x_px / self.canvas_rect.width if self.canvas_rect.width > 0 else 0
            delta_y_rel = delta_y_px / self.canvas_rect.height if self.canvas_rect.height > 0 else 0

        new_points = []
        for p in self.original_points_on_drag_start:
            new_x = max(0, min(1, p[0] + delta_x_rel))
            new_y = max(0, min(1, p[1] + delta_y_rel))
            new_points.append([new_x, new_y])
            
        self.regions[self.selected_region_idx]['shape'] = new_points

    def handle_hover(self, mouse_pos):
        """Highlights a vertex when the mouse hovers over it."""
        self.hovered_point_idx = None
        self.hovered_region_idx = None
        
        fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
        fit_offset_x = (self.canvas_rect.width - fit_size) / 2
        fit_offset_y = (self.canvas_rect.height - fit_size) / 2

        # Iterate through all regions to find a hovered point
        for region_idx in range(len(self.regions) - 1, -1, -1):
            region = self.regions[region_idx]
            mode = region.get('rules', {}).get('placement_mode', 'stretch')
            
            for point_idx, point in enumerate(region['shape']):
                if mode == 'fit':
                    px = self.canvas_rect.x + fit_offset_x + point[0] * fit_size
                    py = self.canvas_rect.y + fit_offset_y + point[1] * fit_size
                else: # stretch
                    px = self.canvas_rect.x + point[0] * self.canvas_rect.width
                    py = self.canvas_rect.y + point[1] * self.canvas_rect.height

                if math.hypot(px - mouse_pos[0], py - mouse_pos[1]) < self.POINT_SELECTION_RADIUS:
                    self.hovered_region_idx = region_idx
                    self.hovered_point_idx = point_idx
                    return # Exit after finding the top-most hovered point

    def handle_button_press(self, button):
        """Dispatcher for all top toolbar and sidebar button presses."""
        # Top Toolbar
        if button == self.new_template_button: self.show_new_template_dialog()
        elif button == self.switch_template_button: self.show_switch_template_dialog()
        elif button == self.rename_template_button: self.show_rename_template_dialog()
        elif button == self.delete_template_button: self.show_delete_template_dialog()
        elif button == self.toggle_aspect_button: self.toggle_aspect_ratio()
        elif button == self.add_region_button: self.add_new_region()
        elif button == self.save_exit_button: self.save_and_exit()
        elif button == self.save_button: 
            self.save_current_template()
            UIMessageWindow(rect=pygame.Rect(self.w/2-150, self.h/2-75, 300, 150), html_message="Template saved.", manager=self.ui_manager, window_title="Saved")
        elif button == self.reload_button:
            self.reload_current_template()
        
        # Sidebar (Properties)
        if 'apply_button' in self.property_ui_elements and button == self.property_ui_elements['apply_button']:
            self.apply_properties_changes()
        if 'delete_region_button' in self.property_ui_elements and button == self.property_ui_elements['delete_region_button']:
            self.delete_selected_region()

    def redraw_sidebar(self):
        """Clears and redraws the sidebar content based on selection."""
        for el in self.property_ui_elements.values():
            el.kill()
        self.property_ui_elements.clear()

        if self.selected_region_idx is None:
            # Add more padding and better layout for "no selection" message
            self.property_ui_elements['no_selection_label'] = UILabel(pygame.Rect(15, 30, self.SIDEBAR_WIDTH - 30, 80),
                    "No region selected.\n\nClick on a region to edit its properties.",
                    self.ui_manager, self.sidebar_panel)
            return


        region = self.regions[self.selected_region_idx]
        y_pos = 20  # Start with more padding

        # Title
        title_text = f"Editing: {region.get('name', 'Unnamed')}"
        self.property_ui_elements['title'] = UILabel(pygame.Rect(15, y_pos, self.SIDEBAR_WIDTH - 30, 30), title_text, self.ui_manager, self.sidebar_panel, object_id='#sidebar_title')
        y_pos += 45  # More spacing after title

        # --- Name ---
        self.property_ui_elements['name_label'] = UILabel(pygame.Rect(15, y_pos, 80, 30), 'Name:', self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['name_entry'] = UITextEntryLine(pygame.Rect(105, y_pos, self.SIDEBAR_WIDTH - 125, 30), self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['name_entry'].set_text(region.get('name', ''))
        y_pos += 45  # More spacing between sections

        # --- Size Range ---
        rules = region.get('rules', {})
        size_range = rules.get('size_range', [20, 50])
        self.property_ui_elements['size_label'] = UILabel(pygame.Rect(15, y_pos, 80, 30), 'Size:', self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['min_size_entry'] = UITextEntryLine(pygame.Rect(105, y_pos, 70, 30), self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['min_size_entry'].set_text(str(size_range[0]))
        self.property_ui_elements['max_size_entry'] = UITextEntryLine(pygame.Rect(195, y_pos, 70, 30), self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['max_size_entry'].set_text(str(size_range[1]))
        y_pos += 45
        
        # --- Word Count ---
        word_range = rules.get('word_count_range', [1, 3])
        self.property_ui_elements['word_label'] = UILabel(pygame.Rect(15, y_pos, 80, 30), 'Words:', self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['min_word_entry'] = UITextEntryLine(pygame.Rect(105, y_pos, 70, 30), self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['min_word_entry'].set_text(str(word_range[0]))
        self.property_ui_elements['max_word_entry'] = UITextEntryLine(pygame.Rect(195, y_pos, 70, 30), self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['max_word_entry'].set_text(str(word_range[1]))
        y_pos += 45

        # --- Text Type ---
        text_types = ['any', 'normal', 'arc', 'asset']
        current_type = rules.get('text_type', 'any')
        # Ensure current_type is in the options list
        if isinstance(current_type, list) and current_type:
            current_type = current_type[0]
        if not isinstance(current_type, str) or current_type not in text_types:
            current_type = 'any'
        self.property_ui_elements['text_type_label'] = UILabel(pygame.Rect(15, y_pos, 80, 30), 'Type:', self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['text_type_dropdown'] = UIDropDownMenu(text_types, current_type, pygame.Rect(105, y_pos, self.SIDEBAR_WIDTH - 125, 30), self.ui_manager, self.sidebar_panel)
        y_pos += 45

        # --- Placement Mode ---
        placement_modes = ['stretch', 'fit']
        current_mode = rules.get('placement_mode', 'stretch')
        if isinstance(current_mode, list) and current_mode:
            current_mode = current_mode[0]
        # Ensure current_mode is a valid string before using it
        if not isinstance(current_mode, str) or current_mode not in placement_modes:
            current_mode = 'stretch'

        self.property_ui_elements['placement_label'] = UILabel(pygame.Rect(15, y_pos, 80, 30), 'Placement:', self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['placement_dropdown'] = UIDropDownMenu(placement_modes, current_mode, pygame.Rect(105, y_pos, self.SIDEBAR_WIDTH - 125, 30), self.ui_manager, self.sidebar_panel)
        y_pos += 45

        # --- Enforce Boundaries ---
        enforce_options = ['True', 'False']
        current_enforce = str(rules.get('enforce_boundaries', 'False'))
        self.property_ui_elements['enforce_label'] = UILabel(pygame.Rect(15, y_pos, 80, 30), 'Fit Word:', self.ui_manager, self.sidebar_panel)
        self.property_ui_elements['enforce_dropdown'] = UIDropDownMenu(enforce_options, current_enforce, pygame.Rect(105, y_pos, self.SIDEBAR_WIDTH - 125, 30), self.ui_manager, self.sidebar_panel)
        y_pos += 60  # Extra spacing before buttons

        # --- Actions ---
        self.property_ui_elements['apply_button'] = UIButton(pygame.Rect(15, y_pos, self.SIDEBAR_WIDTH - 30, 40), 'Apply Changes', self.ui_manager, self.sidebar_panel, object_id='#save_button')
        y_pos += 55  # More spacing between buttons
        self.property_ui_elements['delete_region_button'] = UIButton(pygame.Rect(15, y_pos, self.SIDEBAR_WIDTH - 30, 40), 'Delete This Region', self.ui_manager, self.sidebar_panel, object_id='#delete_button')

    def apply_properties_changes(self):
        """Apply changes from UI to in-memory regions and save to disk."""
        if self.selected_region_idx is None:
            return

        # Read all properties from the UI into local variables.
        name = self.property_ui_elements['name_entry'].get_text()
        try:
            min_size = int(self.property_ui_elements['min_size_entry'].get_text())
            max_size = int(self.property_ui_elements['max_size_entry'].get_text())
            size_range = [max(1, min(min_size, max_size)), max(min_size, max_size)]
        except ValueError:
            size_range = None  # Flag to not update

        try:
            min_words = int(self.property_ui_elements['min_word_entry'].get_text())
            max_words = int(self.property_ui_elements['max_word_entry'].get_text())
            word_count_range = [max(1, min(min_words, max_words)), max(min_words, max_words)]
        except ValueError:
            word_count_range = None  # Flag to not update

        text_type_val = self.property_ui_elements['text_type_dropdown'].selected_option
        placement_mode_val = self.property_ui_elements['placement_dropdown'].selected_option

        # The dropdown might return a tuple (text, id) or just the text string.
        # We only want the text.
        text_type = text_type_val[0] if isinstance(text_type_val, tuple) else text_type_val
        placement_mode = placement_mode_val[0] if isinstance(placement_mode_val, tuple) else placement_mode_val

        enforce_boundaries_val = self.property_ui_elements['enforce_dropdown'].selected_option
        enforce_boundaries = enforce_boundaries_val[0] if isinstance(enforce_boundaries_val, tuple) else enforce_boundaries_val

        # Apply to in-memory regions
        region = self.regions[self.selected_region_idx]
        region['name'] = str(name)  # Ensure string
        if 'rules' not in region:
            region['rules'] = {}

        if size_range is not None:
            region['rules']['size_range'] = size_range  # Already integers
        if word_count_range is not None:
            region['rules']['word_count_range'] = word_count_range  # Already integers

        # Ensure these are strings, not arrays
        region['rules']['text_type'] = str(text_type)
        region['rules']['placement_mode'] = str(placement_mode)
        region['rules']['enforce_boundaries'] = (enforce_boundaries == 'True')

        # Save to disk
        self.save_current_template()

        # Redraw the UI
        self.redraw_sidebar()

        UIMessageWindow(
            rect=pygame.Rect(self.w / 2 - 150, self.h / 2 - 75, 300, 150),
            html_message="Changes saved.",
            manager=self.ui_manager,
            window_title="Success"
        )

    def draw(self):
        """Draw everything to the screen."""
        self.screen.fill(self.colors['bg'])
        self.draw_canvas()
        self.draw_bottom_bar()
        self.ui_manager.draw_ui(self.screen)

    def draw_canvas(self):
        """Draw the main editing area."""
        pygame.draw.rect(self.screen, self.colors['canvas_bg'], self.canvas_rect)
        self.draw_grid()
        self.draw_fit_mode_bounds()
        self.draw_regions()
        
        # Canvas Border
        pygame.draw.rect(self.screen, (0,0,0), self.canvas_rect, 2)

    def draw_bottom_bar(self):
        """Draws the info bar at the bottom of the canvas area."""
        info_font = pygame.font.Font(None, 20)
        
        # Count fit mode regions
        fit_count = 0
        for region in self.regions:
            mode = region.get('rules', {}).get('placement_mode', 'stretch')
            if isinstance(mode, list) and mode:
                mode = mode[0]
            if mode == 'fit':
                fit_count += 1
        stretch_count = len(self.regions) - fit_count
        
        info_text = f"SHIFT for grid snapping | DEL to delete vertex/region | 'A' to add vertex"
        if fit_count > 0:
            info_text += f" | {fit_count} fit mode region(s)"
        if stretch_count > 0:
            info_text += f" | {stretch_count} stretch mode region(s)"
        
        info_surf = info_font.render(info_text, True, self.colors['text'])
        info_x = self.bottom_toolbar.rect.x + 15
        info_y = self.bottom_toolbar.rect.y + (self.bottom_toolbar.rect.height - info_surf.get_height()) // 2
        self.screen.blit(info_surf, (info_x, info_y))

    def draw_grid(self):
        """Draw a background grid for alignment."""
        faint_color = (35, 35, 45)  # Very subtle grid always visible
        strong_color = self.colors['grid']  # Stronger when snapping
        
        # Always draw faint grid
        for x in range(int(self.canvas_rect.x), int(self.canvas_rect.right), self.snap_grid_size):
            pygame.draw.line(self.screen, faint_color, (x, self.canvas_rect.y), (x, self.canvas_rect.bottom))
        for y in range(int(self.canvas_rect.y), int(self.canvas_rect.bottom), self.snap_grid_size):
            pygame.draw.line(self.screen, faint_color, (self.canvas_rect.x, y), (self.canvas_rect.right, y))
        
        if self.grid_snap_enabled:
            # Draw stronger grid on top when SHIFT held
            for x in range(int(self.canvas_rect.x), int(self.canvas_rect.right), self.snap_grid_size):
                pygame.draw.line(self.screen, strong_color, (x, self.canvas_rect.y), (x, self.canvas_rect.bottom))
            for y in range(int(self.canvas_rect.y), int(self.canvas_rect.bottom), self.snap_grid_size):
                pygame.draw.line(self.screen, strong_color, (self.canvas_rect.x, y), (self.canvas_rect.right, y))

    def draw_fit_mode_bounds(self):
        """Draws the square bounding box for 'fit' placement mode visualization."""
        # Only show fit bounds if there are regions using 'fit' mode
        has_fit_regions = False
        for region in self.regions:
            mode = region.get('rules', {}).get('placement_mode', 'stretch')
            if isinstance(mode, list) and mode:
                mode = mode[0]
            if mode == 'fit':
                has_fit_regions = True
                break
        
        if not has_fit_regions:
            return
            
        bounds_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        
        fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
        fit_offset_x = (self.canvas_rect.width - fit_size) / 2
        fit_offset_y = (self.canvas_rect.height - fit_size) / 2
        
        bounds_rect = pygame.Rect(
            self.canvas_rect.x + fit_offset_x,
            self.canvas_rect.y + fit_offset_y,
            fit_size,
            fit_size
        )
        
        # Draw a subtle background for the fit area
        fit_bg_color = (100, 100, 0, 30)  # Very subtle yellow background
        fit_bg_surface = pygame.Surface((fit_size, fit_size), pygame.SRCALPHA)
        fit_bg_surface.fill(fit_bg_color)
        self.screen.blit(fit_bg_surface, bounds_rect.topleft)
        
        # Draw the border
        border_color = (200, 200, 0, 150)
        pygame.draw.line(bounds_surface, border_color, bounds_rect.topleft, bounds_rect.topright, 2)
        pygame.draw.line(bounds_surface, border_color, bounds_rect.topright, bounds_rect.bottomright, 2)
        pygame.draw.line(bounds_surface, border_color, bounds_rect.bottomright, bounds_rect.bottomleft, 2)
        pygame.draw.line(bounds_surface, border_color, bounds_rect.bottomleft, bounds_rect.topleft, 2)
        
        # Draw corner indicators
        corner_size = 8
        corner_color = (255, 255, 0, 200)
        # Top-left corner
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.topleft, (bounds_rect.x + corner_size, bounds_rect.y), 3)
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.topleft, (bounds_rect.x, bounds_rect.y + corner_size), 3)
        # Top-right corner
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.topright, (bounds_rect.right - corner_size, bounds_rect.y), 3)
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.topright, (bounds_rect.right, bounds_rect.y + corner_size), 3)
        # Bottom-right corner
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.bottomright, (bounds_rect.right - corner_size, bounds_rect.bottom), 3)
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.bottomright, (bounds_rect.right, bounds_rect.bottom - corner_size), 3)
        # Bottom-left corner
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.bottomleft, (bounds_rect.x + corner_size, bounds_rect.bottom), 3)
        pygame.draw.line(bounds_surface, corner_color, bounds_rect.bottomleft, (bounds_rect.x, bounds_rect.bottom - corner_size), 3)

        self.screen.blit(bounds_surface, (0, 0))

    def draw_regions(self):
        """Draw all region polygons and their points."""
        fit_size = min(self.canvas_rect.width, self.canvas_rect.height)
        fit_offset_x = (self.canvas_rect.width - fit_size) / 2
        fit_offset_y = (self.canvas_rect.height - fit_size) / 2

        for i, region in enumerate(self.regions):
            mode = region.get('rules', {}).get('placement_mode', 'stretch')
            if isinstance(mode, list) and mode:
                mode = mode[0]
            if not isinstance(mode, str) or mode not in ['stretch', 'fit']:
                mode = 'stretch'

            points = []
            for rel_x, rel_y in region['shape']:
                if mode == 'fit':
                    abs_x = self.canvas_rect.x + fit_offset_x + (rel_x * fit_size)
                    abs_y = self.canvas_rect.y + fit_offset_y + (rel_y * fit_size)
                else: # 'stretch'
                    abs_x = self.canvas_rect.x + (rel_x * self.canvas_rect.width)
                    abs_y = self.canvas_rect.y + (rel_y * self.canvas_rect.height)
                points.append((abs_x, abs_y))

            is_selected = (i == self.selected_region_idx)
            
            # Use different colors for fit vs stretch mode
            if mode == 'fit':
                fill = self.colors['selected_region_fill'] if is_selected else (120, 120, 200, 100)  # Blue tint for fit
                outline = self.colors['selected_region_outline'] if is_selected else (150, 150, 255)
            else:
                fill = self.colors['selected_region_fill'] if is_selected else self.colors['region_fill']
                outline = self.colors['selected_region_outline'] if is_selected else self.colors['region_outline']
            
            if len(points) > 2:
                region_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                pygame.draw.polygon(region_surface, fill, points)
                self.screen.blit(region_surface, (0, 0))
                pygame.draw.polygon(self.screen, outline, points, 2)
                
                # Add mode indicator label
                if len(points) > 0:
                    # Calculate center of region for label placement
                    center_x = sum(p[0] for p in points) / len(points)
                    center_y = sum(p[1] for p in points) / len(points)
                    
                    # Draw small mode indicator
                    label_font = pygame.font.Font(None, 16)
                    mode_text = "FIT" if mode == 'fit' else "STR"
                    mode_color = (255, 255, 0) if mode == 'fit' else (200, 200, 200)
                    mode_surf = label_font.render(mode_text, True, mode_color)
                    mode_rect = mode_surf.get_rect(center=(center_x, center_y))
                    
                    # Draw background for label
                    label_bg = pygame.Surface((mode_rect.width + 4, mode_rect.height + 2))
                    label_bg.fill((0, 0, 0))
                    label_bg.set_alpha(150)
                    self.screen.blit(label_bg, (mode_rect.x - 2, mode_rect.y - 1))
                    self.screen.blit(mode_surf, mode_rect)

            # Draw points for the current region if it's selected or has a hovered point
            if is_selected or i == self.hovered_region_idx:
                for j, p in enumerate(points):
                    is_selected_point = is_selected and (j == self.selected_point_idx)
                    is_hovered_point = (i == self.hovered_region_idx) and (j == self.hovered_point_idx)

                    if is_selected_point:
                        point_color = self.colors['selected_point']
                        point_size = 8
                    elif is_hovered_point:
                        point_color = self.colors['hovered_point']
                        point_size = 7
                    else:
                        point_color = self.colors['point']
                        point_size = 5
                        
                    pygame.draw.circle(self.screen, point_color, p, point_size)
                    pygame.draw.circle(self.screen, (0,0,0), p, point_size, 1)

    def save_current_template(self):
        self.region_manager.set_template(self.active_template_name, self.regions)
        
    def save_and_exit(self):
        self.save_current_template()
        self.running = False

    def add_new_region(self):
        new_region = {
            "name": f"Region {len(self.regions) + 1}",
            "shape": [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]],
            "rules": {
                "size_range": [20, 50], 
                "text_type": "any", 
                "word_count_range": [1, 3], 
                "placement_mode": "stretch",
                "enforce_boundaries": False
            }
        }
        self.regions.append(new_region)
        self.selected_region_idx = len(self.regions) - 1
        self.selected_point_idx = None
        self.redraw_sidebar()

    def delete_selected_region(self):
        if self.selected_region_idx is not None:
            del self.regions[self.selected_region_idx]
            self.selected_region_idx = None
            self.selected_point_idx = None
            self.redraw_sidebar()
            self.save_current_template()

    def add_point_to_selected_region(self):
        if self.selected_region_idx is not None and len(self.regions[self.selected_region_idx]['shape']) > 1:
            region = self.regions[self.selected_region_idx]
            p1 = region['shape'][-2]
            p2 = region['shape'][-1]
            new_point = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]
            region['shape'].insert(-1, new_point)
            self.selected_point_idx = len(region['shape']) - 2

    def delete_selected_point(self):
        if self.selected_region_idx is not None and self.selected_point_idx is not None:
            region = self.regions[self.selected_region_idx]
            if len(region['shape']) > 3:
                del region['shape'][self.selected_point_idx]
                self.selected_point_idx = None

    def toggle_aspect_ratio(self):
        """Switches the canvas aspect ratio and recalculates its rect."""
        self.aspect_mode = 'vertical' if self.aspect_mode == 'horizontal' else 'horizontal'
        self.setup_canvas_rect()
        
        # Update button text to show current aspect mode
        if hasattr(self, 'toggle_aspect_button'):
            self.toggle_aspect_button.set_text(f'Aspect: {self.aspect_mode.title()}')
        
        # Update bottom toolbar position to match new canvas width
        if hasattr(self, 'bottom_toolbar'):
            self.bottom_toolbar.set_relative_position((0, self.h - self.BOTTOM_TOOLBAR_HEIGHT))
            self.bottom_toolbar.set_dimensions((self.w - self.SIDEBAR_WIDTH, self.BOTTOM_TOOLBAR_HEIGHT))

    def switch_to_template(self, new_template_name):
        self.save_current_template()
        self.active_template_name = new_template_name
        self.regions = self.region_manager.get_template(self.active_template_name)
        self.selected_region_idx = None
        self.selected_point_idx = None
        self.redraw_sidebar()
        # Update template name label
        self.template_name_label.set_text(f"Current: {self.active_template_name}")

    def show_new_template_dialog(self):
        dialog = TextInputDialog(pygame.Rect(self.w/2-160, self.h/2-75, 320, 170), self.ui_manager, "Create New Template", "Enter new template name:")
        dialog.completion_callback = self.on_new_template_dialog_close
        
    def on_new_template_dialog_close(self, result):
        if result:
            new_name = result.strip()
            if new_name and new_name not in self.region_manager.get_template_names():
                self.save_current_template()
                self.region_manager.set_template(new_name, []) # Create empty
                self.switch_to_template(new_name)
            elif new_name:
                 UIMessageWindow(rect=pygame.Rect(self.w/2-150, self.h/2-75, 300, 150), html_message=f"Template '{new_name}' already exists.", manager=self.ui_manager, window_title="Error")

    def show_rename_template_dialog(self):
        if self.active_template_name == "Default":
            UIMessageWindow(rect=pygame.Rect(self.w/2-150, self.h/2-75, 300, 150), html_message="Cannot rename the 'Default' template.", manager=self.ui_manager, window_title="Cannot Rename")
            return
        dialog = TextInputDialog(pygame.Rect(self.w/2-160, self.h/2-75, 320, 170), self.ui_manager, "Rename Template", "Enter new name:", initial_text=self.active_template_name)
        dialog.completion_callback = self.on_rename_dialog_close
        
    def on_rename_dialog_close(self, result):
        if result:
            new_name = result.strip()
            if new_name and new_name != self.active_template_name and new_name not in self.region_manager.get_template_names():
                self.region_manager.set_template(new_name, self.regions)
                self.region_manager.delete_template(self.active_template_name)
                self.active_template_name = new_name
            elif new_name:
                UIMessageWindow(rect=pygame.Rect(self.w/2-150, self.h/2-75, 300, 150), html_message=f"Template '{new_name}' already exists.", manager=self.ui_manager, window_title="Error")

    def show_delete_template_dialog(self):
        if self.active_template_name == "Default":
            UIMessageWindow(rect=pygame.Rect(self.w/2-150, self.h/2-75, 300, 150), html_message="Cannot delete the 'Default' template.", manager=self.ui_manager, window_title="Cannot Delete")
            return
        dialog = UIConfirmationDialog(
            rect=pygame.Rect(self.w/2-150, self.h/2-100, 300, 200),
            manager=self.ui_manager,
            window_title="Confirm Deletion",
            action_long_desc=f"Delete template '{self.active_template_name}'? This cannot be undone.",
            action_short_name="Delete",
            blocking=True
        )
        dialog.completion_callback = self.on_delete_dialog_close

    def on_delete_dialog_close(self, confirmed):
        if confirmed:
            self.region_manager.delete_template(self.active_template_name)
            self.switch_to_template("Default")

    def show_switch_template_dialog(self):
        templates = self.region_manager.get_template_names()
        dialog = SelectionDialog(pygame.Rect(self.w/2-160, self.h/2-150, 320, 300), self.ui_manager, "Switch Template", "Select a template:", templates)
        dialog.completion_callback = self.on_switch_template_close
        
    def on_switch_template_close(self, result):
        if result and result != self.active_template_name:
            self.switch_to_template(result)

    def reload_current_template(self):
        """Reload the current template from disk."""
        self.region_manager.load_templates()
        self.regions = self.region_manager.get_template(self.active_template_name)
        self.selected_region_idx = None
        self.selected_point_idx = None
        self.redraw_sidebar()
        UIMessageWindow(rect=pygame.Rect(self.w/2-150, self.h/2-75, 300, 150), html_message="Reloaded template from file.", manager=self.ui_manager, window_title="Reloaded")

# --- Custom Dialog Windows with Callbacks ---
class TextInputDialog(UIWindow):
    def __init__(self, rect, manager, title, label, initial_text="", confirm_text="OK", cancel_text="Cancel"):
        super().__init__(rect, manager, window_display_title=title)
        self.completion_callback = None
        
        UILabel(pygame.Rect(20, 20, rect.width - 40, 30), label, manager, container=self)
        self.text_entry = UITextEntryLine(pygame.Rect(20, 60, rect.width - 40, 30), manager, container=self)
        self.text_entry.set_text(initial_text)
        
        self.ok_button = UIButton(pygame.Rect(20, rect.height - 50, 80, 30), confirm_text, manager, container=self)
        self.cancel_button = UIButton(pygame.Rect(rect.width - 100, rect.height - 50, 80, 30), cancel_text, manager, container=self)

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.ok_button:
                if self.completion_callback: self.completion_callback(self.text_entry.get_text())
                self.kill()
            elif event.ui_element == self.cancel_button:
                if self.completion_callback: self.completion_callback(None)
                self.kill()

class SelectionDialog(UIWindow):
    def __init__(self, rect, manager, title, label, options, confirm_text="OK", cancel_text="Cancel"):
        super().__init__(rect, manager, window_display_title=title)
        self.completion_callback = None

        UILabel(pygame.Rect(20, 20, rect.width-40, 30), label, manager, container=self)
        self.selection_list = UISelectionList(pygame.Rect(20, 60, rect.width-40, rect.height-120), options, manager, container=self)
        
        self.ok_button = UIButton(pygame.Rect(20, rect.height-50, 80, 30), confirm_text, manager, container=self)
        self.cancel_button = UIButton(pygame.Rect(rect.width-100, rect.height-50, 80, 30), cancel_text, manager, container=self)

    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.ok_button:
                if self.completion_callback: self.completion_callback(self.selection_list.get_single_selection())
                self.kill()
            elif event.ui_element == self.cancel_button:
                if self.completion_callback: self.completion_callback(None)
                self.kill()

class ConfirmationDialog(UIConfirmationDialog):
    def __init__(self, rect, manager, **kwargs):
        super().__init__(rect, manager, **kwargs)
        self.completion_callback = None
    
    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            if self.completion_callback: 
                self.completion_callback(True)
        elif event.type == pygame_gui.UI_WINDOW_CLOSE and event.ui_element == self:
            # Handle window close as cancel
            if self.completion_callback: 
                self.completion_callback(False) 