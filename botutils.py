"""
This file contains various miscellaneous functions related towards the creation of tfbots
and interpreting their strength values.

Separated from thinker.py to avoid unnecessary clutter.
"""

from func_extras import colored_text
from popparser import TFBot, Attributes
import json
import random
import math


with open('config_classes.json') as cc:
    class_info = json.loads(cc.read())
with open('config_attributes.json') as ca:
    weapons_info = json.loads(ca.read())
with open('config_ai.json') as cai:
    ai_info = json.loads(cai.read())
with open('config_map.json') as cm:
    map_info = json.loads(cm.read())


all_attributes = weapons_info['attributes_defines']
all_classes = class_info


def refresh():
    global class_info, weapons_info, ai_info, map_info, all_attributes, all_classes
    with open('config_classes.json') as cc:
        class_info = json.loads(cc.read())
    with open('config_attributes.json') as ca:
        weapons_info = json.loads(ca.read())
    with open('config_ai.json') as cai:
        ai_info = json.loads(cai.read())
    with open('config_map.json') as cm:
        map_info = json.loads(cm.read())

    all_attributes = weapons_info['attributes_defines']
    all_classes = class_info


def apply_attribute_values(define: dict, value: float, strength, power, endurance) -> tuple:
    """Apply an attribute's value to either strength, power or endurance"""
    value = float(value)
    mod_type = define.get('type', 'power')
    value_clamp = define.get('clamp', False)  # Clamp prevents any attribute value getting operated on below this value
    ceil_clamp = define.get('ceil', False)  # Ceil prevents any attribute value getting operator above this value

    if value_clamp:
        value = value if value > value_clamp else value_clamp
    elif ceil_clamp:
        value = value if value < ceil_clamp else ceil_clamp

    default = define.get('def', 1)
    if mod_type == 'power':
        power = operator(define.get('operator', 'none'), value, define.get('base', 1), power, define.get('mult', 1), default)
    elif mod_type == 'endurance':
        endurance = operator(define.get('operator', 'none'), value, define.get('base', 1), endurance, define.get('mult', 1), default)
    elif mod_type == 'strength':
        strength = operator(define.get('operator', 'none'), value, define.get('base', 1), strength, define.get('mult', 1), default)
    return float(strength), float(power), float(endurance)


def assign_attributes(tfbot_class: str, weapon: str, strength: float, s_attributes: list, amount: int, priority: list) -> dict:
    """Picks a certain amount of weapon attributes, with priority ones chosen first,
    and then assigns them values based on the weapon and desired strength.
    Returns a dict with the weapon attributes."""
    # NOTE: there's this weird issue where s_attributes gets bigger and bigger?
    # List needs to be copied or else it will override the whitelist in config_attributes.json
    attributes = s_attributes.copy()
    used_attributes = []

    # Remove duplicates
    for i, a in enumerate(priority):
        if a in attributes:  # If this priority attribute is the same as this regular one
            attributes.remove(a)

    if len(attributes) + len(priority) < amount:  # Avoid infinite loop
        used_attributes.extend(priority)
        used_attributes.extend(attributes)
    else:
        while amount >= 1:
            if priority != []:
                chosen = random.choice(priority)
                priority.remove(chosen)
            else:
                chosen = random.choice(attributes)
                attributes.remove(chosen)
            used_attributes.append(chosen)
            amount -= 1
    # Increase variety of attributes
    random.shuffle(used_attributes)

    # Reduce amount variable down to the lengths of used attribute if necessary
    mults = []
    adders = []
    for attr in used_attributes:  # Determine if this multiplies the base power or adds to it
        attr = get_attribute(attr)
        if attr:
            attr_info = all_attributes[attr[1]]
            op = attr_info.get('operator', 'none')
            if op in ['exp', 'inv_exp', 'mult', 'inv_exp_fixed']:
                mults.append(attr_info)
            elif op in ['add', 'mult_add', 'percentage_add']:
                adders.append(attr_info)

    base_power = all_classes[tfbot_class].get('power', 100)
    weapon_info = get_weapon_info(tfbot_class, weapon)
    if weapon_info[0].get('base_power', False):
        base_power = weapon_info[0].get('base_power', False)

    final_attributes = {}  # Attribute: value
    deviance_amount = 0  # The amount of 'deviant' attributes used
    attribute_amount = len(used_attributes)

    # Add any additional default attributes for an item that aren't present in vanilla default
    weapon_attributes = weapons_info[tfbot_class]['items'][weapon].get('default_add', {})

    # Find an approximate strength value we want per attribute.
    # The lower the attribute count, the higher the strength per attribute should be.
    # Then, find the original value that comes closest to that attribute strength value.

    # Do adders first, then mults second
    if attribute_amount != 0:
        strength_per_adder = abs(strength / attribute_amount - base_power)
        strength_per_mult = abs(strength / attribute_amount - base_power)
    else:
        strength_per_adder, strength_per_mult = 0, 0

    for add in adders:
        # Duplicate of the other for loop but I don't care
        possible_values = get_attribute_ranges(tfbot_class, add.get('name'), weapon_info[0].get('name'))
        default = add.get('def', 0)
        if possible_values is False:
            print(colored_text(f'Unknown attribute "{add.get("name")}" for class "{tfbot_class}"! Attribute skipped.', 93))
            continue
        strength_values = list(map(lambda x: operator(add.get('operator', 'none'), x, add.get('base', 1), strength_per_adder, add.get('mult', 1), default), possible_values))
        possible_strength_values = [abs(p - strength) for p in strength_values]
        if ai_info['bot_deviance_max'] > deviance_amount and ai_info['bot_deviance_chance'] > random.uniform(0, 1) and attribute_amount != 1:
            possible_strength_values = [p - strength for p in strength_values]
            v, index = min_index(possible_strength_values)
            deviance_amount += 1
            strength_per_adder += strength / attribute_amount
        else:
            v, index = min_index(possible_strength_values)

        value = possible_values[index]
        attribute_amount -= 1
        final_attributes[add.get('name')] = value

    for mult in mults:
        # Get the value which has the closest approximation to the strength of the bot
        possible_values = get_attribute_ranges(tfbot_class, mult.get('name'), weapon_info[0].get('name'))
        default = mult.get('def', 1)
        # If the attribute doesn't exist, throw a warning and skip it
        if possible_values is False:
            print(colored_text(f'Unknown attribute "{mult.get("name")}" for class "{tfbot_class}"! Attribute skipped.', 93))
            continue
        # Calculate the strength for each value, and then the closest approximation to our desired strength
        strength_values = list(map(lambda x: operator(mult.get('operator', 'none'), x, mult.get('base', 1), strength_per_mult, mult.get('mult', 1), default), possible_values))
        possible_strength_values = [abs(p - strength_per_mult) for p in strength_values]

        if ai_info['bot_deviance_max'] > deviance_amount and ai_info['bot_deviance_chance'] > random.uniform(0, 1) and attribute_amount != 1:
            # Bot deviance tells it to pick a random attribute index instead of the normal min-maxed one
            possible_strength_values = [p - strength for p in strength_values]
            v, index = min_index(possible_strength_values)
            deviance_amount += 1
            # Upgrade next attribute to compensate
            strength_per_mult += strength / attribute_amount
        else:
            v, index = min_index(possible_strength_values)
        # Add the value and attribute to all attributes
        value = possible_values[index]
        attribute_amount -= 1
        final_attributes[mult.get('name')] = value

    final_attributes.update(weapon_attributes)
    return final_attributes


def get_attribute(name: str):
    """Get the attribute with the specified name.
    Returns the default name of that attribute, the index, the inverse name (if found) and the default value."""
    for i, potential in enumerate(all_attributes):
        name_default = potential['name']
        name_inverse = potential.get('inverse', name_default)
        name_alts = potential.get('alt', [])
        inversed = name_inverse if name != name_inverse else name_default
        if name == name_default or name == name_inverse or name in name_alts:
            return name_default, i, inversed, potential.get('def', None)
    return False


def float_range(start: float, end: float, step: float):
    """Create a range of floats with steps"""
    while start < end + step:
        yield round(start, 2)
        start += step


def get_attribute_ranges(tfbot_class: str, attribute: str, weapon: str):
    """Get the possible values an attribute can have for this class and specific weapon."""
    attribute = get_attribute(attribute)
    weapon_slot = get_weapon_info(tfbot_class, weapon)[1]
    if weapon_slot == 1:
        info = weapons_info[tfbot_class]['attributes_secondary']
    elif weapon_slot == 2:
        info = weapons_info[tfbot_class]['attributes_melee']
    else:
        info = weapons_info[tfbot_class]['attributes_primary']

    for attr in info:
        if attr['name'] == attribute[0] or attr['name'] == attribute[2]:
            return list(float_range(attr['min'], attr['max'], attr['step']))
    return False


def get_weapon_info(tfbot_class, weapon: str):
    """Returns the info of a weapon, along with the slot"""
    weapon = weapon.replace('"', '')
    class_weapons = [all_classes[tfbot_class]['primaries'], all_classes[tfbot_class]['secondaries'], all_classes[tfbot_class]['melee']]
    for i, w in enumerate(class_weapons):
        for slot in w:
            weapon_name = slot.get('name')
            weapon_alts = slot.get('alt', [])
            # print(f'Comparing {weapon} - to - {weapon_name}')
            if weapon_name == weapon or weapon in weapon_alts:
                return w[i], i
    return 0


def get_weapon_info_attributes(tfbot_class: str, weapon: str):
    """Returns the weapon info found from config_attributes.json.
    Returns False if the weapon cannot be found."""
    weapon = weapon.replace('"', '')
    weapon_info = weapons_info[tfbot_class]['items'].get(weapon, False)
    return weapon_info


def min_index(array: list):
    """Return the min value, and the index where it was found."""
    index = 0
    min_value = min(array)
    for i, v in enumerate(array):
        if v == min_value:
            index = i
            break
    return min_value, index


def operator(kind: str, value: float, base: int, final: float, mult: float=1, default: float=1) -> float:
    """Returns final, modified by the operator kind using the value, base and mult."""
    if kind == 'exp':
        return final * (mult*(base**(value - 1)))
    elif kind == 'inv_exp':
        return final * (base / value) * mult
    elif kind == 'inv_exp_fixed':
        # Keeps the default value always equal to 1
        # Base must ALWAYS be equal to or greater than the default
        return final * ((1 / (base * value)) + ((base - 1) / default / base))
    elif kind == 'mult':
        return final * (base * value)
    elif kind == 'percentage_add':
        # Adds a percentage of the current strength to the strength
        # Very similar to mult_add
        return final + (final * mult * (value - default) * base + default)
    elif kind == 'mult_add':
        # Multiplies by smaller steps, while keeping the default value normal
        # Base must ALWAYS be equal to or less than the defaul1
        return mult * (final + (value - default) * base + default)
    elif kind == 'add':
        return final + value * mult
    else:
        return final


def odds_value(value: float, slope: float, shift: float) -> float:
    """Customizable sigmoid function. Input is value,
    slope is how quickly values go from 0 to 1 and shift is how far the midpoint is from 0."""
    return (math.exp(slope * (value - shift))) / (1 + math.exp(slope * (value - shift)))


def quotify(string: str) -> str:
    """Adds quotes around the string."""
    return f'"{string}"'


def round_to_nearest(r, v) -> float:
    """Rounds r to the nearest v."""
    modded = r / v
    modded = round(modded)
    return modded * v


def weighted_random(vals_scale: dict):
    """Picks a key randomly from it's numerical weight value.
    Higher values relative to others increase the odds of associated key being chosen."""
    keys = list(vals_scale.keys())
    randomized = random.choices(keys, weights=tuple(vals_scale.values()))
    return randomized[0]


# Big functions


def get_tfbot_icon(tfbot_kind: str, tfbot_class: str, weapon: dict, passive: dict=None, override: str=None):
    """This functions determines what icon a custom tfbot should receive based on its weapon and stats.
    If the tfbot has a passive weapon, the icons belonging to that passive will be used instead, and
    if the passive has no icons, it will default back to the main weapon's icons.
    If an override icon is specified, that icon is immediately returned instead.
    If no other eligible icon is found, returns None (which means to use the default icon of the bot)
    If the weapon the TFBot is using cannot be found, a mystery icon is used instead."""
    if override is not None:
        return override
    # icon = 'random_lite_giant' if tfbot_kind == 'giant' or tfbot_kind == 'boss' else 'random_lite'

    if tfbot_kind in ['giant', 'boss']:
        # If bot is a giant or boss, use the giant icon
        if not weapon:
            return 'random_lite_giant'

        icon = weapon.get('icon_giant', None)

        if passive:
            icon = passive.get('icon_giant', icon)

        return icon

    else:
        # If bot is a common, use the regular icon
        if not weapon:
            return 'random_lite'

        icon = weapon.get('icon', None)

        if passive:
            icon = passive.get('icon', icon)

        return icon


def get_tfbot_weapon(bot: TFBot):
    """This function gets the first non passive weapon a bot is using,
    and returns the relevant info of the weapon from config_classes.json.
    If no weapon is found, then it will return the first weapon it finds with default set to true."""
    tfbot_class = bot.get_kv('Class').lower()
    tfbot_class = 'heavy' if 'heavy' in tfbot_class else tfbot_class  # Check for heavyweapons
    tfbot_restrict = bot.get_kv('WeaponRestrictions', 'PrimaryOnly', True)

    weapon_dict = {'PrimaryOnly': 'primaries', 'SecondaryOnly': 'secondaries', 'MeleeOnly': 'melee'}
    weapon_type = weapon_dict[tfbot_restrict]

    tfbot_weapons = bot.get_kv('Item', [])
    class_weapons = class_info[tfbot_class][weapon_type]
    for possible_weapon in class_weapons:
        for tfbot_weapon in tfbot_weapons:
            if possible_weapon.get('name') == tfbot_weapon and not possible_weapon.get('passive'):
                return possible_weapon

    # If no weapons get returned, chose the default weapon
    for possible_weapon in class_weapons:
        if possible_weapon.get('default', False) is True:
            return possible_weapon

    return False


def get_tfbot_strength(bot: TFBot) -> tuple:
    """Calculate the strength of a tfbot from its power and endurance.
    :returns strength, power, endurance."""

    tfbot_class = bot.get_kv('Class').lower()
    tfbot_class = tfbot_class.replace('"', '')
    tfbot_attributes = bot.kvs.get('Attributes', [])
    tfbot_class = 'heavy' if 'heavy' in tfbot_class else tfbot_class  # Check for heavyweapons
    tfbot_health = bot.get_kv('Health', False)
    tfbot_restriction = bot.get_kv('WeaponRestrictions', False, True)
    tfbot_items = bot.kvs.get('Item', [])
    tfbot_items = [item.lower() for item in tfbot_items]

    # Health is defined health, otherwise default to common health or giant health
    if not tfbot_health:
        if 'MiniBoss' in tfbot_attributes:
            tfbot_health = all_classes[tfbot_class]['health_giant']
        else:
            tfbot_health = all_classes[tfbot_class]['health']
    is_giant = True if 'MiniBoss' in tfbot_attributes else False

    # Apply the power mult of this weapon's slot - NOT COMPLETE

    base_strength = 1
    base_endurance = int(tfbot_health)
    base_power = 0

    has_itemname = []
    has_itemattributes = False

    if bot.item_attributes == []:  # Hard-coded default item powers
        base_power = all_classes[tfbot_class]['power']
        tfbot_skill = bot.get_kv('Skill', 'easy').lower()
        if tfbot_skill == 'easy':
            base_power *= all_classes[tfbot_class]['power_mult_skill'][0]
        elif tfbot_skill == 'normal':
            base_power *= all_classes[tfbot_class]['power_mult_skill'][1]
        elif tfbot_skill == 'hard':
            base_power *= all_classes[tfbot_class]['power_mult_skill'][2]
        elif tfbot_skill == 'expert':
            base_power *= all_classes[tfbot_class]['power_mult_skill'][3]

    # Strength gets modified by the base speed of a class
    base_speed = all_classes[tfbot_class]['speed']
    base_strength *= base_speed / ai_info['bot_speed_default']

    # Apply AlwaysCrit strength bonus
    if 'AlwaysCrit' in tfbot_attributes:
        base_strength *= 2

    for a in bot.all_modifiers:  # If there are attributes with ItemNames
        itemname = a.get_kv('ItemName', False)
        # PROBLEM:
        # All weapons end up having their strength pooled together, instead of being considered separate
        # Add separate variables for weapon strengths, and then add those together

        # If this TFBot has any item attributes, it's to be considered stronger than ones without
        if a.name == 'ItemAttributes':
            has_itemattributes = True

        if itemname:
            has_itemname.append(itemname)
            item_info = get_weapon_info(tfbot_class, itemname)
            if tfbot_restriction and item_info:
                item_passive = item_info[0].get('passive', False)
                if item_info[1] != 0 and tfbot_restriction == 'PrimaryOnly' and not item_passive:
                    continue
                elif item_info[1] != 1 and tfbot_restriction == 'SecondaryOnly' and not item_passive:
                    continue
                elif item_info[1] != 2 and tfbot_restriction == 'MeleeOnly' and not item_passive:
                    continue
            i_power, i_endurance, i_strength = get_weapon_strength(tfbot_class, itemname, a, bot)
            base_power += i_power
            base_endurance += i_endurance
            base_strength *= i_strength

    # PROBLEM:
    # All items are considered to be weapons, which includes cosmetics
    # Check if this item is included in all tfbot weapons defines, including not assigned weapons!
    for item in tfbot_items:  # Any Item with no item attributes gets considered here
        if item not in has_itemname:
            i_power, i_endurance, i_strength = get_weapon_strength(tfbot_class, item, False, bot)
            base_power += i_power
            base_endurance += i_endurance
            base_strength *= i_strength

        # If this weapon has a global strength multiplier, include it
        item_info = get_weapon_info_attributes(tfbot_class, item)
        if item_info:
            if item_info.get('strength_mult', False):
                base_strength *= item_info.get('strength_mult', 1)

    if bot.character_attributes:
        for attribute, value in bot.character_attributes.kvs.items():
            value = bot.character_attributes.get_kv(attribute)
            attribute = attribute.replace('"', '')
            b = get_attribute(attribute)
            if b:  # If this attribute is to be considered,
                attribute_define = all_attributes[b[1]]
                base_strength, base_power, base_endurance = apply_attribute_values(attribute_define, value, base_strength, base_power, base_endurance)

    if is_giant and not has_itemattributes:
        base_strength *= ai_info['bot_giant_stock_mult']

    return base_power, base_endurance, base_strength * (base_power + base_endurance)


def get_weapon_strength(tfbot_class, weapon, attributes, tfbot: TFBot):
    """Calculate the power, endurance and strength modifiers of a weapon."""
    weapon = weapon.replace('"', '')
    base_power = all_classes[tfbot_class]['power']
    base_endurance = 0  # Additive, as weapons will usually not multiply the endurance of a bot
    base_strength = 1

    # INCOMPLETE - Make the base power default to 0 when the weapon is a cosmetic
    weapon_power_base = weapons_info[tfbot_class].get('items', {}).get(weapon, {}).get('power_base', False)
    weapon_power_mult = weapons_info[tfbot_class].get('items', {}).get(weapon, {}).get('power_mult', 1)
    base_power = weapon_power_base if weapon_power_base else base_power

    # Apply the skill mult of this bot
    tfbot_skill = tfbot.get_kv('Skill', 'easy', True).lower()
    if tfbot_skill == 'easy':
        base_power *= all_classes[tfbot_class]['power_mult_skill'][0]
    elif tfbot_skill == 'normal':
        base_power *= all_classes[tfbot_class]['power_mult_skill'][1]
    elif tfbot_skill == 'hard':
        base_power *= all_classes[tfbot_class]['power_mult_skill'][2]
    elif tfbot_skill == 'expert':
        base_power *= all_classes[tfbot_class]['power_mult_skill'][3]

    # Apply the power mult of this weapon's slot
    slot_index = get_weapon_info(tfbot_class, weapon)
    if slot_index:
        slot_index = slot_index[1]
    base_power *= all_classes[tfbot_class]['power_mult_weapon'][slot_index]

    # Apply attribute operators, including default item attributes
    weapon_attributes = weapons_info[tfbot_class]['items'].get(weapon, {}).get('default', {})
    if attributes:
        if weapon_attributes:
            weapon_attributes.update(attributes.attribute_modifiers())
        else:
            weapon_attributes = attributes.attribute_modifiers()

    for attribute, value in weapon_attributes.items():
        b = get_attribute(attribute)
        if b:  # Consider this attribute if it exists
            attribute_define = all_attributes[b[1]]
            base_strength, base_power, base_endurance = apply_attribute_values(attribute_define, value, base_strength, base_power, base_endurance)

    return base_power * weapon_power_mult, base_endurance, base_strength


def create_tfbot(strength: float, tfbot_class: str=False, tfbot_kind: str='common', p_e: tuple=False, restriction: int=None, skill: str=False, f_r: bool=True, support_bot: bool=False) -> TFBot:
    """Create a TFBot with the specified strength and restrictions.
    :param strength The maximum strength this bot can have.
    :param tfbot_class This TFBot will always be this class.
    :param tfbot_kind This TFBot will be this type. Either common, giant or boss.
    :param p_e Tuple of the power and endurance for a robot to use. Forced.
    :param restriction Force a weapon restriction on this bot.
    0 for primary, 1 for secondary, 2 for melee. Defaults to 0."""
    if skill:
        tfbot_skill = skill
    else:
        tfbot_skill = random.choice(['easy', 'normal', 'hard', 'expert'])
    tfbot_scale = 1 if tfbot_kind != 'boss' else 1.9
    if not tfbot_class:
        tfbot_class = random.choice(['scout', 'soldier', 'pyro', 'demoman', 'heavy', 'sniper'])

    # Apply any special weapon restrictions if not specified for certain classes
    if restriction is None:
        if tfbot_class == 'medic':
            # Exclusively medigun
            restriction = 1
        elif tfbot_class == 'spy':
            # Either primary or melee
            restriction = random.choice([0, 2])
        else:
            restriction = int(weighted_random(ai_info['bot_slot_odds']))

    # Apply speed strength modifier
    base_speed = all_classes[tfbot_class]['speed']
    strength *= ai_info['bot_speed_default'] / base_speed

    tfbot_level = 1  # Rough approximations for strength
    if tfbot_kind == 'giant':
        tfbot_level += strength // 300
    elif tfbot_kind == 'boss':
        tfbot_level += strength // 1250
    else:
        tfbot_level += strength // 75

    if not p_e:
        if tfbot_kind == 'common':
            # The HP threshold determines whether to use default health or buffed health
            if ai_info['bot_minigiant_chance'] > random.uniform(0, 1) and strength > ai_info['bot_hp_threshold']:
                endurance = round_to_nearest(strength / 2, 25)
                tfbot_scale = 1.3
            else:
                endurance = all_classes[tfbot_class]['health']
            power = strength - endurance
        elif tfbot_kind == 'giant':
            tfbot_skill = random.choice(['normal', 'hard', 'expert'])
            if strength > ai_info['bot_giant_hp_threshold']:
                endurance = round_to_nearest(strength / 2, 100)
            else:
                endurance = all_classes[tfbot_class]['health_giant']
            power = strength - endurance
        elif tfbot_kind == 'boss':
            tfbot_skill = 'expert'
            strength *= ai_info['bot_boss_strength_mult']
            endurance = round_to_nearest(strength * 0.8 * ai_info['bot_boss_endurance_mult'], 200)
            power = strength - endurance
        else:
            power = strength / 2
            endurance = strength / 2
        power = min([abs(power), strength])
        # if power < 0:  # Absolute value can create some absurd power for low tier bots
        #    power = all_classes[tfbot_class]['power']
    else:
        power, endurance = p_e
        power, endurance = round(power), round(endurance)

    # If this bot's hp would be more than the max, clamp it to the max
    if endurance > ai_info['bot_hp_max']:
        endurance = ai_info['bot_hp_max']
    # Used for attributes

    if tfbot_skill == 'easy':
        power /= all_classes[tfbot_class]['power_mult_skill'][0]
    elif tfbot_skill == 'normal':
        power /= all_classes[tfbot_class]['power_mult_skill'][1]
    elif tfbot_skill == 'hard':
        power /= all_classes[tfbot_class]['power_mult_skill'][2]
    elif tfbot_skill == 'expert':
        power /= all_classes[tfbot_class]['power_mult_skill'][3]

    if (tfbot_kind == 'giant' or tfbot_kind == 'boss') and tfbot_class != 'scout':  # Account for move speed penalty
        power *= 2

    # If this bot has a high enough desired base strength, give it crits
    if strength > ai_info['bot_crit_threshold'] and random.uniform(0, 1) < ai_info['bot_crit_chance']:
        # Prevent mediguns from getting crits
        if not (tfbot_class == 'medic' and restriction == 1):
            crits_enabled = True
            strength /= 2
        else:
            crits_enabled = False
    else:
        crits_enabled = False

    slot_dict = {0: 'primary', 1: 'secondary', 2: 'melee'}
    class_weapons = [all_classes[tfbot_class]['primaries'], all_classes[tfbot_class]['secondaries'], all_classes[tfbot_class]['melee']]
    allowed_weapons = []
    allowed_passives = []
    for i, w in enumerate(class_weapons):
        for item in w:
            is_passive = item.get('passive', False)
            if is_passive and i != restriction:
                allowed_passives.append((item, item.get('weight', 10)))
            elif not is_passive and i == restriction:
                # Support bots get exclusive weapon searches
                if support_bot:
                    # All weapons for a certain slot are allowed for support bots
                    allowed_weapons.append((item, item.get('weight', 10)))
                else:
                    # If this weapon is noy exclusively for support bots, append it
                    if not item.get('support_only', False):
                        allowed_weapons.append((item, item.get('weight', 10)))
    picked_weapon = random.choices([it[0] for it in allowed_weapons], weights=[iw[1] for iw in allowed_weapons])[0]
    if allowed_passives != []:  # Error if empty list
        picked_passive = random.choices([it[0] for it in allowed_passives], weights=[iw[1] for iw in allowed_passives])[0]
        picked_passive_info = weapons_info[tfbot_class]['items'][picked_passive.get('name')]
    else:
        picked_passive = None
        picked_passive_info = None

    # Override passive chance if desired
    passive_chance = ai_info['bot_passive_chance']
    if picked_weapon.get('passive_chance', False):
        passive_chance = picked_weapon.get('passive_chance')

    allow_passive = True if passive_chance > random.uniform(0, 1) else False
    # This line sometimes crashes the program for some reason
    picked_weapon_slot = get_weapon_info(tfbot_class, picked_weapon.get('name'))[1]
    picked_weapon_slot_mult = all_classes[tfbot_class]['power_mult_weapon'][picked_weapon_slot]
    power /= picked_weapon_slot_mult
    picked_weapon_info = weapons_info[tfbot_class]['items'][picked_weapon.get('name')]

    # For reference,
    # picked_weapon - info from config_classes.json
    # picked_weapon_info - info from config_attributes.json
    # Dumb naming but it is how it is

    if picked_weapon_info.get('whitelist', False):
        picked_weapon_whitelist_og = picked_weapon_info.get('whitelist')
        # Copy to avoid referencing original data file
        picked_weapon_whitelist = picked_weapon_whitelist_og.copy()
    else:
        picked_weapon_whitelist_og = weapons_info[tfbot_class][f'whitelist_{slot_dict[restriction]}']
        picked_weapon_whitelist = picked_weapon_whitelist_og.copy()
        if picked_weapon_info.get('whitelist_extend', False):
            picked_weapon_whitelist.extend(picked_weapon_info.get('whitelist_extend').copy())

    # Starts at 0, increase based on strength
    if strength > ai_info['bot_attribute_threshold']:
        attribute_max = strength // ai_info['bot_attribute_giant_per'] if tfbot_kind == 'giant' else strength // ai_info['bot_attribute_per']
        attribute_min = attribute_max - 2 if attribute_max - 2 > 1 else 1
        if attribute_min > attribute_max:  # Avoid crash
            attribute_amounts = attribute_max
        else:
            attribute_amounts = random.randint(attribute_min, attribute_max)
    else:
        attribute_amounts = 0
    # print(tfbot_class, tfbot_kind, tfbot_level, strength, power, attribute_amounts)
    slot_restrict = {0: 'PrimaryOnly', 1: 'SecondaryOnly', 2: 'MeleeOnly'}
    # Create final TFBot
    tfbot = TFBot('TFBot', [])
    # Base stuff
    tfbot_name = tfbot_class.capitalize()
    if tfbot_kind == 'giant':
        tfbot_name = f'Giant {tfbot_name}'
    elif tfbot_kind == 'boss':
        tfbot_name = f'Boss {tfbot_name}'

    tfbot_name = f'Level {round(tfbot_level)} {tfbot_name}'
    base_info = {'Class': tfbot_class, 'Skill': tfbot_skill, 'Health': round(endurance)}

    # Specifically for support robots
    if f_r:  # Force Restriction, if desired
        base_info['WeaponRestrictions'] = slot_restrict[picked_weapon_slot]
    if tfbot_scale != 1:
        base_info['Scale'] = [tfbot_scale]
    base_info['Name'] = quotify(tfbot_name)
    # Main weapon Attributes
    attribute_power = power
    primary_attributes = assign_attributes(tfbot_class, picked_weapon.get('name'), attribute_power, picked_weapon_whitelist, attribute_amounts, picked_weapon_info.get('priority', []))
    primary_attributes_re = {}
    primary_character_attributes = {}
    for k in primary_attributes.keys():
        k_info = get_attribute(k)
        if k_info:
            # If this attribute exists and belongs in character attributes, then we assign it there instead
            # Some attributes only function in character attributes so this needs to be done
            if all_attributes[k_info[1]].get('ca', False):
                primary_character_attributes[quotify(k)] = primary_attributes[k]
            else:
                primary_attributes_re[quotify(k)] = primary_attributes[k]
        else:
            # If this attribute is undefined (like stickybomb info), include it in weapon attributes
            primary_attributes_re[quotify(k)] = primary_attributes[k]

    if primary_attributes_re:
        weapon_attributes = Attributes('ItemAttributes', [])
        weapon_attributes.kvs['ItemName'] = [quotify(picked_weapon.get("name"))]
        weapon_attributes.copy(primary_attributes_re)
        tfbot.item_attributes.append(weapon_attributes)
        tfbot.all_subtrees.append(weapon_attributes)
    tfbot.set_kv('Item', quotify(picked_weapon.get('name')))
    # If one of the chosen weapons can be charged in some way,
    if picked_passive:
        passive_charge = True if picked_passive.get('charge', False) else False
    else:
        passive_charge = False

    # Attributes AlwaysCharge allowed?
    if picked_weapon.get('charge', False) or passive_charge:
        if tfbot_kind == 'common' and ai_info['bot_common_charge_chance'] > random.uniform(0, 1):
            tfbot.set_kv('Attributes', 'SpawnWithFullCharge')
        elif tfbot_kind != 'common' and ai_info['bot_giant_charge_threshold'] < strength:
            tfbot.set_kv('Attributes', 'SpawnWithFullCharge')

    # Attributes HoldFireUntilFullReload allowed?
    burstmode = picked_weapon.get('burst', 0)
    if burstmode == 1:
        if random.uniform(0, 1) < ai_info['bot_burst_chance']:
            tfbot.set_kv('Attributes', 'HoldFireUntilFullReload')
    elif burstmode == 2:
        tfbot.set_kv('Attributes', 'HoldFireUntilFullReload')

    # MaxVisionRange for this weapon
    visionrange = picked_weapon.get('maxvision', False)
    if visionrange:
        tfbot.set_kv('MaxVisionRange', visionrange)

    if crits_enabled:
        tfbot.set_kv('Attributes', 'AlwaysCrit')

    # Do the same thing for mainweapon, except for passive weapon this time
    if allow_passive and picked_passive:
        if picked_passive_info.get('whitelist', False):
            passive_whitelist_og = picked_passive_info.get('whitelist')
            passive_whitelist = passive_whitelist_og.copy()
        else:
            passive_slot = get_weapon_info(tfbot_class, picked_passive.get('name'))[1]
            passive_whitelist_og = weapons_info[tfbot_class][f'whitelist_{slot_dict[passive_slot]}']
            passive_whitelist = passive_whitelist_og.copy()
            if picked_passive_info.get('whitelist_extend', False):
                passive_whitelist.extend(picked_passive_info.get('whitelist_extend').copy())

        if picked_passive_info.get('whitelist', False) == []:
            passive_whitelist = []

        if passive_whitelist != []:
            passive_attributes = assign_attributes(tfbot_class, picked_passive.get('name'), attribute_power, passive_whitelist, attribute_amounts, picked_passive_info.get('priority', []))
            passive_attributes_re = {}
            for k in passive_attributes.keys():
                k_info = get_attribute(k)
                if k_info:
                    # Add to character attributes if attribute for passive weapon is meant for character attributes
                    if all_attributes[k_info[1]].get('ca', False):
                        passive_attributes_re[quotify(k)] = passive_attributes[k]
                    else:
                        primary_character_attributes[quotify(k)] = passive_attributes[k]
                else:
                    passive_attributes_re[quotify(k)] = passive_attributes[k]
            if passive_attributes_re != {}:
                pa = Attributes('ItemAttributes', [])
                pa.kvs['ItemName'] = [quotify(picked_passive.get('name'))]
                pa.copy(passive_attributes_re)
                tfbot.item_attributes.append(pa)
                tfbot.all_subtrees.append(pa)
        tfbot.set_kv('Item', quotify(picked_passive.get('name')))

    if tfbot_kind == 'giant' or tfbot_kind == 'boss':
        tfbot.set_kv('Attributes', 'MiniBoss')
        if tfbot_kind == 'boss':
            tfbot.set_kv('Attributes', 'UseBossHealthBar')
        character_dict = {}
        if tfbot_class == 'medic':
            character_dict['heal rate bonus'] = 200.0
        else:
            character_dict['override footstep sound set'] = 3
        move_speed = 0.5
        dmg_force_mult = 0.25
        airblast_vuln_mult = 0.25
        if tfbot_class != 'scout' or tfbot_kind == 'boss':
            character_dict['move speed bonus'] = move_speed
        if tfbot_kind == 'boss':
            dmg_force_mult = 0.1
            airblast_vuln_mult = 0.05
        character_dict['damage force reduction'] = dmg_force_mult
        character_dict['airblast vulnerability multiplier'] = airblast_vuln_mult
        character_dict = {quotify(k): v for k, v in character_dict.items()}
    else:
        character_dict = primary_character_attributes

    # If there is an icon, use it
    if picked_passive and allow_passive:
        icon = get_tfbot_icon(tfbot_kind, tfbot_class, picked_weapon, picked_passive)
    else:
        icon = get_tfbot_icon(tfbot_kind, tfbot_class, picked_weapon)
    if icon:
        base_info['ClassIcon'] = icon

    # Apply character attributes, if necessary
    character_attributes = Attributes('CharacterAttributes', [])
    if character_dict != {}:
        character_attributes.copy(character_dict)
        tfbot.character_attributes = character_attributes
        tfbot.all_subtrees.append(character_attributes)

    tfbot.copy(base_info)
    tfbot.apply_all_modifiers()
    return tfbot
