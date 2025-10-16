#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yellow Pages Scraper - Simple requests library (most reliable)
"""

from apify import Actor
import asyncio
import requests
import random
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import re
import time

def scrape_page(keyword, location, page_num, timezone, proxy_url=None):
    """Scrape a single page using requests"""
    url = f"https://www.yellowpages.com/search?search_terms={quote_plus(keyword)}&geo_location_terms={quote_plus(location)}&page={page_num}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    proxies = None
    if proxy_url:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }

    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)

        if response.status_code != 200:
            print(f"Page {page_num}: HTTP {response.status_code}")
            return []

        html = response.text

        if len(html) < 1000:
            print(f"Page {page_num}: Response too small ({len(html)} bytes)")
            return []

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Find all results
        results = soup.find_all('div', class_='result')
        if not results:
            results = soup.find_all('div', {'class': re.compile(r'.*result.*')})

        print(f"Page {page_num}: Found {len(results)} result divs")

        listings = []
        for result in results[:40]:
            try:
                # Name
                name_elem = result.find('a', class_='business-name') or result.find('h2')
                name = name_elem.get_text(strip=True) if name_elem else ''
                if not name:
                    continue

                # Phone
                phone = ''
                phone_elem = result.find('div', class_='phones')
                if phone_elem:
                    phone_text = phone_elem.get_text(strip=True)
                    phone = re.sub(r'\D', '', phone_text)

                # Address
                address = ''
                addr_elem = result.find('div', class_='street-address')
                if addr_elem:
                    address = addr_elem.get_text(strip=True)

                # Website
                website = ''
                links = result.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if 'http' in href and 'yellowpages.com' not in href:
                        website = href
                        break

                # Categories
                category = ''
                cat_elem = result.find('div', class_='categories')
                if cat_elem:
                    category = cat_elem.get_text(strip=True)

                listings.append({
                    'name': name,
                    'phone': phone if len(phone) >= 10 else '',
                    'address': address,
                    'website': website,
                    'category': category,
                    'keyword': keyword,
                    'location': location,
                    'timezone': timezone,
                    'status': 'Lead',
                })

            except Exception as e:
                print(f"Error extracting listing: {e}")
                continue

        print(f"Page {page_num}: Extracted {len(listings)} listings")
        return listings

    except Exception as e:
        print(f"Page {page_num}: Error - {e}")
        return []

async def main():
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}

        keywords = actor_input.get('keywords', ['Real Estate'])
        locations = actor_input.get('locations', ['CA'])
        timezone = actor_input.get('timezone', 'PST')
        max_pages = actor_input.get('maxPages', 10)

        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',')]
        if isinstance(locations, str):
            locations = [l.strip() for l in locations.split(',')]

        Actor.log.info(f"Starting requests scraper: {len(keywords)} keywords, {len(locations)} locations")

        # Get proxy configuration from input
        proxy_configuration = actor_input.get('proxyConfiguration')
        proxy_config = await Actor.create_proxy_configuration(actor_proxy_configuration=proxy_configuration)

        if proxy_config:
            # Get new proxy for each request (rotate)
            proxy_url = await proxy_config.new_url()
            Actor.log.info(f"Using proxy: {proxy_url}")
        else:
            proxy_url = None
            Actor.log.warning("No proxy configured - running without proxy")

        for location in locations:
            for keyword in keywords:
                Actor.log.info(f"Scraping '{keyword}' in {location}")

                # Scrape page 1
                listings = scrape_page(keyword, location, 1, timezone, proxy_url)

                if listings:
                    await Actor.push_data(listings)
                    Actor.log.info(f"Pushed {len(listings)} listings")

                time.sleep(random.uniform(2, 5))

        Actor.log.info("Scraping completed!")

# Run the Actor
asyncio.run(main())
