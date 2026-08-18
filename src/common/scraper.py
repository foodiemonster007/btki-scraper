# Imports
import time
import random
import re
import os
import configparser
from enum import Enum
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from src.common.utils import (
  Limits,
  printModuleSeparator,
  getFileContentsByLine,
  formatNovelText,
  formatNovelTextAsMarkdown
)


# === Class: Scraper ===
class Scraper():
  """
  A class that allows you to scrape chapter data from a booktoki novel page
  """


  # === Subclass: HtmlElementData ===
  class HtmlElementData():
    """
    Holds the 2 things needed call find_element() on the seleniumbase webdriver
    """


    # === Subclass: Bys ===
    class Bys():
      """
      Holds constants for an html element's type
      """

      ID: str = "id"
      CLASS_NAME: str = "class name"
      TAG_NAME: str = "tag name"
      X_PATH: str = "xpath"
      CSS_SELECTOR: str = "css selector"


    # === Subclass: Elements ===
    class Elements():
      """
      Holds constants/functions for generating HtmlElementData element names
      """

      FILL_VALUE: str = "{_VALUE_}"


      @staticmethod
      def fillElementWithValue(element: str, value: str) -> str:
        """
        Fill a slot in an element that has the string "_VALUE_" somewhere in it, which represents
        that a place should be replaced with a value at some point

        Params:
          element: String to modify
          value: Value to insert at some position

        Returns:
          str: Modified string with the value inserted in the place of the FILL_VALUE constnat
        """

        # If the fill value constant is in the string, then we should replace something
        if (Scraper.HtmlElementData.Elements.FILL_VALUE in element):
          new_element: str = element.replace(Scraper.HtmlElementData.Elements.FILL_VALUE, str(value))
          return new_element
        
        # The fill value constant wasn't present, so we just return the original value
        return element


    # === Constants ===
    BY: str = "by"
    ELEMENT: str = "element"
    BY_MAP: dict = {
      Bys.ID : By.ID,
      Bys.CLASS_NAME : By.CLASS_NAME,
      Bys.TAG_NAME : By.TAG_NAME,
      Bys.X_PATH : By.XPATH,
      Bys.CSS_SELECTOR : By.CSS_SELECTOR
    }


    # === Variables ===
    by = None # Type of element by to search this element with | NOTE: Use HtmlElement.Bys.XXX
    element: str = None # Actual element to find
  

    # === Function: applyByMap ===
    def applyByMap(self) -> None:
      """
      Apply the by map to a HtmlElementData object
      """

      self.by = self.BY_MAP.get(self.by)


  # ******************************************** #
  # ****************** Private ***************** #
  # ******************************************** #


  # === Constants ===
  # TODO: I HATE THE NAMING OF THESE VARIABLES BUT I DONT KNOW HOW TO FIX IT WITHOUT MAKING THEM VERY VAGUE
  _SCRAPER_SETTINGS_DIRECTORY_PATH: str = "cfg/scraper_settings"
  _SCRAPER_SETTINGS_CHAPTER_LIST_BODY_HTMLDATA_HEADER: str = "ChapterListBodyHtmlData"
  _SCRAPER_SETTINGS_CHAPTER_LIST_ITEM_HTMLDATA_HEADER: str = "ChapterListItemHtmlData"
  _SCRAPER_SETTINGS_NEXT_CHAPTER_BUTTON_HTMLDATA_HEADER: str = "NextChapterButtonHtmlData"
  _SCRAPER_SETTINGS_CHAPTER_TEXT_BODY_HTMLDATA_HEADER: str = "ChapterTextBodyHtmlData"
  _SCRAPER_SETTINGS_STRIP_TRAILING_PLUS_KEY: str = "strip_trailing_plus"
  _SCRAPER_SETTINGS_SCROLL_TO_BOTTOM_KEY: str = "scroll_to_bottom"
  _SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_HEADER: str = "InitialChapterLookupSettings"
  _SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_MODE_KEY: str = "mode"
  _SCRAPER_SETTINGS_CHAPTER_LIST_JAVASCRIPT_HEADER: str = "ChapterListJavaScriptData"
  _SCRAPER_SETTINGS_CHAPTER_LIST_JAVASCRIPT_SCRIPT_KEY: str = "script"
  _SCRAPER_SETTINGS_MANUAL_TOC_HTML_HEADER: str = "ManualTocHtmlData"
  _SCRAPER_SETTINGS_MANUAL_TOC_HTML_PATH_KEY: str = "path"
  _SCRAPER_SETTINGS_LOGIN_HEADER: str = "LoginSettings"
  _SCRAPER_SETTINGS_REQUIRE_MANUAL_LOGIN_KEY: str = "require_manual_login"
  _SCRAPER_SETTINGS_LOGIN_URL_KEY: str = "login_url"

  # === Subclass: InitialChapterLookupModes ===
  class InitialChapterLookupModes():
    """
    Holds constants for the supported ways of finding the URL of the starting chapter
    """

    LIST: str = "list"                    # Scrape the (fully-rendered) chapter list, indexing from the end
    DIRECT_GUESS: str = "direct_guess"     # Guess {novel_url}/chapter-{N}; ask the user if that fails
    EMBEDDED_JSON: str = "embedded_json"   # Run a JS snippet that pulls an ordered URL list out of page state
    MANUAL_HTML: str = "manual_html"       # Scrape a locally-saved copy of the (post-JS) chapter list HTML

  """ How long with nothing happening until the webpage attempts to reconnect """
  _RECONNECT_TIME: int = 6

  """ How long to wait for elements to become present/visible (e.g. waiting on JS-rendered/Alpine-hydrated content) """
  _ELEMENT_WAIT_TIME: int = 15


  # === Variables ===
  _wait = None
  _driver = None
  _novel_chapter_list_url: str = ""

  """ The HTML data when you are on the chapter list webpage that corresponds the list of chapters """
  _chapter_list_body_htmldata: HtmlElementData = HtmlElementData()

  """ The HTML data when you are on the chapter list webpage that corresponds to an actual item in the chapter list"""
  _chapter_list_item_htmldata: HtmlElementData = HtmlElementData()
  
  """ The HTML data used to go to the next chapter when on the reading page for a chapter """
  _next_chapter_button_htmldata: HtmlElementData = HtmlElementData()

  """ The HTML data for the actual text of a chapter """
  _chapter_text_body_htmldata: HtmlElementData = HtmlElementData()

  """ Strip a trailing lone '+' character from every paragraph of scraped chapter text (some
  sources, e.g. Wattpad, bake one onto the end of every paragraph's raw text) """
  _strip_trailing_plus_from_chapter_text: bool = False

  """ Whether to repeatedly scroll to the bottom of the chapter page before scraping its text.
  Some sources (e.g. Wattpad) only render/mount the rest of a chapter's content once it's been
  scrolled into view, so grabbing innerHTML right after page-load can silently cut the chapter
  short """
  _scroll_to_bottom_before_scrape: bool = False

  """ Which strategy to use for finding the starting chapter's URL | NOTE: Use InitialChapterLookupModes.XXX """
  _initial_chapter_lookup_mode: str = "list"

  """ JS snippet (mode=embedded_json only) that returns an ordered array of chapter URLs when run
  against the loaded chapter-list page """
  _chapter_list_javascript: str = ""

  """ Local file path (mode=manual_html only) to a saved, post-JavaScript copy of the chapter list page's
  HTML, scraped in place of live-fetching the chapter list """
  _manual_toc_html_path: str = ""

  """ Whether to pause and wait for the user to manually log in (in the visible browser window)
  before scraping begins """
  _require_manual_login: bool = False

  """ URL to open for the user to log in at, if _require_manual_login is set """
  _login_url: str = ""


  # === Function: _getHrefFromHtmlElement ===
  def _getHrefFromHtmlElement(self, element) -> str | None:
    """
    Get the href element embedded within an html element

    Params:
      element: Element to check
    
    Returns:
      str | None: The href element embedded within the element OR None if there is no href element
    """

    # First, search the element's inner HTML for a nested <a href="...">.
    # This is the original behavior and matches sources like booktoki,
    # where the matched element is a wrapper/button containing an inner
    # link element.
    html_content = element.get_attribute("innerHTML")
    match = re.search(r'href="(.*?)"', html_content)

    if match:
      return match.group(1)

    # Failsafe: if nothing was found inside, check whether the element
    # itself is a link and carries its own 'href' attribute directly
    # (e.g. readhive's chapter list items, where the <a> tag matched by
    # the selector IS the link, with text/icons nested inside it as
    # child elements rather than the href being nested).
    own_href = element.get_attribute("href")
    if own_href:
      return own_href

    # No href found either inside the element or on the element itself
    return None


  # === Function: _getInitialChapterUrl ===
  def _getInitialChapterUrl(self, chapter_num: int) -> str | None:
    """
    Get the url to the initial chapter to scrape

    Params:
      chapter_num: Chapter to start scraping on (If this chapter doesnt exist, this function will return None)

    Returns:
      str | None: The URL to the initial chapter to scrape OR None if the webpage doesn't exist
    """

    # Sites whose chapter list can't be indexed like a fully-rendered list (paginated/lazily
    # rendered, or the URL needs to be pulled from embedded page state / a manual HTML dump)
    # use a different lookup strategy entirely.
    if self._initial_chapter_lookup_mode == Scraper.InitialChapterLookupModes.DIRECT_GUESS:
      return self._getInitialChapterUrlByDirectGuess(chapter_num)
    if self._initial_chapter_lookup_mode == Scraper.InitialChapterLookupModes.EMBEDDED_JSON:
      return self._getInitialChapterUrlByEmbeddedJavaScript(chapter_num)
    if self._initial_chapter_lookup_mode == Scraper.InitialChapterLookupModes.MANUAL_HTML:
      return self._getInitialChapterUrlFromManualHtml(chapter_num)

    # Open web novel chapter list page
    try:
      self._driver.uc_open_with_reconnect(self.getNovelChapterListUrl(), reconnect_time=self._RECONNECT_TIME)
      self._driver.uc_gui_click_captcha()

      # --- Wait for Alpine.js to hydrate before touching the DOM ---
      # Alpine sets 'x-cloak' attributes which are removed once Alpine has
      # initialized and evaluated x-data/x-show. Tabbed content (like a
      # hash-routed "releases" tab) stays hidden via x-cloak/x-show until
      # Alpine runs, so waiting on raw element presence isn't enough; we
      # need Alpine itself to have started up.
      try:
        self._wait.until(
          lambda d: d.execute_script("return window.Alpine !== undefined && window.Alpine.version !== undefined")
        )
      except Exception as e:
        print(f"Warning: Alpine.js hydration check timed out or failed: [{e}]")

      # # Loop through each <li> element and print its data-index attribute and text
      # for i, li in enumerate(list_items):
      #   data_index = li.get_attribute("data-index")
      #   text = li.text
      #   print(f"Item {i} - data-")

      try:
        # Get the target <ul> element on the chapter list page.
        # NOTE: We wait for VISIBILITY here rather than just presence,
        # since Alpine-controlled tab content (x-show/x-cloak) can exist
        # in the DOM while still being hidden until Alpine flips the
        # tab state (e.g. via a #releases URL hash).
        list_body_params: Scraper.HtmlElementData = self.getChapterListBodyHtmlData()
        ul_element = self._wait.until(EC.visibility_of_element_located((list_body_params.by, list_body_params.element)))

        # --- Small settle delay before querying for list items ---
        # Even after the container becomes visible, Alpine may still be
        # finishing up rendering/binding child elements (x-for loops,
        # swiper sliders, etc.) on the same tick. A brief pause here
        # avoids racing that final render pass.
        settle_wait = random.uniform(1.0, 2.0)
        print(f"Waiting {settle_wait:.2f} seconds for page content to settle...")
        time.sleep(settle_wait)

        # Find all <li> elements inside that <ul>
        list_item_params: Scraper.HtmlElementData = self.getChapterListItemHtmlData()
        list_items = ul_element.find_elements(list_item_params.by, list_item_params.element)

        # If nothing was found, treat it the same as a missing element
        if not list_items:
          print("No chapter list items found.")
          return None

        # Return the link OR 'None' if it doesn't exist | NOTE: Get the Nth from the end chapter num
        # TODO: Get the ending chapter number by taking the size of the list_items array (only if it was assigned 'Limits.INT_MAX' ofc)
        return self._getHrefFromHtmlElement(list_items[-chapter_num])

      # Element not found / not visible in time
      except (NoSuchElementException, TimeoutException):
        print("No such element.")
        return None

      # Other error
      except Exception as e:
        print(f"Error: [{e}]")
        return None
    
    # Web driver was closed
    except WebDriverException:
      print("Exited WebDriver early, returning None.")
      return None


  # === Function: _getInitialChapterUrlByDirectGuess ===
  def _getInitialChapterUrlByDirectGuess(self, chapter_num: int) -> str | None:
    """
    Get the url to the initial chapter to scrape by directly guessing the chapter URL
    (novel_url/chapter-N) instead of scraping the chapter list. Used for sites whose chapter
    list is paginated/lazily rendered, so indexing into it directly isn't reliable.

    If the guessed URL doesn't resolve to a valid chapter page, the user is asked to supply
    the correct URL manually.

    Params:
      chapter_num: Chapter to start scraping on

    Returns:
      str | None: The URL to the initial chapter to scrape OR None if the user skips it
    """

    guessed_url: str = self.getNovelChapterListUrl().rstrip("/") + "/chapter-" + str(chapter_num)

    try:
      self._driver.uc_open_with_reconnect(guessed_url, reconnect_time=self._RECONNECT_TIME)
      self._driver.uc_gui_click_captcha()

      # If the chapter text body is present, the guess resolved to a real chapter page
      text_body_params: Scraper.HtmlElementData = self.getChapterTextBodyHtmlData()
      self._wait.until(EC.presence_of_element_located((text_body_params.by, text_body_params.element)))

      return guessed_url

    # Guessed URL didn't resolve to a chapter page (e.g. 404, or the chapter has a title
    # slug appended and the bare number isn't enough)
    except (NoSuchElementException, TimeoutException):
      print(f"Could not find chapter #{chapter_num} at guessed URL: {guessed_url}")

    # Web driver was closed
    except WebDriverException:
      print("Exited WebDriver early, returning None.")
      return None

    # Guess failed; ask the user for the correct URL instead
    manual_url: str = input(f"Enter the correct URL for chapter #{chapter_num} (or press Enter to skip): ")
    return manual_url if manual_url != "" else None


  # === Function: _getInitialChapterUrlByEmbeddedJavaScript ===
  def _getInitialChapterUrlByEmbeddedJavaScript(self, chapter_num: int) -> str | None:
    """
    Get the url to the initial chapter to scrape by running a JS snippet (configured via
    ChapterListJavaScriptData) against the loaded chapter-list page. The snippet is expected to
    return an array of chapter URLs, in ascending chapter order, pulled directly out of the
    page's own embedded state (e.g. a server-rendered hydration payload) rather than scraped
    from rendered/paginated DOM elements. Used for sites like Wattpad, which embed the full,
    already-ordered chapter list as JSON in the initial page load.

    Params:
      chapter_num: Chapter to start scraping on (1-indexed)

    Returns:
      str | None: The URL to the initial chapter to scrape OR None if it couldn't be found
    """

    try:
      self._driver.uc_open_with_reconnect(self.getNovelChapterListUrl(), reconnect_time=self._RECONNECT_TIME)
      self._driver.uc_gui_click_captcha()

      chapter_urls: list = self._driver.execute_script(self._chapter_list_javascript)

      if not chapter_urls:
        print("Embedded chapter list script returned no chapters.")
        return None

      if chapter_num < 1 or chapter_num > len(chapter_urls):
        print(f"Chapter #{chapter_num} is out of range (found {len(chapter_urls)} chapters).")
        return None

      return chapter_urls[chapter_num - 1]

    # Web driver was closed
    except WebDriverException:
      print("Exited WebDriver early, returning None.")
      return None

    # JS execution failed, or returned something unexpected
    except Exception as e:
      print(f"Error extracting embedded chapter list: [{e}]")
      return None


  # === Function: _getInitialChapterUrlFromManualHtml ===
  def _getInitialChapterUrlFromManualHtml(self, chapter_num: int) -> str | None:
    """
    Get the url to the initial chapter to scrape by loading a locally-saved copy of the chapter
    list page's (post-JavaScript) HTML instead of live-fetching it. Path is configured via
    ManualTocHtmlData. Useful for sites whose rendered chapter list can't be reliably captured
    live -- open the chapter list page in a normal browser, save its fully-rendered HTML source
    to a file, and point the settings file at it.

    Uses the same ChapterListBodyHtmlData/ChapterListItemHtmlData selectors and Nth-from-end
    indexing as the default list-scraping mode.

    Params:
      chapter_num: Chapter to start scraping on

    Returns:
      str | None: The URL to the initial chapter to scrape OR None if it couldn't be found
    """

    if not self._manual_toc_html_path or not os.path.isfile(self._manual_toc_html_path):
      print(f"Manual TOC HTML file not found: {self._manual_toc_html_path}")
      return None

    file_url: str = "file:///" + os.path.abspath(self._manual_toc_html_path).replace("\\", "/")

    try:
      self._driver.get(file_url)

      list_body_params: Scraper.HtmlElementData = self.getChapterListBodyHtmlData()
      ul_element = self._wait.until(EC.presence_of_element_located((list_body_params.by, list_body_params.element)))

      list_item_params: Scraper.HtmlElementData = self.getChapterListItemHtmlData()
      list_items = ul_element.find_elements(list_item_params.by, list_item_params.element)

      if not list_items:
        print("No chapter list items found in manual TOC HTML.")
        return None

      return self._getHrefFromHtmlElement(list_items[-chapter_num])

    # Element not found / not visible in time
    except (NoSuchElementException, TimeoutException):
      print("No such element in manual TOC HTML.")
      return None

    # Web driver was closed
    except WebDriverException:
      print("Exited WebDriver early, returning None.")
      return None


  # === Function: _findNextChapterUrl ===
  def _findNextChapterUrl(self) -> str | None:
    """
    Get the URL for the next chapter button. Use when on a chapter page.

    Returns:
      str | None: The URL to the initial chapter to scrape OR None if the webpage doesn't exist
    """

    # Get the params to be used in 'find_element'
    data_params: Scraper.HtmlElementData = self.getNextChapterButtonHtmlData()

    try:
      # Get the target element
      target_element = self._driver.find_element(data_params.by, data_params.element)

      # Return the link OR 'None' if it doesn't exist
      return self._getHrefFromHtmlElement(target_element)
    # Element not found
    except NoSuchElementException:
      print("No such element.")
      return None

    except Exception as e:
      # If there is no such element, print the error and return 'None'
      print(f"Error: {e}")
      return None


  # === Function: _scrollToBottomOfPage ===
  def _scrollToBottomOfPage(self, max_iterations: int = 25, stable_iterations_required: int = 3, pause_seconds: float = 0.8) -> None:
    """
    Repeatedly scroll the current page to the bottom, waiting between scrolls, so that any
    content which only mounts/renders once scrolled into view (lazy-loaded/virtualized content)
    has a chance to load before the page is scraped. Stops once the page's scroll height stops
    growing for a few scrolls in a row (i.e. there's nothing left to reveal), or after
    max_iterations as a safety cap.

    Params:
      max_iterations: Hard cap on the number of scroll attempts
      stable_iterations_required: How many consecutive scrolls with no height change before stopping
      pause_seconds: How long to wait after each scroll for new content to render
    """

    previous_height: int = -1
    stable_count: int = 0

    for _ in range(max_iterations):
      self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
      time.sleep(pause_seconds)

      current_height: int = self._driver.execute_script("return document.body.scrollHeight;")

      if current_height == previous_height:
        stable_count += 1
        if stable_count >= stable_iterations_required:
          break
      else:
        stable_count = 0

      previous_height = current_height


  # === Function: _scrapeChapter ===
  def _scrapeChapter(self, url: str) -> str | None:
      """
      Does the actual scraping of chapter data. Utilizes '_chapter_text_body_htmldata'

      Params:
        url: Url to scrape data from

      Returns:
        str OR None: The URL to the initial chapter to scrape OR None if the webpage doesn't exist
      """
      
      try:
          self._driver.uc_open_with_reconnect(url, reconnect_time=self._RECONNECT_TIME)
          self._driver.uc_gui_click_captcha()

          # --- Random wait AFTER page load, before scraping ---
          wait_after_load = random.uniform(5.0, 10.0)
          print(f"Waiting {wait_after_load:.2f} seconds after page load before scraping...")
          time.sleep(wait_after_load)

          # Some sources only mount/render the rest of a chapter's content once it's been
          # scrolled into view (e.g. Wattpad), so force that content to load before scraping
          if self._scroll_to_bottom_before_scrape:
            self._scrollToBottomOfPage()

          # Get the params to be used in 'find_elements'
          data_params: Scraper.HtmlElementData = self.getChapterTextBodyHtmlData()

          try:
              # Get the target element(s). Using find_elements (plural) instead of a single
              # find_element lets a selector match several separate content blocks (e.g.
              # Wattpad splits one chapter's text across multiple '.page' containers) -- their
              # innerHTML is concatenated in document order. For sources with a selector that
              # matches exactly one wrapping container (the common case), this is identical to
              # the old single-element behavior.
              elements = self._driver.find_elements(data_params.by, data_params.element)

              if not elements:
                  print("No such element.")
                  return None

              # Return the raw innerHTML rather than .text so that inline HTML tags (<em>, <i>,
              # <b>, <strong>, <br>, <p> etc.) are preserved for downstream markdown conversion.
              # formatNovelTextAsMarkdown() will parse these into Markdown syntax; the plain
              # formatNovelText() path (for old sources) still works because it receives .text
              # from the caller's own branch.
              return "".join(element.get_attribute("innerHTML") for element in elements)

          except Exception as e:
              # If there is no such element, print the error and return 'None'
              print(f"Error: {e}")
              return None

      # Web driver was closed
      except WebDriverException:
          print("Exited WebDriver early, returning None.")
          return None
    

  # ******************************************** #
  # ****************** Public ****************** #
  # ******************************************** #


  # === Function: __init__ ===
  def __init__(self, novel_url: str = "", scraper_settings_filename: str = "booktoki.ini") -> None:
    """
    Constructor -> Sets novel chapter list url and elements to check now

    Args:
      novel_url: Url of the novel's chapter list to scrape
      scraper_settings_filename: Name of the scraper settings file to load on construction.
        Defaults to 'booktoki.ini' if not provided, preserving prior behavior.
    """

    # Load the requested settings (or the default, if none was given)
    self.loadScraperSettings(scraper_settings_filename)

    self.setNovelChapterListUrl(novel_url)


  # === Function: initializeWebDriver ===
  def initializeWebDriver(self) -> None:
    """
    Initialize the web driver object
    """

    self._driver = Driver(uc=True, headless=False)
    self._wait = WebDriverWait(self._driver, self._ELEMENT_WAIT_TIME)
  

  # === Function: uninitializeWebDriver ===
  def uninitializeWebDriver(self) -> None:
    """
    Reset the driver object to null to reset/close the browser session
    """
    
    self._driver.close()
    self._driver = None
    self._wait = None
  

  # === Function: loadScraperSettings ===
  def loadScraperSettings(self, filename: str, path_override: bool = False) -> None:
    """
    Loads in settings from a file

    Params:
      filename: Name of the file to load from
      path_override: If this value is "True" then the filename is assumed to be the full path
    """
    
    # Print a module separator
    printModuleSeparator()

    # Log filename
    print(f'Loading Scraper Settings: "{filename}"\n')

    # Get full file path
    full_file_path: str = ""
    if (path_override):
      # If true, then the filename is the full path
      full_file_path += filename
    else:
      # If false(default value), then the filename is just the name of the file that is in the expected location
      full_file_path += self._SCRAPER_SETTINGS_DIRECTORY_PATH + "/" + filename

    # Get the line data of the file
    config = configparser.ConfigParser()
    config.read(full_file_path)

    # Get sections
    chapter_list_body_section = config[Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_BODY_HTMLDATA_HEADER]
    chapter_list_item_section = config[Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_ITEM_HTMLDATA_HEADER]
    next_chapter_button_section = config[Scraper._SCRAPER_SETTINGS_NEXT_CHAPTER_BUTTON_HTMLDATA_HEADER]
    text_body_section = config[Scraper._SCRAPER_SETTINGS_CHAPTER_TEXT_BODY_HTMLDATA_HEADER]

    # List body
    self._chapter_list_body_htmldata.by = chapter_list_body_section.get(Scraper.HtmlElementData.BY).strip('"')
    self._chapter_list_body_htmldata.element = chapter_list_body_section.get(Scraper.HtmlElementData.ELEMENT).strip('"')

    # List item
    self._chapter_list_item_htmldata.by = chapter_list_item_section.get(Scraper.HtmlElementData.BY).strip('"')
    self._chapter_list_item_htmldata.element = chapter_list_item_section.get(Scraper.HtmlElementData.ELEMENT).strip('"')

    # Next chapter button
    self._next_chapter_button_htmldata.by = next_chapter_button_section.get(Scraper.HtmlElementData.BY).strip('"')
    self._next_chapter_button_htmldata.element = next_chapter_button_section.get(Scraper.HtmlElementData.ELEMENT).strip('"')

    # Text body
    self._chapter_text_body_htmldata.by = text_body_section.get(Scraper.HtmlElementData.BY).strip('"')
    self._chapter_text_body_htmldata.element = text_body_section.get(Scraper.HtmlElementData.ELEMENT).strip('"')

    strip_trailing_plus_raw = text_body_section.get(Scraper._SCRAPER_SETTINGS_STRIP_TRAILING_PLUS_KEY)
    self._strip_trailing_plus_from_chapter_text = (
      strip_trailing_plus_raw is not None and strip_trailing_plus_raw.strip('"').strip().lower() in ("1", "yes", "true", "on")
    )

    scroll_to_bottom_raw = text_body_section.get(Scraper._SCRAPER_SETTINGS_SCROLL_TO_BOTTOM_KEY)
    self._scroll_to_bottom_before_scrape = (
      scroll_to_bottom_raw is not None and scroll_to_bottom_raw.strip('"').strip().lower() in ("1", "yes", "true", "on")
    )

    # Initial chapter lookup method (optional section; defaults to the old list-scraping behavior
    # for settings files that don't define it)
    self._initial_chapter_lookup_mode = Scraper.InitialChapterLookupModes.LIST
    if config.has_section(Scraper._SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_HEADER):
      initial_chapter_lookup_section = config[Scraper._SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_HEADER]
      mode_raw = initial_chapter_lookup_section.get(Scraper._SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_MODE_KEY)
      if mode_raw is not None:
        self._initial_chapter_lookup_mode = mode_raw.strip('"').strip().lower()

    # JS snippet used to pull the chapter list directly out of page state (mode=embedded_json only)
    self._chapter_list_javascript = ""
    if config.has_section(Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_JAVASCRIPT_HEADER):
      chapter_list_javascript_section = config[Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_JAVASCRIPT_HEADER]
      script_raw = chapter_list_javascript_section.get(Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_JAVASCRIPT_SCRIPT_KEY)
      if script_raw is not None:
        self._chapter_list_javascript = script_raw.strip('"')

    # Local file path to a manually-saved copy of the chapter list page's HTML (mode=manual_html only)
    self._manual_toc_html_path = ""
    if config.has_section(Scraper._SCRAPER_SETTINGS_MANUAL_TOC_HTML_HEADER):
      manual_toc_html_section = config[Scraper._SCRAPER_SETTINGS_MANUAL_TOC_HTML_HEADER]
      path_raw = manual_toc_html_section.get(Scraper._SCRAPER_SETTINGS_MANUAL_TOC_HTML_PATH_KEY)
      if path_raw is not None:
        self._manual_toc_html_path = path_raw.strip('"')

    # Whether to pause for a manual login before scraping starts (optional section; defaults to
    # off for settings files that don't define it)
    self._require_manual_login = False
    self._login_url = ""
    if config.has_section(Scraper._SCRAPER_SETTINGS_LOGIN_HEADER):
      login_section = config[Scraper._SCRAPER_SETTINGS_LOGIN_HEADER]
      require_manual_login_raw = login_section.get(Scraper._SCRAPER_SETTINGS_REQUIRE_MANUAL_LOGIN_KEY)
      if require_manual_login_raw is not None:
        self._require_manual_login = require_manual_login_raw.strip('"').strip().lower() in ("1", "yes", "true", "on")
      login_url_raw = login_section.get(Scraper._SCRAPER_SETTINGS_LOGIN_URL_KEY)
      if login_url_raw is not None:
        self._login_url = login_url_raw.strip('"')

    # Print results
    print(f"[{Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_BODY_HTMLDATA_HEADER}]: "
          f'\n{Scraper.HtmlElementData.BY} = "{self._chapter_list_body_htmldata.by}"'
          f'\n{Scraper.HtmlElementData.ELEMENT} = "{self._chapter_list_body_htmldata.element}"'
           "\n")
    
    print(f"[{Scraper._SCRAPER_SETTINGS_CHAPTER_LIST_ITEM_HTMLDATA_HEADER}]: "
          f'\n{Scraper.HtmlElementData.BY} = "{self._chapter_list_item_htmldata.by}"'
          f'\n{Scraper.HtmlElementData.ELEMENT} = "{self._chapter_list_item_htmldata.element}"'
          "\n")
    
    print(f"[{Scraper._SCRAPER_SETTINGS_NEXT_CHAPTER_BUTTON_HTMLDATA_HEADER}]: "
          f'\n{Scraper.HtmlElementData.BY} = "{self._next_chapter_button_htmldata.by}"'
          f'\n{Scraper.HtmlElementData.ELEMENT} = "{self._next_chapter_button_htmldata.element}"'
          "\n")
    
    print(f"[{Scraper._SCRAPER_SETTINGS_CHAPTER_TEXT_BODY_HTMLDATA_HEADER}]: "
          f'\n{Scraper.HtmlElementData.BY} = "{self._chapter_text_body_htmldata.by}"'
          f'\n{Scraper.HtmlElementData.ELEMENT} = "{self._chapter_text_body_htmldata.element}"'
          "\n")

    print(f"[{Scraper._SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_HEADER}]: "
          f'\n{Scraper._SCRAPER_SETTINGS_INITIAL_CHAPTER_LOOKUP_MODE_KEY} = "{self._initial_chapter_lookup_mode}"'
          "")
    
    # Apply the by map
    self._chapter_list_body_htmldata.applyByMap()
    self._chapter_list_item_htmldata.applyByMap()
    self._next_chapter_button_htmldata.applyByMap()
    self._chapter_text_body_htmldata.applyByMap()

    # Print a module separator
    printModuleSeparator()


  # === Function: saveScraperSettings ===
  def saveScraperSettings(self, filename: str) -> None:
    """
    Saves scraper settings into a file

    Params:
      filename: Name of the file that contains the scraper settings. This will be located in the 'self._SCRAPER_SETTINGS_FOLDER' directory
    """

    full_file_path: str = self._SCRAPER_SETTINGS_DIRECTORY_PATH + "/" + filename

    # TODO: Implment -> Save the current element data in the file


  # === Function: scrape ===
  def scrape(self, start_idx: int = 0, end_idx: int = Limits.INT_MAX, format_text: bool = True, output_directory: str = None) -> list[str]:
      """
      Starts the scraping of a booktoki novel.

      NOTE: Must have called these functions:
        'setNovelUrl()'

      Args:
        start_idx: Chapter number to start the scrape.    NOTE: Constraints: (start_idx <= end_idx)
        end_idx: Chapter to end the scrape at.    NOTE: Constraints: (end_idx >= start_idx)
        format_text: Should the text be formatted into a more readable form (extra whitespaces, replace some characters, etc.)?
        output_directory: Directory to save chapters to. If provided, chapters will be saved immediately.

      Returns:
        list[str]: List of the scraped novel chapters (if output_directory is None)
      """
      
      # Setup driver
      self.initializeWebDriver()

      # If configured, open a login page in the (visible) browser window and block here until
      # the user confirms they've logged in, before any scraping begins. Some sources (e.g.
      # Wattpad) serve a shorter/gated version of chapter content to anonymous sessions.
      if self._require_manual_login:
        if self._login_url:
          self._driver.uc_open_with_reconnect(self._login_url, reconnect_time=self._RECONNECT_TIME)
        printModuleSeparator()
        input("Log in using the opened browser window, then press Enter here to continue scraping...")
        printModuleSeparator()

      # Check if the proper variables have been instantiated
      if (self.getNovelChapterListUrl() == ""):
        return []

      # Enforce index constraints
      if (end_idx < start_idx):
        end_idx = start_idx

      # Print module separator
      printModuleSeparator()

      # Log starting message
      print(
        "Starting Scrape With Parameters: \n"
        "\tNovel Url: " + self.getNovelChapterListUrl() + "\n"
        "\tStarting Chapter: " + str(start_idx) + "\n"
        "\tEnding Chapter: " + str(end_idx) + "\n"
        "\tText Formatting: " + str(format_text) + "\n"
        "\tOutput Directory: " + (output_directory if output_directory else "Not saving to files") + "\n"
      )

      # Create empty container for each chapter's text data (if returning list)
      chapter_text: list[str] = []
      
      # Get the url for the first chapter
      curr_url: str = self._getInitialChapterUrl(start_idx)

      # Scrape each chapter in the specified range
      for chapter_num in range (int(start_idx), int(end_idx) + 1):
        # If the chapter url doesn't exist, leave loop to prevent errors
        if (curr_url == None): 
          print(f"No URL found for chapter #{chapter_num}. Stopping.")
          break

        # Log chapter scraping progress
        print(f"Scraping chapter #{chapter_num}...")

        # Get the text for this chapter
        curr_chapter_text: str = self._scrapeChapter(curr_url)

        # Format text, if set.
        # Always uses Markdown formatting now: converts inline HTML tags
        # (<em>/<i> → *italic*, <b>/<strong> → **bold**, etc.) and
        # escapes square brackets. Falls back to plain text formatting
        # only if the markdown formatter itself fails for any reason.
        if (format_text and curr_chapter_text):
          try:
            curr_chapter_text = formatNovelTextAsMarkdown(curr_chapter_text, strip_trailing_plus=self._strip_trailing_plus_from_chapter_text)
          except Exception as e:
            print(f"Warning: Markdown formatting failed ({e}), falling back to plain text formatting.")
            curr_chapter_text = formatNovelText(curr_chapter_text)

        # Check if we got data
        if (curr_chapter_text == None): 
          print(f"No data received for chapter #{chapter_num}. Stopping.")
          break

        # Save chapter immediately if output_directory is provided
        if output_directory and curr_chapter_text:
          chapter_num_str: str = str(chapter_num).zfill(4)
          filename: str = f"{output_directory}/{chapter_num_str}.md"
          
          try:
            with open(filename, "w", encoding="utf-8") as f:
              f.write(curr_chapter_text)
            print(f"Saved chapter #{chapter_num} to {filename}")
          except Exception as e:
            print(f"Error saving chapter #{chapter_num}: {e}")

        # --- Fixed 1‑second wait AFTER scraping this chapter (including last) ---
        wait_after = 1.0
        print(f"Waiting {wait_after:.2f} seconds before moving to next URL...")
        time.sleep(wait_after)

        # Get the next chapter's URL
        curr_url = self._findNextChapterUrl()

      # Close driver
      self.uninitializeWebDriver()

      # Log the scrape's completion
      print("\nScraping Complete!")

      # Print module separator
      printModuleSeparator()

      # Return the chapter data (if not saving to files)
      return chapter_text
  

  # ******************************************** #
  # ************** Getters/Setters ************* #
  # ******************************************** #


  # === Function: setNovelChapterListUrl ===
  def setNovelChapterListUrl(self, value: str) -> None:
    """
    Sets the url to the booktoki novel you want to scrape chapter data from

    Args:
      value: Url to the booktoki novel you wish to scrape
    """
    self._novel_chapter_list_url = value
  

  # === Function: getNovelChapterListUrl ===
  def getNovelChapterListUrl(self) -> str:
    """
    Gets the novel url set in a 'Scraper' object

    Returns:
      str: Url to the booktoki novel you wish to scrape
    """
    return self._novel_chapter_list_url


  # # === Function: setThreadCount ===
  # def setThreadCount(self, thread_count: int = None) -> None:
  #   """
  #   Set the number of threads to be used when scraping the novel

  #   Params:
  #     thread_count: New thread count for the scraper
  #   """
  #   self._thread_count = thread_count


  # # === Function: getThreadCount ===
  # def getThreadCount(self) -> int:
  #   """
  #   Get the number of threads to be used when scraping the novel

  #   Returns:
  #     int: The thread count for the scraper
  #   """
  #   return self._thread_count


  # === Function: setChapterListBodyHtmlData ===
  def setChapterListBodyHtmlData(self, by, element: str) -> None:
    """
    Set the HTML data that points to the chapter list body's html data

    Params:
      by: The element type to search for
      element: The element's name ('button.open-menu', 'db.cs-rm', etc.)
    """

    self._chapter_list_body_htmldata.by = by
    self._chapter_list_body_htmldata.element = element


  # === Function: getChapterListBodyHtmlData ===
  def getChapterListBodyHtmlData(self) -> HtmlElementData:
    """
    Get the HTML data that points to a list body

    Returns:
      HtmlElementData: Data structure that outlines the html element that corresponds to the 'chapter list body'
    """

    return self._chapter_list_body_htmldata
  

  # === Function: setChapterListItemHtmlData ===
  def setChapterListItemHtmlData(self, by, element: str) -> None:
    """
    Set the HTML data that points to the chapter list item's html data

    Params:
      by: The element type to search for
      element: The element's name ('button.open-menu', 'db.cs-rm', etc.)
    """

    self._chapter_list_item_htmldata.by = by
    self._chapter_list_item_htmldata.element = element


  # === Function: getChapterListItemHtmlData ===
  def getChapterListItemHtmlData(self) -> HtmlElementData:
    """
    Get the HTML data that points to a list item

    Returns:
      HtmlElementData: Data structure that outlines the html element that corresponds to the 'chapter list item'
    """

    return self._chapter_list_item_htmldata


  # === Function: setNextChapterButtonHtmlData ===
  def setNextChapterButtonHtmlData(self, by, element: str) -> None:
    """
    Set the HTML data that points to the next chapter button on a chapter page

    Params:
      by: The element type to search for
      element: The element's name ('button.open-menu', 'db.cs-rm', etc.)
    """

    self._next_chapter_button_htmldata.by = by
    self._next_chapter_button_htmldata.element = element


  # === Function: getNextChapterButtonHtmlData ===
  def getNextChapterButtonHtmlData(self) -> HtmlElementData:
    """
    Get the HTML data that points to the next chapter button on a chapter page

    Returns:
      HtmlElementData: Data structure that outlines the html element that corresponds to the 'next chapter button'
    """

    return self._next_chapter_button_htmldata


  # === Function: setChapterTextBodyHtmlData ===
  def setChapterTextBodyHtmlData(self, by, element: str) -> None:
    """
    Set the HTML data that points to the text of an actual chapter

    Params:
      by: The element type to search for
      element: The element's name ('button.open-menu', 'db.cs-rm', etc.)
    """

    self._chapter_text_body_htmldata.by = by
    self._chapter_text_body_htmldata.element = element


  # === Function: getChapterTextBodyHtmlData ===
  def getChapterTextBodyHtmlData(self) -> HtmlElementData:
    """
    Get the HTML data that points to the text of an actual chapter

    Returns:
      HtmlElementData: Data structure that outlines the html element that corresponds to the 'chapter text body'
    """
    return self._chapter_text_body_htmldata