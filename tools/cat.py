"""The cat tool, which returns the text contents of one file."""
from tools.utils import is_path_safe, read_text


def cat(path):
    r"""Return the contents of a text file inside the current folder.

    >>> import os, tempfile
    >>> start = os.getcwd()
    >>> folder = tempfile.TemporaryDirectory()
    >>> os.chdir(folder.name)
    >>> with open('notes.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('Game night starts at 6 pm.\nBring a snack.\n')
    >>> cat('notes.txt')
    'Game night starts at 6 pm.\nBring a snack.\n'
    >>> with open('wide.txt', 'w', encoding='utf-16') as f:
    ...     _ = f.write('saved on Windows')
    >>> cat('wide.txt')
    'saved on Windows'
    >>> with open('photo.bin', 'wb') as f:
    ...     _ = f.write(bytes([0x80, 0x81, 0xff]))
    >>> cat('photo.bin')
    'Error: photo.bin is not a text file'
    >>> cat('missing.txt')
    'Error: missing.txt does not exist'
    >>> os.mkdir('docs')
    >>> cat('docs')
    'Error: could not read docs'
    >>> cat('/etc/passwd')
    'Error: unsafe path /etc/passwd'
    >>> cat('../notes.txt')
    'Error: unsafe path ../notes.txt'
    >>> os.chdir(start)
    >>> folder.cleanup()
    """
    if not is_path_safe(path):
        return f'Error: unsafe path {path}'
    try:
        return read_text(path)
    except FileNotFoundError:
        return f'Error: {path} does not exist'
    except UnicodeDecodeError:
        return f'Error: {path} is not a text file'
    except OSError:
        return f'Error: could not read {path}'
