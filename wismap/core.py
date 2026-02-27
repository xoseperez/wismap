"""
WisMAP core business logic — pure data in, data out.
No rich, no inquirer, no print. Suitable for CLI and API consumption.
"""

import os
import re
import copy

import yaml
from mergedeep import merge

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

PINS_PER_TYPE = {
    'Accessories': 0,
    'WisBase': 0,
    'WisCore': 40,
    'WisIO': 40,
    'WisModule': 0,
    'WisPower': 40,
    'WisSensor': 24,
}

SLOT_NAMES = {
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
    'POWER': 'Power slot',
}

SLOT_ORDER = ['CORE', 'POWER', 'IO_A', 'IO_B',
              'SENSOR_A', 'SENSOR_B', 'SENSOR_C', 'SENSOR_D',
              'SENSOR_E', 'SENSOR_F']

# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

def load_data(data_folder="./data"):
    definitions_file = os.path.join(data_folder, "definitions.yml")
    config_file = os.path.join(data_folder, "config.yml")
    rules_file = os.path.join(data_folder, "rules.yml")

    definitions = {}
    if os.path.isfile(definitions_file):
        with open(definitions_file) as f:
            definitions = yaml.load(f, Loader=yaml.loader.SafeLoader)
    definitions = dict(sorted(definitions.items(), key=lambda e: int(re.findall(r"\d+", e[0])[0])))

    config = {}
    if os.path.isfile(config_file):
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.loader.SafeLoader)

    rules = []
    if os.path.isfile(rules_file):
        with open(rules_file) as f:
            rules_data = yaml.load(f, Loader=yaml.loader.SafeLoader)
            rules = rules_data.get('rules', []) if rules_data else []

    return definitions, config, rules

# -----------------------------------------------------------------------------
# Action: list
# -----------------------------------------------------------------------------

def list_modules(definitions, type_filter=None):
    result = []
    for module_id, module_data in definitions.items():
        if type_filter and module_data['type'] != type_filter:
            continue
        result.append({
            'id': module_id,
            'type': module_data['type'],
            'description': module_data['description'],
        })
    return result

# -----------------------------------------------------------------------------
# Action: info
# -----------------------------------------------------------------------------

def get_module_info(definitions, config, module_id, show_nc=False):
    module_id = module_id.lower()
    if module_id not in definitions:
        return None

    mod = definitions[module_id]
    notes = list(mod.get('notes', []))

    info = {
        'id': module_id,
        'type': mod['type'],
        'description': mod['description'],
        'documentation': mod.get('documentation', ''),
        'images': mod.get('images') or [],
        'schematics': mod.get('schematics') or [],
        'double': mod.get('double', False) if mod['type'] == 'WisSensor' else None,
        'i2c_address': mod.get('i2c_address', None),
        'mapping': None,
        'slots_table': None,
        'notes': None,
    }

    # Mapping table
    if 'mapping' in mod:
        pins = PINS_PER_TYPE.get(mod['type'], 0)
        mapping_rows = []
        if pins == 0:
            for k, v in mod['mapping'].items():
                if v:
                    mapping_rows.append({'pin': str(k), 'function': v})
        else:
            for index in range(pins):
                name = mod['mapping'].get(index + 1, 'NC')
                if name != 'NC' or show_nc:
                    mapping_rows.append({'pin': str(index + 1), 'function': name})
        info['mapping'] = mapping_rows

    # Slots table (for WisBase modules)
    if 'slots' in mod:
        slot_def = config.get('slots', {})
        slot_columns = list(mod['slots'].keys())

        for slot_name in slot_columns:
            slot_data = mod['slots'][slot_name] or {}
            double = slot_data.get('double', False)
            double_blocks = slot_data.get('double_blocks', None)
            if double_blocks:
                notes.append(f"Accepts long sensor on {slot_name} slot but blocking {double_blocks} slot")
            elif double:
                notes.append(f"Accepts long sensor on {slot_name} slot")

        # Resolve slots (deepcopy to avoid mutating config)
        resolved_slots = {}
        for slot_name in slot_columns:
            resolved_slots[slot_name] = merge(
                copy.deepcopy(slot_def[slot_name]),
                mod['slots'][slot_name] or {}
            )

        rows = []
        for i in range(1, 41):
            row = {'pin': str(i)}
            for slot_name in slot_columns:
                if i in resolved_slots[slot_name]:
                    val = resolved_slots[slot_name][i]
                    if val != "NC" or show_nc:
                        row[slot_name] = val
                    else:
                        row[slot_name] = ""
                else:
                    row[slot_name] = ""
            rows.append(row)

        info['slots_table'] = {
            'columns': slot_columns,
            'rows': rows,
        }

    info['notes'] = notes
    return info

# -----------------------------------------------------------------------------
# Action: combine — helpers
# -----------------------------------------------------------------------------

def _combine_pins(slot, mapping):
    output = {}
    for k, v in slot.items():
        if (v not in output) or (output[v] == ''):
            output[v] = mapping.get(k, "")
    return output


def _count_non_empty(elements):
    return sum(1 for e in elements if e != '' and '(NC)' not in e)


def _count_unique(elements):
    unique = []
    for e in elements:
        if e != '' and e not in unique:
            unique.append(e)
    return len(unique)


def _function_mapping(definitions, config, mapping_name, slot_module, slots):
    slot_mapping = {}
    for slot in slot_module:
        slot_mapping[slot] = {}
        module = slot_module[slot]
        if module and module != 'BLOCKED' and module != 'EMPTY':
            if definitions[module]['type'] in ['WisBase']:
                slot_mapping[slot] = definitions[module].get('naming', {})
            elif definitions[module]['type'] in ['WisCore', 'WisIO', 'WisSensor', 'WisPower']:
                slot_mapping[slot] = _combine_pins(slots[slot], definitions[module].get('mapping', {}))
            slot_mapping[slot]['I2C_ADDR'] = definitions[module].get('i2c_address', "")

    functions = config.get('functions', {}).get(mapping_name, [])
    function_slot = {}
    for function in functions:
        row = [function]
        for slot in slot_mapping:
            row.append(slot_mapping[slot].get(function, ""))
        function_slot[function] = row

    return function_slot


def _check_condition(condition, values):
    non_empty = _count_non_empty(values)
    if condition == 'duplicates':
        return non_empty > _count_unique(values)
    elif condition == 'any_used':
        return non_empty > 0
    elif condition == 'multiple_used':
        return non_empty > 1
    return False


def _detect_conflicts(definitions, slot_module, function_slot, rules):
    functions = []
    notes = []

    mapping_name = definitions[slot_module['BASE']].get('functions', 'default')
    base_id = slot_module['BASE']

    skip_columns = 3
    if mapping_name == 'raspberry':
        skip_columns -= 1
    if 'POWER' in slot_module:
        skip_columns += 1

    for rule in rules:
        exclude = rule.get('exclude', [])

        # If the base board is excluded, skip the rule entirely
        if base_id in exclude:
            continue

        # Determine which functions this rule applies to
        match = rule['match']
        if 'function' in match:
            target_functions = [match['function']]
        elif 'function_prefix' in match:
            target_functions = [
                f for f in function_slot
                if any(f.startswith(p) for p in match['function_prefix'])
            ]
        else:
            continue

        condition = match['condition']

        for func in target_functions:
            if func not in function_slot:
                continue

            values = function_slot[func][skip_columns:]

            # Filter out values from excluded slot modules
            if exclude:
                slot_names = list(slot_module.keys())[skip_columns:]
                values = [
                    v for v, slot in zip(values, slot_names)
                    if slot_module.get(slot) not in exclude
                ]

            if not _check_condition(condition, values):
                continue

            # Check also_requires (cross-reference)
            if 'also_requires' in match:
                ref = match['also_requires']
                ref_func = ref['function']
                if ref_func not in function_slot:
                    continue
                ref_values = function_slot[ref_func][skip_columns:]
                if not _check_condition(ref['condition'], ref_values):
                    continue

            # Rule fires
            description = rule['description'].format(function=func)
            notes.append(description)

            highlights = rule.get('highlights', [func])
            functions.extend(h for h in highlights if h not in functions)

    return functions, notes

# -----------------------------------------------------------------------------
# Action: combine — slot introspection
# -----------------------------------------------------------------------------

def get_base_slots(definitions, config, base_id):
    base_id = base_id.lower()
    if base_id not in definitions or definitions[base_id]['type'] != 'WisBase':
        return None

    base = definitions[base_id]
    slot_def = config.get('slots', {})
    result = {}

    sorted_slots = sorted(base['slots'].items(),
                          key=lambda x: SLOT_ORDER.index(x[0]) if x[0] in SLOT_ORDER else len(SLOT_ORDER))

    for slot_name, slot_overrides in sorted_slots:
        slot_overrides = slot_overrides or {}
        resolved = merge(copy.deepcopy(slot_def[slot_name]), copy.deepcopy(slot_overrides))
        double = slot_overrides.get('double', False)
        double_blocks = slot_overrides.get('double_blocks', None)

        # Determine accepted types
        if slot_name.startswith('CORE'):
            accepts_types = ['WisCore']
        elif slot_name.startswith('SENSOR'):
            accepts_types = ['WisSensor']
        elif slot_name.startswith('IO'):
            accepts_types = ['WisIO']
        elif slot_name.startswith('POWER'):
            accepts_types = ['WisPower']
        else:
            accepts_types = []

        # Build eligible modules
        eligible = []
        for mod_id, mod_data in definitions.items():
            if mod_data['type'] not in accepts_types:
                continue
            # For non-double slots, skip double-size sensor modules
            if not double and mod_data.get('double', False):
                continue
            eligible.append({
                'id': mod_id,
                'type': mod_data['type'],
                'description': mod_data['description'],
            })

        result[slot_name] = {
            'double': double,
            'double_blocks': double_blocks,
            'eligible_modules': eligible,
        }

    return result

# -----------------------------------------------------------------------------
# Action: combine — main
# -----------------------------------------------------------------------------

def combine(definitions, config, base_id, slot_assignments, rules=None):
    """
    Run the combine analysis.

    Args:
        definitions: module definitions dict
        config: config dict
        base_id: base board module id (e.g. "rak19007")
        slot_assignments: dict mapping slot name to module id or "EMPTY"/"BLOCKED"
            e.g. {"CORE": "rak4631", "SENSOR_A": "rak1901", "SENSOR_B": "EMPTY", ...}

    Returns:
        dict with slot_module, columns, function_table, conflicts, documentation, notes
    """
    base_id = base_id.lower()
    slot_module = {'BASE': base_id}

    # Resolve slot pin definitions (deepcopy to avoid mutation)
    slot_def = config.get('slots', {})
    slots = {}
    sorted_slot_names = sorted(definitions[base_id]['slots'].keys(),
                               key=lambda x: SLOT_ORDER.index(x) if x in SLOT_ORDER else len(SLOT_ORDER))
    for slot_name in sorted_slot_names:
        slots[slot_name] = merge(
            copy.deepcopy(slot_def[slot_name]),
            definitions[base_id]['slots'][slot_name] or {}
        )

    # Fill in slot_module from assignments, defaulting to EMPTY
    for slot_name in slots:
        assigned = slot_assignments.get(slot_name, 'EMPTY')
        if assigned and assigned.lower() != 'empty' and assigned.lower() != 'blocked':
            slot_module[slot_name] = assigned.lower()
        else:
            slot_module[slot_name] = 'EMPTY'

    # Build function mapping
    mapping_name = definitions[base_id].get('functions', 'default')
    function_slot = _function_mapping(definitions, config, mapping_name, slot_module, slots)

    # Detect conflicts
    conflict_functions, conflict_notes = _detect_conflicts(definitions, slot_module, function_slot, rules or [])

    # Gather notes & documentation
    documentation = []
    notes = []
    for k, v in slot_module.items():
        if v in definitions:
            documentation.append(f"{definitions[v]['description']}: {definitions[v]['documentation']}")
            for note in definitions[v].get('notes', []):
                notes.append(f"{v.upper()}: {note}")

    # Build columns
    columns = ["Function"]
    for k in slot_module:
        columns.append(SLOT_NAMES.get(k, k))

    return {
        'slot_module': slot_module,
        'columns': columns,
        'function_table': function_slot,
        'conflicts': {
            'functions': conflict_functions,
            'notes': conflict_notes,
        },
        'documentation': documentation,
        'notes': notes,
    }
