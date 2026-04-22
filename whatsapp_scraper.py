import asyncio
import csv
import re
from playwright.async_api import async_playwright

async def scrape_whatsapp_group():
    async with async_playwright() as p:
        # Launch browser with persistent context to keep login session
        # Use user_data_dir to save the session, so you don't have to scan the QR code every time
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="./whatsapp_session",
            headless=False,  # We need to see the browser to interact
            args=["--start-maximized"],
            no_viewport=True
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        print("Opening WhatsApp Web...")
        await page.goto("https://web.whatsapp.com")
        
        print("Please scan the QR code if you haven't already.")
        print("1. Open the WhatsApp group you want to scrape.")
        print("2. Click on the group subject/title at the top.")
        print("3. Click 'View all' to open the 'Search members' modal.")
        input("\nPress Enter here in the console ONCE the 'Search members' dialog is fully open and visible on screen: ")

        print("\nStarting to scrape contacts. Please don't interact with the browser while it's scrolling...")

        # We will inject a JavaScript snippet to scroll the modal and extract contacts
        # The script finds the modal, scrolls it, and collects all text. We use regex to find numbers.
        
        js_script = """
        async () => {
            // Find the scrollable container. Usually in the modal, it's a div with overflow-y: auto.
            // A good heuristic for the "Search members" dialog is finding the element with "Search members" text
            // or just the largest scrollable container in the current dialog.
            let scrollableDiv = Array.from(document.querySelectorAll('div')).find(el => 
                window.getComputedStyle(el).overflowY === 'auto' && el.clientHeight > 200
            );

            if (!scrollableDiv) {
                // If not found, try the specific roles or just scroll the body if it's the only scrollable thing
                let dialogs = document.querySelectorAll('[role="dialog"]');
                if (dialogs.length > 0) {
                    let d = dialogs[dialogs.length - 1]; // Topmost dialog
                    scrollableDiv = Array.from(d.querySelectorAll('div')).find(el => 
                        window.getComputedStyle(el).overflowY === 'auto'
                    );
                }
            }

            if (!scrollableDiv) { return "Could not find the scrollable container in the dialog."; }

            let contacts = new Set();
            let lastScrollTop = -1;
            let noProgressCount = 0;

            // Helper to wait a bit
            const delay = ms => new Promise(res => setTimeout(res, ms));

            while (true) {
                // Get all rows in the visible area. Often role="listitem" or role="row".
                // If classes are obfuscated, we just grab all inner texts of the deepest reasonably sized containers.
                let rows = scrollableDiv.querySelectorAll('div[role="listitem"]');
                if (rows.length === 0) {
                    rows = scrollableDiv.querySelectorAll('div[role="row"]'); // Fallback
                }
                
                // If still not found, try getting any div that contains a phone number format
                if (rows.length === 0) {
                    rows = Array.from(scrollableDiv.querySelectorAll('div')).filter(
                        d => d.innerText && d.innerText.match(/\\+\\d{1,3}[\\s-]?\\d+/g)
                    );
                }

                for (let row of rows) {
                    if (row.innerText) {
                        // Store exactly what we see. The Python script will parse this.
                        contacts.add(row.innerText);
                    }
                }

                scrollableDiv.scrollTop += 600;
                await delay(800); // 800ms wait to let new items load

                if (scrollableDiv.scrollTop === lastScrollTop) {
                    noProgressCount++;
                } else {
                    noProgressCount = 0;
                    lastScrollTop = scrollableDiv.scrollTop;
                }

                // If we haven't scrolled down further in 3 iterations, we hit the bottom
                if (noProgressCount >= 3) break;
            }

            return Array.from(contacts);
        }
        """

        raw_contacts = await page.evaluate(js_script)

        if isinstance(raw_contacts, str):
            print("Error from browser script:", raw_contacts)
            await browser.close()
            return

        print(f"Scraped raw text blocks block for {len(raw_contacts)} possible contacts.")
        
        # Regex to find phone numbers, e.g. +27 76 198 6736
        phone_regex = re.compile(r'\+\d{1,3}[\s-]?\d{1,4}[\s-]?\d{1,5}[\s-]?\d{1,5}')
        
        parsed_contacts = []
        
        for text in raw_contacts:
            lines = text.split('\n')
            
            number = None
            name = None
            
            # Find the phone number
            for i, line in enumerate(lines):
                match = phone_regex.search(line)
                if match:
                    number = match.group().strip()
                    # Usually the name is one or two lines above the number
                    if i > 0:
                        name = lines[0].replace('~', '').strip() # e.g. "~ carl"
                    break
            
            if number:
                parsed_contacts.append({'Name': name or "Unknown", 'Phone Number': number})

        # Remove duplicates based on phone numbers
        unique_contacts = {c['Phone Number']: c for c in parsed_contacts}.values()

        # Save to CSV
        csv_filename = "whatsapp_contacts.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Name', 'Phone Number'])
            writer.writeheader()
            for contact in unique_contacts:
                writer.writerow(contact)

        print(f"Successfully saved {len(unique_contacts)} contacts to {csv_filename}!")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_whatsapp_group())
