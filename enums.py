from enum import Enum

class BaseEnum(Enum):
    
    @classmethod
    def get_values(cls):
        """Returns a list of all the values in the enum."""
        return [member.value for member in cls]

class CMSProductFolders(BaseEnum):
    APPLICATION_WORKBOOKS = "Application Workbooks"
    SUBMISSIONS = "Submissions"

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

class CMSFoldersOld(BaseEnum):
    CORRESPONDENCE = "1) Correspondence"
    FORMS = "2) Forms"
    EVIDENCE = "3) Evidence"
    ASSESSMENT = "4) Assessment"

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
    CONNECT_TO_CMS = "Connect to CMS"
    PATH_BUILDER = "Path Builder"
    BULK_UPLOADER = "Bulk Uploader"
    INTERACTIVE_PATH_BUILDER = "Interactive Path Builder"

class WorkloadManagementFormNames(BaseEnum):
    PRODUCTS_SOLD_IN_CANADA = "Workload Management Form – Products Sold in Canada – Response"
    MANUFACTURED_IN_CANADA = "Workload Management Form – Manufactured in Canada – Response"
    PRODUITS_VENDUS_AU_CANADA = "Formulaire de gestion de la charge de travail – Produits vendus au Canada – Réponse"
    FABRIQUE_AU_CANADA = "Formulaire de gestion de la charge de travail – Fabriqué au Canada – Réponse"