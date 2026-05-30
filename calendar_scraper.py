import os
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# Initialize AI Client pointing to GitHub's free model endpoint
ai_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("AI_API_KEY")
)

TARGET_URL = "https://www.ign.com/upcoming/games"
SANDBOX_DB = "sandbox_calendar.json"

def scrape_raw_listings():
    print(f"🕵️‍♂️ Fetching raw HTML from {TARGET_URL}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: Status {response.status_code}")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # We scrape the text content of the upcoming game listings dynamically
    listings = []
    # Target common text containers inside IGN's grid layouts
    for card in soup.find_all(['div', 'a'], class_=lambda c: c and 'card' in c.lower()):
        text = card.get_text(separator=" ").strip()
        if text:
            listings.append(text)
            
    # Fallback: if class names are heavily masked, grab the readable text lines directly
    if not listings:
        listings = [line.strip() for line in soup.get_text().split('\n') if any(m in line for m in ['2026', 'May', 'June'])]

    raw_text_dump = "\n".join(listings[:100]) # Keep payload clean for the LLM
    return raw_text_dump

def parse_with_ai_agent(raw_data):
    print("🤖 AI Agent is extracting dates and titles...")
    
    prompt = f"""
    Analyze this raw scraped gaming data. Extract explicit game releases or events that have a clear date.
    
    Format your response strictly as a JSON object matching this structure:
    {{
      "YYYY-MM-DD": {{
        "gaming": [
          {{ "title": "Exact Game Title", "source": "IGN" }}
        ]
      }}
    }}
    
    If multiple events fall on the same day, group them under that single date string.
    
    Raw Scraped Text:
    {raw_data}
    """
    
    response = ai_client.chat.completions.create(
      model="gpt-4o",
      messages=[{"role": "user", "content": prompt}],
      response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def main():
    try:
        # 1. Scrape
        raw_text = scrape_raw_listings()
        
        # 2. Process through AI Agent
        extracted_events = parse_with_ai_agent(raw_text)
        
        # 3. Save to an isolated sandbox database file
        with open(SANDBOX_DB, "w") as f:
            json.dump(extracted_events, f, indent=2)
            
        print(f"✅ Success! Isolated data written to {SANDBOX_DB}")
        print(json.dumps(extracted_events, indent=2))
        
    except Exception as e:
        print(f"❌ Scraper Sandbox Error: {e}")

if __name__ == "__main__":
    main()
