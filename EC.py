import requests
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

# Load secrets securely
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Validate environment variables
if not NOTION_TOKEN or not OPENAI_API_KEY or not NOTION_DATABASE_ID:
    raise EnvironmentError(
        "❌ Missing one or more environment variables: "
        "NOTION_TOKEN, OPENAI_API_KEY, NOTION_DATABASE_ID"
    )

# -----------------------
# Step 1: Query Notion DB
# -----------------------
def get_new_notion_items():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    print(f"🔍 Requesting Notion DB: {url}")
    print(f"🔐 Using Token: {'Yes' if NOTION_TOKEN else 'Missing'}")
    print(f"📁 Using Database ID: {NOTION_DATABASE_ID}")

    response = requests.post(url, headers=headers)
    print(f"📡 Response Status: {response.status_code}")
    response.raise_for_status()
    return response.json()["results"]

# -----------------------
# Step 2: Send to GPT-4
# -----------------------
def summarize_task(title, description):
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"Summarize and prioritize this task:\nTitle: {title}\nDescription: {description}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()

# -----------------------
# Step 3: Update Notion Page
# -----------------------
def update_notion_page(page_id, summary):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "Summary": {
                "rich_text": [
                    {
                        "text": {"content": summary}
                    }
                ]
            }
        }
    }
    print(f"📤 Sending update to page ID: {page_id}")
    response = requests.patch(url, headers=headers, json=data)
    print(f"✅ Notion response status: {response.status_code}")
    response.raise_for_status()

# -----------------------
# Main Logic
# -----------------------
def main():
    items = get_new_notion_items()
    print(f"📦 Retrieved {len(items)} item(s) from Notion")

    for item in items:
        page_id = item["id"]
        props = item["properties"]

        print(f"🔍 Page ID: {page_id}")
        print(f"🔑 Properties: {list(props.keys())}")

        # Handle potential missing or malformed title
        title = ""
        title_block = props.get("Doc name", {}).get("title", [])
        if title_block and isinstance(title_block, list):
            title_data = title_block[0].get("text", {}).get("content", "")
            title = title_data or ""

        # Handle potential missing or malformed description
        description = ""
        desc_block = props.get("Notes / Background", {}).get("rich_text", [])
        if desc_block and isinstance(desc_block, list):
            description_data = desc_block[0].get("text", {}).get("content", "")
            description = description_data or ""

        if not title:
            print("⚠️ Skipping item due to missing title")
            continue

        summary = summarize_task(title, description)
        print(f"📝 Updating page '{title}' with summary:\n{summary}\n")
        update_notion_page(page_id, summary)
        print(f"✅ Summary updated for '{title}'\n")

if __name__ == "__main__":
    main()