# RabbitScrape
## Overview
Ever wanted to read an untranslated web novel or scrape from your favorite novel site? Well, with this tool, you can!


## Dependencies
### For Help with setting up these dependencies, go to the 'Setup' section
* Python 3.5 or later
* A chromium webdriver, such as 'chromedriver.exe' –> i.e. Install Chrome in default location
* PySide6
* Selenium
* SeleniumBase


## Notes
1. As with most python projects, creating a virtual environment is recommended
2. Cloudflare CAPTCHA might appear in some countries, halting the code. Don't worry though, chapters are saved as you go! However, you will have to restart the code manually to continue scraping in the event of CAPTCHA.


## Setup
1. Python: This is a programming language that makes the tool work. You'll need to install it from the official website (https://www.python.org/downloads/). Make sure to check the 2 boxes that say "Add Python to PATH" and "pip" during installation. This step lets your computer easily find and run the program.
2. Install Chrome in default location
3. Double-click 'setup.py' which checks and installs the required packages to run this program OR run these terminal commands:
```console
pip install PySide6
pip install selenium
pip install seleniumbase
```


## How to Use
### Option One -- Run Using File Explorer
* Double click 'raw_scrape.py'

### Option Two -- Run Using Command Prompt
* Navigate to RawScrape folder in explorer, right-click and select "Open in Terminal", then type or copy/paste:
```console
py raw_scrape.py
```
### Using the Terminal/Console
1. Enter the filename for your scraper settings
2. choose a site source based on the .ini config files in the \cfg\scraper_settings folder.
3. Paste the target website table of contents link
4. Enter a starting chapter (Default is 1)
5. Enter an ending chapter (Default is the latest release)
6. Enter your translation directory
7. Enter 'y' to start OR 'n' to close
8. For some sites (e.g. wattpad), the code will prompt you to login
9. Wait until the script completes
10. Check the 'scraped_novels/' directory for your novel

