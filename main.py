"""Main file to run."""
import thinker

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
    strength (int): The amount of overall power this TFBot can have.
    tfbot_kind (str) (optional): The specific kind of TFBot. Can either be command, giant or boss. Defaults to common.
    tfbot_class (str) (optional): The specified class. Defaults to randomly being a scout, soldier, pyro, demoman, heavy or sniper.
    restrict (int) (optional): 0 for PrimaryOnly, 1 for SecondaryOnly or 2 for MeleeOnly."""
    strength = float(strength)
    restrict = int(restrict)
    t = coordinator.create_tfbot(strength=strength, tfbot_kind=tfbot_kind, tfbot_class=tfbot_class, restriction=restrict)
    print('\nNew bot:\n')
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
            print(f'\n{c} | Parameters: {", ".join(d.__annotations__.keys())}')


def command_list_templates():
    """Lists all templates used by the generator, along with their strength."""
    print('-'*30)
    coordinator.get_templates()
    for b, s in coordinator.bot_templates_strengths:
        print(f'Template: {b.name} | Strength: {round(s[2])}')
    print('-'*30)


def command_reload():
    """Reload all the used configs."""
    # Does nothing
    coordinator.reload_config()
    print('Configs reloaded!')


def command_templates_refresh():
    """Refresh all the templates used by the generator."""
    coordinator.get_templates()
    print('Templates reacquired.')


command_reference = {
    'create_mission': command_create_pop,
    'create_tfbot': command_create_tfbot,
    'exit': command_exit,
    'help': command_help,
    'list_templates': command_list_templates,
    'reload': command_reload,
    'templates_refresh': command_templates_refresh
}

print('-'*40)
print('Popfile Generator by JMP. Type "help" for a list of commands.')

while app_open:
    request = input('>>> ')
    args = request.split()
    try:
        command_desired = args[0]
    except IndexError:
        print('Please put in a command.')
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
                print(f'Command "{command_desired}" missing arguments.')
        else:
            print(f'Invalid command "{command_desired}".')
