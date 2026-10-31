"""The grep tool, which prints the lines of matching files that match a regex."""
import glob
import os
import re

from tools.utils import is_path_safe, read_text


def grep(regex, path):
    r"""Return every line that matches regex in the files matching the glob path.

    Files are searched in sorted order and lines keep their file order.
    Directories and files that are not text are skipped. When nothing
    matches, the result is an empty string.

    >>> import os, tempfile
    >>> start = os.getcwd()
    >>> folder = tempfile.TemporaryDirectory()
    >>> os.chdir(folder.name)
    >>> with open('a.py', 'w') as f:
    ...     _ = f.write('x = 1  # TODO rename\nprint(x)\n')
    >>> with open('b.py', 'w') as f:
    ...     _ = f.write('# TODO add tests\n')
    >>> with open('notes.txt', 'w') as f:
    ...     _ = f.write('TODO buy snacks\n')
    >>> with open('data.py', 'wb') as f:
    ...     _ = f.write(bytes([0x80, 0x81]))
    >>> os.mkdir('pkg.py')
    >>> print(grep('TODO', '*.py'))
    x = 1  # TODO rename
    # TODO add tests
    >>> grep(r'^print\(', 'a.py')
    'print(x)'
    >>> grep('TODO', '**/*.txt')
    'TODO buy snacks'
    >>> grep('nothing here', '*.py')
    ''
    >>> grep('TODO', 'missing.py')
    ''
    >>> grep('(unclosed', '*.py')
    'Error: invalid regex (unclosed'
    >>> grep('root', '/etc/passwd')
    'Error: unsafe path rejected'
    >>> grep('TODO', '../*.py')
    'Error: unsafe path rejected'
    >>> os.chdir(start)
    >>> folder.cleanup()
    """
    if not is_path_safe(path):
        return 'Error: unsafe path rejected'
    try:
        pattern = re.compile(regex)
    except re.error:
        return f'Error: invalid regex {regex}'
    matches = []
    for filename in sorted(glob.glob(path, recursive=True)):
        if not os.path.isfile(filename):
            continue
        try:
            text = read_text(filename)
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            if pattern.search(line):
                matches.append(line)
    return '\n'.join(matches)
