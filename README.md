# cms-uploader

## Tool Instructions

### Connect to CMS

This tool maps a network drive to the CMS, allowing the other tools to access it.

**Prerequisites:**
- You must be connected to the company VPN.

**Inputs:**
- **Username:** Your CMS username.
- **Password:** Your CMS password.

### Path Builder

This tool generates CMS destination paths for a list of submissions and adds them to an Excel file.

**Prerequisites:**
- You must be connected to the company VPN.
- You must have successfully run the "Connect to CMS" tool.

**Inputs:**
- **Path to submissions file:** An Excel file (`.xlsx`) with the following columns in this order:
  - `Submission`: The submission ID.
  - `Source`: The path to the source file.

**Output:**
- The tool will add a `Destination` column to the same Excel file, containing the generated CMS path for each submission.

### Interactive Path Builder

This tool provides an interactive way to create an Excel file with submission, source, and destination information. It is useful when you don't have a pre-existing Excel file.

**Prerequisites:**
- You must be connected to the company VPN.
- You must have successfully run the "Connect to CMS" tool.

**Process:**
1.  The tool will ask if you want to provide a file with submissions or enter them manually.
2.  If you choose to enter them manually, you will be prompted to enter the submission IDs.
3.  The tool will then ask if you want to upload the same files for every submission.
4.  A file dialog will open, allowing you to select the source files.
5.  The tool will generate an `output.xlsx` file in the application's directory with `Submission`, `Source`, and `Destination` columns populated with the information you provided.

**Output:**
- An `output.xlsx` file in the application's directory.

### Bulk Uploader

This tool uploads files in bulk to the CMS based on an Excel file.

**Prerequisites:**
- You must be connected to the company VPN.
- You must have successfully run the "Connect to CMS" tool.

**Inputs:**
- **Path to file:** An Excel file (`.xlsx`) with the following columns in this order:
  - `Submission`: The submission ID.
  - `Source`: The path to the source file to be uploaded.
  - `Destination`: The CMS path where the file should be uploaded.
    - This can be generated using the "Path Builder" or "Interactive Path Builder" tools.

**Features:**
- **Logging:** Creates a `bulkUploader.log` file in the application's directory to log the progress and any errors.
- **Create Missing Paths:** Automatically creates destination folders in the CMS if they do not exist.