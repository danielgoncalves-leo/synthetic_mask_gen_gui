import json
import os
from rich.console import Console

console = Console()

DEFAULT_TEMPLATES = {
    "Default": [
        {
            "name": "Bottom Bar",
            "shape": [
                [0.05, 0.8],
                [0.95, 0.8],
                [0.95, 0.95],
                [0.05, 0.95]
            ],
            "rules": {
                "size_range": [10, 20],
                "text_type": "normal",
                "word_count_range": [2, 5],
                "placement_mode": "stretch"
            }
        },
        {
            "name": "Top-Left Triangle",
            "shape": [
                [0.0, 0.0],
                [0.4, 0.0],
                [0.0, 0.4]
            ],
            "rules": {
                "size_range": [5, 10],
                "text_type": "any",
                "word_count_range": [2, 5],
                "placement_mode": "stretch"
            }
        },
        {
            "name": "Center hexagon polygon",
            "shape": [
                [0.5, 0.3],
                [0.7, 0.4],
                [0.7, 0.6],
                [0.5, 0.7],
                [0.3, 0.6],
                [0.3, 0.4]
            ],
            "rules": {
                "size_range": [35, 45],
                "text_type": "normal",
                "word_count_range": [1, 1],
                "placement_mode": "fit"
            }
        }
    ],
    "Empty": [],
    "Header and Footer": [
        {
            "name": "Header",
            "shape": [
                [0.05, 0.05],
                [0.95, 0.05],
                [0.95, 0.2],
                [0.05, 0.2]
            ],
            "rules": {
                "size_range": [40, 80],
                "text_type": "normal",
                "word_count_range": [1, 2],
                "placement_mode": "stretch"
            }
        },
        {
            "name": "Footer",
            "shape": [
                [0.05, 0.85],
                [0.95, 0.85],
                [0.95, 0.95],
                [0.05, 0.95]
            ],
            "rules": {
                "size_range": [15, 25],
                "text_type": "normal",
                "word_count_range": [2, 5],
                "placement_mode": "stretch"
            }
        }
    ]
}

class RegionManager:
    """Manages loading, saving, and editing of region templates."""
    def __init__(self, templates_file='region_templates.json'):
        self.templates_file = templates_file
        self.templates = self.load_templates()

    def load_templates(self):
        """Loads templates from a JSON file, or creates a default one."""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r') as f:
                    templates = json.load(f)
                    # Convert shape tuples to lists for consistency with JSON
                    for template_name, regions in templates.items():
                        for region in regions:
                            region['shape'] = [list(p) for p in region['shape']]
                            # Sanitize rules
                            rules = region.get('rules', {})
                            # Sanitize placement_mode
                            mode = rules.get('placement_mode', 'stretch')
                            if isinstance(mode, list) and mode:
                                mode = mode[0]
                            if not isinstance(mode, str) or mode not in ['stretch', 'fit']:
                                mode = 'stretch'
                            rules['placement_mode'] = mode
                            # Sanitize text_type
                            text_type_val = rules.get('text_type', 'any')
                            if isinstance(text_type_val, list) and text_type_val:
                                text_type_val = text_type_val[0]
                            if not isinstance(text_type_val, str) or text_type_val not in ['any', 'normal', 'arc', 'asset']:
                                text_type_val = 'any'
                            rules['text_type'] = text_type_val
                            # Sanitize size_range
                            size_range = rules.get('size_range', [20, 50])
                            if not isinstance(size_range, list) or len(size_range) != 2 or not all(isinstance(x, (int, float)) for x in size_range):
                                size_range = [20, 50]
                            else:
                                min_val, max_val = map(int, size_range)
                                size_range = [min(min_val, max_val), max(min_val, max_val)]
                            rules['size_range'] = size_range
                            # Sanitize word_count_range
                            word_range = rules.get('word_count_range', [1, 3])
                            if not isinstance(word_range, list) or len(word_range) != 2 or not all(isinstance(x, (int, float)) for x in word_range):
                                word_range = [1, 3]
                            else:
                                min_val, max_val = map(int, word_range)
                                word_range = [min(min_val, max_val), max(min_val, max_val)]
                            rules['word_count_range'] = word_range
                    console.log(f"Loaded {len(templates)} region templates from '{self.templates_file}'")
                    return templates
            except (json.JSONDecodeError, IOError) as e:
                console.log(f"[red]Error loading templates file: {e}. Reverting to default.[/red]")
                self._save_default_templates()
                return DEFAULT_TEMPLATES
        else:
            console.log("Templates file not found. Creating default templates file.")
            self._save_default_templates()
            return DEFAULT_TEMPLATES

    def _save_default_templates(self):
        """Saves the hardcoded default templates to the JSON file."""
        try:
            with open(self.templates_file, 'w') as f:
                json.dump(DEFAULT_TEMPLATES, f, indent=4)
            console.log(f"Saved default templates to '{self.templates_file}'")
        except IOError as e:
            console.log(f"[red]Could not write default templates file: {e}[/red]")

    def save_templates(self):
        """Saves the current state of all templates to the JSON file."""
        try:
            with open(self.templates_file, 'w') as f:
                json.dump(self.templates, f, indent=4)
            console.log(f"Successfully saved {len(self.templates)} templates to '{self.templates_file}'")
        except IOError as e:
            console.log(f"[red]Error saving templates: {e}[/red]")

    def get_template_names(self):
        """Returns a list of all template names."""
        return list(self.templates.keys())

    def get_template(self, name):
        """
        Returns a single template (list of regions).
        The shape coordinates are converted to tuples as expected by pygame.
        """
        regions = self.templates.get(name)
        if regions is None:
            return []
        
        # Create a deep copy to avoid modifying the manager's state
        import copy
        return copy.deepcopy(regions)

    def set_template(self, name, regions):
        """
        Updates or adds a template and saves to file.
        Expects regions with shape coordinates as lists.
        """
        self.templates[name] = regions
        self.save_templates()

    def delete_template(self, name):
        """Deletes a template if it exists and is not the 'Default' template."""
        if name in self.templates and name != "Default":
            del self.templates[name]
            self.save_templates()
            console.log(f"Deleted template '{name}'")
            return True
        elif name == "Default":
            console.log(f"[yellow]Cannot delete the 'Default' template.[/yellow]")
            return False
        else:
            console.log(f"[red]Template '{name}' not found for deletion.[/red]")
            return False 