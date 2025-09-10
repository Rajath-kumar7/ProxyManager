import asyncio
from typing import Optional

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from loguru import logger

from .db.database import init_db
from .main import (
    recheck_workflow,
    collect_only_workflow,
    export_all_workflow,
    delete_all_proxies_workflow
)
from .core.config import config

# Initialize Rich console for styled output
console = Console()

# ASCII art logo
ASCII_LOGO = r"""
  /$$$$$$  /$$ /$$ /$$$$$$$                                /$$$$$$ /$$   /$$
 /$$__  $$| $$|__/| $$__  $$                              |_  $$_/| $$  / $$
| $$  \ $$| $$ /$$| $$  \ $$  /$$$$$$  /$$$$$$$$  /$$$$$$   | $$  |  $$/ $$/
| $$$$$$$$| $$| $$| $$$$$$$/ /$$__  $$|____ /$$/ |____  $$  | $$   \  $$$$/ 
| $$__  $$| $$| $$| $$__  $$| $$$$$$$$   /$$$$/   /$$$$$$$  | $$    >$$  $$ 
| $$  | $$| $$| $$| $$  \ $$| $$_____/  /$$__/   /$$__  $$  | $$   /$$/\  $$
| $$  | $$| $$| $$| $$  | $$|  $$$$$$$ /$$$$$$$$|  $$$$$$$ /$$$$$$| $$  \ $$
|__/  |__/|__/|__/|__/  |__/ \_______/|________/ \_______/|______/|__/  |__/
"""

# Function to display the header with logo and info
def display_header():
    console.clear()
    logo_text = Text(ASCII_LOGO, style="bold magenta", justify="center")
    console.print(logo_text)

    info_text = Text(
        "Developed by AliRezaIX | Telegram: @alirezaix | GitHub: github.com/ArixWorks",
        justify="center",
        style="cyan"
    )

    panel = Panel(
        info_text,
        title="[bold yellow]ProxyManager v2.0[/bold yellow]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()

# Main asynchronous loop for the CLI
async def main_loop():
    while True:
        display_header()

        choice = await questionary.select(
            "What would you like to do?",
            choices=[
                "1. Collect new proxies from sources",
                "2. Re-check all proxies (using default URL)",
                "3. Re-check all proxies (using custom URL)",
                "4. Export all proxies from DB to files",
                "5. Clear the entire proxy database",
                "Exit"
            ],
            use_indicator=True
        ).ask_async()

        console.clear()

        if choice is None or choice == "Exit":
            console.print("[bold cyan]👋 Goodbye![/bold cyan]")
            break

        try:
            if choice.startswith("1."):
                await collect_only_workflow()

            elif choice.startswith("2."):
                default_url = config.get('check_url_default', 'http://httpbin.org/get')
                console.print(f"🎯 Using default URL for re-check: [yellow]{default_url}[/yellow]")
                await recheck_workflow(target_url=default_url)

            elif choice.startswith("3."):
                custom_url = await questionary.text(
                    "Enter the target URL to check proxies against:",
                    validate=lambda url: url.startswith("http")
                ).ask_async()
                if custom_url:
                    await recheck_workflow(target_url=custom_url)

            elif choice.startswith("4."):
                await export_all_workflow()

            elif choice.startswith("5."):
                confirm = await questionary.confirm(
                    "⚠️ Are you sure you want to delete ALL proxies? This action cannot be undone.",
                    default=False
                ).ask_async()
                if confirm:
                    await delete_all_proxies_workflow()
                else:
                    console.print("[yellow]❌ Deletion cancelled.[/yellow]")

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            console.print(f"[bold red]An error occurred. Check 'proxymanager.log' for details.[/bold red]")

        console.print("\n[bold green]Press Enter to return to the main menu...[/bold green]")
        input()

# Entry point to start the application
def start_app():
    logger.add("logs/proxymanager.log", rotation="10 MB", level="INFO")
    asyncio.run(init_db())
    asyncio.run(main_loop())

# Run the application if this file is executed directly
if __name__ == "__main__":
    start_app()
