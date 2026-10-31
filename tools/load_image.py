"""The load_image tool, which adds a local PNG to a chat as an image content block."""
import base64

from tools.utils import is_path_safe

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def load_image(chat, path):
    """Append a relative local PNG to chat.messages as a base64 data URL block.

    Unsafe, missing, and non-PNG paths are rejected without changing history.

    >>> import os, tempfile
    >>> from types import SimpleNamespace
    >>> start = os.getcwd()
    >>> folder = tempfile.TemporaryDirectory()
    >>> os.chdir(folder.name)
    >>> with open('dot.png', 'wb') as f:
    ...     _ = f.write(PNG_SIGNATURE + b'pixels')
    >>> chat = SimpleNamespace(messages=[])
    >>> load_image(chat, 'dot.png')
    'Loaded image dot.png'
    >>> block = chat.messages[-1]['content'][0]
    >>> block['type'], block['image_url']['url']
    ('image_url', 'data:image/png;base64,iVBORw0KGgpwaXhlbHM=')
    >>> load_image(chat, '/tmp/dot.png')
    'Error: unsafe path /tmp/dot.png'
    >>> load_image(chat, '../dot.png')
    'Error: unsafe path ../dot.png'
    >>> load_image(chat, 'missing.png')
    'Error: could not read missing.png'
    >>> with open('notes.txt', 'w') as f:
    ...     _ = f.write('not an image')
    >>> load_image(chat, 'notes.txt')
    'Error: notes.txt is not a PNG image'
    >>> len(chat.messages)
    1
    >>> os.chdir(start)
    >>> folder.cleanup()
    """
    if not is_path_safe(path):
        return f'Error: unsafe path {path}'
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except OSError:
        return f'Error: could not read {path}'
    if not (str(path).lower().endswith('.png') or data.startswith(PNG_SIGNATURE)):
        return f'Error: {path} is not a PNG image'
    url = 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
    chat.messages.append({
        'role': 'user',
        'content': [{'type': 'image_url', 'image_url': {'url': url}}],
    })
    return f'Loaded image {path}'
