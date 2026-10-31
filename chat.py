"""A command-line chat that answers questions about the files in the current folder.

The model can call the ls, cat, grep, and calculate tools on its own, and the
user can run the same tools directly with slash commands such as /ls docs.
"""
import copy
import json
import os
import shlex
import sys
from types import SimpleNamespace

from dotenv import load_dotenv
from groq import Groq

from tools.calculate import calculate
from tools.cat import cat
from tools.grep import grep
from tools.ls import ls
from tools.utils import is_path_safe  # noqa: F401  (shared path check)

load_dotenv()

MODEL = 'openai/gpt-oss-20b'
VISION_MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct'
REQUEST_TIMEOUT = 60
MAX_TOOL_ROUNDS = 10
SYSTEM_PROMPT = (
    'You are a helpful assistant. You always speak like a pirate. '
    'You can inspect the files in the current folder with the ls, cat, and '
    'grep tools, and do arithmetic with the calculate tool. Use the tools '
    'to check facts about the files before answering.'
)

FUNCTIONS = {'calculate': calculate, 'cat': cat, 'grep': grep, 'ls': ls}


def _tool_schema(name, description, properties, required):
    """Build one function-tool description in the chat-completions format.

    >>> schema = _tool_schema('cat', 'Read a file.', {'path': 'File to read.'}, ['path'])
    >>> schema['function']['name']
    'cat'
    >>> schema['function']['parameters']['properties']['path']['type']
    'string'
    """
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': {
                    key: {'type': 'string', 'description': text}
                    for key, text in properties.items()
                },
                'required': required,
            },
        },
    }


TOOLS = [
    _tool_schema(
        'calculate',
        'Evaluate an arithmetic expression using numbers, parentheses, and + - * / %.',
        {'expression': 'The arithmetic expression, for example (2 + 3) * 4.'},
        ['expression'],
    ),
    _tool_schema(
        'ls',
        'List the files in a folder inside the current project. Omit path for the current folder.',
        {'path': 'A relative folder path such as . or src.'},
        [],
    ),
    _tool_schema(
        'cat',
        'Return the text contents of one file inside the current project.',
        {'path': 'A relative file path such as README.md.'},
        ['path'],
    ),
    _tool_schema(
        'grep',
        'Return every line matching a Python regular expression in the files matching a glob.',
        {
            'regex': 'The regular expression to search for.',
            'path': 'A relative path or glob such as *.py or **/*.md.',
        },
        ['regex', 'path'],
    ),
]


def get_field(item, name):
    """Read a field from either a dictionary or an object, returning None if absent.

    >>> get_field({'content': 'hi'}, 'content')
    'hi'
    >>> get_field(SimpleNamespace(content='hi'), 'content')
    'hi'
    >>> get_field({}, 'tool_calls') is None
    True
    """
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


class ScriptedModel:
    """An offline stand-in for the Groq client that replays prepared replies.

    Each request's messages are copied into requests so tests can check
    exactly what was sent. A reply is either a string answer or a list of
    (tool name, arguments) pairs that requests tool calls.

    >>> model = ScriptedModel(['Ahoy!', [('ls', {'path': '.'})]])
    >>> model is model(api_key='offline-test')
    True
    >>> first = model.chat.completions.create(messages=[{'role': 'user', 'content': 'Hi'}])
    >>> first.choices[0].message.content
    'Ahoy!'
    >>> second = model.chat.completions.create(messages=[])
    >>> call = second.choices[0].message.tool_calls[0]
    >>> call.id, call.function.name, call.function.arguments
    ('call-2-0', 'ls', '{"path": "."}')
    >>> model.requests
    [[{'role': 'user', 'content': 'Hi'}], []]
    """

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def __call__(self, *args, **kwargs):
        return self

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs['messages']))
        reply = self.replies.pop(0)
        if isinstance(reply, str):
            message = SimpleNamespace(content=reply, tool_calls=None)
        else:
            calls = [
                SimpleNamespace(
                    id=f'call-{len(self.requests)}-{number}',
                    type='function',
                    function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
                )
                for number, (name, arguments) in enumerate(reply)
            ]
            message = SimpleNamespace(content=None, tool_calls=calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def llm(messages, temperature=1, tools=None):
    """Send messages to the model and return its reply message.

    The client is created here, so importing this module or running a slash
    command never needs an API key.

    >>> from unittest.mock import patch
    >>> model = ScriptedModel(['Paris.'])
    >>> with patch(__name__ + '.Groq', model):
    ...     reply = llm([{'role': 'user', 'content': 'Capital of France?'}], temperature=0)
    >>> reply.content
    'Paris.'
    """
    client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
    has_image = any(isinstance(get_field(m, 'content'), list) for m in messages)
    request = {
        'messages': messages,
        'model': VISION_MODEL if has_image else MODEL,
        'temperature': temperature,
        'timeout': REQUEST_TIMEOUT,
    }
    if tools:
        request['tools'] = tools
    completion = client.chat.completions.create(**request)
    return get_field(get_field(completion, 'choices')[0], 'message')


def reply_text(reply):
    """Return the text of a model reply, which may be a string, dict, or message object.

    >>> reply_text('Arr!')
    'Arr!'
    >>> reply_text({'content': 'Arr!'})
    'Arr!'
    >>> reply_text(SimpleNamespace(content=None))
    ''
    """
    if isinstance(reply, str):
        return reply
    return get_field(reply, 'content') or ''


def run_tool(name, arguments):
    """Run the named tool with a dictionary of keyword arguments and return its text.

    >>> run_tool('calculate', {'expression': '6 * 7'})
    '42'
    >>> run_tool('rm', {})
    'Error: unknown tool rm'
    >>> run_tool('cat', {'nope': 'x'})
    "Error: cat() got an unexpected keyword argument 'nope'"
    """
    if name not in FUNCTIONS:
        return f'Error: unknown tool {name}'
    try:
        return str(FUNCTIONS[name](**arguments))
    except TypeError as error:
        return f'Error: {error}'


def split_command(text):
    r"""Split a slash command into words, honoring quotes but keeping backslashes.

    >>> split_command('grep "def main" *.py')
    ['grep', 'def main', '*.py']
    >>> split_command(r'grep \d+ *.txt')
    ['grep', '\\d+', '*.txt']
    >>> split_command('grep "unclosed *.py')
    ['grep', '"unclosed', '*.py']
    """
    try:
        words = shlex.split(text, posix=False)
    except ValueError:
        words = text.split()
    return [
        word[1:-1] if len(word) >= 2 and word[0] == word[-1] and word[0] in '"\'' else word
        for word in words
    ]


class Chat:
    """A conversation with the model that remembers every message and runs tools.

    When the model asks for a tool, Chat runs the matching Python function,
    sends the result back with the request's ID, and repeats until the model
    answers in text. Slash commands run a tool directly and add its output to
    the history without contacting the model.

    >>> from unittest.mock import patch
    >>> import os, tempfile
    >>> start = os.getcwd()
    >>> folder = tempfile.TemporaryDirectory()
    >>> os.chdir(folder.name)
    >>> with open('notes.txt', 'w') as f:
    ...     _ = f.write('Game night starts at 6 pm.\\n')
    >>> chat = Chat(system='Be brief.')
    >>> print(chat.run_command('/ls .'))
    notes.txt
    >>> model = ScriptedModel([[('cat', {'path': 'notes.txt'})], 'At 6 pm.'])
    >>> with patch(__name__ + '.Groq', model):
    ...     print(chat.send_message('When is game night?', temperature=0))
    At 6 pm.
    >>> 'notes.txt' in model.requests[0][1]['content']
    True
    >>> model.requests[1][-1]
    {'role': 'tool', 'tool_call_id': 'call-1-0', 'name': 'cat', 'content': 'Game night starts at 6 pm.\\n'}
    >>> os.chdir(start)
    >>> folder.cleanup()
    """

    def __init__(self, system=SYSTEM_PROMPT, debug=False):
        self.messages = [{'role': 'system', 'content': system}]
        self.debug = debug

    def send_message(self, message, temperature=0.8):
        """Send a message, run any tools the model requests, and return its answer.

        A follow-up request includes the earlier user message and assistant
        reply. Each request's messages are copied when sent:

        >>> from unittest.mock import patch
        >>> model = ScriptedModel(['Reply 1', 'Reply 2'])
        >>> with patch(__name__ + '.Groq', model):
        ...     chat = Chat(system='Be brief.')
        ...     print(chat.send_message('First', temperature=0))
        ...     print(chat.send_message('Second', temperature=0))
        Reply 1
        Reply 2
        >>> model.requests[1] == [
        ...     {'role': 'system', 'content': 'Be brief.'},
        ...     {'role': 'user', 'content': 'First'},
        ...     {'role': 'assistant', 'content': 'Reply 1'},
        ...     {'role': 'user', 'content': 'Second'},
        ... ]
        True
        >>> len(chat.messages)
        5

        Tool requests are answered with results that carry the request ID:

        >>> model = ScriptedModel([
        ...     [('calculate', {'expression': '6 * 7'}), ('rm', {})],
        ...     'The answer be 42.',
        ... ])
        >>> with patch(__name__ + '.Groq', model):
        ...     chat = Chat(system='Be brief.', debug=True)
        ...     print(chat.send_message('What is 6 times 7?', temperature=0))
        [tool] calculate {"expression": "6 * 7"}
        [tool] rm {}
        The answer be 42.
        >>> [m['role'] for m in model.requests[1]]
        ['system', 'user', 'assistant', 'tool', 'tool']
        >>> model.requests[1][2]['tool_calls'][0]['function']['name']
        'calculate'
        >>> [(m['tool_call_id'], m['content']) for m in model.requests[1][3:]]
        [('call-1-0', '42'), ('call-1-1', 'Error: unknown tool rm')]
        """
        self.messages.append({'role': 'user', 'content': message})
        for _ in range(MAX_TOOL_ROUNDS):
            reply = llm(self.messages, temperature=temperature, tools=TOOLS)
            tool_calls = None if isinstance(reply, str) else get_field(reply, 'tool_calls')
            if not tool_calls:
                answer = reply_text(reply)
                self.messages.append({'role': 'assistant', 'content': answer})
                return answer
            self._run_tool_calls(reply, tool_calls)
        answer = 'Error: the model kept requesting tools without answering.'
        self.messages.append({'role': 'assistant', 'content': answer})
        return answer

    def _run_tool_calls(self, reply, tool_calls):
        """Append the model's tool request, run each call, and append each result."""
        calls = []
        for call in tool_calls:
            function = get_field(call, 'function')
            calls.append({
                'id': get_field(call, 'id'),
                'type': 'function',
                'function': {
                    'name': get_field(function, 'name'),
                    'arguments': get_field(function, 'arguments') or '{}',
                },
            })
        request = {'role': 'assistant', 'tool_calls': calls}
        if get_field(reply, 'content'):
            request['content'] = get_field(reply, 'content')
        self.messages.append(request)
        for call in calls:
            name = call['function']['name']
            raw = call['function']['arguments']
            try:
                arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except ValueError:
                arguments = None
            if self.debug:
                print(f'[tool] {name} {json.dumps(arguments)}')
            if isinstance(arguments, dict):
                result = run_tool(name, arguments)
            else:
                result = f'Error: arguments for {name} were not valid JSON'
            self.messages.append({
                'role': 'tool',
                'tool_call_id': call['id'],
                'name': name,
                'content': result,
            })

    def run_command(self, line):
        """Run a slash command such as /ls docs without the model and record its output.

        The output is added to the history, so the next model request can use it.

        >>> chat = Chat(system='Be brief.')
        >>> chat.run_command('/calculate 2 + 3 * 4')
        '14'
        >>> chat.messages[-1]['content']
        'I ran /calculate 2 + 3 * 4 and got:\\n14'
        >>> chat.run_command('/cat /etc/passwd')
        'Error: unsafe path /etc/passwd'
        >>> chat.run_command('/cat')
        "Error: cat() missing 1 required positional argument: 'path'"
        >>> chat.run_command('/rm notes.txt')
        'Error: unknown command /rm. Try /ls, /cat, /grep, /calculate, /compact, or /load_image.'
        >>> chat.run_command('/')
        'Error: unknown command /. Try /ls, /cat, /grep, /calculate, /compact, or /load_image.'
        """
        words = split_command(line.strip()[1:])
        name, args = (words[0], words[1:]) if words else ('', [])
        if name == 'compact':
            from tools.compact import compact
            return compact(self)
        if name == 'load_image':
            from tools.load_image import load_image
            return load_image(self, *args[:1]) if args else 'Error: give a PNG path'
        if name not in FUNCTIONS:
            return (f'Error: unknown command /{name}. Try /ls, /cat, /grep, '
                    '/calculate, /compact, or /load_image.')
        if name == 'calculate':
            args = [' '.join(args)]
        try:
            result = str(FUNCTIONS[name](*args))
        except TypeError as error:
            result = f'Error: {error}'
        self.messages.append({'role': 'user', 'content': f'I ran {line.strip()} and got:\n{result}'})
        return result


RETRYABLE_ERRORS = ('tool_use_failed', 'output_parse_failed', 'Failed to parse')
MAX_ATTEMPTS = 3


def ask(chat, message, temperature):
    """Send one message and return the answer, retrying when the model's reply is malformed.

    The history is restored after a failed attempt, so the chat can continue.
    Empty answers and malformed tool requests are retried up to three times.

    >>> from unittest.mock import patch
    >>> chat = Chat(system='Be brief.')
    >>> with patch(__name__ + '.Groq', side_effect=RuntimeError('no key')):
    ...     ask(chat, 'Hi', 0)
    'Error: no key'
    >>> len(chat.messages)
    1
    >>> bad = RuntimeError("Error code: 400 - {'code': 'tool_use_failed'}")
    >>> model = ScriptedModel(['', 'Arr!'])
    >>> with patch(__name__ + '.Groq', side_effect=[bad, model, model]):
    ...     ask(chat, 'Hi', 0)
    'Arr!'
    >>> [m['role'] for m in chat.messages]
    ['system', 'user', 'assistant']
    >>> with patch(__name__ + '.Groq', side_effect=[bad, bad, bad]):
    ...     ask(chat, 'Again', 0)
    "Error: Error code: 400 - {'code': 'tool_use_failed'}"
    >>> len(chat.messages)
    3
    """
    size = len(chat.messages)
    result = ''
    for _ in range(MAX_ATTEMPTS):
        try:
            result = chat.send_message(message, temperature=temperature)
        except Exception as error:
            del chat.messages[size:]
            result = f'Error: {error}'
            if not any(code in str(error) for code in RETRYABLE_ERRORS):
                return result
            continue
        if result.strip():
            return result
        del chat.messages[size:]
    return result or 'Error: the model returned an empty answer.'


def command_line_args():
    """Return the command-line arguments when running as the chat program, otherwise [].

    >>> from unittest.mock import patch
    >>> with patch('sys.argv', ['/usr/bin/chat', '--debug']):
    ...     command_line_args()
    ['--debug']
    >>> with patch('sys.argv', ['pytest', 'chat.py']):
    ...     command_line_args()
    []
    """
    program = os.path.basename(sys.argv[0]).lower().split('.')[0]
    if program in ('chat', 'chat-script'):
        return sys.argv[1:]
    return []


def repl(temperature=0.8, debug=False, argv=None):
    """Run the chat: a one-shot message from the command line, or an interactive loop.

    Two scripted inputs produce two printed replies, and the second
    request carries the first exchange:

    >>> from unittest.mock import patch
    >>> model = ScriptedModel(['Arr 1', 'Arr 2'])
    >>> with patch('builtins.input', side_effect=['Ahoy', 'Again', EOFError]):
    ...     with patch(__name__ + '.Groq', model):
    ...         repl(temperature=0)
    Arr 1
    Arr 2
    <BLANKLINE>
    >>> [(m['role'], m['content']) for m in model.requests[1][1:]]
    [('user', 'Ahoy'), ('assistant', 'Arr 1'), ('user', 'Again')]

    A slash command runs without the model, and its output reaches the next request:

    >>> model = ScriptedModel(['It be 5.'])
    >>> with patch('builtins.input', side_effect=['/calculate 2 + 3', '', 'Result?', KeyboardInterrupt]):
    ...     with patch(__name__ + '.Groq', model):
    ...         repl(temperature=0)
    5
    It be 5.
    <BLANKLINE>
    >>> len(model.requests)
    1
    >>> model.requests[0][1]['content']
    'I ran /calculate 2 + 3 and got:\\n5'

    A one-shot message prints one reply, and --debug shows tool calls:

    >>> model = ScriptedModel([[('calculate', {'expression': '1 + 1'})], 'Two.'])
    >>> with patch(__name__ + '.Groq', model):
    ...     repl(temperature=0, argv=['--debug', 'what', 'is', '1 + 1?'])
    [tool] calculate {"expression": "1 + 1"}
    Two.
    >>> model.requests[0][-1]
    {'role': 'user', 'content': 'what is 1 + 1?'}
    """
    if argv is None:
        argv = command_line_args()
    if '--debug' in argv:
        debug = True
        argv = [arg for arg in argv if arg != '--debug']
    chat = Chat(debug=debug)
    if argv:
        print(ask(chat, ' '.join(argv), temperature))
        return
    try:
        while True:
            line = input('chat> ')
            if not line.strip():
                continue
            if line.lstrip().startswith('/'):
                print(chat.run_command(line))
            else:
                print(ask(chat, line, temperature))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == '__main__':
    repl()
