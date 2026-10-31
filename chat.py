import os
from dotenv import find_dotenv, load_dotenv
from groq import Groq

load_dotenv(find_dotenv(usecwd=True))
client = Groq(api_key=os.environ.get('GROQ_API_KEY') or 'missing-key')


def llm(messages, temperature=1):
    """Send messages to the model and return the reply text.

    >>> from unittest.mock import patch
    >>> with patch.object(client.chat.completions, 'create') as request:
    ...     request.return_value.choices[0].message.content = 'Paris.'
    ...     print(llm([{'role': 'user', 'content': 'Capital of France?'}],
    ...               temperature=0))
    ...     print(request.call_args.kwargs['temperature'])
    Paris.
    0
    """
    completion = client.chat.completions.create(
        messages=messages,
        model='openai/gpt-oss-20b',
        temperature=temperature,
    )
    return completion.choices[0].message.content


class Chat:
    """A conversation that remembers its messages.

    >>> Chat().messages
    [{'role': 'system', 'content': 'You are a helpful assistant.'}]
    """

    def __init__(self, system='You are a helpful assistant.'):
        self.messages = [{'role': 'system', 'content': system}]

    def send_message(self, message, temperature=0.8):
        """Send a message and retain the reply.

        A single reply is returned and stored:

        >>> from unittest.mock import patch
        >>> with patch.object(client.chat.completions, 'create') as request:
        ...     request.return_value.choices[0].message.content = 'Hello!'
        ...     chat = Chat(system='Be brief.')
        ...     print(chat.send_message('Hi', temperature=0))
        Hello!
        >>> chat.messages == [
        ...     {'role': 'system', 'content': 'Be brief.'},
        ...     {'role': 'user', 'content': 'Hi'},
        ...     {'role': 'assistant', 'content': 'Hello!'},
        ... ]
        True

        A follow-up request includes the earlier user message and
        assistant reply. Each request's messages are copied when sent:

        >>> from unittest.mock import MagicMock
        >>> sent = []
        >>> def fake_create(**kwargs):
        ...     sent.append([dict(m) for m in kwargs['messages']])
        ...     response = MagicMock()
        ...     response.choices[0].message.content = f'Reply {len(sent)}'
        ...     return response
        >>> with patch.object(client.chat.completions, 'create',
        ...                   side_effect=fake_create):
        ...     chat = Chat(system='Be brief.')
        ...     print(chat.send_message('First', temperature=0))
        ...     print(chat.send_message('Second', temperature=0))
        Reply 1
        Reply 2
        >>> sent[1] == [
        ...     {'role': 'system', 'content': 'Be brief.'},
        ...     {'role': 'user', 'content': 'First'},
        ...     {'role': 'assistant', 'content': 'Reply 1'},
        ...     {'role': 'user', 'content': 'Second'},
        ... ]
        True
        >>> len(chat.messages)
        5
        """
        self.messages.append({'role': 'user', 'content': message})
        reply = llm(self.messages, temperature=temperature)
        self.messages.append({'role': 'assistant', 'content': reply})
        return reply


def repl(temperature=0.8):
    """Run an interactive chat loop until Ctrl-C or end-of-input.

    Two scripted inputs produce two printed replies, and the second
    request carries the first exchange:

    >>> from unittest.mock import patch, MagicMock
    >>> sent = []
    >>> def fake_create(**kwargs):
    ...     sent.append([dict(m) for m in kwargs['messages']])
    ...     response = MagicMock()
    ...     response.choices[0].message.content = f'Arr {len(sent)}'
    ...     return response
    >>> with patch('builtins.input', side_effect=['Ahoy', 'Again', EOFError]):
    ...     with patch.object(client.chat.completions, 'create',
    ...                       side_effect=fake_create) as request:
    ...         repl(temperature=0)
    Arr 1
    Arr 2
    <BLANKLINE>
    >>> request.call_count
    2
    >>> [m['content'] for m in sent[0][1:]]
    ['Ahoy']
    >>> [(m['role'], m['content']) for m in sent[1][1:]]
    [('user', 'Ahoy'), ('assistant', 'Arr 1'), ('user', 'Again')]
    >>> request.call_args.kwargs['temperature']
    0

    Ctrl-C ends the loop cleanly:

    >>> with patch('builtins.input', side_effect=['Ahoy', KeyboardInterrupt]):
    ...     with patch.object(client.chat.completions, 'create') as request:
    ...         request.return_value.choices[0].message.content = 'Arr!'
    ...         repl(temperature=0)
    Arr!
    <BLANKLINE>

    End-of-input with no messages exits without calling the model:

    >>> with patch('builtins.input', side_effect=EOFError):
    ...     with patch.object(client.chat.completions, 'create') as request:
    ...         repl(temperature=0)
    <BLANKLINE>
    >>> request.called
    False
    """
    chat = Chat(system='You are a helpful assistant. You always speak like a pirate.')
    try:
        while True:
            user_input = input('chat> ')
            print(chat.send_message(user_input, temperature=temperature))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == '__main__':
    repl()
