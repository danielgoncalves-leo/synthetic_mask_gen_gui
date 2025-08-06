import yaml
import os
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

@dataclass
class DisplayConfig:
    window_width: int
    window_height: int
    info_bar_height: int
    fps: int
    default_background_color: Tuple[int, int, int]

@dataclass
class CanvasConfig:
    padding: int
    main_area_ratio: float

@dataclass
class FontConfig:
    min_size: int
    max_size: int
    show_info: bool
    rotate_letters_on_arc: bool
    max_arc_letter_rotation: int

@dataclass
class NormalTextConfig:
    padding: int

@dataclass
class ArcTextConfig:
    min_radius: int
    max_radius: int

@dataclass
class TextConfig:
    types: List[str]
    type_weights: List[float]
    fallback_words: List[str]
    normal: NormalTextConfig
    arc: ArcTextConfig

@dataclass
class MaskConfig:
    grow_pixels: int
    padding_size: int

@dataclass
class LayoutConfig:
    max_words: int
    max_attempts_per_word: int
    max_attempts_total: int

@dataclass
class PlacementRegionRules:
    placement_mode: str
    font_size_range: List[int]
    text_types: List[str]
    text_type_weights: List[float]

@dataclass
class PlacementRegion:
    name: str
    shape: List[List[float]]
    rules: PlacementRegionRules

@dataclass
class ZoomConfig:
    min_level: float
    max_level: float
    speed: float

@dataclass
class PerformanceConfig:
    batch_processing_max_workers: int

@dataclass
class PathsConfig:
    default_image_dir: str
    default_font_dir: str
    output_dir: str

@dataclass
class DebugConfig:
    show_mask_overlay: bool
    show_debug_regions: bool
    force_regions_only: bool

@dataclass
class LoggingConfig:
    level: str

@dataclass
class SupportedExtensionsConfig:
    images: List[str]
    fonts: List[str]

@dataclass
class Config:
    display: DisplayConfig
    canvas: CanvasConfig
    fonts: FontConfig
    text: TextConfig
    mask: MaskConfig
    layout: LayoutConfig
    placement_regions: List[PlacementRegion]
    zoom: ZoomConfig
    performance: PerformanceConfig
    paths: PathsConfig
    debug: DebugConfig
    logging: LoggingConfig
    supported_extensions: SupportedExtensionsConfig

class ConfigManager:
    """Manages loading and accessing configuration from YAML file."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = None
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file."""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                yaml_data = yaml.safe_load(file)
            
            self.config = self._parse_config(yaml_data)
            print(f"Configuration loaded successfully from {self.config_path}")
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration...")
            self.config = self._get_default_config()
    
    def _parse_config(self, yaml_data: Dict[str, Any]) -> Config:
        """Parse YAML data into structured configuration objects."""
        
        # Parse placement regions
        placement_regions = []
        for region_data in yaml_data.get('placement_regions', []):
            rules = PlacementRegionRules(**region_data['rules'])
            region = PlacementRegion(
                name=region_data['name'],
                shape=region_data['shape'],
                rules=rules
            )
            placement_regions.append(region)
        
        return Config(
            display=DisplayConfig(**yaml_data['display']),
            canvas=CanvasConfig(**yaml_data['canvas']),
            fonts=FontConfig(**yaml_data['fonts']),
            text=TextConfig(
                types=yaml_data['text']['types'],
                type_weights=yaml_data['text']['type_weights'],
                fallback_words=yaml_data['text']['fallback_words'],
                normal=NormalTextConfig(**yaml_data['text']['normal']),
                arc=ArcTextConfig(**yaml_data['text']['arc'])
            ),
            mask=MaskConfig(**yaml_data['mask']),
            layout=LayoutConfig(**yaml_data['layout']),
            placement_regions=placement_regions,
            zoom=ZoomConfig(**yaml_data['zoom']),
            performance=PerformanceConfig(**yaml_data['performance']),
            paths=PathsConfig(**yaml_data['paths']),
            debug=DebugConfig(**yaml_data['debug']),
            logging=LoggingConfig(**yaml_data.get('logging', {'level': 'INFO'})),
            supported_extensions=SupportedExtensionsConfig(**yaml_data['supported_extensions'])
        )
    
    def _get_default_config(self) -> Config:
        """Return a default configuration if YAML loading fails."""
        return Config(
            display=DisplayConfig(1280, 720, 30, 60, (30, 30, 30)),
            canvas=CanvasConfig(10, 0.5),
            fonts=FontConfig(20, 80, True, True, 45),
            text=TextConfig(
                types=["normal", "arc"],
                type_weights=[0.7, 0.3],
                fallback_words=["SAMPLE", "TEXT", "OVERLAY", "DESIGN"],
                normal=NormalTextConfig(2),
                arc=ArcTextConfig(80, 200)
            ),
            mask=MaskConfig(3, 5),
            layout=LayoutConfig(30, 1000, 3000),
            placement_regions=[],
            zoom=ZoomConfig(0.1, 5.0, 0.1),
            performance=PerformanceConfig(4),
            paths=PathsConfig("input", "fonts", "out"),
            debug=DebugConfig(False, False, False),
            logging=LoggingConfig(level="INFO"),
            supported_extensions=SupportedExtensionsConfig(
                [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"],
                [".ttf", ".otf"]
            )
        )
    
    def get_config(self) -> Config:
        """Get the current configuration."""
        return self.config
    
    def reload_config(self):
        """Reload configuration from file."""
        print("Reloading configuration...")
        self.load_config()
    
    def save_config(self, config: Config):
        """Save configuration to YAML file."""
        try:
            # Convert config back to dictionary format
            config_dict = self._config_to_dict(config)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(config_dict, file, default_flow_style=False, indent=2)
            
            print(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def _config_to_dict(self, config: Config) -> Dict[str, Any]:
        """Convert Config object back to dictionary format."""
        # This is a simplified version - you might want to implement a more robust conversion
        # For now, we'll just return the basic structure
        return {
            'display': {
                'window_width': config.display.window_width,
                'window_height': config.display.window_height,
                'info_bar_height': config.display.info_bar_height,
                'fps': config.display.fps,
                'default_background_color': list(config.display.default_background_color)
            },
            # Add other sections as needed...
        }

# Global configuration manager instance
config_manager = ConfigManager()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config_manager.get_config()

def reload_config():
    """Reload the global configuration."""
    config_manager.reload_config() 