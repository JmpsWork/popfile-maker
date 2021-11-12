"""This file contains the AI which constructs the waves themselves,
along with any custom bots that need to be created.

Uses:
- config_attributes.json
- config_waves.json

As rules to follow when creating waves and bots.
"""

"""
HOW THE COORDINATOR THINKS

The AI - codenamed Coordinator, is responsible for making sure waves follow
a consistent difficulty curve, along with choosing the right bots
to ensure every wave doesn't get boring.

The main thing that is considered is the strength of a wave,
calculated from the current money players have, along with a multiplier to that value.


"""

# PROBLEM
# PYRO secondaries like flare gun crash the ai!


from popparser import *
import json
import random
import os
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

    if mod_type == 'power':
        power = operator(define.get('operator', 'none'), value, define.get('base', 1), power, define.get('mult', 1))
    elif mod_type == 'endurance':
        endurance = operator(define.get('operator', 'none'), value, define.get('base', 1), endurance, define.get('mult', 1))
    elif mod_type == 'strength':
        strength = operator(define.get('operator', 'none'), value, define.get('base', 1), strength, define.get('mult', 1))
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

    random.shuffle(attributes)
    # print(attributes, priority, weapon)

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
    # print(used_attributes)

    # Reduce amount variable down to the lengths of used attribute if necessary

    mults = []
    adders = []
    for attr in used_attributes:  # Determine if this multiplies the base power or adds to it
        attr = get_attribute(attr)
        if attr:
            attr_info = all_attributes[attr[1]]
            op = attr_info.get('operator', 'none')
            if op in ['exp', 'inv_exp', 'mult']:
                mults.append(attr_info)
            elif op in ['add']:
                adders.append(attr_info)

    # Imagine the equation:
    # 175 + ( a_(n) + a_(n-1)... ) * ( a_(n-2) * a_(n-3)... ) = strength
    # Start by assigning values to the adders
    base_power = all_classes[tfbot_class].get('power', 100)
    weapon_info = get_weapon_info(tfbot_class, weapon)
    if weapon_info[0].get('base_power', False):
        base_power = weapon_info[0].get('base_power', False)

    final_attributes = {}  # Attribute: value
    deviance_amount = 0  # The amount of 'deviant' attributes used
    attribute_amount = len(used_attributes)

    # Add any additional default attributes for an item that aren't present in vanilla default
    weapon_attributes = weapons_info[tfbot_class]['items'][weapon].get('default_add', {})
    final_attributes.update(weapon_attributes)

    # PROBLEM - Sometimes attribute values that decrease strength will be chosen over ones that increase strength!
    # Do adders first, the mults second
    for add in adders:
        possible_values = get_attribute_ranges(tfbot_class, add.get('name'), weapon_info[0].get('name'))
        if possible_values is False:
            print(f'Unknown attribute {add.get("name")} for class "{tfbot_class}"! Attribute skipped.')
            continue
        strength_values = list(map(lambda x: operator(add.get('operator', 'none'), x, add.get('base', 1), base_power, add.get('mult', 1)), possible_values))
        possible_strength_values = [abs(p - strength / attribute_amount) for p in strength_values]
        if ai_info['bot_deviance_max'] > deviance_amount and ai_info['bot_deviance_chance'] > random.uniform(0, 1) and attribute_amount != 1:
            possible_strength_values = [p - strength / attribute_amount for p in strength_values]
            # index = random.randrange(0, len(possible_strength_values))
            v, index = min_index(possible_strength_values)
            # v = possible_values[index]
            deviance_amount += 1
        else:
            v, index = min_index(possible_strength_values)

        value = possible_values[index]
        base_power += operator(add.get('operator', 'none'), value, add.get('base', 1), base_power, add.get('mult', 1))
        attribute_amount -= 1
        final_attributes[add.get('name')] = value

    for mult in mults:
        possible_values = get_attribute_ranges(tfbot_class, mult.get('name'), weapon_info[0].get('name'))
        if possible_values is False:
            print(f'Unknown attribute "{mult.get("name")}" for class "{tfbot_class}"! Attribute skipped.')
            continue
        strength_values = list(map(lambda x: operator(mult.get('operator', 'none'), x, mult.get('base', 1), base_power, mult.get('mult', 1)), possible_values))
        possible_strength_values = [abs(p - strength / attribute_amount) for p in strength_values]
        # Get the value which has the closest approximation to the strength of the bot
        if ai_info['bot_deviance_max'] > deviance_amount and ai_info['bot_deviance_chance'] > random.uniform(0, 1) and attribute_amount != 1:
            # Bot deviance tells it to pick a random attribute index instead of the normal min-maxed one
            possible_strength_values = [p - strength / attribute_amount for p in strength_values]
            # index = random.randrange(0, len(possible_strength_values))
            v, index = min_index(possible_strength_values)
            # v = min(possible_strength_values)  # Completion
            deviance_amount += 1
        else:
            v, index = min_index(possible_strength_values)
        value = possible_values[index]

        base_power = operator(mult.get('operator', 'none'), value, mult.get('base', 1), base_power, mult.get('mult', 1))
        attribute_amount -= 1
        final_attributes[mult.get('name')] = value

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
            if weapon_name == weapon or weapon in weapon_alts:
                return w[i], i
    return 0


def min_index(array: list):
    """Return the min value, and the index where it was found."""
    index = 0
    min_value = min(array)
    for i, v in enumerate(array):
        if v == min_value:
            index = i
            break
    return min_value, index


def operator(kind: str, value: float, base: int, final: float, mult: float=1) -> float:
    """Returns final, modified by the operator kind using the value, base and mult."""
    if kind == 'exp':
        return final * (mult*(base**(value - 1)))
    elif kind == 'inv_exp':
        return final * (base / value)
    elif kind == 'mult':
        return final * (base * value)
    elif kind == 'add':
        return final + value * mult
    else:
        return final


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


class Coordinator:
    """The Coordinator is responsible for coordinating the multiple different
    elements that make up a mission together in a coherent way."""

    def __init__(self, templates: list):
        self.templates = templates

        with open('config_waves.json', 'r') as wr:
            self.rules = json.loads(wr.read())

        self.current_wave = 1
        self.strength_mult = 5  # Global
        self.starting_currency = 600
        self.total_currency = self.starting_currency  # Also starting currency
        self.current_wave_rules = {}
        self.rules_reset()

        # Used when giving a newly created TFBot a name
        self.new_bot_template_id = 0
        self.bot_templates = []
        self.bot_templates_new = []
        self.bot_templates_strengths = []
        # Used bot template names for this wave. Gets cleared at the end of every wave
        self.bot_templates_used = []

    def create_mission(self, name: str):
        """Create an entire mission from scratch, using the config from ai_config.json"""
        self.current_wave = 1
        self.strength_mult = ai_info['global_strength_mult']
        self.starting_currency = random.choice(list(float_range(ai_info['cash_start_min'], ai_info['cash_start_max'], 50)))
        self.total_currency = self.starting_currency
        self.current_wave_rules = {}
        self.rules_reset()
        self.new_bot_template_id = 0
        self.bot_templates = []
        self.bot_templates_strengths = []
        self.bot_templates_new = []
        self.get_templates()
        self.bot_templates_used = []

        desired_waves = ai_info['max_waves'] + 1
        waveschedule = WaveSchedule('WaveSchedule', [])

        # Add missions (only sentry busters for now)
        mission_sentry = Mission('Mission', [])
        mission_sentry.set_kv('Objective', 'DestroySentries')
        mission_sentry.set_kv('InitialCooldown', 15)
        mission_sentry.set_kv('CooldownTime', 38)
        mission_sentry.set_kv('BeginAtWave', 1)
        mission_sentry.set_kv('RunForThisManyWaves', 999)
        mission_sentry.set_kv('Where', weighted_random(map_info['spawn_giant']))
        mission_sentry_bot = TFBot('TFBot', [])
        mission_sentry_bot.set_kv('Template', 'T_TFBot_SentryBuster')
        mission_sentry.all_subtrees.append(mission_sentry_bot)
        mission_sentry.spawner = mission_sentry_bot
        waveschedule.all_subtrees.append(mission_sentry)
        waveschedule.missions.append(mission_sentry)

        all_waves = []
        all_mission_support = []
        while desired_waves > 1:
            desired_waves -= 1
            money = random.choice(list(float_range(ai_info['cash_per_min'], ai_info['cash_per_max'], 50)))
            wave, support = self.create_wave(money)
            if ai_info['endless']:
                # If this is to be 1 big wave, simply dump the wavespawns in to all waves
                for i, wavespawn_group in enumerate(wave):
                    for wavespawn in wavespawn_group:
                        wavespawn.set_kv('Name', f'w{self.current_wave}_{i}')
                    all_waves.append(wavespawn_group)
            else:
                # If this is meant to separate waves, make a Wave instance
                new_wave = Wave('Wave', [])
                start_io = WaveIO('StartWaveOutput', [])
                start_io.set_kv('Target', map_info['relay_start'])
                start_io.set_kv('Action', 'Trigger')
                end_io = WaveIO('DoneOutput', [])
                end_io.set_kv('Target', map_info['relay_end'])
                end_io.set_kv('Action', 'Trigger')
                new_wave.io.extend([start_io, end_io])
                new_wave.all_subtrees.extend([start_io, end_io])
                for i, wavespawn_group in enumerate(wave):
                    tank_used = False  # If a tank gets used, use WaitForAllSpawned instead
                    for wavespawn in wavespawn_group:
                        if isinstance(wavespawn.spawner, Tank):
                            tank_used = True
                        if i != 0 and not tank_used:  # First wavespawns don't have any checks
                            wavespawn.set_kv('WaitForAllDead', f'w{self.current_wave}_{i - 1}')
                        elif i != 0 and tank_used:
                            wavespawn.set_kv('WaitForAllSpawned', f'w{self.current_wave}_{i - 1}')
                            tank_used = False
                        wavespawn.set_kv('Name', f'w{self.current_wave}_{i}')
                        new_wave.wavespawns.append(wavespawn)
                        new_wave.all_subtrees.append(wavespawn)
                all_waves.append(new_wave)
                for s in support:
                    all_mission_support.append(s)
            self.current_wave += 1
            print(f'Wave Strength: {self.wave_strength()}, Wave Cash: {money * self.current_wave_rules["cash_mult"]} Current Cash: {self.total_currency}')
            self.total_currency += money * self.current_wave_rules['cash_mult'] + self.current_wave_rules['cash_add']

        if not ai_info['endless']:
            for wave in all_waves:
                waveschedule.waves.append(wave)
                waveschedule.all_subtrees.append(wave)
            # Missions are only added for non endless missions
            for mission_support in all_mission_support:
                waveschedule.missions.append(mission_support)
                waveschedule.all_subtrees.append(mission_support)
        else:
            # UNFINISHED
            new_wave = Wave('Wave', [])
            start_io = WaveIO('StartWaveOutput', [])
            start_io.set_kv('Target', map_info['relay_start'])
            start_io.set_kv('Action', 'Trigger')
            end_io = WaveIO('DoneOutput', [])
            end_io.set_kv('Target', map_info['relay_end'])
            end_io.set_kv('Action', 'Trigger')
            new_wave.io.extend([start_io, end_io])
            new_wave.all_subtrees.extend([start_io, end_io])
            d_w, d_i = 1, 0
            # Figure out how to connect wavespawns in endurance style missions
            for i, wavespawn_group in enumerate(all_waves):
                for wavespawn in wavespawn_group:
                    wavespawn.set_kv('WaitForAllDead', f'w1_{i}')
                    previous = all_waves[d_w][d_i].get_kv('Name', False, True).split('_')
                    previous_w, previous_i = int(previous[0].replace('w', '')), int(previous[1])
                    current = wavespawn.get_kv('Name', False, True).split('_')
                    current_w, current_i = int(current[0].replace('w', '')), int(current[1])
                    # print('WaitForAllDead', wavespawn.get_kv('WaitForAllDead', False, True))

                    if d_w != current_w and current_i != d_i:
                        d_w, d_i = previous_w, previous_i
                    elif d_i != current_i:
                        d_i = previous_i

                    print('Name', wavespawn.get_kv('Name', False, True))
                    print('WaitForAllDead', f'w{d_w}_{d_i}')
                    new_wave.wavespawns.append(wavespawn)
                    new_wave.all_subtrees.append(wavespawn)
            waveschedule.waves.append(new_wave)
            waveschedule.all_subtrees.append(new_wave)

        waveschedule.set_kv('StartingCurrency', self.starting_currency)
        waveschedule.set_kv('RespawnWaveTime', 6)
        if ai_info['bot_attack_spawnroom']:
            waveschedule.set_kv('CanBotsAttackWhileInSpawnRoom', ai_info['bot_attack_spawnroom'])

        # Add any custom templates used
        new_templates = Templates('Templates', [])
        for tfbot in self.bot_templates_new:
            new_templates.templates_bots.append(tfbot)
            new_templates.all_subtrees.append(tfbot)
        waveschedule.templates.append(new_templates)
        waveschedule.all_subtrees.append(new_templates)

        # Add included template files
        final = '// Made using JMP\'s custom mission generator.\n'
        template_files = os.listdir('templates')
        # Ugly but whatever
        final += '#base ' + '\n#base '.join(template_files) + '\n'
        if not ai_info['spaced']:
            final += waveschedule.string
        else:
            final += waveschedule.string_spaced()
        with open(f'{map_info["name"]}_{name}.pop', 'w') as m:
            m.write(final)

    def create_wave(self, money: int=600):
        """Create a wave using the current wave number.
        To start, determine the strength of the wave and any special rules for that wave."""
        self.rules_reset()
        self.rules_current_wave()

        wave_money = money
        wave_money *= self.current_wave_rules['cash_mult']
        wave_money += self.current_wave_rules['cash_add']
        wave_strength = self.wave_strength()
        wave_strength *= self.current_wave_rules['power_mult']
        wave_power, wave_endurance = wave_strength / 2, wave_strength / 2
        wave_strength *= self.current_wave_rules['strength_mult']
        wave_power *= self.current_wave_rules['power_mult']
        wave_endurance *= self.current_wave_rules['endurance_mult']
        wave_strength += self.current_wave_rules['strength_add']
        wave_power += self.current_wave_rules['power_add']
        wave_endurance += self.current_wave_rules['endurance_add']

        # Pick a random number of total subwaves
        if self.current_wave_rules['subwaves'] == -1:
            # desired_subwaves = random.choices(range(1, self.SUBWAVES_MAX + 1), weights=[15, 50, 40, 10, 5])[0]
            desired_subwaves = int(weighted_random(ai_info['subwave_amount']))
        else:
            desired_subwaves = self.current_wave_rules['subwaves']

        # Pick the allowed bot types
        bot_types = {'common': ai_info['bot_common_chance'],
                     'giant': ai_info['bot_giant_chance'],
                     'tank': ai_info['bot_tank_chance'],
                     'boss': ai_info['bot_boss_chance']}
        for not_allowed in self.current_wave_rules['no']:
            if not_allowed not in self.current_wave_rules['must_include']:
                bot_types.pop(not_allowed)
        bot_types_priority = {k: 1 for k in self.current_wave_rules['must_include']}

        money_amounts = list(float_range(50, wave_money, 50))
        # print(f'Wave Number: {self.current_wave}, Money: {wave_money}, Total Money: {self.total_currency + self.starting_currency}')
        all_subwaves = []
        all_supports = []

        # Create mission support for this wave, if allowed
        if self.current_wave_rules['support_allowed']:
            v = random.uniform(0, 1)
            if ai_info['wave_support_chance'] > v:
                desired_supports = int(weighted_random(ai_info['wave_support_amount']))
                while desired_supports > 0:
                    support_bot_amount = int(weighted_random(ai_info['wave_support_bot_amount']))
                    support_strength = ai_info['wave_support_strength_mult'] * self.total_currency / self.wave_strength(mult=True)
                    all_supports.append(self.create_support(self.current_wave, support_strength, support_bot_amount, random.randint(0, 2)))
                    desired_supports -= 1

        while desired_subwaves > 0:  # Create subwave groups
            ideal_money = wave_money / desired_subwaves
            approximate = [abs(m - ideal_money) for m in money_amounts]
            ideal_value, index = min_index(approximate)  # money_amounts[index] is the value we want
            powers = wave_power, wave_endurance, wave_strength
            # print(f'-' * 80)
            # print(f'Wavespawn group ID: {desired_subwaves}, Money: {money_amounts[index]}, WaveSpawn Strength: {powers}')

            # Pick a random number of wavespawns for this subwave
            if self.current_wave_rules.get('bot_types', -1) != -1:
                desired_wavespawns = self.current_wave_rules['bot_types']
            else:
                desired_wavespawns = int(weighted_random(ai_info['wavespawn_amount']))

            wavespawns = self.create_subwave_section(desired_wavespawns, bot_types, bot_types_priority, money_amounts[index], powers)
            desired_subwaves -= 1
            wave_money -= money_amounts[index]
            all_subwaves.append(wavespawns)
        self.bot_templates_used = []
        return all_subwaves, all_supports

    def create_subwave_section(self, wavespawn_amount: int, allowed: dict, priority: dict, money: float, powers: tuple, slot_restrict: int=0) -> list:
        """Create a group of wavespawns with the same name that spawn at the same time.
        :arg wavespawn_amount create this many number of wavespawns for this subwave.
        :arg allowed allowed bot types. Bots from here will get chosen randomly from their associated weights.
        :arg priority bot types in this list will get priority over allowed.
        :arg money the amount of money to be used for this group of subwaves.
        :arg powers the power, endurance and strength of this subwave group in tuple form."""
        power, endurance, strength = powers
        strength_per = strength / wavespawn_amount
        # total_max_bots is used to determine what bot slots are already occupied
        total_max_bots = slot_restrict
        # Weights for the "duration" of this subwave section, which are consistent over every wavespawn
        total_groups = weighted_random({int(k): v for k, v in ai_info['wavespawn_durations'].items()})
        created_wavespawns = []
        # Keep track of the kinds of things we make
        wavespawn_stream_made = False
        money_amounts = list(float_range(10, money, 10))
        used = []
        while wavespawn_amount > 0:
            # Determine currency
            ideal_money = money / wavespawn_amount
            approximate = [abs(m - ideal_money) for m in money_amounts]
            ideal_value, index = min_index(approximate)
            # print(f'-'*20)
            # print(f'Wavespawn ID: {wavespawn_amount}, Money: {money_amounts[index]}, Ideal Money: {ideal_money}')
            # Determine the bot type we want to use
            if priority:
                chosen = weighted_random(priority)
                priority.pop(chosen)
            else:
                chosen = weighted_random(allowed)
                # Reduce likelyhood of same thing being chosen again
                allowed[chosen] = round(allowed[chosen] / 2)
            used.append(chosen)
            # Determine the wavespawn kind we want
            if self.current_wave_rules.get('bot_types', -1) == 1:
                wavespawn_kind = 'regular'
            else:
                wavespawn_kind = weighted_random({'regular': ai_info['wavespawn_regular_weight'],
                                                  'random': ai_info['wavespawn_random_weight'],
                                                  'squad': ai_info['wavespawn_squad_weight']})

            # Determine the amounts of robots (TotalCount, SpawnCount, MaxActive)
            """Determining spawning behavior is difficult to provide consistency to, as there are many possible combinations.
            Instead, a generalization will be applied for bot amounts and spawning behavior.
            - The total amount of bots depends on total_groups and maxactive, which represents the length of the subwave
            - In general, all bot slots should be occupied, depending on the amount of wavespawns
                - Giants take up more slots than commons do, and have overall reduced counts
                - Giants are also much more likely to spawn in singles instead of groups
            - The higher the spawn count, the longer the delay between bot spawns
            - The amount of bots spawned depends on the maximum active. The value of the amount spawned can be random"""
            # Think of this as the maximum possible of bots that can be active for this wavespawn
            cap = ai_info['max_tfbots'] - total_max_bots
            ideal = cap // wavespawn_amount
            if chosen == 'boss':
                # Bosses always spawn alone
                spawncount, maxactive, totalcount = 1, 1, 1
            elif chosen == 'tank':
                # Tanks also always spawn alone
                spawncount, maxactive, totalcount = 1, 1, 1
            elif chosen == 'giant':
                # Giants spawn much less than commons
                # Also prevent giant med squads from showing up early or with giant scouts
                if ai_info['wavespawn_gsquad_threshold'] > strength_per or chosen == 'scout':
                    wavespawn_kind = 'regular'

                if wavespawn_kind == 'squad':
                    spawncount, maxactive, totalcount = 2, 2 * random.randrange(1, 2), 2 * total_groups
                else:
                    if strength_per > ai_info['wavespawn_ggroup_threshold']:
                        chosen_amount = int(weighted_random(ai_info['wavespawn_giant_amount']))
                    else:
                        chosen_amount = 1
                    spawncount, maxactive, totalcount = chosen_amount, chosen_amount * random.randrange(1, 3), chosen_amount * total_groups
            else:
                if wavespawn_kind == 'squad':
                    spawncount = 2
                    maxactive = spawncount * (ideal // spawncount)
                    totalcount = maxactive * total_groups
                else:
                    maxactive = ideal
                    if not wavespawn_stream_made:  # Guarantee one stream style wavespawn
                        spawncount = random.randint(1, 2)
                        wavespawn_stream_made = True
                    else:
                        spawncount = random.randrange(1, maxactive)
                    totalcount = maxactive * total_groups
            # Determine the spawning behavior (WaitBetweenSpawns)
            """Spawning times (WaitBetweenSpawns) are very difficult to determine due to how strength and bot type
            correlate to the time between each spawning. Almost any combo can work and can't work at the same time.
            In General,
            - Bosses and Tanks only spawn in 1 group, and thus don't apply.
            - Giants spawn more frequently as the strength of the subwave goes up.
            - Commons spawn based on how big their maxactive count is. (the higher MaxActive is, the higher WaitBetweenSpawns is)"""
            if chosen == 'boss' or chosen == 'tank':
                # Spawning delay doesn't matter for tanks or bosses
                waitbetweenspawns = 1
            elif wavespawn_amount == 1 and chosen == 'giant':
                # Create stream wavespawn
                waitbetweenspawns = spawncount * 4
            else:
                if chosen == 'giant':
                    waitbetweenspawns = spawncount * 6
                else:
                    waitbetweenspawns = spawncount
            if wavespawn_kind == 'squad' and chosen != 'giant':
                waitbetweenspawns //= 2

            # Completion
            waitbeforestarting = random.randrange(1, 6)

            # Determine the spawner (aka robots) to use
            # As the spawncount goes up, the strength per tfbot goes down
            # print(f'Base strength per tfbot: {strength_per}, Modified: {(strength_per / spawncount * math.log(spawncount + 1, ai_info["bot_group_power"]))}')
            tfbot_strength = strength_per / maxactive * spawncount
            if chosen == 'boss':
                tfbot_strength *= ai_info['bot_boss_strength_mult']
            # print(f'TFBot strength: {tfbot_strength}, Max and total: {maxactive}, {totalcount}')
            if chosen == 'giant':
                eligible = self.get_templates_eligible(tfbot_strength + ai_info['bot_giant_search_add'], ai_info['strength_variance'], ['engineer', 'medic', 'sniper', 'spy'], chosen)
            else:
                eligible = self.get_templates_eligible(tfbot_strength, ai_info['strength_variance'], ['engineer', 'medic', 'sniper', 'spy'], chosen)
            if chosen == 'boss':
                if eligible and not self.current_wave_rules['custom_only'] and not ai_info['bot_boss_custom_only']:
                    template = random.choice(eligible)
                    tfbot = TFBot('TFBot', [])
                    tfbot.set_kv('Template', template.name)
                    spawner = tfbot
                else:
                    spawner = self.create_tfbot(strength=strength_per, tfbot_kind=chosen, restriction=random.randrange(0, 2))
            elif chosen == 'tank':
                # Tank strength too low per wavespawn, so it's per subwave instead
                spawner = self.create_tank(strength=strength * ai_info['tank_strength_mult'], speed=75)
            else:
                if wavespawn_kind == 'squad':
                    # Squads will always have medics as their support
                    if eligible and not self.current_wave_rules['custom_only']:
                        # Middle steps avoid using full bot info
                        template = random.choice(eligible)
                        leader = TFBot('TFBot', [])
                        leader.set_kv('Template', template.name)
                        self.bot_templates_used.append(template.name)
                    else:
                        leader = self.create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen)
                        self.template_add(leader, tfbot_strength / maxactive)
                    eligible_squad = self.get_templates_eligible(tfbot_strength, 0.5, ['scout', 'soldier', 'pyro', 'demoman', 'heavy', 'heavyweapons', 'engineer', 'sniper', 'spy'], kind=chosen)
                    if eligible_squad and eligible and not self.current_wave_rules['custom_only']:
                        squadded_bot = random.choice(eligible_squad)
                        squadded = TFBot('TFBot', [])
                        squadded.set_kv('Template', squadded_bot.name)
                        self.bot_templates_used.append(squadded_bot.name)
                    else:
                        squadded = self.create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen, tfbot_class='medic', restriction=1)
                        self.template_add(squadded, tfbot_strength / maxactive)
                    squadded_amount = spawncount - 1
                    all_squadded = []
                    # Add as many bots as needed to complete the spawncount
                    while squadded_amount > 0:
                        all_squadded.append(squadded)
                        squadded_amount -= 1
                    squad = Spawner('Squad', [])
                    squad.spawners.append(leader)
                    squad.spawners.extend(all_squadded)
                    squad.all_subtrees.append(leader)
                    squad.all_subtrees.extend(all_squadded)
                    spawner = squad
                elif wavespawn_kind == 'random':
                    # Random will have a random set of tfbots that fill up spawncount
                    # Avoid using too many templates for randomchoice
                    required = spawncount if spawncount <= 3 else round(spawncount / 2)
                    used = []
                    while required > 0:
                        # If there are any eligible TFBots, use those first
                        if eligible and not self.current_wave_rules['custom_only']:
                            template = eligible.pop()
                            self.bot_templates_used.append(template.name)
                            tfbot = TFBot('TFBot', [])
                            tfbot.set_kv('Template', template.name)
                            used.append(tfbot)
                        # If we run out of eligible bots, create some more
                        else:
                            spawner = self.create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen)
                            self.template_add(spawner, tfbot_strength / maxactive)
                            used.append(spawner)
                        required -= 1
                    randomchoice = Spawner('RandomChoice', [])
                    randomchoice.spawners.extend(used)
                    randomchoice.all_subtrees.extend(used)
                    spawner = randomchoice
                else:
                    if eligible and not self.current_wave_rules['custom_only']:
                        template = random.choice(eligible)
                        tfbot = TFBot('TFBot', [])
                        tfbot.set_kv('Template', template.name)
                        self.bot_templates_used.append(template.name)
                        spawner = tfbot
                    else:
                        spawner = self.create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen)
                        self.template_add(spawner, tfbot_strength / maxactive)

            # Determine the spawnpoint
            where = weighted_random(map_info[f'spawn_{chosen}'])

            # Put it all together
            wavespawn = WaveSpawn('WaveSpawn', [])
            wavespawn.spawner = spawner
            wavespawn.all_subtrees.append(spawner)
            wavespawn.set_kv('TotalCurrency', money_amounts[index])
            wavespawn.set_kv('TotalCount', totalcount)
            wavespawn.set_kv('MaxActive', maxactive)
            wavespawn.set_kv('SpawnCount', spawncount)
            wavespawn.set_kv('WaitBetweenSpawns', waitbetweenspawns)
            wavespawn.set_kv('WaitBeforeStarting', waitbeforestarting)
            if chosen != 'tank':
                wavespawn.set_kv('Where', where)

            # print(f'BOT TYPE {chosen} WS KIND {wavespawn_kind}')
            # print(f'Desired Duration {total_groups}, Ideal Max {ideal}, Ideal Strength {strength_per}')
            # print(f'TotalCount {totalcount}, MaxActive {maxactive}, SpawnCount {spawncount}')
            # print(f'WaitBetweenSpawns {waitbetweenspawns}\n')
            # Prepare for next wavespawn
            money -= money_amounts[index]
            wavespawn_amount -= 1
            total_max_bots += ideal
            created_wavespawns.append(wavespawn)

        return created_wavespawns

    def create_support(self, wave_num: int, strength: float, number: int, kind: int) -> Mission:
        """Create mission support using the specified wave, strength and the number of bots desired.
        kind is type of support wanted. 0 for sniper, 1 for spy and 2 for engineer. Cannot be anything else."""
        kind_ref = ['Sniper', 'Spy', 'Engineer']
        kind_slot = [0, 2, 2]
        support = Mission('Mission', [])
        support.set_kv('Objective', kind_ref[kind])
        support.set_kv('InitialCooldown', random.randint(10, 20))
        support.set_kv('Where', weighted_random(map_info['spawn_common']))
        support.set_kv('BeginAtWave', wave_num)
        support.set_kv('RunForThisManyWaves', 1)
        support.set_kv('CooldownTime', random.choice(list(float_range(20, 40, 5))))
        support.set_kv('DesiredCount', number)
        desired_class = kind_ref[kind].lower()
        not_allowed = ['scout', 'soldier', 'pyro', 'demoman', 'heavy', 'heavyweapons', 'engineer', 'medic', 'sniper', 'spy']
        not_allowed.remove(desired_class)
        eligible = self.get_templates_eligible(strength, ai_info['strength_variance'] * 2, not_allowed)
        if eligible and not self.current_wave_rules['custom_only']:
            template = random.choice(eligible)
            tfbot = TFBot('TFBot', [])
            tfbot.set_kv('Template', template.name)
            self.bot_templates_used.append(template.name)
            spawner = tfbot
        else:
            spawner = self.create_tfbot(strength=strength, restriction=kind_slot[kind], tfbot_class=desired_class)
            self.template_add(spawner, strength)
            if desired_class == 'engineer':
                teleports = list(map_info['spawn_common'].keys())
                teleports.extend(list(map_info['spawn_giant'].keys()))
                # Engineers have specific abilities that other support bots don't
                for t in teleports:
                    # Prevent duplicate spawn names
                    if t not in spawner.kvs.get('TeleportWhere', []):
                        spawner.set_kv('TeleportWhere', t)
                if strength > 750:
                    spawner.set_kv('Attributes', 'TeleportToHint')
        support.spawner = spawner
        support.all_subtrees.append(spawner)
        return support

    def create_tank(self, strength: float, speed: int=75) -> Tank:
        """Create a tank with the desired strength and optional speed."""
        strength = round_to_nearest(strength, 500)
        tank = Tank('Tank', [])
        tank.set_kv('Name', 'tankboss')
        health = round(strength * (75 / speed))
        tank.set_kv('Health', str(health))
        tank.set_kv('Speed', str(speed))
        path = weighted_random(map_info['spawn_tank'])
        tank.set_kv('StartingPathTrackNode', quotify(path))
        io_killed = WaveIO('OnKilledOutput', [])
        io_killed.set_kv('Target', 'boss_dead_relay')
        io_killed.set_kv('Action', 'Trigger')
        io_bomb = WaveIO('OnBombDroppedOutput', [])
        io_bomb.set_kv('Target', 'boss_deploy_relay')
        io_bomb.set_kv('Action', 'Trigger')
        tank.io.extend([io_bomb, io_killed])
        tank.all_subtrees.extend([io_bomb, io_killed])
        return tank

    def create_tfbot(self, strength: float, tfbot_class: str=False, tfbot_kind: str='common', p_e: tuple=False, restriction: int=0) -> TFBot:
        """Create a TFBot with the specified strength and restrictions.
        :param strength The maximum strength this bot can have.
        :param tfbot_class This TFBot will always be this class.
        :param tfbot_kind This TFBot will be this type. Either common, giant or boss.
        :param p_e Tuple of the power and strength of a robot to use
        :param restriction Force a weapon restriction on this bot.
        0 for primary, 1 for secondary, 2 for melee. Defaults to 0."""
        tfbot_skill = random.choice(['easy', 'normal', 'hard', 'expert'])
        tfbot_scale = 1 if tfbot_kind != 'boss' else 1.9
        if not tfbot_class:
            tfbot_class = random.choice(['scout', 'soldier', 'pyro', 'demoman', 'heavy', 'sniper'])
            if tfbot_class == 'sniper':
                restriction = random.randrange(1, 3)  # Ends at 2, doesn't reach 3

        # Apply speed strength modifier
        base_speed = all_classes[tfbot_class]['speed']
        strength *= base_speed / ai_info['bot_speed_default']

        tfbot_level = 1  # Rough approximations for strength
        if tfbot_kind == 'giant':
            tfbot_level += strength // 400
        elif tfbot_kind == 'boss':
            tfbot_level += strength // 2500
        else:
            tfbot_level += strength // 100

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
                endurance = round_to_nearest(strength * 0.8, 200)
                power = strength - endurance
            else:
                power = strength / 2
                endurance = strength / 2
            power = min([abs(power), strength])
            # if power < 0:  # Absolute value can create some absurd power for low tier bots
            #    power = all_classes[tfbot_class]['power']
        else:
            power, endurance = p_e

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
            crits_enabled = True
            strength /= 2
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
                    allowed_weapons.append((item, item.get('weight', 10)))
        picked_weapon = random.choices([it[0] for it in allowed_weapons], weights=[iw[1] for iw in allowed_weapons])[0]
        if allowed_passives != []:  # Error if empty list
            picked_passive = random.choices([it[0] for it in allowed_passives], weights=[iw[1] for iw in allowed_passives])[0]
            picked_passive_info = weapons_info[tfbot_class]['items'][picked_passive.get('name')]
        else:
            picked_passive = None
            picked_passive_info = None
        allow_passive = True if ai_info['bot_passive_chance'] > random.uniform(0, 1) else False
        picked_weapon_slot = get_weapon_info(tfbot_class, picked_weapon.get('name'))[1]
        picked_weapon_slot_mult = all_classes[tfbot_class]['power_mult_weapon'][picked_weapon_slot]
        power /= picked_weapon_slot_mult
        picked_weapon_info = weapons_info[tfbot_class]['items'][picked_weapon.get('name')]

        if picked_weapon_info.get('whitelist', False):
            picked_weapon_whitelist_og = picked_weapon_info.get('whitelist')
            # Copy to avoid referencing original data file
            picked_weapon_whitelist = picked_weapon_whitelist_og.copy()
        else:
            picked_weapon_whitelist_og = weapons_info[tfbot_class][f'whitelist_{slot_dict[restriction]}']
            picked_weapon_whitelist = picked_weapon_whitelist_og.copy()
            if picked_weapon_info.get('whitelist_extend', False):
                picked_weapon_whitelist = picked_weapon_whitelist_og.copy()
                picked_weapon_whitelist.extend(picked_weapon_info.get('whitelist_extend'))

        # Starts at 0, increase based on strength
        if strength > ai_info['bot_attribute_threshold']:
            attribute_max = strength // ai_info['bot_attribute_giant_per'] if tfbot_kind == 'giant' else strength // ai_info['bot_attribute_per']
            attribute_min = attribute_max - 3 if attribute_max - 3 > 1 else 1
            if attribute_min >= attribute_max + 1:  # Avoid crash
                attribute_amounts = 0
            else:
                attribute_amounts = random.randrange(attribute_min, attribute_max + 1)
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
        icon = 'random_lite_giant' if tfbot_kind == 'giant' or tfbot_kind == 'boss' else 'random_lite'
        base_info = {'Class': tfbot_class, 'ClassIcon': icon, 'Skill': tfbot_skill, 'Health': round(endurance), 'WeaponRestrictions': slot_restrict[picked_weapon_slot]}
        if tfbot_scale != 1:
            base_info['Scale'] = [tfbot_scale]
        base_info['Name'] = quotify(tfbot_name)
        # Main weapon Attributes
        primary_attributes = assign_attributes(tfbot_class, picked_weapon.get('name'), power, picked_weapon_whitelist, attribute_amounts, picked_weapon_info.get('priority', []))
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
            if tfbot_kind == 'common' and ai_info['bot_common_charge_chance'] < random.uniform(0, 1):
                tfbot.set_kv('Attributes', 'SpawnWithFullCharge')
            elif tfbot_kind != 'common' and ai_info['bot_giant_charge_threshold'] < strength:
                tfbot.set_kv('Attributes', 'SpawnWithFullCharge')

        burstmode = picked_weapon.get('burst', 0)
        if burstmode == 1:
            if random.uniform(0, 1) < ai_info['bot_burst_chance']:
                tfbot.set_kv('Attributes', 'HoldFireUntilFullReload')
        elif burstmode == 2:
            tfbot.set_kv('Attributes', 'HoldFireUntilFullReload')

        if crits_enabled:
            tfbot.set_kv('Attributes', 'AlwaysCrit')

        if allow_passive and picked_passive:
            if picked_passive_info.get('whitelist', False):
                passive_whitelist_og = picked_passive_info.get('whitelist')
                passive_whitelist = passive_whitelist_og.copy()
            else:
                passive_slot = get_weapon_info(tfbot_class, picked_passive.get('name'))[1]
                passive_whitelist_og = weapons_info[tfbot_class][f'whitelist_{slot_dict[passive_slot]}']
                passive_whitelist = passive_whitelist_og.copy()
                if picked_passive_info.get('whitelist_extend', False):
                    passive_whitelist.extend(picked_passive_info.get('whitelist_extend'))

            if picked_passive_info.get('whitelist', False) == []:
                passive_whitelist = []

            if passive_whitelist != []:
                passive_attributes = assign_attributes(tfbot_class, picked_passive.get('name'), power, passive_whitelist, attribute_amounts, picked_passive_info.get('priority', []))
                passive_attributes_re = {}
                for k in passive_attributes.keys():
                    k_info = get_attribute(k)
                    if k_info:
                        # Add to character attributes if attribute for passive weapon is meant for character attributes
                        if all_attributes[k_info[1]].get('ca', False):
                            passive_attributes_re[quotify(k)] = passive_attributes[k]
                        else:
                            primary_character_attributes[quotify(k)] = passive_attributes[k]
                if passive_attributes_re != {}:
                    pa = Attributes('ItemAttributes', [])
                    pa.kvs['ItemName'] = [quotify(picked_passive.get('name'))]
                    pa.copy(passive_attributes)
                    tfbot.item_attributes.append(pa)
                    tfbot.all_subtrees.append(pa)
            tfbot.set_kv('Item', quotify(picked_passive.get('name')))

        if tfbot_kind == 'giant' or tfbot_kind == 'boss':
            tfbot.set_kv('Attributes', 'MiniBoss')
            if tfbot_kind == 'boss':
                tfbot.set_kv('Attributes', 'UseBossHealthBar')
            character_attributes = Attributes('CharacterAttributes', [])
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

        character_attributes = Attributes('CharacterAttributes', [])
        if character_dict != {}:
            character_attributes.copy(character_dict)
            tfbot.character_attributes = character_attributes
            tfbot.all_subtrees.append(character_attributes)

        tfbot.copy(base_info)
        tfbot.apply_all_modifiers()
        return tfbot

    def get_templates(self):
        """Get all the templates from the popfiles in the templates folder."""
        os.chdir('.')
        bot_templates = []
        for popfile_name in os.listdir('templates'):
            popfile_name = popfile_name.replace('.pop', '')
            pop = PopFile(str(popfile_name))
            pop.read(f'templates/{popfile_name}')
            for template in pop.ws.templates:
                bot_templates.extend(template.templates_bots)
        self.bot_templates.extend(bot_templates)
        self.get_templates_strengths()

    def get_templates_strengths(self):
        """Creates a list of all TFBots and their strengths, and stores it in self.bot_templates_strength."""
        for tfbot in self.bot_templates:
            strength = self.get_tfbot_strength(tfbot)
            self.bot_templates_strengths.append((tfbot, strength))

    def get_templates_eligible(self, strength: float, variance: float, restrictions: list, kind: str=None, ignore_used: bool=False) -> list:
        """Get tfbots within templates with the specified strength and within the range
        of (1-variance) * strength, strength * (1+variance).
        restrictions is simply a list of what classes not to select.
        kind only allows this kind of tfbot.
        ignore_used tells this function to still consider previously used templates."""
        strength_min = strength * (1 - variance)
        strength_max = strength * (1 + variance)
        eligible = []
        for b, s in self.bot_templates_strengths:
            restrict = b.get_kv('Class', False, True).lower() not in restrictions and (b.name not in self.bot_templates_used or ignore_used)
            restrict = restrict and b.get_kv('ClassIcon', '', True) != 'sentry_buster'
            if strength_min < s[2] < strength_max and restrict:
                tfbot_attributes = b.get_kv('Attributes', [])
                if kind:
                    if kind == 'boss' and 'UseBossHealthBar' in tfbot_attributes:
                        eligible.append(b)
                    elif kind == 'giant' and 'MiniBoss' in tfbot_attributes and 'UseBossHealthBar' not in tfbot_attributes:
                        eligible.append(b)
                    elif kind == 'common' and 'MiniBoss' not in tfbot_attributes:
                        eligible.append(b)
                else:
                    eligible.append(b)
        return eligible

    def reload_config(self):
        """Reloads all configs."""
        refresh()

    def template_add(self, bot: TFBot, strength: float) -> TFBot:
        """Add a bot to the new bot templates. Called whenever a new randomly generated bot is made.
        returns the used TFBot with its new template name."""
        new_template = TFBot('', [])
        new_template.inherit(bot)
        name = bot.get_kv("Name", "", True).replace(" ", "_").replace("\"", "")
        new_template.name = f'T_TFBot_{name}_{self.new_bot_template_id}'
        self.bot_templates.append(new_template)
        self.bot_templates_new.append(new_template)
        self.new_bot_template_id += 1
        if ai_info['allow_reoccuring']:
            # power, endurance, strength
            self.bot_templates_strengths.append((new_template, (strength / 2, strength / 2, strength)))
        return new_template

    def get_tfbot_strength(self, bot: TFBot) -> tuple:
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

        # Apply the power mult of this weapon's slot - NOT COMPLETE

        base_strength = 1
        base_endurance = int(tfbot_health)
        base_power = 0

        has_itemname = []

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
                i_power, i_endurance, i_strength = self.get_weapon_strength(tfbot_class, itemname, a, bot)
                base_power += i_power
                base_endurance += i_endurance
                base_strength *= i_strength

        # PROBLEM:
        # All items are considered to be weapons, which includes cosmetics
        # Check if this item is included in all tfbot weapons defines, including not assigned weapons!
        for item in tfbot_items:  # Any Item with no item attributes gets considered here
            if item not in has_itemname:
                i_power, i_endurance, i_strength = self.get_weapon_strength(tfbot_class, item, False, bot)
                base_power += i_power
                base_endurance += i_endurance
                base_strength *= i_strength

        if bot.character_attributes:
            for attribute, value in bot.character_attributes.kvs.items():
                value = bot.character_attributes.get_kv(attribute)
                attribute = attribute.replace('"', '')
                b = get_attribute(attribute)
                if b:  # If this attribute is to be considered,
                    attribute_define = all_attributes[b[1]]
                    base_strength, base_power, base_endurance = apply_attribute_values(attribute_define, value, base_strength, base_power, base_endurance)

        return base_power, base_endurance, base_strength * (base_power + base_endurance)

    def get_weapon_strength(self, tfbot_class, weapon, attributes, tfbot: TFBot):
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

    def rules_current_wave(self):
        """Get the rules for the current wave."""
        rules_reduced = self.current_wave_rules
        for every, info in self.rules['pattern']['every'].items():
            every = int(every)
            conditions = info.get('conds', False)
            rules = info.get('rules', False)
            if self.current_wave % every == 0:
                if conditions:
                    starting_from = conditions.get('starting_from', 0)
                    if self.current_wave >= starting_from:
                        self.rules_apply(rules, rules_reduced)
                elif rules:
                    self.rules_apply(rules, rules_reduced)
        for info in self.rules['pattern']['range']:
            wave_min, wave_max = info[0], info[1]
            wave_max = 999999 if wave_max == -1 else wave_max
            if wave_min <= self.current_wave <= wave_max:
                self.rules_apply(info[2], rules_reduced)
        for wave_num, info in self.rules['individual'].items():
            if self.current_wave == int(wave_num):
                self.rules_apply(info, rules_reduced)

    def rules_apply(self, rules: dict, new_rules: dict):
        """Apply any rules fed to the new rules."""
        new_rules['power_mult'] *= rules.get('power_mult_max', 1)
        new_rules['endurance_mult'] *= rules.get('endurance_mult_max', 1)
        new_rules['strength_mult'] *= rules.get('strength_mult_max', 1)
        new_rules['cash_mult'] *= rules.get('cash_mult', 1)

        new_rules['power_add'] += rules.get('power_add', 0)
        new_rules['endurance_add'] += rules.get('endurance_add', 0)
        new_rules['strength_add'] += rules.get('strength_add', 0)
        new_rules['cash_add'] += rules.get('cash_add', 0)

        new_rules['subwaves'] = rules.get('subwaves', -1)
        new_rules['bot_amount'] = rules.get('bot_amount', -1)
        new_rules['bot_types'] = rules.get('bot_types', -1)
        new_rules['custom_only'] = rules.get('custom_only', False)
        new_rules['support_allowed'] = rules.get('support_allowed', False)

        includes = rules.get('must_include', [])
        if includes != []:
            new_rules['must_include'].append(*includes)
        not_included = rules.get('no', [])
        if not_included != []:
            new_rules['no'].extend(not_included)

    def rules_reset(self):
        """All rules are defined here, and have them reset back to their default values."""
        self.current_wave_rules['power_mult'] = 1
        self.current_wave_rules['endurance_mult'] = 1
        self.current_wave_rules['strength_mult'] = 1
        self.current_wave_rules['cash_mult'] = 1
        self.current_wave_rules['power_add'] = 0
        self.current_wave_rules['endurance_add'] = 0
        self.current_wave_rules['strength_add'] = 0
        self.current_wave_rules['cash_add'] = 0

        self.current_wave_rules['must_include'] = []
        self.current_wave_rules['no'] = []

        self.current_wave_rules['subwaves'] = -1  # -1 = infinite
        self.current_wave_rules['bot_amount'] = -1
        self.current_wave_rules['bot_types'] = -1
        self.current_wave_rules['custom_only'] = False
        self.current_wave_rules['support_allowed'] = False

    def wave_strength(self, mult: bool=False, capped: bool=True):
        """Calculate the strength of this current wave from the current money available.
        If mult is set to true, it returns the strength mutliplier instead of the strength value.
        If capped is set to true, it returns default value instead of the min.

        If the alternate function has a lower strength value than the normal strength function,
        that value will be used instead, since player strength eventually caps."""

        # Exponentially increases wave strength as cash goes up, up to 2 times
        gradual_slope = ai_info['wave_strength_growth']  # Think of this as the max multiplier
        gradual_step = ai_info['wave_strength_steep']
        gradual_mult = 2 * (math.exp(gradual_slope * self.total_currency) / (gradual_step + math.exp(gradual_slope * self.total_currency)))
        # Alternate function, much smaller slope
        alt_strength = ai_info['wave_strength_alt_mult'] * self.strength_mult * (self.total_currency**(1 / ai_info['wave_strength_alt_slope']))
        if mult:
            return self.strength_mult * gradual_mult
        else:
            if capped:
                return min(self.total_currency * self.strength_mult * gradual_mult, alt_strength)
            else:
                return self.total_currency * self.strength_mult * gradual_mult
