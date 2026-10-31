# docchat

`chat` is a command-line assistant that answers questions about the files in the folder where you start it. The model can list, read, and search those files with built-in `ls`, `cat`, and `grep` tools, do arithmetic with `calculate`, and you can run any tool yourself with a slash command such as `/ls .`.

## Install

```
python -m pip install -e . -r requirements.txt
```

Put your Groq key in a `.env` file in this repository:

```
GROQ_API_KEY=gsk_your_key_goes_here
```

## Usage

```
chat                      # interactive session
chat "what does main.py do?"   # one question, one answer
chat --debug              # also print each tool the model calls
```

Inside a session, `/ls [folder]`, `/cat file`, `/grep regex glob`, and `/calculate expression` run a tool directly without contacting the model, and the output is added to the conversation. `/compact` replaces the history with a short summary, and `/load_image picture.png` attaches a PNG. The tools only read files inside the starting folder: absolute paths and paths containing `..` are rejected. Press Ctrl+D or Ctrl+C to quit.

## Examples

### Personal webpage

````
$ cd test_projects/lab-homepage
$ chat
chat> /ls .
1536x864_cmsv2_6fd6c015-be60-5aea-a95f-0975fb6f91c7-9075866.webp
2015-08-12T120000Z_1336851902_GF10000171595_RTRMADP_3_TAIWAN-MILITARY-1-e1616647968961.webp
README.md
defense-banner.jpg
emerging-trends.html
index.html
market-policy.html
style.css
submission.toml
chat> what pages does this website have, and what is each one about?
Arrr, matey! Here be the map of this web‑deck and what each of its sails be carrying:

| Page | URL | What it be talkin' about |
|------|-----|--------------------------|
| **Home** | `index.html` | The grand welcome port – an overview of how the U.S. defense industry be shifting, a shout‑out to the newest tech‑savvy startups (Anduril, Shield AI, Palantir, etc.), and a quick tour of the site. |
| **Market & Policy** | `market-policy.html` | The trade winds of procurement – explains how the Pentagon's buying habits are changing (DIU, Replicator, direct buys) and how venture capital is now pouring into defense, reshaping the market. |
| **Emerging Trends** | `emerging-trends.html` | The future horizon – highlights key tech trends like autonomous drone swarms, AI‑driven electronic warfare, VR training, and the rise of counter‑drone tech. |

These three HTML files are the actual web pages. The other files (`style.css`, images, `README.md`, `submission.toml`) are just the deck's rigging and paperwork. So, ye've got a three‑page site that charts the seas of modern defense tech, the shifting market, and the trends that be steering the future. Arrr!
````

The model found the three HTML pages on its own and summarized each one correctly; the site covers the shifting defense industry, Pentagon procurement and venture funding, and emerging technology such as drone swarms and counter-drone systems.

### Markdown compiler

````
$ cd test_projects/markdown-compiler
$ chat
chat> /ls .
README.md
example
markdown_compiler
pyproject.toml
requirements.txt
submission.toml
chat> how are headings converted?
Ahoy, matey! 🎩🦜
Let's spin the yarn of how the Markdown compiler turns those "#" signs into proper HTML header tags.

---

### 1. The `compile_headers` function – the treasure map

```python
def compile_headers(line):
    '''
    Convert markdown headers into <h1>,<h2>,etc tags.
    ...
    '''
    for n in range(6, 0, -1):
        if line[:n] == '#' * n:
            return '<h' + str(n) + '>' + line[n:] + '</h' + str(n) + '>'
    return line
```

#### How it works
1. **Loop from 6 down to 1** – the highest‑level header (`######`) to the lowest (`#`).
2. **Check the start of the line** – if the first *n* characters are exactly *n* `#` symbols, we've found a header level *n*.
3. **Wrap the rest of the line** (everything after those `#` symbols) in the corresponding `<hN>` tag.
4. **If no header is detected** – return the line unchanged.

#### Edge‑case handling
- Leading spaces before the `#` mean it's **not** a header.
  Example: `"      # this is not a header"` → unchanged.
- Only the exact number of `#` at the very start qualifies.

#### Quick examples
```python
compile_headers('# This is the main header')
# '<h1> This is the main header</h1>'

compile_headers('## This is a sub-header')
# '<h2> This is a sub-header</h2>'

compile_headers('   # nope')
# '   # nope'   (spaces keep it from being a header)
```

---

### 2. Where it fits in the big picture

- **`markdown_compiler/__init__.py`** calls `compile_headers` at the very start of `compile_inline(line)`.
- That means every line is first checked for a header before any other inline formatting (bold, italic, links, etc.) is applied.
- Headers are *not* wrapped in `<p>` tags; they're rendered as standalone heading elements.

---

### 3. Bottom line

The compiler looks for a run of `#` characters at the **very beginning** of a line.
The number of `#` determines the heading level (`1` → `<h1>`, `2` → `<h2>`, …, `6` → `<h6>`).
If the line doesn't start with a `#`, it just stays as it is (unless other inline rules kick in).

That's the secret of heading conversion, ye scallywag! 🚢💀
````

The model located `compile_headers` and explained that the compiler checks for one to six `#` characters at the very start of a line, picks the heading level from the count, and leaves lines with leading spaces unchanged.

### eBay scraper

````
$ cd test_projects/ebay-scraper
$ chat
chat> /ls .
README.md
digital camera.csv
digital camera.json
ebay-dl.py
film camera.csv
film camera.json
practice-pages
submission.toml
tripod.csv
tripod.json
chat> what fields does ebay-dl.py save for each item?
Arrr! Ye be askin' what treasures the `ebay-dl.py` be stashin' for each item it scours from the web.  The script keeps the following booty in its output:

| Field name      | What it holds |
|-----------------|----------------|
| **name**        | The item's title – what the seller calls it. |
| **price**       | The price in *cents* (so $12.50 becomes 1250). |
| **status**      | The listing status – e‑g, "Currently Auction", "Buy It Now", "Sold", etc. |
| **shipping**    | Shipping cost in cents, or `0` if it be free.  `None` if the info is missing. |
| **free_returns**| `True` if the listing offers free returns, `False` if not, or `None` if the info wasn't found. |
| **items_sold**  | How many of that item have been sold (parsed from the hot‑ness string).  `None` if the data can't be read. |

When you run it with `--csv` it writes a CSV with those six columns; without `--csv` it dumps a JSON array of objects each containing the same keys. That's the haul the script leaves behind.  Arrr!
````

The model read `ebay-dl.py` and listed the six fields the scraper saves for each listing; prices and shipping are stored in cents, missing values become `None`, and the `--csv` flag switches the output from JSON to CSV.

## Testing

```
python -m pytest --doctest-modules tools chat.py
python -m coverage run --source=tools -m pytest --doctest-modules tools
python -m coverage report -m
python -m flake8 chat.py tools --ignore=E501
```

The doctests use an offline stand-in for the model, so they never need an API key.
