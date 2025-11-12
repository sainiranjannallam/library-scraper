# Digital Library Metadata Scraper

A web-based UI for scraping metadata from the Buffalo Digital Library admin interface. Built with Streamlit and Playwright.

## Features

- User-friendly web interface
- Real-time progress tracking
- Live logs display
- CSV download functionality
- Configurable scraping parameters
- Headless and visible browser modes

## Local Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

### Running Locally

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to `http://localhost:8501`

3. Configure your settings:
   - Enter your username and password
   - Set the number of rows to process
   - Set how many rows to skip (if resuming)
   - Choose headless mode or visible browser

4. Click "Start Scraping"

5. Download the results CSV when complete

## Deployment Options

### Option 1: Streamlit Community Cloud (Recommended for UI)

**Note:** Streamlit Community Cloud has limitations with browser automation. For best results, run locally or use Option 2.

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Deploy the app
5. Add secrets in Streamlit Cloud dashboard (Settings > Secrets):
```toml
# Not recommended to hardcode credentials
# Better to input them in the UI each time
```

**Limitations:**
- May timeout on large scraping jobs
- Browser automation might be restricted
- Limited memory and CPU

### Option 2: Render.com (Better for Playwright)

1. Create a `render.yaml` file (provided in this repo)
2. Push to GitHub
3. Connect to [render.com](https://render.com)
4. Create a new Web Service
5. Select your repository
6. Render will auto-deploy using the render.yaml configuration

**Pros:**
- Better support for browser automation
- More generous resource limits on free tier
- Persistent file storage

### Option 3: Railway.app

1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. Create new project from GitHub repo
4. Railway auto-detects Streamlit apps
5. Add environment variables if needed

**Pros:**
- Easy deployment
- Good free tier
- Playwright support

### Option 4: Run Locally (Best Performance)

For the most reliable experience with browser automation:
- Run the app locally using `streamlit run app.py`
- Access from any device on your local network
- No deployment limitations

## Files

- `app.py` - Main Streamlit application
- `final.py` - Original CLI scraper (backup)
- `requirements.txt` - Python dependencies
- `results.csv` - Output file (generated after scraping)
- `.env` - Environment variables (optional, for local testing)

## Configuration

### Environment Variables (Optional)

Create a `.env` file for default values:
```
USERNAME=your_username
PASSWORD=your_password
LOOPS=10
SKIP=0
```

**Security Note:** Never commit `.env` files or credentials to version control!

## Troubleshooting

### "Playwright not found"
Run: `playwright install chromium`

### "Browser timeout"
- Increase timeout values in code
- Check internet connection
- Try non-headless mode to debug

### "Memory error on cloud deployment"
- Reduce the number of rows to process
- Use local deployment instead
- Consider upgrading to paid hosting tier

### "Login failed"
- Verify credentials are correct
- Check if the website structure has changed
- Try non-headless mode to see what's happening

## Support

For issues or questions:
1. Check the logs in the UI
2. Try running in non-headless mode to debug
3. Review the original `final.py` script for comparison

## License

This project is for educational and authorized use only. Ensure you have permission to scrape the target website.
