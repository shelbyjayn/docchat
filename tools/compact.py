"""The compact tool, which shrinks a chat's history to a short model-written summary."""

SUMMARY_REQUEST = (
    'Summarize this conversation in at most five short lines. Keep the facts, '
    'file names, and open questions needed to continue it.'
)


def compact(chat):
    """Replace chat.messages with one entry holding a summary of at most five lines.

    >>> from unittest.mock import patch
    >>> import chat as chat_module
    >>> conversation = chat_module.Chat(system='Be brief.')
    >>> conversation.messages += [
    ...     {'role': 'user', 'content': 'Where is game night?'},
    ...     {'role': 'assistant', 'content': 'In the library.'},
    ... ]
    >>> summary = 'Game night is in the library.\\n' + '\\n'.join(f'Line {n}' for n in range(2, 9))
    >>> model = chat_module.ScriptedModel([summary])
    >>> with patch('chat.Groq', model):
    ...     print(compact(conversation))
    Game night is in the library.
    Line 2
    Line 3
    Line 4
    Line 5
    >>> len(conversation.messages)
    1
    >>> model.requests[0][-1]['content'] == SUMMARY_REQUEST
    True
    """
    from chat import llm, reply_text

    request = list(chat.messages) + [{'role': 'user', 'content': SUMMARY_REQUEST}]
    summary = reply_text(llm(request, temperature=0)).strip()
    summary = '\n'.join(summary.splitlines()[:5])
    chat.messages = [{'role': 'system', 'content': summary}]
    return summary
