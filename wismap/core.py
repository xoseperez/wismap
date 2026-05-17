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
# Helpers
# -----------------------------------------------------------------------------

def _normalize_i2c_address(value):
    """Normalize i2c_address to a list or None."""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value]

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


def load_data_v1(data_folder="./data"):
    """Same as load_data but also returns the precomputed compatible-slots index."""
    definitions, config, rules = load_data(data_folder)
    compatible_slots_index = _build_compatible_slots_index(definitions)
    return definitions, config, rules, compatible_slots_index

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
            'tags': module_data.get('tags', []),
        })
    return result

# -----------------------------------------------------------------------------
# Action: info
# -----------------------------------------------------------------------------

def get_module_info(definitions, config, module_id, show_nc=False):
    module_id = module_id.strip().lower()
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
        'i2c_address': _normalize_i2c_address(mod.get('i2c_address', None)),
        'tags': mod.get('tags', []),
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
            addr = _normalize_i2c_address(definitions[module].get('i2c_address', None))
            slot_mapping[slot]['I2C_ADDR'] = ', '.join(addr) if addr else ""

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
        # Expand comma-separated values (e.g. I2C addresses) and check
        # for individual collisions across slots
        all_items = []
        for v in values:
            if v == '' or '(NC)' in v:
                continue
            all_items.extend(item.strip() for item in v.split(','))
        unique_items = set(all_items)
        return len(all_items) > len(unique_items)
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
    base_id = base_id.strip().lower()
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
    base_id = base_id.strip().lower()
    if base_id not in definitions:
        return None
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
        if assigned and assigned.strip().lower() not in ('empty', 'blocked'):
            canonical = assigned.strip().lower()
            if canonical not in definitions:
                slot_module[slot_name] = 'EMPTY'
            else:
                slot_module[slot_name] = canonical
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


# =============================================================================
# v1 API helpers
# =============================================================================

# Module types that map to specific slot prefixes (used for compatible_slots
# index computation — includes Cores since a Core "fits" in the CORE slot).
_TYPE_TO_SLOT_PREFIX = {
    'WisCore': 'CORE',
    'WisIO': 'IO_',
    'WisSensor': 'SENSOR_',
    'WisPower': 'POWER',
}

# Module types exposed via /api/v1/modules. Cores have their own endpoint;
# Bases have their own; Accessories are passive cables. WisModule covers
# externally-connected modules (OLED, joysticks, keypads) that don't slot in
# the standard way but are still part of the catalog.
_MODULE_LISTING_TYPES = {'WisIO', 'WisSensor', 'WisPower', 'WisModule'}

# Roles ignored when deriving signals / interfaces (power, ground, USB, NC, etc.).
_STRUCTURAL_ROLES = {
    'GND', '3V3', '3V3_S', '5V', 'VDD', 'VDD_NRF', 'VBAT', 'VBAT_NRF', 'VBAT_SX',
    'VIN', 'VBUS', 'USB+', 'USB-', 'USB_P', 'USB_N',
    'NC', 'RESET', 'BOOT0', 'SW1',
    'LED1', 'LED2', 'LED3',
    'CHRG', 'EN',
}

# Module-side role -> signal alias (used in module.signal_map).
_MODULE_ROLE_TO_SIGNAL = {
    'I2C_SDA': 'SDA',
    'I2C_SCL': 'SCL',
    'I2C1_SDA': 'SDA',
    'I2C1_SCL': 'SCL',
    'I2C2_SDA': 'SDA2',
    'I2C2_SCL': 'SCL2',
    'SPI_CS': 'CS',
    'SPI_CLK': 'SCK',
    'SPI_SCK': 'SCK',
    'SPI_NSS': 'CS',
    'SPI_MISO': 'MISO',
    'SPI_MOSI': 'MOSI',
    'UART_TX': 'TX',
    'UART_RX': 'RX',
    'UART0_TX': 'TX',
    'UART0_RX': 'RX',
    'UART1_TX': 'TX1',
    'UART1_RX': 'RX1',
}


def _to_display_id(canonical_id):
    """rak4631 -> RAK4631; rak5005-o -> RAK5005-O."""
    if canonical_id is None:
        return None
    return canonical_id.upper()


def _to_canonical_id(maybe_display):
    """Any-case input -> canonical lowercase."""
    if maybe_display is None:
        return None
    return maybe_display.strip().lower()


def _clean_role(role):
    """Strip `(NC)` markers and whitespace from a role string."""
    if not isinstance(role, str):
        return None
    r = role.strip()
    if not r or r == 'NC' or '(NC)' in r:
        return None
    return r


def _interesting_role(role):
    """True if the role is a signal a generator would care about."""
    r = _clean_role(role)
    if r is None:
        return False
    return r not in _STRUCTURAL_ROLES


def _role_to_bus_family(role):
    """Map role to bus family (I2C, SPI, UART, GPIO, analog, I2S, PDM) or None."""
    r = _clean_role(role)
    if r is None:
        return None
    R = r.upper()
    if 'I2C' in R:
        return 'I2C'
    if R.startswith('SPI'):
        return 'SPI'
    if R.startswith('UART') or R.startswith('TXD') or R.startswith('RXD'):
        return 'UART'
    if R.startswith('AIN') or R.startswith('ADC') or R.startswith('ANALOG'):
        return 'analog'
    if R.startswith('I2S'):
        return 'I2S'
    if R.startswith('PDM'):
        return 'PDM'
    if R.startswith('IO') or R.startswith('GPIO'):
        return 'GPIO'
    return None


def _role_to_bus_instance(role):
    """Map role to specific bus instance (I2C1, UART0, SPI1, GPIO, analog) or None."""
    r = _clean_role(role)
    if r is None:
        return None
    R = r.upper()
    m = re.match(r'^I2C(\d+)_', R)
    if m:
        return f'I2C{m.group(1)}'
    if R in ('I2C_SDA', 'I2C_SCL'):
        return 'I2C1'
    m = re.match(r'^UART(\d+)_', R)
    if m:
        return f'UART{m.group(1)}'
    m = re.match(r'^[TR]XD(\d+)$', R)
    if m:
        return f'UART{m.group(1)}'
    if R.startswith('SPI'):
        return 'SPI1'
    if R.startswith('IO') or R.startswith('GPIO'):
        return 'GPIO'
    if R.startswith('AIN') or R.startswith('ADC'):
        return 'analog'
    return None


# ----- Core derivations -----

def _derive_core_peripherals(core_def, core_slot_def):
    """Bus instances the Core exposes via the CORE slot, given its pin mapping."""
    mapping = core_def.get('mapping') or {}
    peripherals = set()
    for pin_num, role in core_slot_def.items():
        if not isinstance(pin_num, int):
            continue
        mcu = mapping.get(pin_num)
        if mcu is None or (isinstance(mcu, str) and ('(NC)' in mcu or mcu.strip() == '')):
            continue
        bus = _role_to_bus_instance(role)
        if bus and bus != 'GPIO':
            peripherals.add(bus)
    peripherals.add('GPIO')
    return sorted(peripherals)


def _derive_compatible_bases(definitions):
    """Bases that expose a CORE slot."""
    return sorted(
        _to_display_id(bid)
        for bid, b in definitions.items()
        if b.get('type') == 'WisBase' and 'CORE' in (b.get('slots') or {})
    )


# ----- Module derivations -----

def _module_mapping_values(module_def):
    """Yield non-empty role strings from a module's mapping."""
    m = module_def.get('mapping') or {}
    for v in m.values():
        cleaned = _clean_role(v)
        if cleaned is not None:
            yield cleaned


def _derive_module_interfaces(module_def):
    """Bus families this module uses (e.g. ['I2C', 'SPI'])."""
    families = set()
    for role in _module_mapping_values(module_def):
        fam = _role_to_bus_family(role)
        if fam:
            families.add(fam)
    ordered = ['I2C', 'SPI', 'UART', 'analog', 'I2S', 'PDM', 'GPIO']
    return [f for f in ordered if f in families]


def _derive_module_signal_map(module_def):
    """Map module signal aliases (SDA, SCL, CS, ...) to {role: <role>}."""
    seen = {}
    for role in _module_mapping_values(module_def):
        alias = _MODULE_ROLE_TO_SIGNAL.get(role)
        if alias and alias not in seen:
            seen[alias] = {'role': role}
    return seen


def _derive_module_core_requirements(module_def):
    """Numbered peripherals the module needs (WisBlock-default bus per family)."""
    fams = _derive_module_interfaces(module_def)
    mapped = []
    for f in fams:
        if f == 'I2C':
            mapped.append('I2C1')
        elif f == 'SPI':
            mapped.append('SPI1')
        elif f == 'UART':
            # Module doesn't know which UART; expose the family.
            mapped.append('UART')
        elif f in ('analog', 'I2S', 'PDM', 'GPIO'):
            mapped.append(f)
    return {'peripherals': mapped}


def _derive_module_power(module_def):
    """Detect 3V3_S rail / IO2 enable from the module's pin mapping."""
    roles = [str(v) for v in _module_mapping_values(module_def)]
    uses_3v3_s = any('3V3_S' in r for r in roles)
    return {
        'rail': '3V3_S' if uses_3v3_s else '3V3',
        'control_pin': 'IO2' if uses_3v3_s else None,
        'warmup_ms': None,
        'current_typical_uA': None,
        'current_peak_mA': None,
    }


# ----- Base derivations -----

def _resolved_slot_pin_map(base_def, slot_def):
    """Resolve each slot's pin map (config + base overrides). Returns {slot: {pin: role}}."""
    resolved = {}
    for slot_name, overrides in (base_def.get('slots') or {}).items():
        if slot_name not in slot_def:
            continue
        merged = merge(copy.deepcopy(slot_def[slot_name]), copy.deepcopy(overrides or {}))
        resolved[slot_name] = merged
    return resolved


def _derive_base_slot_pin_map(base_def, slot_def):
    """For each slot, return a dict of role -> role for interesting roles."""
    out = {}
    for slot_name, merged in _resolved_slot_pin_map(base_def, slot_def).items():
        signals = {}
        for pin_num, role in merged.items():
            if not isinstance(pin_num, int):
                continue
            cleaned = _clean_role(role)
            if cleaned is None or not _interesting_role(cleaned):
                continue
            if cleaned not in signals:
                signals[cleaned] = cleaned
        out[slot_name] = signals
    return out


def _derive_base_shared_buses(slot_pin_map):
    """Group slots by which bus instance they share."""
    bus_to_slots = {}
    for slot_name, signals in slot_pin_map.items():
        seen_buses = set()
        for role in signals:
            bus = _role_to_bus_instance(role)
            if bus and bus != 'GPIO' and bus != 'analog':
                seen_buses.add(bus)
        for bus in seen_buses:
            bus_to_slots.setdefault(bus, set()).add(slot_name)
    return [
        {'bus': bus, 'slots': sorted(slots)}
        for bus, slots in sorted(bus_to_slots.items())
    ]


# ----- Compatible-slots index -----

def _build_compatible_slots_index(definitions):
    """Precompute {canonical_module_id: {display_base_id: [slot_names]}}.

    Called once at load time. Slot ids are WisMAP descriptive names (SENSOR_A, ...).
    Base ids in the inner dict are display form (RAK19007) for direct embedding
    in v1 responses.
    """
    index = {}
    bases = [(bid, b) for bid, b in definitions.items() if b.get('type') == 'WisBase']
    for mid, m in definitions.items():
        mtype = m.get('type')
        if mtype not in _TYPE_TO_SLOT_PREFIX:
            continue
        is_double = m.get('double', False) and mtype == 'WisSensor'
        per_base = {}
        for bid, b in bases:
            base_slots = b.get('slots') or {}
            eligible = []
            for slot_name, overrides in base_slots.items():
                overrides = overrides or {}
                if mtype == 'WisCore' and slot_name != 'CORE':
                    continue
                if mtype == 'WisPower' and not slot_name.startswith('POWER'):
                    continue
                if mtype == 'WisIO' and not slot_name.startswith('IO_'):
                    continue
                if mtype == 'WisSensor' and not slot_name.startswith('SENSOR_'):
                    continue
                if is_double and not overrides.get('double', False):
                    continue
                eligible.append(slot_name)
            if eligible:
                per_base[_to_display_id(bid)] = sorted(
                    eligible,
                    key=lambda x: SLOT_ORDER.index(x) if x in SLOT_ORDER else len(SLOT_ORDER)
                )
        index[mid] = per_base
    return index


# =============================================================================
# v1 entry points (called by api_v1 blueprint)
# =============================================================================

def get_cores(definitions, config):
    """List Cores, summary form."""
    core_slot = (config.get('slots') or {}).get('CORE', {})
    out = []
    for cid, c in definitions.items():
        if c.get('type') != 'WisCore':
            continue
        out.append({
            'id': _to_display_id(cid),
            'name': c.get('description', ''),
            'mcu': c.get('mcu'),
            'lora_chip': c.get('lora_chip'),
            'peripherals': _derive_core_peripherals(c, core_slot),
            'datasheet_url': c.get('documentation') or None,
        })
    return out


def get_core(definitions, config, core_id):
    """Get a single Core, full detail. Returns None if not found."""
    cid = _to_canonical_id(core_id)
    if cid not in definitions or definitions[cid].get('type') != 'WisCore':
        return None
    c = definitions[cid]
    core_slot = (config.get('slots') or {}).get('CORE', {})
    return {
        'id': _to_display_id(cid),
        'name': c.get('description', ''),
        'mcu': c.get('mcu'),
        'lora_chip': c.get('lora_chip'),
        'peripherals': _derive_core_peripherals(c, core_slot),
        'lora_pins': c.get('lora_pins'),
        'power_pins': c.get('power_pins'),
        'compatible_bases': _derive_compatible_bases(definitions),
        'notes': c.get('notes') or [],
        'datasheet_url': c.get('documentation') or None,
    }


def get_bases(definitions):
    """List Bases, summary form."""
    out = []
    for bid, b in definitions.items():
        if b.get('type') != 'WisBase':
            continue
        slots = list((b.get('slots') or {}).keys())
        slots.sort(key=lambda x: SLOT_ORDER.index(x) if x in SLOT_ORDER else len(SLOT_ORDER))
        out.append({
            'id': _to_display_id(bid),
            'name': b.get('description', ''),
            'form_factor': b.get('form_factor'),
            'slots': slots,
            'core_socket': b.get('core_socket'),
            'datasheet_url': b.get('documentation') or None,
        })
    return out


def get_base(definitions, config, base_id):
    """Get a single Base, full detail. Returns None if not found."""
    bid = _to_canonical_id(base_id)
    if bid not in definitions or definitions[bid].get('type') != 'WisBase':
        return None
    b = definitions[bid]
    slot_def = config.get('slots') or {}
    slots = list((b.get('slots') or {}).keys())
    slots.sort(key=lambda x: SLOT_ORDER.index(x) if x in SLOT_ORDER else len(SLOT_ORDER))
    slot_pin_map = _derive_base_slot_pin_map(b, slot_def)
    return {
        'id': _to_display_id(bid),
        'name': b.get('description', ''),
        'form_factor': b.get('form_factor'),
        'slots': slots,
        'core_socket': b.get('core_socket'),
        'slot_pin_map': slot_pin_map,
        'shared_buses': _derive_base_shared_buses(slot_pin_map),
        'datasheet_url': b.get('documentation') or None,
    }


def get_modules_v1(definitions, compatible_slots_index, *,
                   type=None, category=None, interface=None, compatible_with_core=None):
    """List modules (summary), with v1-spec filters."""
    out = []
    for mid, m in definitions.items():
        mtype = m.get('type')
        if mtype not in _MODULE_LISTING_TYPES:
            continue
        if type is not None and mtype != type:
            continue
        if category is not None and m.get('category') != category:
            continue
        interfaces = _derive_module_interfaces(m)
        if interface is not None and interface not in interfaces:
            continue
        if compatible_with_core is not None:
            ccid = _to_canonical_id(compatible_with_core)
            if ccid not in definitions or definitions[ccid].get('type') != 'WisCore':
                continue
        compat = compatible_slots_index.get(mid, {})
        out.append({
            'id': _to_display_id(mid),
            'name': m.get('description', ''),
            'chip': m.get('chip'),
            'type': mtype,
            'category': m.get('category'),
            'interfaces': interfaces,
            'i2c_addresses': _normalize_i2c_address(m.get('i2c_address')) or [],
            'compatible_slots': compat,
            'datasheet_url': m.get('documentation') or None,
            'tags': m.get('tags') or [],
        })
    return out


def get_module_v1(definitions, compatible_slots_index, module_id):
    """Get a single module, full detail. Returns None if not found."""
    mid = _to_canonical_id(module_id)
    if mid not in definitions:
        return None
    m = definitions[mid]
    if m.get('type') not in _MODULE_LISTING_TYPES:
        return None
    return {
        'id': _to_display_id(mid),
        'name': m.get('description', ''),
        'chip': m.get('chip'),
        'type': m.get('type'),
        'category': m.get('category'),
        'interfaces': _derive_module_interfaces(m),
        'i2c_addresses': _normalize_i2c_address(m.get('i2c_address')) or [],
        'i2c_alternate_addresses': m.get('i2c_alternate_addresses') or [],
        'signal_map': _derive_module_signal_map(m),
        'compatible_slots': compatible_slots_index.get(mid, {}),
        'core_requirements': _derive_module_core_requirements(m),
        'power': _derive_module_power(m),
        'electrical_notes': None,
        'datasheet_url': m.get('documentation') or None,
        'example_urls': m.get('example_urls') or [],
        'tags': m.get('tags') or [],
        'images': m.get('images') or [],
        'schematics': m.get('schematics') or [],
    }
