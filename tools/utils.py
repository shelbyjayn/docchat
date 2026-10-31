"""Shared helpers for the file tools: the path safety check and text reading."""
import codecs
import os


def is_path_safe(path):
    r"""Return True when path is relative and never contains '..'.

    >>> is_path_safe('notes.txt')
    True
    >>> is_path_safe('docs/*.md')
    True
    >>> is_path_safe('/etc/passwd')
    False
    >>> is_path_safe('\\server\\share')
    False
    >>> is_path_safe('C:\\Windows')
    False
    >>> is_path_safe('..')
    False
    >>> is_path_safe('../secret.txt')
    False
    >>> is_path_safe('docs/../../secret.txt')
    False
    """
    path = str(path)
    if os.path.isabs(path) or path.startswith(('/', '\\')):
        return False
    if len(path) > 1 and path[1] == ':':
        return False
    return '..' not in path


def read_text(path):
    r"""Return a file's text, decoded as UTF-8 or as UTF-16 when it has a byte-order mark.

    >>> import os, tempfile
    >>> start = os.getcwd()
    >>> folder = tempfile.TemporaryDirectory()
    >>> os.chdir(folder.name)
    >>> with open('plain.txt', 'w', encoding='utf-8') as f:
    ...     _ = f.write('caf\u00e9\n')
    >>> read_text('plain.txt')
    'café\n'
    >>> with open('wide.txt', 'w', encoding='utf-16') as f:
    ...     _ = f.write('hello')
    >>> read_text('wide.txt')
    'hello'
    >>> os.chdir(start)
    >>> folder.cleanup()
    """
    with open(path, 'rb') as f:
        data = f.read()
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode('utf-16')
    return data.decode('utf-8')
