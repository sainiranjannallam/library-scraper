import streamlit as st
from playwright.sync_api import sync_playwright
import csv
from pathlib import Path
import time
import pandas as pd
from io import StringIO
import os
import subprocess
import sys

# Install Playwright browsers if not already installed
@st.cache_resource
def install_playwright_browsers():
    """Install Playwright browsers on first run"""
    try:
        # Try to launch browser, this will fail if not installed
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                # Browsers not installed, install them
                st.info("Installing Playwright browsers... This may take a few minutes on first run.")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
                st.success("Playwright browsers installed successfully!")
                return True
    except Exception as e:
        st.error(f"Failed to install Playwright browsers: {e}")
        return False

# Install browsers before app starts
install_playwright_browsers()

st.set_page_config(
    page_title="Digital Library Scraper",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Digital Library Metadata Scraper")
st.markdown("Extract metadata from Buffalo Digital Library admin interface")

# Initialize session state
if 'scraping' not in st.session_state:
    st.session_state.scraping = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'csv_data' not in st.session_state:
    st.session_state.csv_data = None

def log_message(msg):
    """Add a log message to the UI"""
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {msg}")

def process_browse_page(page, start_row, rows_remaining, writer, f, progress_bar, status_text, browse_url, base_domain):
    """Process rows on the current browse page starting from start_row."""
    rows = page.locator("table tbody tr")
    total_rows = rows.count()
    log_message(f"Page has {total_rows} rows, starting from row {start_row+1}")
    status_text.text(f"Processing page with {total_rows} rows...")

    processed = 0
    for i in range(start_row, total_rows):
        if processed >= rows_remaining:
            break

        rows = page.locator("table tbody tr")
        row = rows.nth(i)
        link = row.locator("a[href*='/admin/items/show/']").first
        href = link.get_attribute("href")

        try:
            link.click()
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            log_message(f"Could not open item row #{i+1}: {e}")
            page.goto(browse_url)
            page.wait_for_load_state("networkidle")
            continue

        try:
            item_heading = page.inner_text("h1").strip()
        except Exception as e:
            log_message(f"Could not read item heading: {e}")
            page.go_back()
            page.wait_for_load_state("networkidle")
            continue

        log_message(f"Processing Row #{i+1}: {item_heading}")
        status_text.text(f"Processing: {item_heading}")

        image_elements = page.locator("div#content img")
        image_count = image_elements.count()
        log_message(f"Found {image_count} image(s)")

        for img_index in range(image_count):
            try:
                image_elements = page.locator("div#content img")
                image_elements.nth(img_index).click()
                page.wait_for_load_state("networkidle")
                log_message(f"Clicked image {img_index+1}/{image_count}")

                file_heading_full = page.inner_text("h1").strip()
                file_heading = file_heading_full.split(":")[0]

                page.wait_for_selector("text=Format Metadata", timeout=10000)
                filename = page.inner_text(
                    "xpath=//dt[normalize-space()='Filename:']/following-sibling::dd[1]"
                ).strip()
                original_filename = page.inner_text(
                    "xpath=//dt[normalize-space()='Original Filename:']/following-sibling::dd[1]"
                ).strip()

                full_file_url = f"{base_domain}/files/original/{filename}"

                writer.writerow([item_heading, file_heading, original_filename, full_file_url])
                f.flush()
                log_message(f"Saved row for {file_heading}")

                page.go_back()
                page.wait_for_load_state("networkidle")

            except Exception as e:
                log_message(f"Error processing image {img_index+1}: {e}")
                try:
                    page.go_back()
                    page.wait_for_load_state("networkidle")
                except:
                    pass

        page.go_back()
        page.wait_for_load_state("networkidle")
        processed += 1

        # Update progress
        progress_bar.progress(min(1.0, processed / rows_remaining))
        log_message(f"Returned to browse page. Rows processed: {processed}")

    return processed

def run_scraper(username, password, loops, skip, browse_url, headless=True):
    """Main scraper function"""
    CSV_FILE = Path("results.csv")

    # Extract base domain from browse_url
    from urllib.parse import urlparse
    parsed = urlparse(browse_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    write_header = not CSV_FILE.exists()

    # Create progress placeholders
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        with sync_playwright() as p:
            log_message("Launching browser...")
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(browse_url)
            page.wait_for_load_state("networkidle")

            # Login
            log_message("Logging in...")
            status_text.text("Logging in...")
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")

            if "login" in page.url:
                log_message("❌ Login failed. Check credentials.")
                browser.close()
                return False

            log_message(f"✅ Login successful! Starting from row {skip+1}, processing up to {loops} rows total.")

            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["Item Heading", "File Heading", "Original Filename", "Full File URL"])

                remaining = loops
                skip_rows = skip

                while remaining > 0:
                    rows = page.locator("table tbody tr")
                    if rows.count() == 0:
                        log_message("No rows found on this page. Stopping.")
                        break

                    processed = process_browse_page(page, skip_rows, remaining, writer, f, progress_bar, status_text, browse_url, base_domain)
                    remaining -= processed
                    skip_rows = 0

                    if remaining <= 0:
                        log_message("✅ Reached processing limit. Stopping.")
                        break

                    # Robust next-page detection
                    next_button = page.locator("a[rel='next'], a[title='Next page'], a[aria-label='Next']")
                    if next_button.count() > 0 and next_button.first.is_enabled():
                        log_message("➡️ Moving to next page...")
                        next_button.first.click()
                        page.wait_for_load_state("networkidle")
                    else:
                        log_message("No more pages left (no next button found). Stopping.")
                        break

            browser.close()
            log_message("✅ Script completed! Results saved in results.csv.")
            status_text.text("✅ Scraping completed!")
            progress_bar.progress(1.0)

            # Load CSV data for display
            if CSV_FILE.exists():
                st.session_state.csv_data = pd.read_csv(CSV_FILE)

            return True

    except Exception as e:
        log_message(f"❌ Error: {str(e)}")
        status_text.text(f"Error: {str(e)}")
        return False

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    username = st.text_input("Username", type="default", help="Your login username")
    password = st.text_input("Password", type="password", help="Your login password")

    st.divider()

    browse_url = st.text_input("Browse URL",
                                value="https://digital.lib.buffalo.edu/admin/items/browse?collection=30",
                                help="The URL to browse items (change the collection number as needed)")

    st.divider()

    loops = st.number_input("Number of Rows to Process", min_value=1, max_value=1000, value=10,
                            help="How many rows to process")
    skip = st.number_input("Rows to Skip", min_value=0, max_value=1000, value=0,
                           help="Skip the first N rows")

    headless = st.checkbox("Headless Mode", value=True,
                          help="Run browser in background (uncheck to see browser)")

    st.divider()

    start_button = st.button("🚀 Start Scraping", type="primary", disabled=st.session_state.scraping)

    if start_button:
        if not username or not password:
            st.error("Please provide both username and password!")
        elif not browse_url:
            st.error("Please provide a browse URL!")
        else:
            st.session_state.scraping = True
            st.session_state.logs = []
            st.rerun()

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Scraping Progress")

    if st.session_state.scraping:
        with st.spinner("Scraping in progress..."):
            success = run_scraper(username, password, loops, skip, browse_url, headless)
            st.session_state.scraping = False
            if success:
                st.success("Scraping completed successfully!")
            else:
                st.error("Scraping failed. Check logs for details.")
            st.rerun()

    # Display logs
    if st.session_state.logs:
        log_container = st.container(height=400)
        with log_container:
            for log in st.session_state.logs:
                st.text(log)
    else:
        st.info("Configure settings in the sidebar and click 'Start Scraping' to begin.")

with col2:
    st.subheader("📊 Quick Stats")

    # Check if results.csv exists and display stats
    csv_file = Path("results.csv")
    if csv_file.exists():
        df = pd.read_csv(csv_file)
        st.metric("Total Records", len(df))
        st.metric("Unique Items", df["Item Heading"].nunique() if "Item Heading" in df.columns else 0)

        st.divider()

        # Download button
        csv_string = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_string,
            file_name="results.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Clear data button
        if st.button("🗑️ Clear Data", use_container_width=True, type="secondary"):
            try:
                csv_file.unlink()
                st.session_state.csv_data = None
                st.success("Data cleared successfully!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing data: {e}")
    else:
        st.info("No results yet. Start scraping to see stats.")

# Display results table
if csv_file.exists():
    st.divider()
    st.subheader("📄 Results Preview")
    df = pd.read_csv(csv_file)
    st.dataframe(df, use_container_width=True, height=300)

# Footer
st.divider()
st.caption("💡 Tip: Run in non-headless mode to see the browser in action and debug any issues.")
