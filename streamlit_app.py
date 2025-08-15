import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import json
import re

API_KEY = st.secrets.get("API_KEY","")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

def llm_generate_keywords_sync(brand_content, competitor_content, locations):
    prompt = f"""
    Analyze the following content from a brand's website and its competitor.
    Identify 10-15 highly relevant, high-intent seed keywords that a potential customer
    would use to search for these products/services. Include brand terms, competitor terms,
    and general category terms. Also, consider adding location-specific keywords for these areas:     {', '.join(locations)}.
    Provide the keywords as a comma-separated list.

    Brand Content (first 1000 chars from {brand_content[:100]}...):
    {brand_content[:1000]}

    Competitor Content (first 1000 chars from {competitor_content[:100]}...):
    {competitor_content[:1000]}
    """

    chat_history = []
    chat_history.append({"role": "user", "parts": [{"text": prompt}]})
    payload = {"contents": chat_history}

    headers = {'Content-Type': 'application/json'}
    full_api_url = f"{API_URL}?key={API_KEY}"

    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            response = requests.post(full_api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()

            if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                keywords = [kw.strip() for kw in text.split(',') if kw.strip()]
                return keywords
            else:
                st.warning(f"LLM response structure unexpected (retry {retries+1}/{max_retries}): {result}")
                time.sleep(2 ** retries)
                retries += 1
                continue
        except requests.exceptions.RequestException as e:
            st.error(f"API call failed (retry {retries+1}/{max_retries}): {e}")
            time.sleep(2 ** retries)
            retries += 1
        except Exception as e:
            st.error(f"An unexpected error occurred (retry {retries+1}/{max_retries}): {e}")
            time.sleep(2 ** retries)
            retries += 1

    st.error("Failed to generate keywords after multiple retries. Using fallback keywords.")
    return [
        "allbirds shoes", "rothys shoes", "sustainable sneakers",
        "wool runners", "tree dashers", "best comfortable travel shoes",
        "allbirds review", "rothys flats", "allbirds vs rothys",
        "ai marketing platform", "seo automation", "reputation management software"
    ]


def llm_group_keywords(keywords_data, brand_name, competitor_name):
    ad_groups = {
        "Brand Terms": [],
        "Product/Service Category": [],
        "Competitor Terms": [],
        "Long-Tail / Informational": [],
        "Location-Based Queries": []
    }

    brand_keywords_regex = r'\b(?:' + '|'.join([
        brand_name.replace('.', '\\.?'), 'allbirds', 'all birds', 'wool runners', 'tree dashers', 'cubehq', 'cube ai'
    ]) + r')\b'
    competitor_keywords_regex = r'\b(?:' + '|'.join([
        competitor_name.replace('.', '\\.?'), 'rothys', 'rothys shoes', 'reputation.com', 'birdeye'
    ]) + r')\b'
    
    brand_pattern = re.compile(brand_keywords_regex, re.IGNORECASE)
    competitor_pattern = re.compile(competitor_keywords_regex, re.IGNORECASE)

    for item in keywords_data:
        kw = item['keyword'].lower()
        
        is_brand_term = bool(brand_pattern.search(kw))
        is_competitor_term = bool(competitor_pattern.search(kw))

        if is_brand_term and not is_competitor_term:
            ad_groups["Brand Terms"].append(item)
        elif is_competitor_term:
            ad_groups["Competitor Terms"].append(item)
        elif "shoes" in kw or "sneakers" in kw or "runners" in kw or "flats" in kw or \
             "marketing platform" in kw or "seo" in kw or "ads optimization" in kw or "reputation management" in kw:
            ad_groups["Product/Service Category"].append(item)
        elif "new york" in kw or "los angeles" in kw or "london" in kw or "berlin" in kw or "sydney" in kw or \
             "san ramon" in kw or "chicago" in kw or "scottsdale" in kw or "lehi" in kw or \
             "liverpool" in kw or "munich" in kw or "mannheim" in kw or "hyderabad" in kw:
            ad_groups["Location-Based Queries"].append(item)
        else:
            ad_groups["Long-Tail / Informational"].append(item)
            
    for group in ad_groups:
        for item in ad_groups[group]:
            if group == "Brand Terms":
                item['suggested_match_type'] = "Exact"
            elif group == "Competitor Terms":
                item['suggested_match_type'] = "Phrase"
            elif group == "Product/Service Category" or group == "Location-Based Queries":
                item['suggested_match_type'] = "Phrase"
            else:
                item['suggested_match_type'] = "Broad"

    return ad_groups


def get_website_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        return " ".join(text.split())
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return ""

def simulate_keyword_planner_data(keywords):
    data = []
    for kw in keywords:
        if len(kw.split()) < 3:
            avg_monthly_searches = random.randint(1000, 100000)
            low_bid = round(random.uniform(0.5, 3.0), 2)
            high_bid = round(random.uniform(3.5, 10.0), 2)
            competition = "High" if random.random() > 0.5 else "Medium"
        else:
            avg_monthly_searches = random.randint(50, 5000)
            low_bid = round(random.uniform(0.2, 1.5), 2)
            high_bid = round(random.uniform(1.8, 5.0), 2)
            competition = "Medium" if random.random() > 0.3 else "Low"
        
        data.append({
            "keyword": kw,
            "avg_monthly_searches": avg_monthly_searches,
            "top_of_page_bid_low": low_bid,
            "top_of_page_bid_high": high_bid,
            "competition": competition
        })
    return pd.DataFrame(data)

def calculate_shopping_bids(shopping_budget, conversion_rate, keywords_data, is_product_based):
    if not is_product_based or shopping_budget == 0:
        return "\n## Deliverable #3: Suggested CPC Bids for Manual Shopping Campaign\n\nNot Applicable for this service-based brand or zero budget.\n"

    average_order_value = 150
    target_cpa = average_order_value * 0.20
    target_cpc = target_cpa * (conversion_rate / 100)

    bid_suggestions = f"""
## Deliverable #3: Suggested CPC Bids for Manual Shopping Campaign

### Methodology & Calculations:
- **Simulated Average Order Value (AOV):** ${average_order_value}
- **Target CPA (20% of AOV):** ${target_cpa:.2f}
- **Target Conversion Rate:** {conversion_rate}%
- **Calculated Target CPC:** ${target_cpc:.2f} (This is our maximum profitable bid per click)

### Suggested CPC Bid Strategy for Manual Shopping Campaign:
"""

    shopping_keywords = [item for item in keywords_data if
                         'shoes' in item['keyword'].lower() or
                         'sneakers' in item['keyword'].lower() or
                         'runners' in item['keyword'].lower() or
                         'flats' in item['keyword'].lower()]

    if not shopping_keywords:
        bid_suggestions += "\nNo relevant product keywords found for Shopping campaign based on current data."
        return bid_suggestions

    shopping_keywords.sort(key=lambda x: x['avg_monthly_searches'], reverse=True)

    for kw_data in shopping_keywords[:5]:
        suggested_bid = target_cpc * 0.8

        if kw_data['competition'] == "High" and kw_data['top_of_page_bid_low'] > target_cpc:
            suggested_bid = max(target_cpc * 1.2, kw_data['top_of_page_bid_low'] * 0.8)
        elif kw_data['competition'] == "Medium" and kw_data['top_of_page_bid_low'] > target_cpc:
            suggested_bid = target_cpc * 1.1
        
        suggested_bid = max(0.1, suggested_bid)

        bid_suggestions += f"""
- **Product Keyword:** "{kw_data['keyword']}"
  - **Monthly Searches:** {kw_data['avg_monthly_searches']}
  - **Competition:** {kw_data['competition']}
  - **Top of Page Bid Range:** ${kw_data['top_of_page_bid_low']} - ${kw_data['top_of_page_bid_high']}
  - **Suggested Manual Bid:** ${suggested_bid:.2f}
"""
    bid_suggestions += "\n*Note: Bids are suggestions and should be continuously optimized based on live campaign performance and ROAS goals.*\n"
    return bid_suggestions

def generate_pmax_themes(ad_groups, brand_name, competitor_name):
    themes = f"""
## Deliverable #2: Search Themes for Performance Max Campaign ({brand_name})

These themes are derived from high-performing keyword categories and ad groups, guiding the creation of asset groups for optimal PMax campaign performance.

### Product/Service Category Themes:
"""

    if ad_groups["Product/Service Category"]:
        product_keywords = [item['keyword'] for item in ad_groups["Product/Service Category"]]
        themes += f"""
- **Core Offerings:** Focus on the primary products/services.
    - Examples: "{product_keywords[0]}"{f", \"{product_keywords[1]}\"" if len(product_keywords) > 1 else ""}
- **Specific Product/Service Lines:** Break down into more granular offerings.
    - Examples: "Sustainable Sneakers", "AI Marketing Automation"
"""
    else:
        themes += "\n- No specific product/service category themes identified based on current keywords."

    themes += """
### Use-Case Based Themes:
"""
    if ad_groups["Long-Tail / Informational"]:
        informational_keywords = [item['keyword'] for item in ad_groups["Long-Tail / Informational"]]
        themes += f"""
- **Problem/Solution Focused:** Address specific customer needs.
    - Examples: "{informational_keywords[0]}"{f", \"{informational_keywords[1]}\"" if len(informational_keywords) > 1 else ""}
- **Value Proposition:** Highlight key benefits.
    - Examples: "eco-friendly footwear", "AI-driven growth"
"""
    else:
        themes += "\n- No specific use-case based themes identified based on current keywords."

    themes += """
### Competitive Themes:
"""
    if ad_groups["Competitor Terms"]:
        competitor_keywords = [item['keyword'] for item in ad_groups["Competitor Terms"]]
        themes += f"""
- **Direct Competitor Targeting:** Capture users searching for rivals.
    - Examples: "{competitor_keywords[0]}"{f", \"{competitor_keywords[1]}\"" if len(competitor_keywords) > 1 else ""}
- **Comparison Queries:** Engage users comparing brands.
    - Examples: "{brand_name} vs {competitor_name}"
"""
    else:
        themes += f"\n- No specific competitor themes identified based on current keywords."

    themes += """
### Location-Based Themes:
"""
    if ad_groups["Location-Based Queries"]:
        location_keywords = [item['keyword'] for item in ad_groups["Location-Based Queries"]]
        themes += f"""
- **Geographic Targeting:** Focus on specific service areas or store locations.
    - Examples: "{location_keywords[0]}"{f", \"{location_keywords[1]}\"" if len(location_keywords) > 1 else ""}
"""
    else:
        themes += "\n- No specific location-based themes identified based on current keywords."

    return themes


# --- Streamlit App Layout ---
st.set_page_config(page_title="SEM Plan Generator", layout="wide")

st.title("📈 AI-Powered SEM Plan Generator")
st.markdown("""
This application helps you generate a structured Search Engine Marketing (SEM) plan,
including keyword lists for Search campaigns, themes for Performance Max (PMax) campaigns,
and suggested CPC bids for Shopping campaigns.
""")

with st.expander("Input Parameters", expanded=True):
    st.subheader("Brand & Competitor Information")
    brand_website = st.text_input("Brand's Website URL", "https://www.allbirds.com")
    competitor_website = st.text_input("Competitor Website URL", "https://www.rothys.com")
    service_locations_str = st.text_area(
        "Service Locations (comma-separated)",
        "New York, NY, Los Angeles, CA, London, UK, Berlin, Germany, Sydney, Australia"
    )

    st.subheader("Ad Budgets ($)")
    col1, col2, col3 = st.columns(3)
    with col1:
        search_budget = st.number_input("Search Ads Budget", min_value=0, value=5000, step=100)
    with col2:
        shopping_budget = st.number_input("Shopping Ads Budget", min_value=0, value=4000, step=100)
    with col3:
        pmax_budget = st.number_input("PMax Ads Budget", min_value=0, value=2500, step=100)

if st.button("Generate SEM Plan", type="primary"):
    if not API_KEY:
        st.error("Gemini API Key not found. Please add it to your Streamlit secrets.toml file or Streamlit Cloud secrets.")
    else:
        with st.spinner("Generating your SEM plan... This may take a moment (up to 30-60 seconds for API calls and processing)."):
            service_locations = [loc.strip() for loc in service_locations_str.split(',') if loc.strip()]
            brand_name = brand_website.replace('https://www.', '').split('.')[0]
            competitor_name = competitor_website.replace('https://www.', '').split('.')[0]
            is_product_based = (shopping_budget > 0) # Heuristic for shopping applicability

            # Step 1 & 2: Scraping and Keyword Discovery
            brand_content = get_website_content(brand_website)
            competitor_content = get_website_content(competitor_website)
            
            # Use synchronous version for Streamlit
            master_keyword_list = llm_generate_keywords_sync(brand_content, competitor_content, service_locations)
            
            # Step 3 & 4: Simulate Keyword Planner Data & Filter
            keyword_df = simulate_keyword_planner_data(master_keyword_list)
            filtered_keywords_list = [kw for kw in keyword_df.to_dict('records') if kw['avg_monthly_searches'] >= 500]

            # Step 5: Group Keywords into Ad Groups
            final_ad_groups = llm_group_keywords(filtered_keywords_list, brand_name, competitor_name)

            # --- Generate Deliverable #1 Content ---
            d1_output = f"## Deliverable #1: Keyword List Grouped by Ad Groups ({brand_name})\n\n"
            d1_output += "Based on brand website content, competitor insights, and simulated keyword data with specific location targeting.\n\n"
            
            for ad_group_name, keywords_in_group in final_ad_groups.items():
                if keywords_in_group:
                    d1_output += f"### Ad Group: {ad_group_name}\n"
                    d1_output += "--------------------------------\n"
                    for kw_data in keywords_in_group:
                        d1_output += (
                            f" - Keyword: {kw_data['keyword']}\n"
                            f"   - Suggested Match Type: {kw_data['suggested_match_type']}\n"
                            f"   - Suggested CPC Range: ${kw_data['top_of_page_bid_low']} - ${kw_data['top_of_page_bid_high']}\n"
                            f"   - Monthly Searches: {kw_data['avg_monthly_searches']}\n"
                            f"   - Competition: {kw_data['competition']}\n"
                            f"\n"
                        )
                    d1_output += "\n"
            
            # --- Generate Deliverable #2 Content ---
            d2_output = generate_pmax_themes(final_ad_groups, brand_name, competitor_name)

            # --- Generate Deliverable #3 Content ---
            d3_output = calculate_shopping_bids(shopping_budget, 2, filtered_keywords_list, is_product_based)

            st.success("SEM Plan Generated Successfully!")
            st.markdown(d1_output)
            st.markdown(d2_output)
            st.markdown(d3_output)
