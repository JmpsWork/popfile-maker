"""
This file contains the AI which constructs and coordinates missions and their elements together.
Comes with a lot of utility and secondary functions to aid in this goal.

Can be customized using one of the many config files available.
- config_ai.json
- config_attributes.json
- config_classes.json
- config_map.json
- config_waves.json
"""


from popparser import *
from func_extras import colored_text
from botutils import *
import json
import random
import os
import math


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
        # Final tank to give Skin 1 to
        self.final_tank = False

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
        self.final_tank = False

        desired_waves = ai_info['max_waves'] + 1
        waveschedule = WaveSchedule('WaveSchedule', [])

        # Add missions (only sentry busters for now)
        mission_sentry = Mission('Mission', [])
        mission_sentry.set_kv('Objective', 'DestroySentries')
        mission_sentry.set_kv('InitialCooldown', 15)
        mission_sentry.set_kv('CooldownTime', 40)
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
                        wavespawn.set_kv('Name', f'w{self.current_wave}_{i}')
                        new_wave.wavespawns.append(wavespawn)
                        new_wave.all_subtrees.append(wavespawn)
                all_waves.append(new_wave)
                for s in support:
                    all_mission_support.append(s)
            print(colored_text(f'Wave {self.current_wave} Strength: {self.wave_strength()}, Current Cash: {self.total_currency}, Wave Cash: {money * self.current_wave_rules["cash_mult"]}', 34))
            self.current_wave += 1
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

        # Modify remaining stuff
        if isinstance(self.final_tank, Tank):
            self.final_tank.set_kv('Skin', 1)

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
        print(colored_text('Mission successfully finished.', 96))

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

            if self.current_wave_rules.get('bot_amount', -1) != -1:
                desired_duration = self.current_wave_rules['bot_amount']
            else:
                desired_duration = None

            wavespawns = self.create_subwave_section(desired_wavespawns, bot_types, bot_types_priority, money_amounts[index], powers, duration=desired_duration)
            desired_subwaves -= 1
            wave_money -= money_amounts[index]
            all_subwaves.append(wavespawns)
        self.bot_templates_used = []
        return all_subwaves, all_supports

    def create_subwave_section(self, wavespawn_amount: int, allowed: dict, priority: dict, money: float, powers: tuple, slot_restrict: int=0, duration: int=None) -> list:
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
        total_wavespawns = wavespawn_amount
        # Weights for the "duration" of this subwave section, which are consistent over every wavespawn
        if duration is not None:
            total_groups = duration
        else:
            total_groups = weighted_random({int(k): v for k, v in ai_info['wavespawn_durations'].items()})
        created_wavespawns = []
        # Keep track of the kinds of things we make
        wavespawn_stream_made = False
        money_amounts = list(float_range(10, money, 10))
        used = []
        used_tanks = 0
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
                if ai_info['wavespawn_gsquad_threshold'] > strength_per:
                    wavespawn_kind = 'regular'

                if wavespawn_kind == 'squad':
                    spawncount, maxactive, totalcount = 2, 2 * random.randrange(1, 2), 2 * total_groups
                else:
                    if strength_per > ai_info['wavespawn_ggroup_threshold']:
                        chosen_amount = int(weighted_random(ai_info['wavespawn_giant_amount']))
                    else:
                        chosen_amount = 1
                    spawncount, maxactive, totalcount = chosen_amount, chosen_amount * random.randint(2, 3), chosen_amount * total_groups
                if total_wavespawns == 1:
                    maxactive *= 2
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
                    # Make the totalcount a multiple of spawncount
                    totalcount = maxactive * total_groups
                    rem = totalcount % spawncount
                    if rem != 0:
                        totalcount += spawncount - rem
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
            elif wavespawn_amount == 1:
                # Create stream wavespawn
                if chosen == 'giant':
                    # Reduce giant spawn time as strength goes up
                    waitbetweenspawns = math.ceil(spawncount * 5 * odds_value(strength_per, -ai_info['wavespawn_giant_spawn_decrement'], ai_info['wavespawn_giant_spawn_shift']))
                else:
                    waitbetweenspawns = spawncount // 2
            else:
                if chosen == 'giant':
                    waitbetweenspawns = math.ceil(spawncount * 8 * odds_value(strength_per, -ai_info['wavespawn_giant_spawn_decrement'], ai_info['wavespawn_giant_spawn_shift']))
                else:
                    waitbetweenspawns = spawncount
            if wavespawn_kind == 'squad' and chosen != 'giant':
                waitbetweenspawns //= 2

            # Completion
            if chosen == 'tank':
                waitbeforestarting = random.randint(5, 8) + (14 * used_tanks)
                used_tanks += 1
            else:
                waitbeforestarting = random.randint(1, 6)

            # Determine the spawner (aka robots) to use
            # As the spawncount goes up, the strength per tfbot goes down
            if chosen == 'boss':
                tfbot_strength = ai_info['bot_strength_giant_min'] + strength_per / math.ceil(maxactive * 0.5) * math.ceil(spawncount * 0.5)
                tfbot_strength *= ai_info['bot_boss_strength_mult']
            # print(f'TFBot strength: {tfbot_strength}, Max and total: {maxactive}, {totalcount}')
            if chosen == 'giant':
                tfbot_strength = ai_info['bot_strength_giant_min'] + strength_per / math.ceil(maxactive * 0.5) * math.ceil(spawncount * 0.5)
                eligible = self.get_templates_eligible(tfbot_strength + ai_info['bot_giant_search_add'], ai_info['strength_variance'], ['engineer', 'medic', 'spy'], chosen)
            else:
                tfbot_strength = ai_info['bot_strength_min'] + strength_per / math.ceil(maxactive * 0.5) * math.ceil(spawncount * 0.5)
                eligible = self.get_templates_eligible(tfbot_strength, ai_info['strength_variance'], ['engineer', 'medic', 'spy'], chosen)
            if chosen == 'boss':
                if eligible and not self.current_wave_rules['custom_only'] and not ai_info['bot_boss_custom_only']:
                    template = random.choice(eligible)
                    tfbot = TFBot('TFBot', [])
                    tfbot.set_kv('Template', template.name)
                    spawner = tfbot
                else:
                    spawner = create_tfbot(strength=strength_per, tfbot_kind=chosen, restriction=random.randrange(0, 2))
            elif chosen == 'tank':
                # Tank strength is per subwave modified by the amount of wavespawns in the subwave
                # The more tanks there are in a subwave, each future tank has less and less HP
                bias = (1 - total_wavespawns * ai_info['tank_strength_bias'])
                tank_strength = self.wave_tank_strength(divisor=used_tanks) * bias
                tank_speed = int(weighted_random(ai_info['tank_speeds']))
                spawner = self.create_tank(strength=tank_strength, speed=tank_speed)
                self.final_tank = spawner
            else:
                if wavespawn_kind == 'squad':
                    # Remove scouts from eligible
                    eligible = [e for e in eligible if e.get_kv('Class').lower() != 'scout']
                    # Squads will always have medics as their support
                    if eligible and not self.current_wave_rules['custom_only']:
                        # Middle steps avoid using full bot info
                        template = random.choice(eligible)
                        leader = TFBot('TFBot', [])
                        leader.set_kv('Template', template.name)
                        self.bot_templates_used.append(template.name)
                        tfbot_class = leader.get_kv('Class', False, True)
                    else:
                        tfbot_class = random.choice(['soldier', 'pyro', 'demoman', 'heavy', 'medic', 'sniper'])
                        if tfbot_class == 'medic':
                            restriction = random.choice([0, 2])
                        else:
                            restriction = None
                        leader = create_tfbot(tfbot_class=tfbot_class, strength=tfbot_strength / maxactive, tfbot_kind=chosen, restriction=restriction)
                        self.template_add(leader, tfbot_strength / maxactive)
                    eligible_squad = self.get_templates_eligible(tfbot_strength, 0.5, ['scout', 'soldier', 'pyro', 'demoman', 'heavy', 'heavyweapons', 'engineer', 'sniper', 'spy'], kind=chosen)
                    if eligible_squad and eligible and not self.current_wave_rules['custom_only']:
                        squadded_bot = random.choice(eligible_squad)
                        squadded = TFBot('TFBot', [])
                        squadded.set_kv('Template', squadded_bot.name)
                        self.bot_templates_used.append(squadded_bot.name)
                    else:
                        squadded = create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen, tfbot_class='medic', restriction=1)
                        self.template_add(squadded, tfbot_strength / maxactive)
                    squadded_amount = spawncount - 1
                    all_squadded = []
                    # Add as many bots as needed to complete the spawncount
                    while squadded_amount > 0:
                        all_squadded.append(squadded)
                        squadded_amount -= 1
                    squad = Spawner('Squad', [])
                    if tfbot_class == 'medic':
                        squad.set_kv('ShouldPreserveSquad', 1)
                    squad.spawners.append(leader)
                    squad.spawners.extend(all_squadded)
                    squad.all_subtrees.append(leader)
                    squad.all_subtrees.extend(all_squadded)
                    spawner = squad
                elif wavespawn_kind == 'random':
                    # Random will have a random set of tfbots that fill up spawncount
                    # Avoid using too many templates for randomchoice
                    required = random.randint(2, 3)
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
                            spawner = create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen)
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
                        spawner = create_tfbot(strength=tfbot_strength / maxactive, tfbot_kind=chosen)
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
            spawner = create_tfbot(strength=strength, restriction=kind_slot[kind], f_r=False, tfbot_class=desired_class, skill='expert', support_bot=True)
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
        tank = Tank('Tank', [])
        tank.set_kv('Name', 'tankboss')
        health = round_to_nearest(strength * (75 / speed), 500)
        # If health exceeds maximum, clamp it
        if health > ai_info['tank_hp_max']:
            health = ai_info['tank_hp_max']
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
            strength = get_tfbot_strength(tfbot)
            self.bot_templates_strengths.append((tfbot, strength))

    def get_templates_eligible(self, strength: float, variance: float, restrictions: list, kind: str=None, ignore_used: bool=False, support_bot: bool=False) -> list:
        """Get tfbots within templates with the specified strength and within the range
        of (1-variance) * strength, strength * (1+variance).
        restrictions is simply a list of what classes not to select.
        kind only allows this kind of tfbot.
        ignore_used tells this function to still consider previously used templates.
        support_bot if set to true allows any template using a support exclsuive weapon to be used"""
        strength_min = strength * (1 - variance)
        strength_max = strength * (1 + variance)
        eligible = []
        for b, s in self.bot_templates_strengths:
            restrict = b.get_kv('Class', False, True).lower() not in restrictions and (b.name not in self.bot_templates_used or ignore_used)
            restrict = restrict and b.get_kv('ClassIcon', '', True) != 'sentry_buster'
            if strength_min < s[2] < strength_max and restrict:
                tfbot_attributes = b.get_kv('Attributes', [])

                tfbot_weapon_info = get_tfbot_weapon(b)
                if support_bot:
                    weapon_valid = True
                else:
                    if not tfbot_weapon_info.get('support_only', False):
                        weapon_valid = True
                    else:
                        # Skip classes without valid weapons
                        continue

                if kind and weapon_valid:
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
        with open('config_waves.json', 'r') as wr:
            self.rules = json.loads(wr.read())
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

        new_rules['subwaves'] = rules.get('subwaves', new_rules.get('subwaves', -1))
        new_rules['bot_amount'] = rules.get('bot_amount', new_rules.get('bot_amount', -1))
        new_rules['bot_types'] = rules.get('bot_types', new_rules.get('bot_types', -1))
        new_rules['custom_only'] = rules.get('custom_only', new_rules.get('custom_only', False))
        new_rules['support_allowed'] = rules.get('support_allowed', new_rules.get('support_allowed', False))

        includes = rules.get('must_include', [])
        if includes != []:
            new_rules['must_include'].extend(includes)
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

    def wave_tank_strength(self, divisor: int=1):
        """Calculate the strength for this tank using the current money available.
        Tank HP needs a different strength calculation to accommodate for lower cash.

        divisor divides the input cash by the specified amount."""
        tank_mult = ai_info['wave_strength_tank_mult']
        tank_slope = ai_info['wave_strength_tank_slope']
        return ai_info['tank_strength_mult'] * self.strength_mult * tank_mult * (self.total_currency / divisor)**(1 / tank_slope)
