import requests
import json
import csv
import argparse
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

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
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year, month, day = dt.strftime('%Y'), dt.strftime('%m'), dt.strftime('%d')
        
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/ar.wikipedia/all-access/{year}/{month}/{day}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        top_articles = []
        articles = [
            item for item in data.get('items', [])[0].get('articles', [])
            if "بوابة:" not in item['article'] and "الصفحة_الرئيسية" not in item['article'] and "الصفحة الرئيسة" not in item['article']
            and "خاص:بحث" not in item['article'] and "تصنيف:أفلام إثارة جنسية" not in item['article'] and "تصنيف:ممثلات إباحيات أمريكيات" not in item ['article']
        ]

        for item in articles[:top_n]:
            top_articles.append({
                'rank': item['rank'],
                'article': item['article'].replace('_', ' '),
                'views': item['views']
            })
            
        print("Successfully fetched Wikipedia data.")
        return top_articles
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wikipedia data: {e}")
        return []
    except (IndexError, KeyError) as e:
        print(f"Error parsing Wikipedia API response for {date_str}. The data might not be available yet. Details: {e}")
        return []

def search_aljazeera_for_topic(topic):
    """
    Searches Al Jazeera's Arabic website to see if a topic has been covered.

    Args:
        topic (str): The topic string to search for.

    Returns:
        bool: True if search results are found, False otherwise.
    """
    query = quote_plus(topic)
    url = f"https://www.aljazeera.net/search/{query}"
    print(f"Searching Al Jazeera for: {topic}...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results_container = soup.find('div', {'class': 'gc-container'})
        return bool(results_container and results_container.find('article'))
            
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
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print("CSV file exported successfully.")

def main(date_str, top_n):
    """
    Main function to fetch, search, and save trending topics.
    """
    trending_topics = get_top_wikipedia_arabic_topics(date_str, top_n)
    
    if trending_topics:
        for topic in trending_topics:
            coverage_found = search_aljazeera_for_topic(topic['article'])
            topic['aljazeera_coverage'] = "نعم" if coverage_found else "لا"
        
        # Generate dynamic filenames
        json_filename = f"trending_{date_str}.json"
        csv_filename = f"trending_{date_str}.csv"
        
        save_to_json(trending_topics, json_filename)
        export_to_csv(trending_topics, csv_filename)
        
        print(f"\n--- Summary for {date_str} ---")
        for topic in trending_topics:
            print(f"Article: {topic['article']}, Views: {topic['views']:,}, Al Jazeera Coverage: {topic['aljazeera_coverage']}")
    else:
        print("Could not retrieve trending topics. Exiting.")

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
    
    args = parser.parse_args()
    
    # Call the main function with the provided or default arguments
    main(args.date, args.top_n)
