import asyncio
import json
import sys
from tools.internshala import scrape_internshala
from agents.extraction_agent import extract_html_job
from core.config import settings

async def main():
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Ollama base URL: {settings.ollama_base_url}")
    print(f"Ollama model: {settings.ollama_model}")
    print(f"Gemini model: {settings.gemini_model}")
    print(f"Gemini API key set: {bool(settings.gemini_api_key)}")
    
    # Try scraping "Content and Social Media Marketing"
    role = "Content and Social Media Marketing"
    print(f"Scraping '{role}' from Internshala...")
    results = await scrape_internshala(role, "")
    print(f"Found {len(results)} results.")
    
    if not results:
        print("No results scraped.")
        sys.exit(1)
        
    first_job = results[0]
    print(f"Url: {first_job['url']}")
    print("Running extraction...")
    try:
        extracted = await extract_html_job(first_job)
        print("Extraction completed successfully!")
        print(json.dumps(extracted, indent=2))
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
