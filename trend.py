import requests
import json
import csv
from datetime import datetime, timedelta
from urllib.parse import quote_plus

def get_top_wikipedia_arabic_topics(date_str, top_n=10):
    """
    Fetches the top N most viewed articles from Arabic Wikipedia for a specific date.
    
    Args:
        date_str (str): The date in 'YYYY-MM-DD' format.
        top_n (int): The number of top articles to fetch.

    Returns:
        list: A list of dictionaries, each containing an 'article' and its 'views'.
    """
    print(f"Fetching top {top_n} Wikipedia articles for {date_str}...")
    try:
        # The API requires the date to be split into year, month, and day
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year, month, day = dt.strftime('%Y'), dt.strftime('%m'), dt.strftime('%d')
        
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/ar.wikipedia/all-access/{year}/{month}/{day}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        
        top_articles = []
        # Filter out special pages and main page which often top the list
        articles = [
            item for item in data.get('items', [])[0].get('articles', [])
            if "بوابة:" not in item['article'] and "الصفحة_الرئيسية" not in item['article']
        ]

        for item in articles[:top_n]:
            top_articles.append({
                'rank': item['rank'],
                'article': item['article'].replace('_', ' '), # Use spaces for readability
                'views': item['views']
            })
            
        print("Successfully fetched Wikipedia data.")
        return top_articles
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wikipedia data: {e}")
        return []
    except (IndexError, KeyError) as e:
        print(f"Error parsing Wikipedia API response: {e}")
        return []

def search_aljazeera_for_topic(topic):
    """
    Searches Al Jazeera's Arabic website to see if a topic has been covered.

    Args:
        topic (str): The topic string to search for.

    Returns:
        bool: True if search results are found, False otherwise.
    """
    # URL-encode the search query to handle Arabic characters and spaces
    query = quote_plus(topic)
    url = f"https://www.aljazeera.net/search/{query}"
    
    print(f"Searching Al Jazeera for: {topic}...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # We use BeautifulSoup to parse the HTML content of the search results page
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Al Jazeera's search results are contained within <article> tags in a specific div.
        # If this element exists and contains articles, it means there is coverage.
        results_container = soup.find('div', {'class': 'gc-container'})
        if results_container and results_container.find('article'):
            return True
        else:
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Could not connect to Al Jazeera to search for '{topic}': {e}")
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
        # Using 'utf-8-sig' ensures Arabic characters are readable in Excel
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print("CSV file exported successfully.")


# --- Main Execution ---
if __name__ == '__main__':
    # Set the date for which you want to fetch trending topics.
    # The script defaults to yesterday as today's data may not be complete.
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # You can override with a specific date like this:
    # target_date = '2023-10-07' 
    
    # Number of top articles you want to fetch
    number_of_topics = 10
    
    trending_topics = get_top_wikipedia_arabic_topics(target_date, top_n=number_of_topics)
    
    if trending_topics:
        # Enhance the data with Al Jazeera coverage information
        for topic in trending_topics:
            # The search is done on the article title
            coverage_found = search_aljazeera_for_topic(topic['article'])
            topic['aljazeera_coverage'] = "نعم" if coverage_found else "لا"
        
        # Save the final data to JSON and CSV
        save_to_json(trending_topics, 'wikipedia_arabic_trending.json')
        export_to_csv(trending_topics, 'wikipedia_arabic_trending.csv')
        
        print("\n--- Summary ---")
        for topic in trending_topics:
            print(f"Article: {topic['article']}, Views: {topic['views']:,}, Al Jazeera Coverage: {topic['aljazeera_coverage']}")
    else:
        print("Could not retrieve trending topics. Exiting.")
