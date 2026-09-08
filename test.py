import openpyxl

def split_cell_data(file_path):
    # 1. Load the workbook and select the active sheet
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    # 2. Read the value from cell A2
    cell_value = sheet['A2'].value

    if cell_value:
        # 3. Split the text by comma and strip extra whitespace
        data_list = [item.strip() for item in str(cell_value).split(',')]

        # 4. Write numbers starting from cell A3 (Row 3, Column 1)
        start_row = 3
        for index, value in enumerate(data_list):
            sheet.cell(row=start_row + index, column=1).value = value.strip()

        # 5. Save the changes
        wb.save(file_path)
        print(f"Successfully processed {len(data_list)} items.")
    else:
        print("Cell A2 is empty.")

# Run the function
split_cell_data(r"C:\Development\CMS\572\npn.xlsx")