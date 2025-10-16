#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yellow Pages Scraper - Apify Actor using Crawlee (better Cloudflare handling)
"""

from apify import Actor
from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
import asyncio
import random
from urllib.parse import urlencode
from datetime import datetime

class YellowPagesCrawler:
    def __init__(self):
        self.all_results = []
        self.keywords = []
        self.locations = []
        self.timezone = 'PST'
        self.max_pages = 50

    async def handle_page(self, context: PlaywrightCrawlingContext):
        """Handle each page request"""
        page = context.page
        url = context.request.url

        Actor.log.info(f"Processing: {url}")

        # Wait for content
        await asyncio.sleep(random.uniform(2, 4))

        # Check page
        title = await page.title()
        html = await page.content()
        Actor.log.info(f"Title: '{title}', HTML length: {len(html)}")

        if len(html) < 1000:
            Actor.log.error(f"Page too small - likely blocked")
            return

        # Extract listings
        listings = await page.evaluate("""
            () => {
                const selectors = ['.result', '[data-testid="organic-listing"]', '.search-results .result'];
                let results = [];

                for (const selector of selectors) {
                    results = document.querySelectorAll(selector);
                    console.log(`Selector ${selector}: ${results.length} results`);
                    if (results.length > 0) break;
                }

                if (results.length === 0) {
                    console.log('No results found, checking page...');
                    console.log('Title:', document.title);
                    console.log('Body text length:', document.body.innerText.length);
                    return [];
                }

                const listings = [];

                for (let i = 0; i < results.length && i < 40; i++) {
                    const result = results[i];
                    try {
                        // Name
                        let name = '';
                        const nameSelectors = ['.business-name span', '.business-name', 'h3 a', 'h2 a'];
                        for (const sel of nameSelectors) {
                            const elem = result.querySelector(sel);
                            if (elem && elem.textContent.trim()) {
                                name = elem.textContent.trim();
                                break;
                            }
                        }
                        if (!name) continue;

                        // Phone
                        let phone = '';
                        const phoneSelectors = ['.phone', '.phones', 'a[href*="tel:"]'];
                        for (const sel of phoneSelectors) {
                            const elem = result.querySelector(sel);
                            if (elem) {
                                const phoneText = elem.textContent.replace(/\\D/g, '');
                                if (phoneText.length >= 10) {
                                    phone = phoneText;
                                    break;
                                }
                            }
                        }

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
                        if (catElems.length > 0) {
                            categories = Array.from(catElems)
                                .map(e => e.textContent.trim())
                                .filter(c => c)
                                .slice(0, 2)
                                .join(', ');
                        }

                        listings.push({
                            name: name,
                            phone: phone,
                            address: address,
                            website: website,
                            category: categories
                        });

                    } catch (error) {
                        console.error('Extraction error:', error);
                    }
                }

                return listings;
            }
        """)

        if listings:
            Actor.log.info(f"Extracted {len(listings)} listings")
            # Add metadata
            for listing in listings:
                listing['keyword'] = context.request.user_data.get('keyword', '')
                listing['location'] = context.request.user_data.get('location', '')
                listing['timezone'] = self.timezone
                listing['status'] = 'Lead'

            await Actor.push_data(listings)
            self.all_results.extend(listings)
        else:
            Actor.log.warning(f"No listings found on {url}")

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

        Actor.log.info(f"Starting Crawlee scraper: {len(keywords)} keywords, {len(locations)} locations")

        crawler_instance = YellowPagesCrawler()
        crawler_instance.keywords = keywords
        crawler_instance.locations = locations
        crawler_instance.timezone = timezone
        crawler_instance.max_pages = max_pages

        # Create Crawlee crawler with better anti-detection
        crawler = PlaywrightCrawler(
            headless=True,
            browser_type='chromium',
            request_handler=crawler_instance.handle_page,
            max_requests_per_crawl=max_pages * len(keywords) * len(locations),
            max_request_retries=2,
            request_handler_timeout_secs=120,
        )

        # Build URLs to scrape
        urls = []
        for location in locations:
            for keyword in keywords:
                # Start with page 1 only for now
                url = f"https://www.yellowpages.com/search?{urlencode({'search_terms': keyword, 'geo_location_terms': location, 'page': 1})}"
                urls.append({
                    'url': url,
                    'user_data': {'keyword': keyword, 'location': location}
                })

        Actor.log.info(f"Crawling {len(urls)} URLs")

        # Run crawler
        await crawler.run(urls)

        Actor.log.info(f"Scraping completed! Total: {len(crawler_instance.all_results)} listings")

# Run the Actor
asyncio.run(main())
