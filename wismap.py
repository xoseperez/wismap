#!/bin/python3

import os
import sys
import yaml
from rich.console import Console
from rich.table import Table
from mergedeep import merge
import openpyxl
import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

mapping_file = "config/mapping.yml"
slots_file = "config/slots.yml"
patches_file = "config/patches.yml"

# -----------------------------------------------------------------------------
# Action LIST
# -----------------------------------------------------------------------------

def action_list():

    # Open data module
    if not os.path.isfile(mapping_file):
        print("ERROR: map file does not exist, please run import first")
        sys.exit(1)
    with open(mapping_file) as f:
        data = yaml.load(f, Loader=yaml.loader.SafeLoader)

    print()
    table = Table()
    for column in ['Module', "Type", "Description"]:
        table.add_column(column)
    for module in data.keys():
        table.add_row(*[module.upper(), data[module]['type'], data[module]['description']], style='bright_green')
    console = Console()
    console.print(table)
    print()

# -----------------------------------------------------------------------------
# Action LIST
# -----------------------------------------------------------------------------

def action_info():

    # Open data module
    if not os.path.isfile(mapping_file):
        print("ERROR: map file does not exist, please run import first")
        sys.exit(1)
    with open(mapping_file) as f:
        data = yaml.load(f, Loader=yaml.loader.SafeLoader)

    module = sys.argv[2].lower()
    if not module in data.keys():
        print(f"ERROR: module {module.upper()} does not exist")
        sys.exit(1)
    
    if 'slots' in data[module]:
        if not os.path.isfile(slots_file):
            print("ERROR: slots file does not exist, please checkout project again")
            sys.exit(1)
        with open(slots_file) as f:
            slot_def = yaml.load(f, Loader=yaml.loader.SafeLoader)

    print()
    
    print(f"Module: {module.upper()}")
    print(f"Type: {data[module]['type']}")
    print(f"Description: {data[module]['description']}")
    print(f"Documentation: {data[module]['documentation']}")
    
    if 'i2c_address' in data[module]:
        print(f"I2C Address: {data[module]['i2c_address']}")
    
    if 'mapping' in data[module]:
        print(f"Mapping:")
        table = Table()
        for column in ["PIN", "Function"]:
            table.add_column(column)
        for row in [[str(k), v] for k, v in data[module]['mapping'].items()]:
            table.add_row(*row, style='bright_green')
        console = Console()
        console.print(table)
    
    if 'slots' in data[module]:

        print(f"Slots:")
        table = Table()
        columns = list(data[module]['slots'].keys())
        columns.insert(0, "ID")
        for column in columns:
            table.add_column(column)
        
        slots = {}
        for slot in data[module]['slots'].keys():
            slots[slot] = merge(slot_def[slot], data[module]['slots'][slot] or {})
        
        for i in range(1, 41):
            row = [str(i)]
            for slot in slots:
                if i in slots[slot]:
                    row.append(slots[slot][i])
                else:
                    row.append("")
            table.add_row(*row, style='bright_green')

        console = Console()
        console.print(table)

    if 'notes' in data[module]:
        print(f"Notes:")
        for note in data[module]['notes']:
            print(f"- {note}")
    
    print()

# -----------------------------------------------------------------------------
# Action IMPORT
# -----------------------------------------------------------------------------

def import_sheet(data, sheet):

    # Get code
    module_code = sheet.title.lower()
    if not module_code in data:
        data[module_code] = {}

    # Get type
    module_type = "WisBase"
    if sheet['C26'].value == 'BOOT0':
        module_type = "WisCore"
    elif sheet['B43'].value == 40:
        module_type = "WisIO"
    elif sheet['D2'].value == 'SLOT A':
        module_type = "WisSensor"
    data[module_code]['type'] = module_type

    # Get description
    pin_column = 2
    function_column = 4
    if module_type == "WisBase":
        module_description = module_code
    if module_type == "WisCore":
        module_description = module_code
        function_column = 3
    if module_type == "WisIO":
        module_description = sheet['C45'].value
    if module_type == "WisSensor":
        module_description = sheet['C29'].value
    data[module_code]['description'] = module_description.strip()

    # Get documentation
    module_docs = "https://docs.rakwireless.com/Product-Categories/WisBlock/" + sheet.title.upper()
    data[module_code]['documentation'] = module_docs

    # Get mapping
    row = 4 
    mapping = {}   
    while True:
        pin = str(sheet.cell(row = row, column = pin_column).value)
        if not pin.isnumeric():
            break
        function = sheet.cell(row = row, column = function_column).value
        if function != "NC":
            mapping[int(pin)] = function
        row = row + 1
    data[module_code]['mapping'] = mapping

    # I2C Address
    address = str(sheet.cell(row = row+2, column = 3).value)
    if address.startswith("I2C Address:"):
        data[module_code]['i2c_address'] = address[13:].strip()

           
def action_import():

    url = "https://downloads.rakwireless.com/LoRa/WisBlock/Pin-Mapper/WisBlock-IO-Pin-Mapper.xlsx"
    filename = "WisBlock-IO-Pin-Mapper.xlsx"
    if not os.path.isfile(filename):
        response = requests.get(url)
        if not response.ok:
            sys.exit(1)
        with open(filename, mode="wb") as file:
            file.write(response.content)

    # Open Pin Mapper spreadsheet
    wb = openpyxl.load_workbook(filename)

    # Output data
    data = {}

    # Walk sheets
    skip_sheets = ["Pin Mapper", "model list", "NA IO", "NA_SENS", "RAK18003"]
    for sheet_name in wb.sheetnames:
        if sheet_name not in skip_sheets:
            sheet = wb[sheet_name]
            import_sheet(data, sheet)

    # Apply patches
    if os.path.isfile(patches_file):
        with open(patches_file) as f:
            patches = yaml.load(f, Loader=yaml.loader.SafeLoader)
        data = merge(data, patches)

    # Save
    with open("config/mapping.yml", "w") as w:
        yaml.dump(data, w)

    # Delete file
    if os.path.isfile(filename):
        os.remove(filename) 

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

ACTIONS = { 
    "list" : { 'arguments': [], 'method': action_list },
    "info" : { 'arguments': ['<module>'], 'method': action_info },
    "import" : { 'arguments': [], 'method': action_import },
}

def usage():
    for action in ACTIONS:
        print(f"> wismap.py {action} {' '.join(ACTIONS[action]['arguments'])}")

# Check arguments
if len(sys.argv) < 2:
    print(f"ERROR: unspecified action")
    usage()
    sys.exit(1)
action = sys.argv[1]
if action not in ACTIONS.keys():
    print(f"ERROR: unknown action '{action}'")
    usage()
    sys.exit(1)
arguments = len(ACTIONS[action]['arguments']) + 2
if len(sys.argv) < arguments:
    print(f"ERROR: action requires extra arguments")
    usage()
    sys.exit(1)

# Execute
ACTIONS[action]['method']()
