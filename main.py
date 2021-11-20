"""Main file to run."""
import thinker
from func_extras import colored_text

coordinator = thinker.Coordinator([])
app_open = True


def command_create_pop(name: str):
    """Creates a new mission from scratch using the various settings in the config files.
    Inputs:
    name (str) - The name of the new mission."""
    coordinator.create_mission(name)


def command_create_tfbot(strength: int, tfbot_kind: str='common', tfbot_class: str=False, restrict: int=0):
    """Create a new TFBot from it's strength and, if specified, various specifications.
    Inputs:
    strength (int) - The amount of overall power this TFBot can have.
    tfbot_kind (str) (optional) - The specific kind of TFBot. Can either be command, giant or boss. Defaults to common.
    tfbot_class (str) (optional) - The specified class. Defaults to randomly being a scout, soldier, pyro, demoman, heavy or sniper.
    restrict (int) (optional) - 0 for PrimaryOnly, 1 for SecondaryOnly or 2 for MeleeOnly."""
    strength = float(strength)
    restrict = int(restrict)
    t = coordinator.create_tfbot(strength=strength, tfbot_kind=tfbot_kind, tfbot_class=tfbot_class, restriction=restrict)
    print(colored_text('\nNew bot:\n', 34))
    print(t.string_spaced())
    print()


def command_exit():
    """Closes the program."""
    global app_open
    app_open = False


def command_help(command: str = ''):
    """Shows a list of specified commands, or provides specific info on a desired command.
    Inputs:
    command (str) (optional) - The specified command to get help on."""
    ref = command_reference.get(command, False)
    if ref:
        print(ref.__doc__)
    else:
        for c, d in command_reference.items():
            if len(d.__annotations__.keys()) == 0:
                params = "None"
            else:
                params = ", ".join(d.__annotations__.keys())
            print(f'\n{c} | Parameters: {params}')


def command_list_templates():
    """Lists all templates used by the generator, along with their strength."""
    print('-'*30)
    coordinator.get_templates()
    for b, s in coordinator.bot_templates_strengths:
        print(f'Template: {b.name} | Strength: {colored_text(round(s[2]), 34)}')
    print('-'*30)


def command_reload():
    """Reload all the used configs."""
    # Does nothing
    coordinator.reload_config()
    print(colored_text('Configs reloaded!', 97))


def command_templates_refresh():
    """Refresh all the templates used by the generator."""
    coordinator.get_templates()
    print(colored_text('Templates reacquired.', 97))


command_reference = {
    'create_mission': command_create_pop,
    'create_tfbot': command_create_tfbot,
    'exit': command_exit,
    'help': command_help,
    'list_templates': command_list_templates,
    'reload': command_reload,
    'templates_refresh': command_templates_refresh
}

print(f'\33[{30}m', end='')  # White default text
print('-'*40)
print('Popfile Generator by JMP. Type "help" for a list of commands.')

while app_open:
    request = input(colored_text('>>> ', 35))
    args = request.split()
    try:
        command_desired = args[0]
    except IndexError:
        print(colored_text('Please put in a command.', 31))
        command_desired = None

    if len(args) > 1:
        command_arguments = args[1:]
    else:
        command_arguments = []

    if command_desired is not None:
        command = command_reference.get(command_desired, False)
        if command:
            try:
                command(*command_arguments)
            except TypeError as e:
                print(colored_text(f'Command "{command_desired}" missing arguments.', 31))
        else:
            print(colored_text(f'Invalid command "{command_desired}".', 31))
