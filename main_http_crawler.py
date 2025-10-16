#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yellow Pages Scraper - Using HttpCrawler (like successful Apify actors)
"""

from apify import Actor
from crawlee.http_crawler import HttpCrawler, HttpCrawlingContext
import asyncio
import random
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import re

async def router(context: HttpCrawlingContext):
    """Handle each page request"""
    url = context.request.url
    Actor.log.info(f"Processing: {url}")

    # Get HTML
    html = context.http_response.read().decode('utf-8')

    if context.http_response.status_code != 200:
        Actor.log.error(f"HTTP {context.http_response.status_code} for {url}")
        return

    if len(html) < 1000:
        Actor.log.error(f"Response too small: {len(html)} bytes")
        return

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Find all results
    results = soup.find_all('div', class_='result')
    if not results:
        results = soup.find_all('div', {'class': re.compile(r'.*result.*')})

    Actor.log.info(f"Found {len(results)} result divs")

    # Get metadata from request
    keyword = context.request.user_data.get('keyword', '')
    location = context.request.user_data.get('location', '')
    timezone = context.request.user_data.get('timezone', 'PST')

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

    if listings:
        Actor.log.info(f"Extracted {len(listings)} listings")
        await Actor.push_data(listings)
    else:
        Actor.log.warning(f"No listings found")

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

        Actor.log.info(f"Starting HttpCrawler: {len(keywords)} keywords, {len(locations)} locations")

        # Create crawler with auto-proxy configuration
        crawler = HttpCrawler(
            request_handler=router,
            max_requests_per_crawl=max_pages * len(keywords) * len(locations),
            max_request_retries=3,
        )

        # Build requests
        requests = []
        for location in locations:
            for keyword in keywords:
                url = f"https://www.yellowpages.com/search?search_terms={quote_plus(keyword)}&geo_location_terms={quote_plus(location)}&page=1"
                requests.append({
                    'url': url,
                    'user_data': {
                        'keyword': keyword,
                        'location': location,
                        'timezone': timezone
                    }
                })

        Actor.log.info(f"Crawling {len(requests)} URLs")

        # Run crawler
        await crawler.run(requests)

        Actor.log.info("Scraping completed!")

# Run the Actor
asyncio.run(main())
