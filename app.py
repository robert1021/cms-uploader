import os
import logging
import re
import openpyxl
from enums import CMSPathTypes, CMSSubmissionsFileExcelColumns, CMSTools
import shutil
from constants import DRIVE_LETTER, CMS_FOLDER
from rich.console import Console
from rich.prompt import Prompt
import tkinter as tk
from tkinter import filedialog
from utils import prompt_from_numbered_list, find_cms_paths_for_submissions, clean_filename



def handle_cms_path_builder(submissions_file_path: str, path_type: str) -> str:
    """
   Handle building CMS (Content Management System) paths based on the provided submissions file and path type.

   :param submissions_file_path: The path to the Excel file containing submission information.
   :param path_type: The type of CMS path to build.

   :return: A string indicating the outcome of building CMS paths.
       Possible return values:
       - "success": CMS path building was successful.
       - "error - file path": The provided file path is invalid.
       - "error - invalid cms path type": The provided CMS path type is invalid.
       - "error - Excel file columns": The columns in the Excel file are invalid.
       - "error - cms path": The CMS path is invalid.
   """

    if not os.path.isfile(submissions_file_path):
        return "error - file path"

    if not submissions_file_path.endswith(".xlsx"):
        return "error - file path"

    if not os.path.exists("Y:\\HC"):
        return "error - not connected to vpn and oes"

    cms_path = os.path.join(DRIVE_LETTER, CMS_FOLDER)
    if not os.path.isdir(cms_path):
        return "error - cms path"

    valid_path_type = False

    for item in CMSPathTypes:
        if item.value == path_type:
            valid_path_type = True
            break

    if not valid_path_type:
        return "error - invalid cms path type"

    wb = openpyxl.load_workbook(submissions_file_path)
    ws = wb.active

    submissions_col = ws.cell(row=1, column=1).value
    source_col = ws.cell(row=1, column=2).value

    if submissions_col is None or source_col is None:
        return "error - excel file columns"

    if submissions_col.lower() != CMSSubmissionsFileExcelColumns.SUBMISSION.value.lower() or source_col.lower() != CMSSubmissionsFileExcelColumns.SOURCE.value.lower():
        return "error - excel file columns"

    ws.cell(row=1, column=3).value = CMSSubmissionsFileExcelColumns.DESTINATION.value

    submissions = [cell.value for cell in ws["A"][1:] if cell.value is not None]

    submission_cms_path_dict = find_cms_paths_for_submissions(submissions, path_type)

    min_row = 2
    for idx, row in enumerate(ws.iter_rows(min_row=min_row, max_col=2, values_only=True)):
        current_row_number = idx + min_row
        submission = row[0]
        destination_path = submission_cms_path_dict[submission]
        ws.cell(row=current_row_number, column=3).value = destination_path

    wb.save(submissions_file_path)
    return "success"

def handle_interactive_cms_path_builder(path_type: str, is_submissions_file_path: str, console: Console) -> str:

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
   
    if is_submissions_file_path.lower() == "yes":
        submissions_file_path = Prompt.ask("[bold green]Enter path to the file containing submissions[/bold green]", console=console)

        if not os.path.isfile(submissions_file_path):
            return "error - file path"

        if not submissions_file_path.endswith(".xlsx"):
            return "error - file path"

        wb = openpyxl.load_workbook(submissions_file_path)
        ws = wb.active

        submissions_col = ws.cell(row=1, column=1).value
        ws.cell(row=1, column=2).value = CMSSubmissionsFileExcelColumns.SOURCE.value
        ws.cell(row=1, column=3).value = CMSSubmissionsFileExcelColumns.DESTINATION.value

        if submissions_col is None:
            return "error - excel file columns"

        if submissions_col.lower() != CMSSubmissionsFileExcelColumns.SUBMISSION.value.lower():
            return "error - excel file columns"

        submissions = [cell.value for cell in ws["A"][1:] if cell.value is not None]

        row = 2

        # TODO: Only handles post licence path for now

        submission_cms_path_dict = find_cms_paths_for_submissions(submissions, path_type)

        is_same_files_each_sub = Prompt.ask("[bold green]Would you like to upload the same files to every submission?[/bold green]", choices=["Yes", "No"], show_choices=True, case_sensitive=False, console=console)

        # Handle the "same files" case first, getting source files once
        if is_same_files_each_sub.lower() == "yes":
            shared_source_files = filedialog.askopenfilenames(title="Select Files for All Submissions")
        else:
            shared_source_files = []

        # Single loop to process all submissions and their files
        for sub in submissions:
            # Determine the source files for the current submission
            if is_same_files_each_sub.lower() == "no":
                # If "different files," prompt for them inside the loop
                source_files = filedialog.askopenfilenames(title=f"Select Files for Submission: {sub}")
            else:
                # If "same files," use the previously selected files
                source_files = shared_source_files

            destination_path = submission_cms_path_dict.get(sub, "")

            # Write each file path to the workbook
            for file_path in source_files:
                ws.cell(row=row, column=1).value = sub
                ws.cell(row=row, column=2).value = file_path
                ws.cell(row=row, column=3).value = destination_path
                row += 1

        wb.save(submissions_file_path)

    else:

        user_submissions_str = Prompt.ask("[bold green]Enter submission ID(s) (comma-separated if multiple)[/bold green]", console=console)
        submissions = [s.strip() for s in user_submissions_str.split(',') if s.strip()]
        
        if not submissions:
            return "error - no submissions entered"

        # Create a new workbook
        wb = openpyxl.Workbook()
        ws = wb.active

        row = 2

        ws.cell(row=1, column=1).value = CMSSubmissionsFileExcelColumns.SUBMISSION.value
        ws.cell(row=1, column=2).value = CMSSubmissionsFileExcelColumns.SOURCE.value
        ws.cell(row=1, column=3).value = CMSSubmissionsFileExcelColumns.DESTINATION.value

        submission_cms_path_dict = find_cms_paths_for_submissions(submissions, path_type)

        is_same_files_each_sub = Prompt.ask("[bold green]Would you like to upload the same files to every submission?[/bold green]", choices=["Yes", "No"], show_choices=True, case_sensitive=False, console=console)

        # Handle the "same files" case first, getting source files once
        if is_same_files_each_sub.lower() == "yes":
            shared_source_files = filedialog.askopenfilenames(title="Select Files for All Submissions")
        else:
            shared_source_files = []

        # Single loop to process all submissions and their files
        for sub in submissions:
            # Determine the source files for the current submission
            if is_same_files_each_sub.lower() == "no":
                # If "different files," prompt for them inside the loop
                source_files = filedialog.askopenfilenames(title=f"Select Files for Submission: {sub}")
            else:
                # If "same files," use the previously selected files
                source_files = shared_source_files

            destination_path = submission_cms_path_dict.get(sub, "")

            # Write each file path to the workbook
            for file_path in source_files:
                ws.cell(row=row, column=1).value = sub
                ws.cell(row=row, column=2).value = file_path
                ws.cell(row=row, column=3).value = destination_path
                row += 1

        wb.save("output.xlsx")

    return "success"


def handle_bulk_uploader(file_path: str, generate_log_file: bool, create_missing_paths: bool) -> str:
    """
    Handle bulk uploading of files to the CMS based on the information provided in the Excel file.

    :param file_path: The path to the Excel file containing file upload information.
    :param generate_log_file: A boolean indicating whether to generate a log file during the upload process.
    :param create_missing_paths: A boolean indicating whether to create missing paths in the CMS during the upload process.

    :return: A string indicating the outcome of the bulk uploading process.
        Possible return values:
        - "success": Bulk uploading was successful.
        - "error - file path": The provided file path is invalid.
        - "error - Excel file columns": The columns in the Excel file are invalid.
        - "error - cms path": The CMS path is invalid.
    """
    if not os.path.isfile(file_path):
        return "error - file path"

    if not file_path.endswith(".xlsx"):
        return "error - file path"

    if not os.path.exists("Y:\\HC"):
        return "error - not connected to vpn and oes"

    cms_path = os.path.join(DRIVE_LETTER, CMS_FOLDER)
    if not os.path.isdir(cms_path):
        return "error - cms path"

    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    submissions_col = ws.cell(row=1, column=1).value
    source_col = ws.cell(row=1, column=2).value
    dest_col = ws.cell(row=1, column=3).value

    if submissions_col is None or source_col is None or dest_col is None:
        return "error - excel file columns"

    if (submissions_col.lower() != CMSSubmissionsFileExcelColumns.SUBMISSION.value.lower() or
            source_col.lower() != CMSSubmissionsFileExcelColumns.SOURCE.value.lower() or
            dest_col.lower() != CMSSubmissionsFileExcelColumns.DESTINATION.value.lower()):
        return "error - excel file columns"

    # Configure the logger
    if generate_log_file:
        logging.basicConfig(level=logging.INFO, filename="bulkUploader.log", filemode="w",
                            format="%(asctime)s - %(levelname)s - %(message)s")
        logging.info("File upload started...")

    for row in ws.iter_rows(min_row=2, max_col=3, values_only=True):
        try:
            print(f"{str(row[0])}")
            print(f"Working on copying {row[1]} to {row[2]}")
            if generate_log_file:
                logging.info(f"Working on copying {row[1]} to {row[2]}")

            source_file = os.path.basename(row[1])
            cleaned_file_name = clean_filename(source_file)
            # Create the full destination path with the new filename
            full_dest_path = os.path.join(row[2], cleaned_file_name)

            # Check if row destination is empty
            if row[2] is None:
                print("Row destination is empty! Skipping...")
                if generate_log_file:
                    logging.info("Row destination is empty! Skipping...")

            # Check CMS to see if the folder path of the destination exists
            elif not os.path.exists(row[2]):
                print("Destination folder path doesn't exist in CMS!")
                if generate_log_file:
                    logging.info("Destination folder path doesn't exist in CMS!")

                # Create the path
                if create_missing_paths:
                    # Create the necessary directories (destination)
                    os.makedirs(row[2])
                    # Copy source file to the destination
                    shutil.copy2(row[1], full_dest_path)
                    print("Created missing path and copied file to it!")
                    if generate_log_file:
                        logging.info("Created missing path and copied file to it!")

                # If the folder create missing paths is not checked exist skip
                else:
                    print("Skipping...")
                    if generate_log_file:
                        logging.info("Skipping...")

            # Check CMS to see if the source file already exists at the destination
            elif not os.path.exists(full_dest_path):
                # Copy source file to the destination
                shutil.copy2(row[1], full_dest_path)
                print("File copied successfully!")
                if generate_log_file:
                    logging.info("File copied successfully!")

            # If the file exists don't overwrite it
            else:
                print("File already exists at the destination! No creation necessary...")
                if generate_log_file:
                    logging.info("File already exists at the destination! No creation necessary...")
        except Exception as e:
            # Log the error
            if generate_log_file:
                logging.error(str(e))

    return "success"


def run_app():
    console = Console()
    console.print("CMS Automation Tool", style="bold green")
    console.print(f"{'-'*50}", style="bold blue")

    while True:

        tool_selection = prompt_from_numbered_list(
            console,
            "Which tool would you like to use?",
            CMSTools.get_values()
        )

        results = ""

        if tool_selection == CMSTools.PATH_BUILDER.value:
            file_path_input = Prompt.ask("[bold green]Enter path to the file containing submissions[/bold green]", console=console)
            path_type_selection = prompt_from_numbered_list(console, "Which type of path would you like to build?", CMSPathTypes.get_values())
            results = handle_cms_path_builder(file_path_input, path_type_selection)

        elif tool_selection == CMSTools.INTERACTIVE_PATH_BUILDER.value:
            path_types = [CMSPathTypes.PRODUCT.value, CMSPathTypes.PRODUCT_POST_LICENCE_FOLDER.value]
            path_type_selection = prompt_from_numbered_list(console, "Which type of path would you like to build?", path_types)
            is_submissions_file_path = Prompt.ask(prompt="[bold green]Would you like to enter the path to the file containing submissions?[/bold green]", choices=["Yes", "No"], show_choices=True, case_sensitive=False, console=console)
            result = handle_interactive_cms_path_builder(path_type_selection, is_submissions_file_path, console)

        elif tool_selection == CMSTools.BULK_UPLOADER.value:
            file_path_input = Prompt.ask("[bold green]Enter path to the file containing submissions, along with their source and destination information[/bold green]", console=console)
            results = handle_bulk_uploader(file_path_input, True, True)

        console.print(f"{results}", style="bold green")
        run_another_input = Prompt.ask(prompt="[bold blue]Would you like to run another tool?[/bold blue]", choices=["Yes", "No"], show_choices=True, case_sensitive=False, console=console)

        if run_another_input.lower() == "no":
            console.print(f"Exiting...", style="bold red")
            break

