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
    
    # Highly specific text cleaner to keep token count minimal
    clean_lines = []
    for item in soup.find_all(['h3', 'div', 'span', 'p']):
        text = item.get_text().strip()
        # Only extract lines that contain valid game names or 2026 calendar months
        if text and any(m in text for m in ['2026', 'May', 'June', 'July', 'Release']):
            if len(text) < 100 and text not in clean_lines:
                clean_lines.append(text)
            
    # Fallback to broad filtering if specific elements aren't caught
    if not clean_lines:
        clean_lines = [line.strip() for line in soup.get_text().split('\n') if any(m in line for m in ['2026', 'May', 'June'])]

    # Keep a strict limit on content size to protect the 8,000 token limit
    final_payload = "\n".join(clean_lines[:40])
    print(f"📉 Optimized payload size down to {len(final_payload)} characters.")
    return final_payload

def parse_with_ai_agent(raw_data):
    print("🤖 AI Agent is extracting dates and titles via GitHub Models...")
    
    prompt = f"""
    Extract game releases with explicit dates from the following text fragment.
    
    Format your response strictly as a single JSON object matching this structure:
    {{
      "2026-05-28": {{
        "gaming": [
          {{ "title": "Pictonico!", "source": "IGN" }}
        ]
      }}
    }}
    
    Raw text to process:
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
        # 1. Scrape clean rows
        raw_text = scrape_raw_listings()
        
        if not raw_text.strip():
            raise Exception("No readable text structure extracted from targeted elements.")
            
        # 2. Process through AI Agent
        extracted_events = parse_with_ai_agent(raw_text)
        
        # 3. Save to database file
        with open(SANDBOX_DB, "w") as f:
            json.dump(extracted_events, f, indent=2)
            
        print(f"✅ Success! Data written to {SANDBOX_DB}")
        
    except Exception as e:
        print(f"❌ Scraper Sandbox Error: {e}")
        # Explicitly fail the workflow step so GitHub doesn't show a false green checkmark
        exit(1) 

if __name__ == "__main__":
    main()
