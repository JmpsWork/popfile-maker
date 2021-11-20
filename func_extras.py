"""Assorted functions used throughout various files."""


def colored_text(text, color: int) -> str:
    """Returns the text colored.
    Possible value are:
    30 - White
    31 - Red
    32 - Green
    33 - Tan
    34 - Blue
    35 - Purple
    36 - Dark Cyan
    37 - Gray
    90 - Dark Gray
    91 - Pink
    92 - Green
    93 - Yellow
    94 - Light Blue
    95 - Magenta
    96 - Cold Fusion
    97 - Black
    In General,
    31 for error messages, 93 for warnings, 34 for process, 96 for completion."""
    return f'\33[{color}m' + str(text) + f'\33[{30}m'
