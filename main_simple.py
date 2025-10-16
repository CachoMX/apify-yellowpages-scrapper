#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yellow Pages Scraper - Simple HTTP approach (like old actors)
"""

from apify import Actor
import asyncio
import aiohttp
import random
from urllib.parse import urlencode, quote_plus
from bs4 import BeautifulSoup
import re

async def scrape_page(session, keyword, location, page_num, timezone):
    """Scrape a single page using simple HTTP"""
    url = f"https://www.yellowpages.com/search?search_terms={quote_plus(keyword)}&geo_location_terms={quote_plus(location)}&page={page_num}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status != 200:
                Actor.log.error(f"Page {page_num}: HTTP {response.status}")
                return []

            html = await response.text()

            if len(html) < 1000:
                Actor.log.error(f"Page {page_num}: Response too small ({len(html)} bytes)")
                return []

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Find all results
            results = soup.find_all('div', class_='result')
            if not results:
                results = soup.find_all('div', {'class': re.compile(r'.*result.*')})

            Actor.log.info(f"Page {page_num}: Found {len(results)} result divs")

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
                    Actor.log.warning(f"Error extracting listing: {e}")
                    continue

            Actor.log.info(f"Page {page_num}: Extracted {len(listings)} listings")
            return listings

    except asyncio.TimeoutError:
        Actor.log.error(f"Page {page_num}: Timeout")
        return []
    except Exception as e:
        Actor.log.error(f"Page {page_num}: Error - {e}")
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

        Actor.log.info(f"Starting simple HTTP scraper: {len(keywords)} keywords, {len(locations)} locations")

        # Create HTTP session
        async with aiohttp.ClientSession() as session:
            for location in locations:
                for keyword in keywords:
                    Actor.log.info(f"Scraping '{keyword}' in {location}")

                    # Scrape first page to detect total pages
                    first_page_listings = await scrape_page(session, keyword, location, 1, timezone)

                    if first_page_listings:
                        await Actor.push_data(first_page_listings)
                        Actor.log.info(f"Pushed {len(first_page_listings)} listings from page 1")

                    # For now just do page 1 to test
                    # TODO: Add page detection and scrape multiple pages

                    await asyncio.sleep(random.uniform(2, 5))

        Actor.log.info("Scraping completed!")

# Run the Actor
asyncio.run(main())
