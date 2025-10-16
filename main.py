#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yellow Pages Scraper - Apify Actor
Scrapes business listings from Yellow Pages with smart page detection
"""

from apify import Actor
from playwright.async_api import async_playwright
import asyncio
import random
import logging
from urllib.parse import urlencode
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YellowPagesScraper:
    def __init__(self, actor):
        self.actor = actor
        self.all_results = []

    async def scrape_single_page(self, context, keyword, place, page_num, timezone):
        """Scrape a single page using Apify's browser pool"""
        page = None
        try:
            # Use Apify's browser pool (much faster than creating new browsers)
            page = await context.new_page()

            # Stealth
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            # Build URL
            url = f"https://www.yellowpages.com/search?{urlencode({'search_terms': keyword, 'geo_location_terms': place, 'page': page_num})}"

            logging.info(f"Page {page_num}: {url}")

            # Navigate
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Handle Cloudflare
            title = await page.title()
            if 'just a moment' in title.lower():
                logging.info(f"Page {page_num}: Cloudflare detected, waiting...")
                await page.mouse.move(random.randint(200, 600), random.randint(200, 400))
                await asyncio.sleep(random.uniform(1, 2))

                try:
                    await page.wait_for_function(
                        "document.title !== 'Just a moment...'",
                        timeout=30000
                    )
                    logging.info(f"Page {page_num}: Cloudflare bypassed")
                except:
                    logging.error(f"Page {page_num}: Cloudflare timeout")
                    return []

            # Wait for content
            await asyncio.sleep(random.uniform(1, 2))

            # Extract listings
            listings = await page.evaluate(f"""
                () => {{
                    const selectors = ['.result', '[data-testid="organic-listing"]', '.search-results .result'];
                    let results = [];

                    for (const selector of selectors) {{
                        results = document.querySelectorAll(selector);
                        if (results.length > 0) break;
                    }}

                    if (results.length === 0) return [];

                    const listings = [];

                    for (let i = 0; i < results.length && i < 40; i++) {{
                        const result = results[i];
                        try {{
                            // Name
                            let name = '';
                            const nameSelectors = ['.business-name span', '.business-name', 'h3 a', 'h2 a'];
                            for (const sel of nameSelectors) {{
                                const elem = result.querySelector(sel);
                                if (elem && elem.textContent.trim()) {{
                                    name = elem.textContent.trim();
                                    break;
                                }}
                            }}
                            if (!name) continue;

                            // Phone
                            let phone = '';
                            const phoneSelectors = ['.phone', '.phones', 'a[href*="tel:"]'];
                            for (const sel of phoneSelectors) {{
                                const elem = result.querySelector(sel);
                                if (elem) {{
                                    const phoneText = elem.textContent.replace(/\\D/g, '');
                                    if (phoneText.length >= 10) {{
                                        phone = phoneText;
                                        break;
                                    }}
                                }}
                            }}

                            // Address
                            let address = '';
                            const addrElem = result.querySelector('.adr, .address');
                            if (addrElem) address = addrElem.textContent.trim();

                            // Website
                            let website = '';
                            const webElem = result.querySelector('a[href*="http"]:not([href*="yellowpages.com"])');
                            if (webElem) website = webElem.href;

                            // Categories
                            let categories = '';
                            const catElems = result.querySelectorAll('.categories a, .category');
                            if (catElems.length > 0) {{
                                categories = Array.from(catElems)
                                    .map(e => e.textContent.trim())
                                    .filter(c => c)
                                    .slice(0, 2)
                                    .join(', ');
                            }}

                            listings.push({{
                                name: name,
                                phone: phone,
                                address: address,
                                website: website,
                                category: categories,
                                keyword: '{keyword}',
                                location: '{place}',
                                timezone: '{timezone}',
                                status: 'Lead',
                            }});

                        }} catch (error) {{
                            console.error('Extraction error:', error);
                        }}
                    }}

                    return listings;
                }}
            """)

            if listings:
                logging.info(f"Page {page_num}: SUCCESS - {len(listings)} listings extracted")
            else:
                logging.warning(f"Page {page_num}: No listings found")

            return listings

        except Exception as e:
            logging.error(f"Page {page_num} error: {e}")
            return []
        finally:
            if page:
                await page.close()

    async def detect_total_pages(self, context, keyword, place):
        """Detect how many real pages exist for this search"""
        page = None
        try:
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            url = f"https://www.yellowpages.com/search?{urlencode({'search_terms': keyword, 'geo_location_terms': place, 'page': 1})}"
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(1, 2))

            # Extract total results and calculate pages
            total_pages = await page.evaluate("""
                () => {
                    // Method 1: Yellow Pages specific - "Showing 1-30 of 103"
                    const showingCount = document.querySelector('.pagination .showing-count');
                    if (showingCount) {
                        const text = showingCount.textContent;
                        const match = text.match(/Showing\\s+\\d+-\\d+\\s+of\\s+(\\d+)/i);
                        if (match) {
                            const totalResults = parseInt(match[1]);
                            const pages = Math.ceil(totalResults / 30);
                            return pages;
                        }
                    }

                    // Method 2: Count actual pagination numbers
                    const pageNumbers = document.querySelectorAll('.pagination ul li a[data-page]');
                    if (pageNumbers.length > 0) {
                        const maxPage = Math.max(...Array.from(pageNumbers)
                            .map(a => parseInt(a.getAttribute('data-page')))
                            .filter(num => !isNaN(num)));
                        return maxPage;
                    }

                    // Method 3: Check if single page
                    const nextButton = document.querySelector('.pagination .next');
                    if (!nextButton) {
                        const results = document.querySelectorAll('.result, [data-testid="organic-listing"]');
                        if (results.length > 0) return 1;
                    }

                    // Method 4: No results
                    const results = document.querySelectorAll('.result, [data-testid="organic-listing"]');
                    if (results.length === 0) return 0;

                    return 10;
                }
            """)

            logging.info(f"Detected {total_pages} pages for '{keyword}' in {place}")
            return min(total_pages, 100)  # Cap at 100 pages

        except Exception as e:
            logging.error(f"Error detecting pages: {e}")
            return 10
        finally:
            if page:
                await page.close()

    async def scrape_multiple_pages_parallel(self, context, keyword, place, pages_to_scrape, timezone, max_concurrency):
        """Scrape multiple pages in parallel"""
        logging.info(f"Scraping {len(pages_to_scrape)} pages in parallel for '{keyword}' in {place}")

        semaphore = asyncio.Semaphore(max_concurrency)

        async def scrape_with_semaphore(page_num):
            async with semaphore:
                await asyncio.sleep(random.uniform(0, 1))
                return await self.scrape_single_page(context, keyword, place, page_num, timezone)

        tasks = [scrape_with_semaphore(page_num) for page_num in pages_to_scrape]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_listings = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_listings.extend(result)

        logging.info(f"PARALLEL SCRAPING COMPLETE: {len(all_listings)} total listings")
        return all_listings

async def main():
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}

        keywords = actor_input.get('keywords', ['Real Estate'])
        locations = actor_input.get('locations', ['CA'])
        timezone = actor_input.get('timezone', 'PST')
        max_pages = actor_input.get('maxPages', 50)
        max_concurrency = actor_input.get('maxConcurrency', 20)  # Apify can handle much more!

        # Convert string inputs to lists if needed
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',')]
        if isinstance(locations, str):
            locations = [l.strip() for l in locations.split(',')]

        Actor.log.info(f"Starting scraper: {len(keywords)} keywords, {len(locations)} locations")

        scraper = YellowPagesScraper(Actor)

        # Use Apify's browser pool (much faster than creating browsers)
        async with async_playwright() as playwright:
            # Launch browser with Apify's residential proxies
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-first-run',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                ]
            )

            # Use Apify's proxy configuration
            proxy_config = await Actor.create_proxy_configuration()
            proxy_url = await proxy_config.new_url() if proxy_config else None

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                proxy={'server': proxy_url} if proxy_url else None
            )

            try:
                for location in locations:
                    for keyword in keywords:
                        Actor.log.info(f"Processing '{keyword}' in {location}")

                        # Detect pages
                        total_pages = await scraper.detect_total_pages(context, keyword, location)

                        if total_pages == 0:
                            Actor.log.info(f"No results for '{keyword}' in {location}")
                            continue

                        pages_to_scrape = list(range(1, min(total_pages, max_pages) + 1))

                        # Scrape pages
                        listings = await scraper.scrape_multiple_pages_parallel(
                            context, keyword, location, pages_to_scrape, timezone, max_concurrency
                        )

                        # Push results to Apify dataset
                        if listings:
                            await Actor.push_data(listings)
                            Actor.log.info(f"Pushed {len(listings)} listings to dataset")

                        # Shorter delay on Apify (has better anti-ban)
                        await asyncio.sleep(random.uniform(2, 5))

            finally:
                await context.close()
                await browser.close()

        Actor.log.info("Scraping completed!")
