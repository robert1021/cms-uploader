from enum import Enum


class CMSFolders(Enum):
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

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]


class CMSPathTypes(Enum):
    PRODUCT = "Product"
    PRODUCT_POST_LICENCE_FOLDER = "Product - Post Licence Folder"
    SITE = "Site"
    FOREIGN_SITE = "Foreign Site"
    TRADING_PARTNER = "Trading Partner"
    CLINICAL_TRIAL = "Clinical Trial"
    COMPANY = "Company"
    MASTER_FILE = "Master File"

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]


class CMSSubmissionsFileExcelColumns(Enum):
    SUBMISSION = "Submission"
    SOURCE = "Source"
    DESTINATION = "Destination"

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]


class CMSTools(Enum):
    PATH_BUILDER = "Path Builder"
    BULK_UPLOADER = "Bulk Uploader"

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]

