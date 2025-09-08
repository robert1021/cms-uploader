from enum import Enum

class BaseEnum(Enum):
    
    @classmethod
    def get_values(cls):
        """Returns a list of all the values in the enum."""
        return [member.value for member in cls]


class CMSFolders(BaseEnum):
    CORRESPONDENCE_GENERAL = "a) Correspondence General"
    CORRESPONDENCE_ASSESSMENT = "b) Correspondence Assessment"
    EPLA_LABEL = "c) ePLA & label"
    SE_EVIDENCE = "d) S&E Evidence"
    EVIDENCE_SUMMARY = "e) Evidence Summary"
    ASSESSMENT = "f) Assessment"
    QUALITY_EVIDENCE = "g) Quality Evidence"
    DECISION = "h) Decision"
    POST_LICENCE = "i) Post Licence"
    ORIGINAL_SUBMISSION = "j) Original Submission"


class CMSPathTypes(BaseEnum):
    PRODUCT = "Product"
    PRODUCT_POST_LICENCE_FOLDER = "Product - Post Licence Folder"
    PRODUCT_CORRESPONDENCE_GENERAL_FOLDER = "Product - Correspondence General"
    SITE = "Site"
    FOREIGN_SITE = "Foreign Site"
    TRADING_PARTNER = "Trading Partner"
    CLINICAL_TRIAL = "Clinical Trial"
    COMPANY = "Company"
    MASTER_FILE = "Master File"


class SubmissionsFileExcelColumns(BaseEnum):
    SUBMISSION = "Submission"
    SOURCE = "Source"
    DESTINATION = "Destination"


class CMSTools(BaseEnum):
    PATH_BUILDER = "Path Builder"
    BULK_UPLOADER = "Bulk Uploader"
    INTERACTIVE_PATH_BUILDER = "Interactive Path Builder"

