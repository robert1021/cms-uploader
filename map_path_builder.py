import os.path
from constants import *


class MapPathBuilder:

    @staticmethod
    def build_product_path(file_number: str) -> str or None:
        """
        Build the Product CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        # Check to see if the submission number is within specific ranges
        if 100000 <= int(file_number) <= 257999:
            return os.path.join(DRIVE_LETTER, CMS_FOLDER, APPLICATION_WORKBOOKS,
                                file_number[:3] + "000" + "-" + file_number[:3] + "999",
                                file_number[:3] + file_number[3] + "00" + "-" + file_number[:3] +
                                file_number[3] + "99")
        elif 400000 <= int(file_number) <= 807999:
            return os.path.join(DRIVE_LETTER, CMS_FOLDER, SUBMISSIONS,
                                file_number[:3] + "000" + "-" + file_number[:3] + "999",
                                file_number[:3] + file_number[3] + "00" + "-" + file_number[:3] +
                                file_number[3] + "99")
        else:
            return None

    @staticmethod
    def build_site_path(company_code: str, file_number: str) -> str or None:
        """
        Build the Site CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        return os.path.join(DRIVE_LETTER, CMS_FOLDER, SITE_SUBMISSIONS, "0" + company_code[:2] + "000" + "-" + "0" +
                            company_code[:2] + "999", "0" + company_code[:3] + "00" + "-" + "0" +
                            company_code[:3] + "99", company_code, file_number)

    def build_foreign_site_path(self, company_code, file_number) -> str or None:
        """
        Build the Foreign Site CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        return self.build_site_path(company_code, file_number)

    @staticmethod
    def build_trading_partner_path(company_code) -> str or None:
        """
        Build the Trading Partner CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        return os.path.join(DRIVE_LETTER, CMS_FOLDER, TRADING_PARTNER_FILES,
                            company_code[0] + "0000" + "-" + company_code[0] + "9999",
                            company_code[:2] + "000" + "-" + company_code[:2] + "999",
                            company_code[:3] + "00" + "-" + company_code[:3] + "99", company_code)

    @staticmethod
    def build_clinical_trial_path() -> str or None:
        """
        Build the Clinical Trial CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        # TODO: NEED TO CODE THIS
        return None

    @staticmethod
    def build_company_path(company_code) -> str or None:
        """
        Build the Company CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        return os.path.join(DRIVE_LETTER, CMS_FOLDER, COMPANY_UPDATES,
                            company_code[0] + "0000" + "-" + company_code[0] + "9999",
                            company_code[:2] + "000" + "-" + company_code[:2] + "999",
                            company_code[:3] + "00" + "-" + company_code[:3] + "99", company_code)

    @staticmethod
    def build_master_file_path(company_code) -> str or None:
        """
        Build the Master File CMS path based on the submission number.

        :return: The built path as a string or None if the submission number is not within the specified ranges.
        """
        folder_range = company_code[0] + "0000" + "-" + company_code[0] + "4999" if int(company_code[1]) <= 4 else \
            company_code[0] + "5000" + "-" + company_code[0] + "9999"
        return os.path.join(DRIVE_LETTER, CMS_FOLDER, MASTER_FILES, folder_range, company_code)