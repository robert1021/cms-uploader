import os
from enums import CMSFolders
from constants import *


class PathFinder:

    @staticmethod
    def find_product_folder(range_path: str, file_number: str, submission_number: str = None):
        """
        Finds the product folder based on the given parameters.

        :param range_path: The path of the range.
        :param file_number: The file number.
        :param submission_number: (Optional) The submission number. Default is None.

        :return: The path of the found folder or None if not found.
        """
        # Get a filtered list of relevant folders
        folders = [folder for folder in os.listdir(range_path) if
                   file_number.lower() in folder and os.path.isdir(os.path.join(range_path, folder))]
        # Submission number passed as an argument
        if submission_number is not None:
            # Iterate the folders
            for folder in folders:
                # Submission number is in the folder name
                if submission_number.lower() in folder.lower():
                    return os.path.join(range_path, folder)
                # Submission number not in the parent folder name - Walk through the directories to find it
                for root, dirs, files in os.walk(os.path.join(range_path, folder)):
                    for item in dirs:
                        # Submission number is in the sub folder name
                        if submission_number.lower() in item.lower():
                            return os.path.join(root, item)
            # Folder doesn't exist for file number - submission number - create one based on pattern
            return os.path.join(range_path, file_number, f"{file_number} - {submission_number}")

        else:
            for folder in folders:
                # Find matching file number
                if file_number.lower() in folder.lower() and f"{file_number}." not in folder.lower() and f"{file_number} -" not in folder.lower() and f"{file_number}-" not in folder.lower():
                    # Get a list of sub folders
                    sub_folders = [sub_folder for sub_folder in os.listdir(os.path.join(range_path, folder)) if
                                   os.path.isdir(os.path.join(range_path, folder, sub_folder))]
                    # Check for CMS folders - If they exist you can use the current folder as the path
                    for subFolder in sub_folders:
                        for item in CMSFolders:
                            if item.value in subFolder:
                                return os.path.join(range_path, folder)
                    # CMS Folders don't exist at this level
                    # Search for sub folder with file number in it
                    for subFolder in sub_folders:
                        if file_number.lower() in subFolder.lower() and f"{file_number}." not in subFolder.lower() and f"{file_number} -" not in subFolder.lower() and f"{file_number}-" not in subFolder.lower() and "discussion" not in subFolder.lower():
                            return os.path.join(range_path, folder, subFolder)
                    # File number doesn't exist in sub folders - Create it
                    return os.path.join(range_path, folder, file_number)
            # Folder doesn't exist for file number - create one based on pattern
            return os.path.join(range_path, file_number, file_number)

    def find_product_post_licence_folder(self, range_path: str, file_number: str):
        """
        Finds the post-licence product folder based on the given parameters.

        :param range_path: The path of the range.
        :param file_number: The file number.

        :return: The path to the Post Licence folder.
        """
        file_path = self.find_product_folder(range_path, file_number)
        if os.path.isdir(file_path):
            for folder in os.listdir(file_path):
                if POST_LICENCE_FOLDER_NAME.lower() in folder.lower():
                    return os.path.join(file_path, folder)
        # Post Licence folder not found - Create path based on pattern
        return os.path.join(file_path, POST_LICENCE_FOLDER_NAME)