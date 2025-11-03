import requests
import json
import csv
import argparse
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Define exclusion patterns - easily customizable
EXCLUSION_PATTERNS = [
#--- General Exclusions ---
الصفحة_الرئيسة
خاص:بحث
]


def should_exclude_article(article_title, exclusion_patterns):
    """
    Checks if an article title contains any of the exclusion patterns.
    
    Args:
        article_title (str): The article title to check.
        exclusion_patterns (list): List of strings to exclude.
    
    Returns:
        bool: True if the article should be excluded, False otherwise.
    """
    for pattern in exclusion_patterns:
        if pattern in article_title:
            return True
    return False


def get_top_wikipedia_arabic_topics(date_str, top_n=10, exclusion_patterns=None):
    """
    Fetches the top N most viewed articles from Arabic Wikipedia for a specific date.
    
    Args:
        date_str (str): The date in 'YYYY-MM-DD' format.
        top_n (int): The number of top articles to fetch.
        exclusion_patterns (list): List of strings to exclude from results.

    Returns:
        list: A list of dictionaries, each containing an 'article' and its 'views'.
    """
    if exclusion_patterns is None:
        exclusion_patterns = EXCLUSION_PATTERNS
        
    print(f"Fetching top {top_n} Wikipedia articles for {date_str}...")
    print(f"Excluding articles containing: {', '.join(exclusion_patterns)}")
    
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year, month, day = dt.strftime('%Y'), dt.strftime('%m'), dt.strftime('%d')
        
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/ar.wikipedia/all-access/{year}/{month}/{day}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Filter articles using the exclusion function
        articles = [
            item for item in data.get('items', [])[0].get('articles', [])
            if not should_exclude_article(item['article'], exclusion_patterns)
        ]
        
        top_articles = []
        for item in articles[:top_n]:
            top_articles.append({
                'rank': item['rank'],
                'article': item['article'].replace('_', ' '),
                'views': item['views']
            })
            
        print(f"Successfully fetched {len(top_articles)} Wikipedia articles (after filtering).")
        return top_articles
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wikipedia data: {e}")
        return []
    except (IndexError, KeyError) as e:
        print(f"Error parsing Wikipedia API response for {date_str}. Data might not be available yet. Details: {e}")
        return []


def search_aljazeera_with_selenium(topic, driver):
    """
    Searches Al Jazeera's Arabic website using Selenium to handle dynamic content.

    Args:
        topic (str): The topic string to search for.
        driver: The Selenium WebDriver instance.

    Returns:
        bool: True if search results are found, False otherwise.
    """
    exact_phrase_query = f'"{topic}"'
    query = quote_plus(exact_phrase_query)
    url = f"https://www.aljazeera.net/search/{query}"
    print(f"Searching Al Jazeera for exact phrase: {exact_phrase_query}...")

    try:
        driver.get(url)
        # Wait up to 10 seconds for the search results container to appear.
        # Wait for EITHER the success element OR the no-results element.
        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".search-results__no-results"))
            )
        )
        
        # Now that we've waited, check if there are any <article> elements inside the container.
        #results_container = driver.find_element(By.CLASS_NAME, "gc-container")
        #articles = results_container.find_elements(By.TAG_NAME, "article")
        #return len(articles) > 0

        # Now, check which element was actually found.
        if driver.find_elements(By.CSS_SELECTOR, ".search-results__no-results"):
            print(f"Confirmed: No results for '{topic}'.")
            return False
        else:
            return True
            
    except TimeoutException:
        # This will be triggered if the .search-summary__query element does not appear.
        print(f"Results found for '{topic}' on Al Jazeera.")
        return True
    except WebDriverException as e:
        print(f"A browser error occurred while searching for '{topic}': {e}")
        return False


def save_to_json(data, filename):
    """Saves data to a JSON file with UTF-8 encoding."""
    print(f"Saving results to {filename}...")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("JSON file saved successfully.")


def export_to_csv(data, filename):
    """Exports a list of dictionaries to a CSV file."""
    if not data:
        print("No data to export to CSV.")
        return
        
    print(f"Exporting results to {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print("CSV file exported successfully.")


def load_exclusions_from_file(filepath):
    """
    Loads exclusion patterns from a text file (one pattern per line).
    
    Args:
        filepath (str): Path to the exclusion file.
    
    Returns:
        list: List of exclusion patterns.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"Loaded {len(patterns)} exclusion patterns from {filepath}")
        return patterns
    except FileNotFoundError:
        print(f"Exclusion file '{filepath}' not found. Using default exclusions.")
        return EXCLUSION_PATTERNS


def main(date_str, top_n, exclusion_file=None, custom_exclusions=None):
    """
    Main function to fetch, search, and save trending topics.
    
    Args:
        date_str (str): Date in YYYY-MM-DD format.
        top_n (int): Number of top articles to fetch.
        exclusion_file (str): Path to file containing exclusion patterns.
        custom_exclusions (list): Additional exclusion patterns to add.
    """
    # Determine which exclusions to use
    if exclusion_file:
        exclusions = load_exclusions_from_file(exclusion_file)
    else:
        exclusions = EXCLUSION_PATTERNS.copy()
    
    # Add any custom exclusions passed via command line
    if custom_exclusions:
        exclusions.extend(custom_exclusions)
        print(f"Added {len(custom_exclusions)} custom exclusion(s).")
    
    trending_topics = get_top_wikipedia_arabic_topics(date_str, top_n, exclusions)
    
    if not trending_topics:
        print("Could not retrieve trending topics. Exiting.")
        return

    # --- Setup Selenium WebDriver ---
    print("\nSetting up the browser for searching Al Jazeera...")
    options = FirefoxOptions()
    options.add_argument("--headless")  # Run in the background without a visible browser window
    
    try:
        driver = webdriver.Firefox(options=options)
    except WebDriverException as e:
        print(f"Failed to start browser. Ensure geckodriver is in your PATH and Firefox is installed. Error: {e}")
        return
        
    # --- Process Topics ---
    for topic in trending_topics:
        coverage_found = search_aljazeera_with_selenium(topic['article'], driver)
        topic['aljazeera_coverage'] = "نعم" if coverage_found else "لا"
    
    # --- Cleanup and Save ---
    driver.quit()  # Close the browser session
    print("\nBrowser closed.")
    
    json_filename = f"trending_{date_str}.json"
    csv_filename = f"trending_{date_str}.csv"
    
    save_to_json(trending_topics, json_filename)
    export_to_csv(trending_topics, csv_filename)
    
    print(f"\n--- Summary for {date_str} ---")
    for topic in trending_topics:
        print(f"Article: {topic['article']}, Views: {topic['views']:,}, Al Jazeera Coverage: {topic['aljazeera_coverage']}")


# --- Main Execution ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Fetch top viewed Arabic Wikipedia articles and check for Al Jazeera coverage."
    )
    
    # Set up the command-line arguments
    parser.add_argument(
        "--date", 
        type=str, 
        default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        help="The date to fetch data for in YYYY-MM-DD format. Defaults to yesterday."
    )
    
    parser.add_argument(
        "--top-n", 
        type=int, 
        default=10,
        help="The number of top articles to fetch. Defaults to 10."
    )
    
    parser.add_argument(
        "--exclusion-file",
        type=str,
        help="Path to a text file containing exclusion patterns (one per line)."
    )
    
    parser.add_argument(
        "--exclude",
        type=str,
        action='append',
        help="Add a custom exclusion pattern. Can be used multiple times."
    )
    
    args = parser.parse_args()
    
    # Call the main function with the provided or default arguments
    main(args.date, args.top_n, args.exclusion_file, args.exclude)
