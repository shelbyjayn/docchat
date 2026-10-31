"""The calculate tool, which safely evaluates a plain arithmetic expression."""

ALLOWED_CHARACTERS = set('0123456789.+-*/%() ')


def calculate(expression):
    """Evaluate an arithmetic expression and return the result as text.

    Only digits, decimal points, spaces, parentheses, and + - * / % are
    accepted, so names and function calls are rejected before eval runs.

    >>> calculate('2 + 3')
    '5'
    >>> calculate('2 * (3 + 4) - 1')
    '13'
    >>> calculate('7 / 2')
    '3.5'
    >>> calculate('17 % 5')
    '2'
    >>> calculate('1 / 0')
    'Error: division by zero'
    >>> calculate("__import__('os').system('ls')")
    "Error: invalid expression __import__('os').system('ls')"
    >>> calculate('abs(-3)')
    'Error: invalid expression abs(-3)'
    >>> calculate('9 ** 9 ** 9')
    'Error: invalid expression 9 ** 9 ** 9'
    >>> calculate('2 +')
    'Error: invalid expression 2 +'
    >>> calculate('')
    'Error: invalid expression '
    """
    expression = str(expression)
    allowed = set(expression) <= ALLOWED_CHARACTERS and '**' not in expression
    if not expression.strip() or not allowed:
        return f'Error: invalid expression {expression}'
    try:
        result = eval(expression, {'__builtins__': {}}, {})
    except ZeroDivisionError:
        return 'Error: division by zero'
    except (SyntaxError, TypeError, ValueError, OverflowError):
        return f'Error: invalid expression {expression}'
    return str(result)
