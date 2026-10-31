"""The ls tool, which lists the files in a folder like the shell's ls."""
import glob
import os

from tools.utils import is_path_safe


def ls(path='.'):
    """List the files in a folder, one name per line, sorted asciibetically.

    With no argument it lists the current folder. Hidden files are skipped,
    as in the shell.

    >>> import os, tempfile
    >>> start = os.getcwd()
    >>> folder = tempfile.TemporaryDirectory()
    >>> os.chdir(folder.name)
    >>> for name in ['b.txt', 'a.txt', 'Zeta.md', '.hidden']:
    ...     open(name, 'w').close()
    >>> os.mkdir('docs')
    >>> open(os.path.join('docs', 'guide.md'), 'w').close()
    >>> os.mkdir('empty')
    >>> print(ls())
    Zeta.md
    a.txt
    b.txt
    docs
    empty
    >>> ls('docs')
    'guide.md'
    >>> ls('docs/guide.md')
    'docs/guide.md'
    >>> ls('empty')
    ''
    >>> ls('nowhere')
    'Error: nowhere does not exist'
    >>> ls('/etc')
    'Error: unsafe path /etc'
    >>> ls('..')
    'Error: unsafe path ..'
    >>> os.chdir(start)
    >>> folder.cleanup()
    """
    if not is_path_safe(path):
        return f'Error: unsafe path {path}'
    if os.path.isfile(path):
        return path
    if not os.path.isdir(path):
        return f'Error: {path} does not exist'
    pattern = os.path.join(glob.escape(path), '*')
    names = sorted(os.path.basename(name) for name in glob.glob(pattern))
    return '\n'.join(names)
