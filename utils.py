from rich.console import Console
from rich.prompt import Prompt
from typing import List, Dict
from path_finder import PathFinder
from map_path_builder import MapPathBuilder
import re
from enums import CMSPathTypes, SubmissionsFileExcelColumns
import os
from constants import DRIVE_LETTER, CMS_FOLDER, Y_DRIVE_PATH


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

def find_cms_paths_for_submissions(submissions: List[str], path_type: str) -> Dict[str, str]:
    """
    Finds the CMS destination paths for a list of submissions.

    This function extracts a 6-digit submission ID from each submission string,
    then uses the path_builder and path_finder objects to locate
    the corresponding CMS folder. It handles cases where a path is not found.

    Args:
        submissions (List[str]): A list of submission strings to process.

    Returns:
        Dict[str, str]: A dictionary mapping each submission string to its
                        found CMS path. If a path is not found, the value
                        is an empty string.
    """

    path_builder = MapPathBuilder()
    path_finder = PathFinder()
    submission_cms_path_dict = {}
    
    # Iterate through each submission to find its CMS path
    for sub in submissions:
        # Use regex to find a 6-digit number, assuming it's the product ID
        matches = re.findall(r"\b\d{6}", str(sub).lower())
        
        # Ensure a submission ID was found
        if not matches:
            submission_cms_path_dict[sub] = ""
            continue
            
        submission_id = str(matches[0])
        
        try:
            path = None

            # Build the generic product path and then find the specific folder
            if path_type == CMSPathTypes.PRODUCT.value:
                path = path_finder.find_product_folder(path_builder.build_product_path(submission_id), submission_id)

            elif path_type == CMSPathTypes.PRODUCT_POST_LICENCE_FOLDER.value:
                path = path_finder.find_product_post_licence_folder(path_builder.build_product_path(submission_id), submission_id)

            elif path_type == CMSPathTypes.PRODUCT_CORRESPONDENCE_GENERAL_FOLDER.value:
                path = path_finder.find_product_correspondence_general_folder(path_builder.build_product_path(submission_id), submission_id)
            # Store the found path in the dictionary
            submission_cms_path_dict[sub] = path if path is not None else ""
            
        except FileNotFoundError:
            # If the product ID or path is not found, store an empty string
            submission_cms_path_dict[sub] = ""
            
    return submission_cms_path_dict


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