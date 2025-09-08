from rich.console import Console
from rich.prompt import Prompt
from typing import List
import re
from enums import SubmissionsFileExcelColumns
import os
from constants import DRIVE_LETTER, CMS_FOLDER, Y_DRIVE_PATH
import subprocess


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

def clean_filename(filename: str) -> str:
    """
    Removes a trailing ' (number)' suffix from a filename.

    For example, 'My Report (1).pdf' becomes 'My Report.pdf'.

    :param filename: The input filename string.
    :return: The cleaned filename string.
    """
    # Separate the filename from its extension (e.g., 'My Report (1)', '.pdf')
    name_part, extension = os.path.splitext(filename)

    # Use a regular expression to find and replace the pattern at the end of the name
    # r' \(\d+\)$' looks for: a space, '(', one or more digits, ')' at the end ($)
    cleaned_name_part = re.sub(r' \(\d+\)$', '', name_part)

    # Rejoin the cleaned name with the original extension
    return cleaned_name_part + extension

def is_valid_file_path(file_path):
    """Checks if a given path is a valid file."""
    return os.path.isfile(file_path)

def is_xlsx_file(file_path):
    """Checks if a file has a .xlsx extension."""
    return file_path.endswith(".xlsx")

def is_connected_to_vpn():
    """Checks if connected to VPN."""
    return os.path.exists(Y_DRIVE_PATH)

def is_connected_to_cms():
    cms_path = os.path.join(DRIVE_LETTER, CMS_FOLDER)
    return os.path.isdir(cms_path)

def is_valid_directory(directory_path):
    """Checks if a given path is a valid directory."""
    return os.path.isdir(directory_path)

def validate_bulk_uploader_excel_columns(submissions_col, source_col, dest_col):
    """
    Checks if the given column names match the expected enum values, ignoring case.

    Args:
        submissions_col (str): The name of the submission column.
        source_col (str): The name of the source column.
        dest_col (str): The name of the destination column.

    Returns:
        bool: True if all column names match the expected values, otherwise False.
    """
    if (submissions_col.lower() != SubmissionsFileExcelColumns.SUBMISSION.value.lower() or
            source_col.lower() != SubmissionsFileExcelColumns.SOURCE.value.lower() or
            dest_col.lower() != SubmissionsFileExcelColumns.DESTINATION.value.lower()):
        return False
    return True

def validate_path_builder_excel_columns(submissions_col, source_col):
    """
    Checks if the given column names match the expected enum values, ignoring case.

    Args:
        submissions_col (str): The name of the submission column.
        source_col (str): The name of the source column.

    Returns:
        bool: True if both column names match the expected values, otherwise False.
    """
    if (submissions_col.lower() != SubmissionsFileExcelColumns.SUBMISSION.value.lower() or
            source_col.lower() != SubmissionsFileExcelColumns.SOURCE.value.lower()):
        return False
    return True

def validate_interactive_path_builder_excel_column(submissions_col):
    """
    Checks if the given column names match the expected enum values, ignoring case.

    Args:
        submissions_col (str): The name of the submission column.

    Returns:
        bool: True if the name matches the expected value, otherwise False.
    """
    if submissions_col.lower() != SubmissionsFileExcelColumns.SUBMISSION.value.lower():
        return False
    return True

def get_non_empty_column_values(worksheet, column_letter):
    """
    Retrieves a list of non-empty cell values from a specified column of a worksheet.

    Args:
        worksheet: The worksheet object (e.g., from openpyxl).
        column_letter (str): The letter of the column to retrieve values from (e.g., "A", "B").

    Returns:
        list: A list of all non-None cell values in the specified column, starting from the second row.
    """
    # Build the cell range string, e.g., "A[1:]"
    column_range = worksheet[column_letter][1:]

    # Use a list comprehension to get non-empty values
    return [cell.value for cell in column_range if cell.value is not None]

def map_network_drive(drive_letter, network_path, username=None, password=None):
    """
    Maps a network share to a local drive letter using the 'net use' command.

    Args:
        drive_letter (str): The local drive letter to use (e.g., 'Z:').
        network_path (str): The UNC path to the network share (e.g., '\\\\ServerName\\ShareName').
        username (str, optional): Username for authentication, if required.
        password (str, optional): Password for authentication, if required.

    Returns:
        bool: True if the mapping was successful, False otherwise.
    """
    try:
        # 1. Start with the base command to map the drive
        command = f"net use {drive_letter} {network_path}"

        # 2. Add authentication details if provided
        if username and password:
            command += f" {password} /user:{username}"
        # 3. Add '/persistent:no' to ensure the map is not retained after reboot
        command += " /persistent:no"

        # Execute the command and capture output
        result = subprocess.run(
            command,
            shell=True,
            check=True,  # Raise an exception for non-zero exit codes
            capture_output=True,
            text=True
        )

        # Success is usually indicated by a zero return code
        print(f"Successfully mapped {network_path} to {drive_letter}")
        print("Output:", result.stdout.strip())
        return True

    except subprocess.CalledProcessError as e:
        # Handle cases where the command fails (e.g., invalid path, wrong credentials)
        print(f"Error mapping drive: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False