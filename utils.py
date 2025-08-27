from rich.console import Console
from rich.prompt import Prompt
from typing import List

def prompt_from_numbered_list(console: Console, prompt_title: str, options: List[str]) -> str:
    """
    Displays a numbered menu from a list of options and returns the user's selection.

    :param console: The Rich Console object for printing.
    :param prompt_title: The question to display above the numbered list.
    :param options: A list of strings to be displayed as numbered choices.
    :return: The string value of the selected option.
    """
    # Build the prompt text with a numbered list
    prompt_lines = [f"\n[bold green]{prompt_title}[/bold green]\n"]
    choices = []
    
    for i, option in enumerate(options, 1):
        prompt_lines.append(f"  [cyan]{i}[/cyan]. {option}")
        choices.append(str(i))
    
    console.print("\n".join(prompt_lines))

    # Ask the user for a numeric choice
    selection = Prompt.ask(
        prompt="[bold green]Enter your choice[/bold green]",
        choices=choices,
        show_choices=False,
        console=console
    )

    # Map the number back to the corresponding string value from the original list
    selected_option = options[int(selection) - 1]
    
    return selected_option