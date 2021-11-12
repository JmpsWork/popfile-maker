"""This file contains all the structures that are part of popfiles
It can also read and write to them using the various classes here, making
it possible and easy to interact between the popfile and code.

A reference to all the vanilla popfile keyvalues and data types can be found here
https://gist.github.com/sigsegv-mvm/9ce39744fde2aa4c6156
"""

import re
import json


def strip_whitespaces(string: str, trailing: bool=False):
    """Strip any character that satisfies the regex \\\\s
    If trailing is set to true, it will only remove whitespaces which surround the string"""
    if trailing:
        return re.sub(r'(^\s+|\s+$)', '', string)
    else:
        return re.sub(r'\s', '', string)


def correct_types(kvs: dict):
    """Converts strings in to their correct type in the kvs of subtrees.
    no, yes -> False, True
    number -> int|float if possible
    otherwise -> string"""
    for k, v in kvs.items():
        if 'no' in v.lower():
            v = False
        elif 'yes' in v.lower():
            v = True
        else:
            try:
                v = float(v)
                if v.is_integer():
                    v = int(v)
            except ValueError:
                pass
        kvs[k] = v
    return kvs


class Subtree:
    """A general class representing any subtree"""
    def __init__(self, name: str, raw: list):
        self.name = name
        self.raw = raw

        self.kvs = {}
        self.all_subtrees = []
        self.subtrees = []  # Subtrees with an unknown name to associate a class instance with

    def __repr__(self):
        return f'{self.name}{self.raw}'

    def copy(self, kvs: dict):
        """Copy the keyvalues from this dict and assign them to our kvs."""
        for k, v in kvs.items():
            if self.get_kv(k, False):
                if isinstance(v, list):
                    self.kvs[k].extend(v)
                else:
                    self.kvs[k].append(v)
            else:
                self.kvs[k] = v if isinstance(v, list) else [v]

    def find_subtree(self, name: str, cont: bool=False, existing: list=None) -> list:
        """Find a subtree with the specified name, found within all subtrees inside this one.
        cont allows this to return more than one match found.
        Do not use the parameter of existing."""
        if existing is None:
            found = []
        else:
            found = existing
        for subtree in self.all_subtrees:
            if subtree.name == name:
                found.append(subtree)
                if cont:
                    found.extend(subtree.find_subtree(name, cont, found))
                else:
                    break
        return found

    @property
    def string(self) -> str:
        kvs = ''
        for k, v in self.kvs.items():
            length = len(v)
            if length == 1:
                kvs += f'{k} {v[0]} '
            else:
                while length > 0:
                    length -= 1
                    kvs += f'{k} {v[length]} '

        subtrees = ' '.join(map(lambda x: x.string, self.all_subtrees))
        returned = f'{self.name} {{ {kvs}{subtrees}}}'
        return returned

    def string_spaced(self, depth: int=0) -> str:
        """Identical to string method, except adds newlines. Useful for human readability."""
        kvs = ''
        returned = f'\t'*depth
        depth += 1
        for k, v in self.kvs.items():
            length = len(v)
            if len == 1:
                kvs += f'\t'*depth + f'{k} {v}\n'
            else:
                while length > 0:
                    length -= 1
                    kvs += f'\t'*depth + f'{k} {v[length]}\n'
        subtrees = ' '.join(map(lambda x: x.string_spaced(depth), self.all_subtrees))
        returned = returned + f'{self.name}\n' + returned + f'{{\n{kvs} {subtrees}' + returned + f'}}\n'
        return returned

    def get_kv(self, k: str, d=False, l: bool=False):
        """Get a requested value from a key.
        If the key has a single value associated, return that indexed value.
        A default argument can be specified.
        If the returned value would be a list, the last element of the list can be returned"""
        v = self.kvs.get(k, d)
        if isinstance(v, list):
            if l:
                return v[-1]
            return v[0] if len(v) == 1 else v
        else:
            return v

    def inherit(self, subtree):
        """Inherit the kvs and subtrees of another subtree.
        Useful for converting subtrees to other kinds of subtrees"""
        self.kvs = subtree.kvs
        self.subtrees = subtree.subtrees
        self.raw = subtree.raw
        self.name = subtree.name
        self.all_subtrees = subtree.all_subtrees
        # self.parse_inner()

    def parse(self):
        """Parse self.raw, creating new subtrees as needed
        Fully parsed keys and values can be found at self.kvs, subtrees at self.subtrees"""

        start = True
        depth = 0
        subtree = ''
        i1 = 0
        skipped = None  # Skip this index
        for i, kv in enumerate(self.raw):
            if kv == '{' and start:  # Start at this
                start = False
                depth += 1
                subtree = strip_whitespaces(self.raw[i - 1])
                i1 = i
                continue
            if not start:
                if kv == '{':
                    depth += 1
                elif kv == '}':
                    depth -= 1
                if kv == '}' and depth == 0:  # End at this and determine the type of subtree
                    start = True
                    self.remember_subtree(subtree, self.raw[i1+1:i])  # i1+1:i-1
            elif kv != '{' and kv != '}':  # Anything that isn't a subtree or a curly bracket gets stored as a kv pair
                if i == skipped:  # Skip anything that is inside another subtree
                    continue
                try:
                    if self.raw[i + 1] != '{':
                        kv = strip_whitespaces(kv, True)
                        if self.kvs.get(kv, False):
                            self.kvs[kv].append(strip_whitespaces(self.raw[i + 1], True))
                        else:
                            self.kvs[kv] = [strip_whitespaces(self.raw[i + 1], True)]
                        skipped = i + 1
                except IndexError:
                    pass
        self.parse_inner()

    def parse_inner(self):
        """Parse any new subtrees that have been found."""
        for subtree in self.subtrees:
            subtree.parse()
            self.all_subtrees.append(subtree)

    def remember_subtree(self, subtree_kind: str, info: list):
        """Allows a custom class to hook in to the subtree creation and assign
        specific classes to them instead of the arbitray subtree class."""
        self.subtrees.append(Subtree(subtree_kind, info))

    def set_kv(self, k: string, v):
        """Set or add to this key with the specified value."""
        if self.get_kv(k, False):
            self.kvs[k].append(v)
        else:
            self.kvs[k] = [v]


class Attributes(Subtree):
    """General name for anything that has attributes. Always either ItemAttributes or CharacterAttributes"""
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

    def attribute_modifiers(self):
        """Returns anything that doesn't have ItemName as a key. Also remove double quotes from keys."""
        fixed = {}
        for k, v in self.kvs.items():
            if k != 'ItemName':
                try:
                    fixed[k.replace('"', '')] = float(self.get_kv(k, False, True))
                except ValueError:  # Anything that isn't a number just gets kept as string
                    fixed[k.replace('"', '')] = self.get_kv(k, False, True)
        return fixed

    def has_attribute(self, name: str) -> bool:
        """Check if this contains the specified attribute."""
        for k, v in self.kvs.items():
            if k.lower() == name:
                return True
        return False


class TFBot(Subtree):
    """A TFBot"""
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

        self.istemplate = False
        self.health = 0
        self.item_attributes = []
        self.all_modifiers = []
        self.character_attributes = None

    def apply_all_modifiers(self):
        """Returns a list of all item and character attributes."""
        self.all_modifiers.extend(self.item_attributes)
        if self.character_attributes:
            self.all_modifiers.append(self.character_attributes)

    def has_attribute(self, a: str):
        """Check if the TFBot has this attribute as part of Attributes.
        Distinct from ItemAttributes or CharacterAttributes"""
        attribs = self.get_kv('Attributes', False)
        if attribs:
            if a in attribs:
                return True
        return False

    def inherit(self, subtree):
        super().inherit(subtree)
        for i, sub in enumerate(self.subtrees):
            if 'ItemAttributes' in sub.name:
                attributes = Attributes(sub.name, sub.raw)
                attributes.parse()
                self.item_attributes.append(attributes)
                self.subtrees.pop(i)
            elif 'CharacterAttributes' in sub.name:
                attributes = Attributes(sub.name, sub.raw)
                attributes.parse()
                self.character_attributes = attributes
                self.subtrees.pop(i)

    def parse_inner(self):
        super().parse_inner()
        self.apply_all_modifiers()
        for itemattributes in self.item_attributes:
            itemattributes.parse()
            self.all_subtrees.append(itemattributes)
        if self.character_attributes:
            self.character_attributes.parse()
            self.all_subtrees.append(self.character_attributes)

    def remember_subtree(self, subtree_kind: str, info: list):
        if 'ItemAttributes' in subtree_kind:
            self.item_attributes.append(Attributes(subtree_kind, info))
        elif 'CharacterAttributes' in subtree_kind:
            self.character_attributes = Attributes(subtree_kind, info)
        else:
            self.subtrees.append(Subtree(subtree_kind, info))


class Tank(Subtree):
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

        self.health = 0
        self.speed = 0
        self.io = []

    def parse_inner(self):
        super().parse_inner()
        for waveio in self.io:
            waveio.parse()
            self.all_subtrees.append(waveio)

    def remember_subtree(self, subtree_kind: str, info: list):
        if subtree_kind in ['OnBombDroppedOut', 'OnKilledOutput']:
            self.io.append(WaveIO(subtree_kind, info))
        else:
            self.subtrees.append(Subtree(subtree_kind, info))


class Spawner(Subtree):
    """Used inside of wavespawn to determine what can appear. Can either be a:
    - TFBot
    - Tank
    - Squad
    - RandomChoice"""

    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

        self.spawner = None
        self.spawners = []  # If this is a RandomChoice or Squad, there are multiple spawners within

    def parse_inner(self):
        super().parse_inner()
        if self.spawner:
            self.spawner.parse()
            self.all_subtrees.append(self.spawner)
        for spawner in self.spawners:
            spawner.parse()
            self.all_subtrees.append(spawner)

    def remember_subtree(self, subtree_kind: str, info: list):
        if subtree_kind in ['RandomChoice', 'Squad']:
            self.spawner = Spawner(subtree_kind, info)
        elif subtree_kind in ['TFBot', 'Tank']:
            if self.name in ['RandomChoice', 'Squad']:
                self.spawners.append(Spawner(subtree_kind, info))
            else:
                self.spawner = Spawner(subtree_kind, info)
        else:
            self.subtrees.append(Subtree(subtree_kind, info))

    def tank(self):
        """If this spawner is a Tank, create a new Tank instance with the kvs and subtrees of this one."""
        if self.name == 'Tank':
            tank = Tank(self.name, self.raw)
            tank.inherit(self)
            return tank
        else:
            return False

    def tfbot(self):
        """If this spawner is a TFBot, create a new TFBot instance with the kvs and subtrees of this one."""
        if self.name == 'TFBot':
            tfbot = TFBot(self.name, self.raw)
            tfbot.inherit(self)
            return tfbot
        else:
            return False


class WaveSpawn(Subtree):
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

        self.istemplate = False
        self.io = []
        self.wavename = None
        self.spawner = None
        self.maxactive = 0

    def __repr__(self):
        return f'{self.name} {self.wavename}'

    def parse_inner(self):
        super().parse_inner()
        self.wavename = self.get_kv('Name')
        self.maxactive = self.get_kv('MaxActive')
        for waveio in self.io:
            waveio.parse()
            self.all_subtrees.append(waveio)
        if self.spawner:
            self.spawner.parse()
            self.all_subtrees.append(self.spawner)

    def remember_subtree(self, subtree_kind: str, info: list):
        if subtree_kind in ['TFBot', 'Tank', 'RandomChoice', 'Squad']:
            self.spawner = Spawner(subtree_kind, info)
        elif subtree_kind in ['StartWaveOutput', 'DoneOutput']:
            self.io.append(WaveIO(subtree_kind, info))
        else:
            self.subtrees.append(Subtree(subtree_kind, info))


class WaveIO(Subtree):
    """Any output related thing goes here."""
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)
        self.target = None
        self.action = None

    def __repr__(self):
        return f'{self.name}( Target: {self.target} Action: {self.action})'

    def parse_inner(self):
        super().parse_inner()
        self.target = self.kvs.get('Target', None)
        self.action = self.kvs.get('Action', None)


class Templates(Subtree):
    """General construct which contains a massive list of TFBots or WaveSpawns which can be used.
    Also contains methods for finding TFBots requested by the Coordinator"""
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

        self.templates_bots = []
        self.templates_wavespawns = []

    def list_tfbots(self):
        for tfbot in self.templates_bots:
            print(tfbot.kvs)

    def parse_inner(self):
        super().parse_inner()
        removed = []  # Remove any matching indexes from self.subtrees
        for i, subtree in enumerate(self.subtrees):
            # TFBots will always have Class, WaveSpawns will always have Where
            if subtree.get_kv('Class'):
                tfbot = TFBot(subtree.name, subtree.raw)
                tfbot.parse()
                self.templates_bots.append(tfbot)
                self.all_subtrees.append(tfbot)
                removed.append(i)
            elif subtree.get_kv('Where') or subtree.get_kv('TotalCount'):
                wavespawn = WaveSpawn(subtree.name, subtree.raw)
                wavespawn.parse()
                self.templates_wavespawns.append(wavespawn)
                self.all_subtrees.append(wavespawn)
                removed.append(i)
        for index in reversed(removed):  # Pop indexes in reverse
            self.subtrees.pop(index)

    def template_add(self, bot: TFBot):
        """Add a bot to the template list."""

    def template_remove(self, index: int):
        """Remove a bot from the template list using an index."""
        del self.templates_bots[index]


class Wave(Subtree):
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)

        self.number = 0
        self.io = []
        self.wavespawns = []

    def __repr__(self):
        return f'{self.name} {self.number}'

    def parse_inner(self):
        super().parse_inner()
        for wavespawn in self.wavespawns:
            wavespawn.parse()
            self.all_subtrees.append(wavespawn)
        for waveio in self.io:
            waveio.parse()
            self.all_subtrees.append(waveio)

    def remember_subtree(self, subtree_kind: str, info: list):
        if 'WaveSpawn' in subtree_kind:
            self.wavespawns.append(WaveSpawn(subtree_kind, info))
        elif subtree_kind in ['StartWaveOutput', 'DoneOutput']:
            self.io.append(WaveIO(subtree_kind, info))
        else:
            self.subtrees.append(Subtree(subtree_kind, info))

    @property
    def total_currency(self) -> int:
        return sum(map(lambda x: int(x.get_kv('TotalCurrency')), self.wavespawns))


class Mission(Subtree):
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)
        self.spawner = None

    def parse_inner(self):
        super().parse_inner()
        if self.spawner:
            self.spawner.parse()
            self.all_subtrees.append(self.spawner)

    def remember_subtree(self, subtree_kind: str, info: list):
        if subtree_kind in ['TFBot', 'RandomChoice', 'Squad']:
            self.spawner = Spawner(subtree_kind, info)
        else:
            self.subtrees.append(Subtree(subtree_kind, info))


class WaveSchedule(Subtree):
    """This contains all the information a popfile needs, which is why it's distinct from Subtree"""
    def __init__(self, name: str, raw: list):
        super().__init__(name, raw)
        self.defines = {'#base': []}
        self.templates = []
        self.missions = []
        self.waves = []
        self.subtrees = []

    def parse_inner(self):
        super().parse_inner()
        for subtree in self.subtrees: subtree.parse(); self.all_subtrees.append(subtree)
        for wave in self.waves: wave.parse(); self.all_subtrees.append(wave)
        for mission in self.missions: mission.parse(); self.all_subtrees.append(mission)
        for template in self.templates: template.parse(); self.all_subtrees.append(template)

    def remember_subtree(self, subtree_kind: str, info: list):
        if subtree_kind == 'Wave':
            self.waves.append(Wave(subtree_kind, info))
        elif subtree_kind == 'Templates':
            self.templates.append(Templates(subtree_kind, info))
        elif subtree_kind == 'Mission':
            self.missions.append(Mission(subtree_kind, info))
        else:
            self.subtrees.append(Subtree(subtree_kind, info))


class PopFile:
    """Contains all the information relating to a popfile mission."""
    def __init__(self, name: str):
        self.name = name
        self.ws = None

    def read(self, file: str):
        """Read this popfile and inherit its information."""
        with open(f'{file}.pop', 'r') as f:
            popfile = f.read()

        # Break down popfile in to 'tokens'
        # re_keys = r'(\"|' + r'|'.join(keys) + '|\{|\})'
        re_keys = r'(\s|\"|\{|\})'  # Lol just split by whitespaces and quotes
        # Remove comments by starting at every '//', and ending at the first newline, removing the span of that section.
        # Also remove any [$SIGSEGV] blocks
        re_comment = r'(\/\/.+\n|\/\/|\[\$SIGSEGV\])'
        popfile = re.sub(re_comment, '', popfile)
        popfile = re.sub(r'\s+', ' ', popfile)  # Remove any excess whitespaces, newlines and tabs
        # Then, split all the curly brackets, quotes and keys, then re-add them back to the list
        popfile = re.split(re_keys, popfile)
        popfile = [kv for kv in popfile if kv not in ['', ' ', None]]  # Remove empty / null values
        # Merge separate quotes in to single values
        start = True
        ranges = []
        i1 = 0
        fixed_popfile = []
        for i, kv in enumerate(popfile):
            if kv == '\"' and start:  # Start at this index
                start = False
                i1 = i
            elif kv == '\"' and not start:  # End at this index, capturing everything that is in it
                start = True
                ranges.append((i1, i + 1))  # add 1 to capture following quote
                fixed_popfile.append('"' + ' '.join(popfile[i1 + 1:i]) + '"')
            elif start:  # Skip values when concatenating quotes
                fixed_popfile.append(kv)

        # Once everything is split in to keys, values and concatenated strings, parsing can now commence
        # Start by creating an instance of WaveSchedule, then WaveSchedule parses through itself, ainsi de suite
        pre = []
        i1 = 0
        for i, kv in enumerate(fixed_popfile):  # Find first {
            if 'WaveSchedule' not in kv:
                pre.append(kv)
            else:
                i1 = i + 1  # Next value is first {
                break

        # Remove the first and last curly bracket
        ws = WaveSchedule('WaveSchedule', fixed_popfile[i1+1:-1])
        ws.parse()
        self.ws = ws


# testfile = PopFile('thing')
# testfile.read('templates/robot_giant')
# bot = testfile.ws.templates[0].templates_bots[0]

# print(isinstance(bot, TFBot))
# print(bot.kvs)
