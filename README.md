# docchat

A command-line chatbot that talks like a pirate and remembers the conversation. It sends each message, along with the earlier history, to a model on Groq.

## Install

    python -m pip install .

Put your Groq key in a `.env` file in the folder where you run the command:

    GROQ_API_KEY=gsk_your_key_goes_here

## Use

Run `chat` and type at the `chat>` prompt. Press Ctrl+C or Ctrl+D to quit.

## Test

    python -m pytest chat.py --doctest-modules

The doctests replace the API call with a fake, so they run offline.
