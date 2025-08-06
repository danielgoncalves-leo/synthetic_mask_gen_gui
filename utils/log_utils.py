import os
from rich.console import Console

console = Console()

class AppLogger:
    def __init__(self, config):
        self.config = config

    def info(self, message):
        if self.config.logging.level.upper() == "INFO":
            console.print(message)

    def warning(self, message):
        if self.config.logging.level.upper() in ["INFO", "WARNING"]:
            console.print(f"⚠️  [yellow]WARNING:[/] {message}")

    def error(self, message):
        console.print(f"❌ [bold red]ERROR:[/] {message}")

    def success(self, message):
        if self.config.logging.level.upper() == "INFO":
            console.print(f"✅ [green]SUCCESS:[/] {message}")

    def debug(self, message):
        if self.config.logging.level.upper() == "DEBUG":
            console.print(f"⚙️  [dim]DEBUG:[dim] {message}")

# You can create a global logger instance if you pass the config to it
# logger = AppLogger(config) 