import logging
import openpyxl
from enums import CMSTools, CMSPathTypes, CMSFolders, CMSProductFolders, WorkloadManagementFormNames
from path_finder import PathFinder
import shutil
import tkinter as tk
from tkinter import filedialog
from utils import *
from config import *


def handle_connect_to_cms(username: str, password: str):
    if is_connected_to_cms():
        return "Already connected to CMS"

    result = map_network_drive(CMS_TARGET_DRIVE, CMS_NETWORK_PATH, username=username, password=password)

    if not result:
        return "Failed to connect to CMS"

    return "success"



def handle_cms_path_builder(submissions_file_path: str, path_type: str, console=None) -> str:
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

    if not is_xlsx_file(submissions_file_path):
        return "error - file path not xlsx"

    if not is_connected_to_vpn():
        return "error - not connected to vpn and oes"

    if not is_connected_to_cms():
        return "error - cms path"

    wb = openpyxl.load_workbook(submissions_file_path)
    ws = wb.active

    submissions_col = ws.cell(row=1, column=1).value
    source_col = ws.cell(row=1, column=2).value

    if not validate_path_builder_excel_columns(submissions_col, source_col):
        return "error - excel file columns"

    ws.cell(row=1, column=3).value = SubmissionsFileExcelColumns.DESTINATION.value

    submissions = get_non_empty_column_values(ws, "A")

    cms_path_finder = PathFinder()
    submission_cms_path_dict = cms_path_finder.find_cms_paths_for_submissions(submissions, path_type, console=console)

    min_row = 2
    for idx, row in enumerate(ws.iter_rows(min_row=min_row, max_col=2, values_only=True)):
        current_row_number = idx + min_row
        submission = row[0]
        if submission:
            destination_path = submission_cms_path_dict[submission]
            ws.cell(row=current_row_number, column=3).value = destination_path

    wb.save(submissions_file_path)
    return "success"

def handle_interactive_cms_path_builder(path_type: str, is_submissions_file_path: str, console: Console) -> str:

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    cms_path_finder = PathFinder()
   
    if is_submissions_file_path.lower() == "yes":
        console.print("Select Excel file containing the submissions: ", style="bold green")

        submissions_file_path = filedialog.askopenfilename(
            title="Select Excel file containing the submissions: ",
            filetypes=[("Excel files", "*.xlsx")]
        )

        if not os.path.isfile(submissions_file_path):
            return "error - file path"

        if not is_xlsx_file(submissions_file_path):
            return "error - file path not xlsx"

        wb = openpyxl.load_workbook(submissions_file_path)
        ws = wb.active

        submissions_col = ws.cell(row=1, column=1).value
        ws.cell(row=1, column=2).value = SubmissionsFileExcelColumns.SOURCE.value
        ws.cell(row=1, column=3).value = SubmissionsFileExcelColumns.DESTINATION.value

        if not validate_interactive_path_builder_excel_column(submissions_col):
            return "error - excel file columns"

        submissions = get_non_empty_column_values(ws, "A")

        row = 2

        submission_cms_path_dict = cms_path_finder.find_cms_paths_for_submissions(submissions, path_type)

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

        ws.cell(row=1, column=1).value = SubmissionsFileExcelColumns.SUBMISSION.value
        ws.cell(row=1, column=2).value = SubmissionsFileExcelColumns.SOURCE.value
        ws.cell(row=1, column=3).value = SubmissionsFileExcelColumns.DESTINATION.value

        submission_cms_path_dict = cms_path_finder.find_cms_paths_for_submissions(submissions, path_type)

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


def handle_bulk_uploader(file_path: str, generate_log_file: bool, create_missing_paths: bool, console=None) -> str:
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

    if not is_xlsx_file(file_path):
        return "error - file path not xlsx"

    if not is_connected_to_vpn():
        return "error - not connected to vpn and oes"

    if not is_connected_to_cms():
        return "error - cms path"

    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    submissions_col = ws.cell(row=1, column=1).value
    source_col = ws.cell(row=1, column=2).value
    dest_col = ws.cell(row=1, column=3).value

    if not validate_bulk_uploader_excel_columns(submissions_col, source_col, dest_col):
        return "error - excel file columns"

    # Configure the logger — also log submission, source file and new full path per row
    if generate_log_file:
        # use log next to the Excel when possible, fall back to cwd
        try:
            _log_dir = os.path.dirname(os.path.abspath(file_path)) if file_path else os.getcwd()
        except Exception:
            _log_dir = os.getcwd()
        _log_path = os.path.join(_log_dir, "bulkUploader.log")
        # fallback name kept for backwards compat — also log to bulkUploader2.log if different
        logging.basicConfig(level=logging.INFO, filename=_log_path, filemode="w",
                            format="%(asctime)s - %(levelname)s - %(message)s", force=True)
        logging.info(f"File upload started — Excel: '{file_path}' | Log: '{_log_path}' | create_missing={create_missing_paths}")

    for row in ws.iter_rows(min_row=2, max_col=3, values_only=True):
        # pre-compute detailed context for every row (submission, file, new full path) even before try
        _sub_raw = row[0]
        _src_raw = row[1]
        _dst_raw = row[2]
        _submission = str(_sub_raw).strip() if _sub_raw is not None else ""
        _src_str = str(_src_raw).strip() if _src_raw is not None else ""
        _dst_str = str(_dst_raw).strip() if _dst_raw is not None else ""
        _cleaned = clean_filename(os.path.basename(_src_str)) if _src_str else ""
        _full_dest = os.path.join(_dst_str, _cleaned) if _dst_str and _cleaned else (_dst_str or _cleaned or "")
        try:
            print(f"[{_submission}] Working on file '{_src_str}' → '{_dst_str}' | New full path: '{_full_dest}'")
            if generate_log_file:
                logging.info(f"[{_submission}] Working on file '{_src_str}' → destination folder '{_dst_str}' | New full path: '{_full_dest}' | Submission: '{_submission}'")

            # keep original variable names for copy logic but derived from the detailed context
            source_file = os.path.basename(_src_str) if _src_str else ""
            dest_path = _dst_raw  # use raw (None preserved for empty-check)
            cleaned_file_name = clean_filename(source_file) if source_file else ""
            # Create the full destination path with the new filename
            if dest_path is not None and dest_path != "":
                _dest_str_for_path = str(dest_path)
            else:
                _dest_str_for_path = _dst_str
            full_dest_path = os.path.join(_dest_str_for_path, cleaned_file_name) if _dest_str_for_path and cleaned_file_name else _full_dest

            # Check if row destination is empty
            if dest_path is None or (isinstance(dest_path, str) and not dest_path.strip()):
                print(f"[{_submission}] SKIP - Row destination empty for file '{_src_str}' | Submission: '{_submission}' | No file created")
                if generate_log_file:
                    logging.info(f"[{_submission}] SKIP - Row destination empty for file '{_src_str}' | Submission: '{_submission}' | No file created (destination was empty)")

            # Check CMS to see if the folder path of the destination exists
            elif not os.path.exists(_dst_str):
                print(f"[{_submission}] Destination folder does not exist in CMS: '{_dst_str}' | File: '{_src_str}' | New full path would be: '{full_dest_path}'")
                if generate_log_file:
                    logging.info(f"[{_submission}] Destination folder does not exist in CMS: '{_dst_str}' | File: '{_src_str}' | New full path would be: '{full_dest_path}' | Submission: '{_submission}'")

                # Create the path
                if create_missing_paths:
                    # Create the necessary directories (destination)
                    os.makedirs(_dst_str, exist_ok=True)
                    # Copy source file to the destination
                    shutil.copy2(_src_str, full_dest_path)
                    print(f"[{_submission}] COPIED (created missing folder) - file '{_src_str}' → '{full_dest_path}' | Submission: '{_submission}'")

                    if generate_log_file:
                        logging.info(f"[{_submission}] COPIED (created missing folder) - file '{_src_str}' → '{full_dest_path}' | Submission: '{_submission}'")

                    # Create the correct folder structure if the folders are missing
                    # This will reduce manual work of creating the folders later if they don't exist
                    target_folders = [
                        CMSFolders.CORRESPONDENCE_GENERAL.value,
                        CMSFolders.POST_LICENCE.value,
                        CMSFolders.DECISION.value
                    ]

                    # Check if dest_path ends with any of the target folders
                    if any(_dst_str.endswith(folder) for folder in target_folders):

                        parent_path = os.path.dirname(_dst_str)
                        try:
                            parent_path_folders = os.listdir(parent_path)
                        except Exception:
                            parent_path_folders = []

                        for item in CMSFolders.get_values():
                            if item not in parent_path_folders:
                                os.makedirs(os.path.join(parent_path, item), exist_ok=True)

                        print(f"[{_submission}] Created sibling CMS folders under '{os.path.dirname(_dst_str)}' for file '{_src_str}' | Submission: '{_submission}'")

                        if generate_log_file:
                            logging.info(f"[{_submission}] Created sibling CMS folders under '{os.path.dirname(_dst_str)}' for file '{_src_str}' | Submission: '{_submission}'")

                # If the folder create missing paths is not checked exist skip
                else:
                    print(f"[{_submission}] SKIP (create_missing disabled) - file '{_src_str}' not copied — destination '{_dst_str}' missing | Would have been: '{full_dest_path}'")
                    if generate_log_file:
                        logging.info(f"[{_submission}] SKIP (create_missing disabled) - file '{_src_str}' not copied — destination '{_dst_str}' missing | Would have been: '{full_dest_path}' | Submission: '{_submission}'")

            # Check CMS to see if the source file already exists at the destination
            elif not os.path.exists(full_dest_path):
                # Copy source file to the destination
                shutil.copy2(_src_str, full_dest_path)
                print(f"[{_submission}] COPIED - file '{_src_str}' → '{full_dest_path}' | Submission: '{_submission}'")
                if generate_log_file:
                    logging.info(f"[{_submission}] COPIED - file '{_src_str}' → '{full_dest_path}' | Submission: '{_submission}'")

            # Handle naming Workload Management Form in CMS
            elif os.path.exists(full_dest_path) and is_workload_management_form(full_dest_path):
                name_part, extension = os.path.splitext(cleaned_file_name)

                print(f"[{_submission}] Workload Management Form '{name_part}' already exists at '{full_dest_path}' — incrementing filename for file '{_src_str}' | Submission: '{_submission}'")
                if generate_log_file:
                    logging.info(f"[{_submission}] Workload Management Form exists at '{full_dest_path}' for file '{_src_str}' — incrementing filename | Submission: '{_submission}'")

                count = 0
                file_name = cleaned_file_name
                new_full_dest_path = os.path.join(_dst_str, file_name)

                while os.path.exists(new_full_dest_path):
                    count += 1
                    file_name = f"{name_part} ({count}){extension}"
                    new_full_dest_path = os.path.join(_dst_str, file_name)

                # # Copy source file to the destination
                shutil.copy2(_src_str, new_full_dest_path)
                print(f"[{_submission}] COPIED (workload form incremented) - file '{_src_str}' → '{new_full_dest_path}' | Submission: '{_submission}' | Original full path was '{full_dest_path}'")
                if generate_log_file:
                    logging.info(f"[{_submission}] COPIED (workload form incremented) - file '{_src_str}' → '{new_full_dest_path}' | Submission: '{_submission}' | Original full path was '{full_dest_path}'")


            # If the file exists don't overwrite it
            else:
                print(f"[{_submission}] SKIP - Already exists — file '{_src_str}' already at '{full_dest_path}' | Submission: '{_submission}'")
                if generate_log_file:
                    logging.info(f"[{_submission}] SKIP - Already exists — file '{_src_str}' already at '{full_dest_path}' | Submission: '{_submission}'")
        except Exception as e:
            # Log the error with full context
            print(f"[{_submission}] ERROR - file '{_src_str}' → '{_full_dest}' | Submission: '{_submission}' | Error: {e}")
            if generate_log_file:
                logging.error(f"[{_submission}] ERROR - file '{_src_str}' → '{_full_dest}' | Submission: '{_submission}' | Error: {e}")

    return "success"


def run_app():
    console = Console()
    console.print(f"{APP_NAME}", style="bold green")
    console.print(f"{'-'*50}", style="bold blue")

    while True:

        tool_selection = prompt_from_numbered_list(
            console,
            "Which tool would you like to use?",
            CMSTools.get_values()
        )

        result = ""

        if tool_selection == CMSTools.CONNECT_TO_CMS.value:

            username = Prompt.ask("[bold green]Enter username[/bold green]", console=console)
            password = Prompt.ask("[bold green]Enter password[/bold green]", console=console)

            result = handle_connect_to_cms(username, password)

        elif tool_selection == CMSTools.PATH_BUILDER.value:
            file_path_input = Prompt.ask("[bold green]Enter path to the file containing submissions[/bold green]", console=console)
            path_types = [CMSPathTypes.PRODUCT.value, CMSPathTypes.PRODUCT_POST_LICENCE_FOLDER.value,
                          CMSPathTypes.PRODUCT_CORRESPONDENCE_GENERAL_FOLDER.value,
                          CMSPathTypes.PRODUCT_DECISION_FOLDER.value]
            path_type_selection = prompt_from_numbered_list(console, "Which type of path would you like to build?", path_types)
            result = handle_cms_path_builder(file_path_input, path_type_selection, console=console)

        elif tool_selection == CMSTools.INTERACTIVE_PATH_BUILDER.value:
            path_types = [CMSPathTypes.PRODUCT.value, CMSPathTypes.PRODUCT_POST_LICENCE_FOLDER.value,
                          CMSPathTypes.PRODUCT_CORRESPONDENCE_GENERAL_FOLDER.value,
                          CMSPathTypes.PRODUCT_DECISION_FOLDER.value]
            path_type_selection = prompt_from_numbered_list(console, "Which type of path would you like to build?", path_types)
            is_submissions_file_path = Prompt.ask(prompt="[bold green]Would you like to enter the path to the file containing submissions?[/bold green]", choices=["Yes", "No"], show_choices=True, case_sensitive=False, console=console)
            result = handle_interactive_cms_path_builder(path_type_selection, is_submissions_file_path, console)

        elif tool_selection == CMSTools.BULK_UPLOADER.value:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)

            console.print("Select file containing submissions, along with their source and destination information:", style="bold green")

            file_path = filedialog.askopenfilename(
                title="Select file containing submissions, along with their source and destination information",
                filetypes=[("Excel files", "*.xlsx")]
            )

            result = handle_bulk_uploader(file_path, True, True, console=console)

        console.print(f"{result}", style="bold green")
        run_another_input = Prompt.ask(prompt="[bold blue]Would you like to run another tool?[/bold blue]", choices=["Yes", "No"], show_choices=True, case_sensitive=False, console=console)

        if run_another_input.lower() == "no":
            console.print(f"Exiting...", style="bold red")
            break

