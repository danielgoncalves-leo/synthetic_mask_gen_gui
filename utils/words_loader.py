import os
import json
from typing import List, Dict, Optional

class WordsLoader:
    """Handles loading words from a single JSON file with fallback to config."""
    
    def __init__(self, filepath: str = "words.json"):
        self.filepath = filepath
        self.words = []
        self.load_words()
    
    def load_words(self, fallback_words: Optional[List[str]] = None):
        """Load words from the JSON file."""
        try:
            if not os.path.exists(self.filepath):
                print(f"Warning: Words file not found at '{self.filepath}'")
                if fallback_words:
                    print("Using fallback words from configuration")
                    self.words = fallback_words
                else:
                    self.words = []
                return

            with open(self.filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            self.words = self._parse_words(data)
            print(f"Loaded {len(self.words)} words from '{self.filepath}'")
            
        except Exception as e:
            print(f"Error loading words from {self.filepath}: {e}")
            if fallback_words:
                print("Using fallback words from configuration")
                self.words = fallback_words
            else:
                self.words = []
    
    def _parse_words(self, data: Dict[str, List[str]]) -> List[str]:
        """Parse words from the JSON data, combining all categories."""
        all_words = []
        
        if not isinstance(data, dict):
            print("Warning: Invalid JSON structure. Root should be a dictionary.")
            return []
        
        for category, words in data.items():
            if isinstance(words, list):
                all_words.extend([word.upper() for word in words])
            elif isinstance(words, dict):
                # Handle nested categories
                for sub_category, sub_words in words.items():
                    if isinstance(sub_words, list):
                        all_words.extend([word.upper() for word in sub_words])
            else:
                print(f"Warning: Category '{category}' does not contain a list or dictionary")
        
        # Remove duplicates while preserving order
        unique_words = []
        seen = set()
        for word in all_words:
            if word not in seen:
                unique_words.append(word)
                seen.add(word)
        
        return unique_words
    
    def get_words(self) -> List[str]:
        """Get the loaded words."""
        return self.words
    
    def reload_words(self, fallback_words: Optional[List[str]] = None):
        """Reload words from the JSON file."""
        print("Reloading words...")
        self.load_words(fallback_words)

# Global words loader instance
words_loader = WordsLoader()

def get_words() -> List[str]:
    """Get the global words list."""
    return words_loader.get_words()

def reload_words(fallback_words: Optional[List[str]] = None):
    """Reload the global words list."""
    words_loader.reload_words(fallback_words) 