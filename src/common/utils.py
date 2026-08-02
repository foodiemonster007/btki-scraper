# Imports
import sys
import os
import re
import configparser
from bs4 import BeautifulSoup, NavigableString, Tag


# === Class: OperatingSystems ===
class OperatingSystems():
  """
  Defines constants for different operating systems.
  """
  
  # === Constants ===
  WINDOWS: str = "win32"
  LINUX: str = "linux"
  MACOS: str = "darwin"


# === Class: Limits ===
class Limits():
  """
  Defines the maximum sizes of variable types in python, mainly numbers.
  """
  
  # === Constants ===
  INT_MAX: int = sys.maxsize
  INT_MIN: int = -sys.maxsize - 1

# === Function: splitRangeIntoChunks ===
def splitRangeIntoChunks(start: int, end: int, chunk_count: int) -> list[tuple[int]]:
  """
  Given a start, end, and chunk_count, create a list that defines each range of numbers

  Params:
    start: Starting number
    end: Ending number
    chunk_count: How many ways should this range be split by

  Returns:
    list[tuple[int]]: Correct ranges for each block
  """
  
  # Get the total size and the base chunk size (doesn't include the leftover odd digits)
  total: int = end - start + 1
  base_chunk: int = total // chunk_count
  remainder: int = total % chunk_count

  ranges: list[int] = [] * chunk_count
  current_starting_num = start

  for i in range(chunk_count):
    # Add one if the the current index is lower than the amount of indexes that should get a remainder
    chunk_size: int = base_chunk + (1 if i < remainder else 0)

    # Set start and end values
    start_val: int = current_starting_num
    end_val = current_starting_num + chunk_size - 1

    # Add values to the list as a tuple
    ranges.append((start, end))

    # Set new range's starting value
    current_starting_num = end + 1

  # Return properly created list
  return ranges


# === Function: createDirectory ===
def createDirectory(directory_path: str, exist_ok: bool = True) -> bool:
  """
  Attempt to create a directory

  Params:
    directory_path: Path of the directory to create
    exist_ok: The same as exist_ok in 'os.makedirs'

  Returns:
    bool: True/False of creation of the directory

  Raises:
    Exception if 'exist_ok' is False and the path is not valid/already exists
  """

  try:
    os.makedirs(directory_path, exist_ok=exist_ok)

    # If code reaches this point, no error in dir creation
    return True
  except Exception as e:
    print("Invalid output directory name.")
    return False


# === Function: formatNovelText ===
def formatNovelText(text: str) -> str:
  """
  Format a novel chapter's text to be more readable

  Params:
    text: Text to format
  
  Returns:
    str: A formatted version of the original text
  """

  # Replace weird ellipses characters with actual periods
  text = text.replace('…', '...')

  # Replace one newline with 2, for visual seperation
  text = text.replace("\n", "\n\n")

  # Return formatted text
  return text


# === Function: formatNovelTextAsMarkdown ===
def formatNovelTextAsMarkdown(html: str) -> str:
  """
  Convert a novel chapter's raw innerHTML into clean Markdown text.

  Conversion rules:
    - <em> and <i>  →  *italic*
    - <b> and <strong>  →  **bold**
    - <br>  →  newline
    - <p>  →  paragraph (double newline after closing tag)
    - Footnote inline ref  <a href="#_ftn1"  name="_ftnref1">[1]</a>  →  [^1]
    - Footnote definition  <a href="#_ftnref1" name="_ftn1">[1]</a>   →  [^1]:
    - *** or * * *  →  {sep}
    - All other HTML tags are stripped (their text content is kept)
    - HTML entities (e.g. &#8220;) are decoded to their Unicode equivalents
    - Weird ellipsis character '…' is normalised to '...'
    - Runs of more than two consecutive blank lines are collapsed to two

  Params:
    html: Raw innerHTML string from a Selenium element

  Returns:
    str: A Markdown-formatted string
  """

  def _node_to_md(node) -> str:
    """Recursively walk a BeautifulSoup node tree and emit Markdown."""

    # Plain text node — return as-is
    if isinstance(node, NavigableString):
      return str(node)

    if not isinstance(node, Tag):
      return ""

    tag = node.name.lower() if node.name else ""

    # Footnote links — must be checked before the generic anchor fallthrough.
    #
    # Two patterns used by noodlebrainsquad (and many WordPress novel themes):
    #
    #   Inline reference (in body text):
    #     <a href="#_ftn1" name="_ftnref1">[1]</a>  →  [^1]
    #
    #   Footnote definition (at bottom of chapter):
    #     <a href="#_ftnref1" name="_ftn1">[1]</a>  →  [^1]:
    #
    # The href is the reliable distinguisher:
    #   href="#_ftnN"    → inline reference → [^N]
    #   href="#_ftnrefN" → footnote definition → [^N]:
    if tag == "a":
      href = node.get("href", "")
      # Match both patterns and extract the numeric index N
      ftn_ref_match = re.match(r'^#_ftnref(\d+)$', href)   # definition anchor
      ftn_match     = re.match(r'^#_ftn(\d+)$', href)      # inline reference

      if ftn_ref_match:
        # This is the footnote definition (bottom of chapter)
        return f"[^{ftn_ref_match.group(1)}]:"
      elif ftn_match:
        # This is the inline citation (body text)
        return f"[^{ftn_match.group(1)}]"
      # Any other <a> tag: just recurse into its text, drop the link
      return "".join(_node_to_md(c) for c in node.children)

    # Block-level paragraph: recurse into children, then add blank line after
    if tag == "p":
      inner = "".join(_node_to_md(c) for c in node.children)
      inner = inner.strip()
      return inner + "\n\n" if inner else ""

    # Line break
    if tag == "br":
      return "\n"

    # Italic: <em> or <i>
    if tag in ("em", "i"):
      inner = "".join(_node_to_md(c) for c in node.children).strip()
      return f"*{inner}*" if inner else ""

    # Bold: <b> or <strong>
    if tag in ("b", "strong"):
      inner = "".join(_node_to_md(c) for c in node.children).strip()
      return f"**{inner}**" if inner else ""

    # Heading tags — treat as bold lines for novel context
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
      inner = "".join(_node_to_md(c) for c in node.children).strip()
      return f"**{inner}**\n\n" if inner else ""

    # Division / span / article / section and other containers:
    # just recurse into children transparently
    return "".join(_node_to_md(c) for c in node.children)

  # Parse with BeautifulSoup, which also handles HTML entity decoding
  # (e.g. &#8220; → ", &nbsp; → non-breaking space, etc.)
  soup = BeautifulSoup(html, "html.parser")

  # Remove ad/script/style noise that sometimes appears inside the scraped element
  for tag in soup.find_all(["script", "style", "ins", "noscript"]):
    tag.decompose()

  # Walk the tree and build markdown
  markdown = "".join(_node_to_md(node) for node in soup.children)

  # Normalise non-breaking spaces left over from &nbsp; entities
  markdown = markdown.replace("\u00a0", " ")

  # Normalise ellipsis character
  markdown = markdown.replace("…", "...")

  # Replace scene-break separators with a consistent {sep} token.
  markdown = re.sub(r'^\*[\s*]*\*[\s*]*\*$', '{sep}', markdown, flags=re.MULTILINE)

  # Collapse runs of more than 2 consecutive blank lines into 2
  markdown = re.sub(r"\n{3,}", "\n\n", markdown)

  return markdown.strip()


# === Function: getFileContentsByLine ===
def getFileContentsByLine(filepath: str, remove_newlines: bool = True) -> list[str]:
  """
  Get the contents of a file sorted by each line

  Params:
    filepath: Path to the file to read
    remove_newlines: If this value is True, then newlines willbe removed on each line
  
  Returns:
    list[str]: List containing the contents of a line per index
  """

  # If the file doesn't exist, just return an empty list
  if (not os.path.exists(filepath)):
    return []

  # Create return value
  lines: list[str] = ""

  # Read file
  with open(filepath, "r") as file:
    # Get contents of the lines
    lines = file.readlines()
  
  # Strip newline characters from each line. They are kinda redundant since
  # they are obviously a newline. If you want to write back to the file, you
  # know a line needs newlines anyways
  if (remove_newlines):
    lines = [line.strip("\n") for line in lines]

  return lines


# === Function: filerKeysFromSet ===
def filterKeysFromSet(set, exclude_list: list) -> list:
  """
  Given some set of values, remove values that are in the exclude_list

  Params:
    set: Set to get a filtered set from
    exclude_list: List of values to exclude
  """

  return [v for v in set if v not in exclude_list]

# === Function: printModuleSeparator ===
def printModuleSeparator() -> None:
  """
  Print a sepator that is useful when looking at the terminal's print history when debugging
  """

  print("\n*********************************************************\n")