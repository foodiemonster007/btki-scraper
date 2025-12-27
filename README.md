# NovelScrape
## Overview
Ever wanted to read an untranslated web novel? Well, with this tool, you can!


## Dependencies
### For Help with setting up these dependencies, go to the 'Setup' section
* Python 3.5 or later
* A chromium webdriver, such as 'chromedriver.exe' –> i.e. Install Chrome in default location
* PySide6
* Selenium
* SeleniumBase


## Notes
1. As with most python projects, creating a virtual environment is recommended
2. I have not figured out a way to bypass the Booktoki CAPTCHA, Cloudfare was easy, but Booktoki's is a letter/number recognition system. If the CAPTCHA appears it will break your script, so you must scroll up in the terminal and find the last chapter it was scraping and restart at that chapter and do the CAPTCHA yourself FOR NOW. Update coming soon!


## Setup
### INSTALL CHROME in default location

#### Installing packages
* Run 'setup.py' which checks and installs the required packages to run this program OR run these terminal commands:
```console
pip install PySide6
pip install selenium
pip install seleniumbase
pip install deep-translator
```


## How to Use
### Option One -- Run Using File Explorer
* Double click 'raw_scrape.py'

### Option Two -- Run Using Command Prompt
* Navigate to RawScrape folder in explorer, right-click and select "Open in Terminal", then type or copy/paste:
```console
py raw_scrape.py
```
### Using the Terminal/Console Edition
1. Enter the filename for your scraper settings
2. Paste a booktoki link
3. Enter a starting chapter (Default is 1)
4. Enter an ending chapter (Default is the latest release)
5. Enter your translation directory
6. Enter 'y' to start OR 'n' to close
7. Wait until the script completes AND watch out for any Booktoki CAPTCHAs
8. Check the 'scraped_novels/' directory for your novel

