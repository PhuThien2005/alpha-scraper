import requests
import markdownify
import os

def run_scraper():
    print("Starting Zendesk scraper...")
    url_sections = "https://support.optisigns.com/api/v2/help_center/en-us/categories.json?sort_by=position&sort_order=asc&per_page=100"
    response_sections = requests.get(url_sections)

    if response_sections.status_code == 200:
        sections_data = response_sections.json()
        sections = sections_data.get("categories", [])
        for section in sections:
            url = f"https://support.optisigns.com/api/v2/help_center/en-us/categories/{section['id']}/articles?sort_by=position&sort_order=desc&per_page=100"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                for idx, article in enumerate(articles):
                    title = article.get("title")

                    html_body = article.get("body")
                    slug_parts = article.get("html_url").split("/")[-1].split("-")[1:]
                    slug = "-".join(slug_parts) if slug_parts else f"article-{article.get('id')}"

                    if html_body:
                        markdown_content = markdownify.markdownify(html_body, heading_style="ATX")
                        os.makedirs("articles", exist_ok=True)
                        file_name = f"articles/{slug}.md"
                        with open(file_name, "w", encoding="utf-8") as f:
                            f.write(f"# {title}\n\n{markdown_content}")

                        print(f"[{idx+1}] Saved: {file_name}")
            else:
                print(f"Failed to fetch section {section['name']}, status: {response.status_code}")
    print("Scraping complete.\n")

if __name__ == "__main__":
    run_scraper()