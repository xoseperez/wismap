#!/bin/python3

import os
import sys
import yaml
from rich.console import Console
from rich.table import Table
from mergedeep import merge
import openpyxl
import requests
import inquirer

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

definitions_file = "config/definitions.yml"
config_file = "config/config.yml"
definitions = {}
config = {}

# -----------------------------------------------------------------------------
# Action LIST
# -----------------------------------------------------------------------------

def action_list():

    print()
    table = Table()
    for column in ['Module', "Type", "Description"]:
        table.add_column(column)
    for module in definitions.keys():
        table.add_row(*[module.upper(), definitions[module]['type'], definitions[module]['description']], style='bright_green')
    console = Console()
    console.print(table)
    print()

# -----------------------------------------------------------------------------
# Action INFO
# -----------------------------------------------------------------------------

def action_info():

    # Get module
    questions = [inquirer.List('module', message="Select module", choices=[(definitions[module]['description'], module) for module in definitions.keys()], carousel=True,)]
    answer = inquirer.prompt(questions)
    module = answer['module']

    # Notes
    notes = definitions[module].get('notes', [])

    print(f"Module: {module.upper()}")
    print(f"Type: {definitions[module]['type']}")
    print(f"Description: {definitions[module]['description']}")
    print(f"Documentation: {definitions[module]['documentation']}")

    if definitions[module]['type'] == 'WisSensor':
        print(f"Long: {definitions[module].get('double', False)}")
    
    if 'i2c_address' in definitions[module]:
        print(f"I2C Address: {definitions[module]['i2c_address']}")
    
    if 'mapping' in definitions[module]:
        print(f"Mapping:")
        table = Table()
        for column in ["PIN", "Function"]:
            table.add_column(column)
        for row in [[str(k), v] for k, v in definitions[module]['mapping'].items()]:
            table.add_row(*row, style='bright_green')
        console = Console()
        console.print(table)
    
    if 'slots' in definitions[module]:

        print(f"Slots:")
        table = Table()
        table.add_column("ID")
        for slot in definitions[module]['slots'].keys():
            double = (definitions[module]['slots'][slot] or {}).get('_double', False)
            double_blocks = (definitions[module]['slots'][slot] or {}).get('_double_blocks', None)
            if double_blocks:
                notes.append(f"Accepts long sensor on {slot} slot but blocking {double_blocks} slot")
            elif double:
                notes.append(f"Accepts long sensor on {slot} slot")
            table.add_column(slot)
        
        slots = {}
        slot_def = config.get('slots', {})
        for slot in definitions[module]['slots'].keys():
            slots[slot] = merge(slot_def[slot], definitions[module]['slots'][slot] or {})

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

    if len(notes):
        print(f"Notes:")
        for note in notes:
            print(f"- {note}")
    
    print()

# -----------------------------------------------------------------------------
# Action COMBINE
# -----------------------------------------------------------------------------

def combine_pins(slot, mapping):
    output = {}
    for k, v in slot.items():
        output[v] = mapping.get(k, "")
    return output

def count_non_empty(elements):
    return sum(1 for element in elements if element != '')

def count_unique(elements):
    unique = []
    for element in elements:
        if element != '':
            if element not in unique:
                unique.append(element)
    return len(unique)

def function_mapping(slot_module, slots):

    # Populate slot mapping
    slot_mapping = {}
    for slot in slot_module:
        slot_mapping[slot] = {}
        module = slot_module[slot]
        if module and module != 'BLOCKED' and module != 'EMPTY':
            if (definitions[module]['type'] == 'WisCore') or (definitions[module]['type'] == 'WisBase'):
                slot_mapping[slot] = definitions[module].get('mapping', {})
            elif (definitions[module]['type'] == 'WisIO') or (definitions[module]['type'] == 'WisSensor'):
                slot_mapping[slot] = combine_pins(slots[slot], definitions[module].get('mapping', {}))
            slot_mapping[slot]['I2C_ADDR'] = definitions[module].get('i2c_address', "")

    # Function mapping
    functions = [
        'I2C_ADDR', '3V3', '3V3_S', 'AIN0', 'AIN1', 'BOOT0', 'GND', 'I2C1_SCL', 'I2C1_SDA', 'I2C2_SCL', 'I2C2_SDA', 
        'IO1', 'IO2', 'IO3', 'IO4', 'IO5', 'IO6', 'IO7', 'LED1', 'LED2', 'LED3', 'RESET', 'RXD0', 'RXD1', 
        'SPI_CLK', 'SPI_CS', 'SPI_MISO', 'SPI_MOSI', 'SW1', 'TXD0', 'TXD1', 'USB+', 
        'USB-', 'VBAT', 'VBAT_NRF', 'VBAT_SX', 'VBUS', 'VDD', 'VDD_NRF', 'VIN'
    ]
    function_slot = {}
    for function in functions:
        row = [function]
        for slot in slot_mapping:
            row.append(slot_mapping[slot].get(function, ""))
        function_slot[function] = row

    return function_slot

def detect_conflicts(function_slot):

    functions = []
    notes = []    

    for function, values in function_slot.items():
        non_empty = count_non_empty(values[3:])
        unique = count_unique(values[3:])
        if function == 'I2C_ADDR':
            if non_empty > unique:
                notes.append('Possible conflict with I2C addresses')
                functions.append(function)
        if function == 'AIN0':
            if non_empty > 0:
                notes.append('Possible conflict with ADC_VBAT if using AIN0')
                functions.append(function)
        if function in ('IO1', 'IO2', 'IO3', 'IO4', 'IO5', 'IO6', 'IO7', 'AIN0', 'AIN1', 'RXD0', 'TXD0', 'RXD1', 'TXD1'):
            if non_empty > 1:
                notes.append(f"Possible conflict with {function}")
                functions.append(function)
        if function == 'IO2':
            if non_empty > 0:
                if count_non_empty(function_slot['3V3_S'][3:]) > 0:
                    notes.append(f"Possible conflict with 3V3_S enable signal if using IO2")
                    functions.append(function)
                    functions.append('3V3_S')

    return [functions, notes]

def action_combine():

    # -------------------------------------------------------------------------
    # Gather info
    # -------------------------------------------------------------------------

    slot_module={}

    # Select base module
    choices = [(definitions[module]['description'], module) for module in definitions.keys() if definitions[module]['type'] == 'WisBase']
    questions = [inquirer.List('output', message="Select Base Board", choices=choices, carousel=True)]
    slot_module['BASE'] = inquirer.prompt(questions)['output']

    # Get slot definitions
    slot_def = config.get('slots', {})
    slots = {}
    for slot in definitions[slot_module['BASE']]['slots'].keys():
        slots[slot] = merge(slot_def[slot], definitions[slot_module['BASE']]['slots'][slot] or {})

    # Walk the different slots
    blocked = []
    for slot in slots:
        
        if slot in blocked:
            print(f"{slot} is blocked by another sensor\n")
            slot_module[slot] = 'BLOCKED'
            continue

        if slot.startswith('CORE'):
            choices = [(definitions[module]['description'], module) for module in definitions.keys() if definitions[module]['type'] == 'WisCore']
            questions = [inquirer.List('output', message="Select Core Module", choices=choices, carousel=True)]
            slot_module[slot] = inquirer.prompt(questions)['output']

        if slot.startswith('SENSOR'):
            is_double = slots[slot].get('double', False)
            choices = [(definitions[module]['description'], module) for module in definitions.keys() if (definitions[module]['type'] == 'WisSensor') and (is_double or not definitions[module].get('double', False))]
            choices.insert(0, ("Empty", "EMPTY"))
            questions = [inquirer.List('output', message=f"Select Sensor Module in slot {slot}", choices=choices, carousel=True)]
            slot_module[slot] = inquirer.prompt(questions)['output']
            if slot_module[slot] != 'EMPTY':
                if definitions[slot_module[slot]].get('double', False):
                    blocks = slots[slot].get('double_blocks', None)
                    if blocks:
                        blocked.append(blocks)


        if slot.startswith('IO'):
            choices = [(definitions[module]['description'], module) for module in definitions.keys() if definitions[module]['type'] == 'WisIO']
            choices.insert(0, ("Empty", "EMPTY"))
            questions = [inquirer.List('output', message=f"Select IO Module in slot {slot}", choices=choices, carousel=True)]
            slot_module[slot] = inquirer.prompt(questions)['output']

    # -------------------------------------------------------------------------
    # Build mapping
    # -------------------------------------------------------------------------
    
    function_slot = function_mapping(slot_module, slots)
    (conflict_functions, conflict_notes) = detect_conflicts(function_slot)

    # -------------------------------------------------------------------------
    # View
    # -------------------------------------------------------------------------

    # Header
    slot_names = {
        'BASE': 'Base board',
        'CORE': 'Core module',
        'SENSOR_A': 'SENSOR_A slot',
        'SENSOR_B': 'SENSOR_B slot',
        'SENSOR_C': 'SENSOR_C slot',
        'SENSOR_D': 'SENSOR_D slot',
        'SENSOR_E': 'SENSOR_E slot',
        'SENSOR_F': 'SENSOR_F slot',
        'IO_A': 'IO_A slot',
        'IO_B': 'IO_B slot',
    }

    columns = ["Function\n"]
    for k, v in slot_module.items():
        if v:
            columns.append(f"{slot_names[k]}\n({v.upper()})")
        else:
            columns.append(f"{slot_names[k]}\n")


    # Get core board mapping
    print()
    table = Table()
    for column in columns:
        table.add_column(column)
    for function, row in function_slot.items():
        style = "bright_yellow" if function in conflict_functions else "bright_green"
        table.add_row(*row, style=style)
    console = Console()
    console.print(table)

    if len(conflict_notes):
        print(f"Potential conflicts:")
        for conflict in conflict_notes:
            print(f"- {conflict}")

    print(f"Documentation:")
    for k, v in slot_module.items():
        if v in definitions:
            print(f"- {definitions[v]['description']}: {definitions[v]['documentation']}")

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
    key_column = 2
    value_column = 4
    rows = 40
    if module_type == "WisBase":
        module_description = module_code
    if module_type == "WisCore":
        module_description = module_code
        key_column = 3
    if module_type == "WisIO":
        module_description = sheet['C45'].value
    if module_type == "WisSensor":
        module_description = sheet['C29'].value
        rows = 24
    data[module_code]['description'] = module_description.strip(' "\'\t\r\n')

    # Get documentation
    module_docs = "https://docs.rakwireless.com/Product-Categories/WisBlock/" + sheet.title.upper()
    data[module_code]['documentation'] = module_docs

    # Get mapping
    mapping = {}   
    for row in range(4, rows+4):
        pin = str(sheet.cell(row = row, column = key_column).value)
        if pin == "" or pin == "Description":
            break
        function = sheet.cell(row = row, column = value_column).value
        if pin.isnumeric():
            pin = int(pin)
        if function != "NC":
            mapping[pin] = function
    data[module_code]['mapping'] = mapping

    # I2C Address
    address = str(sheet.cell(row = row+3, column = 3).value)
    if address.startswith("I2C Address:"):
        data[module_code]['i2c_address'] = address[13:].strip(' "\'\t\r\n')

           
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
    data = merge(data, config.get('patches', {}))

    # Save
    with open(definitions_file, "w") as w:
        yaml.dump(data, w)

    # Delete file
    if os.path.isfile(filename):
        os.remove(filename) 

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

ACTIONS = { 
    "list" : { 'arguments': [], 'method': action_list },
    "info" : { 'arguments': [], 'method': action_info },
    "combine" : { 'arguments': [], 'method': action_combine },
    "import" : { 'arguments': [], 'method': action_import },
}

def usage():
    for action in ACTIONS:
        print(f"> wismap.py {action} {' '.join(ACTIONS[action]['arguments'])}")

# Load definitions data
if os.path.isfile(definitions_file):
    with open(definitions_file) as f:
        definitions = yaml.load(f, Loader=yaml.loader.SafeLoader)

# Load configuration data
if os.path.isfile(config_file):
    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.loader.SafeLoader)

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
