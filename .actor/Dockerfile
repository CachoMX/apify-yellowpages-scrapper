# Use Apify's base Python image with Playwright
FROM apify/actor-python-playwright:3.11

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium && playwright install-deps chromium

# Copy source code
COPY . ./

# Run the Actor (using simple HTTP approach)
CMD ["python", "main_simple.py"]
