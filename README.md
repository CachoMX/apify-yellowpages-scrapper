# Yellow Pages Scraper - Apify Actor

Fast and intelligent Yellow Pages business scraper with automatic page detection and parallel processing.

## Features

- **Smart Page Detection**: Automatically detects how many pages exist for each search (no wasted requests!)
- **Parallel Scraping**: Scrapes multiple pages simultaneously for maximum speed
- **Residential Proxies**: Uses Apify's proxy pool to avoid blocks
- **Rich Data**: Extracts business name, phone, address, website, and categories
- **Flexible Input**: Search multiple keywords across multiple locations
- **CSV Export**: Download results in CSV format

## Input

```json
{
  "keywords": ["Real Estate", "Plumber", "Lawyer"],
  "locations": ["CA", "WA", "New York, NY"],
  "timezone": "PST",
  "maxPages": 50,
  "maxConcurrency": 20
}
```

### Input Parameters

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `keywords` | Array | List of business types to search | `["Real Estate"]` |
| `locations` | Array | State abbreviations or cities | `["CA"]` |
| `timezone` | String | Timezone label (PST/EST/CST/MST) | `"PST"` |
| `maxPages` | Integer | Max pages per search (30 results/page) | `50` |
| `maxConcurrency` | Integer | Parallel pages to scrape | `20` |

## Output

Each result contains:

```json
{
  "name": "ABC Real Estate",
  "phone": "5551234567",
  "address": "123 Main St, Los Angeles, CA 90001",
  "website": "https://example.com",
  "category": "Real Estate Agents, Property Management",
  "keyword": "Real Estate",
  "location": "CA",
  "timezone": "PST",
  "status": "Lead"
}
```

## Performance

- **Speed**: 20x faster than local scraping (uses Apify infrastructure)
- **Efficiency**: Only scrapes pages that actually have results
- **Scale**: Can handle 100+ keywords across multiple locations
- **Reliability**: Built-in retry logic and proxy rotation

## Estimated Costs

- Small run (5 keywords × 3 locations): ~$0.50
- Medium run (20 keywords × 5 locations): ~$2.00
- Large run (100 keywords × 10 locations): ~$10.00

*Based on Apify pricing. Actual costs depend on results found.*

## Usage

### On Apify Platform

1. Open the Actor in Apify Console
2. Configure input (keywords, locations, etc.)
3. Click "Start"
4. Download results as CSV, JSON, or Excel

### Via API

```bash
curl "https://api.apify.com/v2/acts/YOUR_USERNAME~yellow-pages-scraper/runs" \\
  -X POST \\
  -d '{
    "keywords": ["Real Estate"],
    "locations": ["CA"],
    "maxPages": 50
  }' \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### With Apify SDK

```python
from apify_client import ApifyClient

client = ApifyClient('YOUR_API_TOKEN')

run = client.actor('YOUR_USERNAME/yellow-pages-scraper').call(
    run_input={
        'keywords': ['Real Estate', 'Plumber'],
        'locations': ['CA', 'WA'],
        'maxPages': 50
    }
)

dataset = client.dataset(run['defaultDatasetId']).list_items().items
print(f"Scraped {len(dataset)} listings")
```

## Local Development

### Prerequisites

```bash
pip install apify playwright
playwright install chromium
```

### Run Locally

```bash
# Set up Apify CLI
npm install -g apify-cli
apify login

# Test locally
apify run
```

### Deploy to Apify

```bash
apify push
```

## Tips for Best Results

1. **Be Specific**: Use specific keywords like "Real Estate Agent" instead of just "Real Estate"
2. **Test First**: Start with 1-2 keywords to verify results before scaling up
3. **Use Locations Wisely**: State abbreviations (CA, NY) work best
4. **Monitor Costs**: Check Apify dashboard for real-time usage
5. **Schedule Runs**: Use Apify's scheduler for daily/weekly scraping

## GitHub Integration

This Actor supports automatic deployment from GitHub:

1. Push code to your GitHub repo
2. In Apify Console: Settings → GitHub Integration
3. Connect your repository
4. Enable auto-deploy on push

## Support

- [Apify Documentation](https://docs.apify.com/)
- [Issue Tracker](https://github.com/CachoMX/apify-yellowpages-scrapper/issues)

## License

MIT License - feel free to use and modify!
