from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
from gsheet import job_street_listing_details 
import re


def normalize_indonesian_phone(phone):
    """
    Normalize an Indonesian phone number to the format 628XXXXXXXXX.
    Returns empty string for missing or invalid numbers.
    """
    if pd.isna(phone):
        return ""
    
    phone = str(phone)  # Ensure it's a string
    # Remove all non-digit characters
    phone = re.sub(r"[^\d]", "", phone)
    
    # Skip empty strings
    if not phone:
        return ""
    
    # Convert leading 0 to 62
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    
    return phone



# Setup Chrome driver
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# Function to scrape candidates from job details page with pagination
def scrape_candidates_from_job_details(driver, job_title, job_url, jobs_list_url):
    """
    Navigate to job details page and scrape all candidate information across all pages
    jobs_list_url: URL of the jobs list page to return to
    """
    all_candidates_data = []
    current_page = 1

    try:
        print(f"\n  📄 Job: {job_title}")
        driver.get(job_url)
        time.sleep(3)

        while True:
            page_candidates = scrape_candidates_on_current_page(driver, job_title)
            all_candidates_data.extend(page_candidates)
            print(f"  ✓ Page {current_page}: {len(page_candidates)} candidates")

            if not go_to_next_candidate_page(driver, current_page):
                print(f"  ✓ Total: {len(all_candidates_data)} candidates")
                break

            current_page += 1
            time.sleep(2)

        # Return to jobs list page using saved URL
        print("  🔙 Returning to job list...")
        driver.get(jobs_list_url)
        time.sleep(4)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.border-l-8"))
            )
        except Exception:
            time.sleep(2)

    except Exception as e:
        print(f"  Error: {str(e)}")
        driver.get(jobs_list_url)
        time.sleep(4)

    return all_candidates_data


# Function to scrape candidates on the current page
def scrape_candidates_on_current_page(driver, job_title):
    """
    Scrape all candidates on the current page
    """
    candidates_data = []

    try:
        # Wait for page content to fully load
        time.sleep(2)

        email_buttons = driver.find_elements(
            By.XPATH, "//button[contains(text(), 'Lihat email')]"
        )
        expected_candidate_count = len(email_buttons)

        if expected_candidate_count == 0:
            print("  ⚠️ No candidates found")
            return candidates_data

        candidate_sections = []

        for idx, email_btn in enumerate(email_buttons):
            try:
                parent = email_btn.find_element(
                    By.XPATH,
                    "./ancestor::*[.//div[contains(@class, 'divide-x')]][1]",
                )
                candidate_sections.append(parent)
            except Exception:
                try:
                    parent = email_btn.find_element(
                        By.XPATH,
                        "./ancestor::div[contains(@class, 'grid') and contains(@class, 'gap-6')][1]",
                    )
                    candidate_sections.append(parent)
                except Exception:
                    try:
                        parent = email_btn.find_element(
                            By.XPATH,
                            "./ancestor::div[@class='grid grid-cols-1 gap-6 px-8 pt-4 pb-8 md:grid-cols-[1fr_auto]'][1]",
                        )
                        candidate_sections.append(parent)
                    except Exception:
                        try:
                            parent = email_btn.find_element(
                                By.XPATH,
                                "./ancestor::div[.//h2 and .//div[contains(@class, 'divide-x')]][1]",
                            )
                            candidate_sections.append(parent)
                        except Exception:
                            pass

        if len(candidate_sections) == 0:
            candidate_sections = email_buttons

        for idx, section in enumerate(candidate_sections):
            try:
                candidate_info = {
                    "Job Title": job_title,
                    "Application Date": "N/A",
                    "Status": "N/A",
                    "Name": "N/A",
                    "Qualifications": [],
                    "Email": "N/A",
                    "Phone": "N/A",
                    "Location": "N/A",
                }

                try:
                    name_elem = section.find_element(By.CSS_SELECTOR, "h2.font-light")
                    candidate_info["Name"] = name_elem.text.strip()
                except Exception:
                    pass

                try:
                    date_status_div = None

                    try:
                        date_status_div = section.find_element(
                            By.CSS_SELECTOR, ".flex.divide-x.border"
                        )
                    except Exception:
                        try:
                            parent = section.find_element(
                                By.CSS_SELECTOR, ".flex.justify-center"
                            )
                            date_status_div = parent.find_element(
                                By.CSS_SELECTOR, ".flex.divide-x"
                            )
                        except Exception:
                            try:
                                date_status_div = section.find_element(
                                    By.XPATH, ".//div[contains(@class, 'divide-x')]"
                                )
                            except Exception:
                                try:
                                    date_status_div = section.find_element(
                                        By.XPATH,
                                        "./preceding-sibling::*//*[contains(@class, 'divide-x')] | ./following-sibling::*//*[contains(@class, 'divide-x')]",
                                    )
                                except Exception:
                                    try:
                                        parent_elem = section.find_element(
                                            By.XPATH, ".."
                                        )
                                        date_status_div = parent_elem.find_element(
                                            By.XPATH,
                                            ".//*[contains(@class, 'divide-x')]",
                                        )
                                    except Exception:
                                        pass

                    if date_status_div:
                        try:
                            date_elem = date_status_div.find_element(
                                By.CSS_SELECTOR, ".text-base-500"
                            )
                            candidate_info["Application Date"] = date_elem.text.strip()
                        except Exception:
                            try:
                                date_elem = date_status_div.find_element(
                                    By.XPATH, ".//div[contains(text(), 'Melamar')]"
                                )
                                candidate_info["Application Date"] = (
                                    date_elem.text.strip()
                                )
                            except Exception:
                                pass

                        try:
                            status_elem = date_status_div.find_element(
                                By.CSS_SELECTOR, '[role="status"]'
                            )
                            candidate_info["Status"] = status_elem.text.strip()
                        except Exception:
                            try:
                                status_elem = date_status_div.find_element(
                                    By.CSS_SELECTOR,
                                    "div[class*='bg-yellow'], div[class*='bg-red'], div[class*='bg-green'], div[class*='bg-blue']",
                                )
                                candidate_info["Status"] = status_elem.text.strip()
                            except Exception:
                                try:
                                    status_elem = date_status_div.find_element(
                                        By.XPATH,
                                        ".//*[@role='status' or contains(text(), 'Terpilih') or contains(text(), 'Ditolak') or contains(text(), 'Menunggu')]",
                                    )
                                    candidate_info["Status"] = status_elem.text.strip()
                                except Exception:
                                    pass
                    else:
                        try:
                            date_elem = section.find_element(
                                By.XPATH, ".//div[contains(text(), 'Melamar tanggal')]"
                            )
                            candidate_info["Application Date"] = date_elem.text.strip()
                        except Exception:
                            try:
                                date_elem = section.find_element(
                                    By.XPATH, ".//*[contains(text(), 'Melamar')]"
                                )
                                candidate_info["Application Date"] = (
                                    date_elem.text.strip()
                                )
                            except Exception:
                                try:
                                    date_elem = section.find_element(
                                        By.XPATH,
                                        "./preceding-sibling::*//*[contains(text(), 'Melamar')] | ./following-sibling::*//*[contains(text(), 'Melamar')]",
                                    )
                                    candidate_info["Application Date"] = (
                                        date_elem.text.strip()
                                    )
                                except Exception:
                                    pass

                        try:
                            status_elem = section.find_element(
                                By.XPATH,
                                ".//div[@role='status' or contains(text(), 'Terpilih') or contains(text(), 'Ditolak') or contains(text(), 'Menunggu')]",
                            )
                            status_text = status_elem.text.strip()
                            if status_text:
                                candidate_info["Status"] = status_text
                            else:
                                candidate_info["Status"] = "Tidak ada status"
                        except Exception:
                            try:
                                status_elem = section.find_element(
                                    By.XPATH,
                                    ".//*[contains(@class, 'bg-yellow') or contains(@class, 'bg-red') or contains(@class, 'bg-green') or contains(@class, 'bg-blue')]",
                                )
                                status_text = status_elem.text.strip()
                                if status_text:
                                    candidate_info["Status"] = status_text
                                else:
                                    candidate_info["Status"] = "Tidak ada status"
                            except Exception:
                                candidate_info["Status"] = "Tidak ada status"

                except Exception as e:
                    print(f"    ⚠️ Error getting date/status: {str(e)}")

                # Get qualifications (badges)
                try:
                    badge_elements = section.find_elements(
                        By.CSS_SELECTOR, ".badge.badge-primary.badge-outline"
                    )
                    qualifications = []
                    for badge in badge_elements:
                        badge_text = badge.text.strip()
                        if badge_text:
                            qualifications.append(badge_text)
                    candidate_info["Qualifications"] = ", ".join(qualifications)
                except Exception:
                    pass

                # Get email - click "Lihat email" button first
                try:
                    email_button = None
                    try:
                        buttons = section.find_elements(
                            By.CSS_SELECTOR, "button.link-info.btn-text"
                        )
                        for btn in buttons:
                            if "Lihat email" in btn.text or "email" in btn.text.lower():
                                email_button = btn
                                break
                    except Exception:
                        pass

                    if not email_button:
                        email_button = section.find_element(
                            By.XPATH, ".//button[contains(text(), 'Lihat email')]"
                        )

                    if email_button:
                        driver.execute_script(
                            "arguments[0].scrollIntoView(true);", email_button
                        )
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", email_button)
                        time.sleep(3)

                        try:
                            email_link = section.find_element(
                                By.CSS_SELECTOR, 'a[href^="mailto:"]'
                            )
                            candidate_info["Email"] = email_link.text.strip()
                        except Exception:
                            time.sleep(2)
                            try:
                                email_links = driver.find_elements(
                                    By.CSS_SELECTOR, 'a[href^="mailto:"]'
                                )
                                if email_links:
                                    candidate_info["Email"] = email_links[
                                        -1
                                    ].text.strip()
                                else:
                                    email_span = section.find_element(
                                        By.XPATH, ".//span[contains(text(), '@')]"
                                    )
                                    candidate_info["Email"] = email_span.text.strip()
                            except Exception:
                                pass

                except Exception:
                    pass

                # Get phone - click "Lihat telepon" button first
                try:
                    phone_button = None
                    try:
                        buttons = section.find_elements(
                            By.CSS_SELECTOR, "button.link-info.btn-text"
                        )
                        for btn in buttons:
                            if (
                                "Lihat telepon" in btn.text
                                or "telepon" in btn.text.lower()
                            ):
                                phone_button = btn
                                break
                    except Exception:
                        pass

                    if not phone_button:
                        phone_button = section.find_element(
                            By.XPATH, ".//button[contains(text(), 'Lihat telepon')]"
                        )

                    if phone_button:
                        driver.execute_script(
                            "arguments[0].scrollIntoView(true);", phone_button
                        )
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", phone_button)
                        time.sleep(3)

                        try:
                            phone_number_button = section.find_element(
                                By.CSS_SELECTOR,
                                "button.text-info.text-base.cursor-pointer",
                            )
                            candidate_info["Phone"] = phone_number_button.text.strip()
                        except Exception:
                            time.sleep(2)
                            try:
                                phone_buttons = driver.find_elements(
                                    By.CSS_SELECTOR,
                                    "button.text-info.text-base.cursor-pointer",
                                )
                                if phone_buttons:
                                    candidate_info["Phone"] = phone_buttons[
                                        -1
                                    ].text.strip()
                                else:
                                    phone_spans = section.find_elements(
                                        By.CSS_SELECTOR, "span.text-base"
                                    )
                                    for span in phone_spans:
                                        text = span.text.strip()
                                        if (
                                            text
                                            and any(char.isdigit() for char in text)
                                            and "@" not in text
                                            and len(text) > 3
                                        ):
                                            candidate_info["Phone"] = text
                                            break
                            except Exception:
                                pass

                except Exception:
                    pass

                # Get location
                try:
                    location_div = section.find_element(
                        By.XPATH,
                        ".//div[contains(text(), 'Kota') or contains(text(), 'West Java') or contains(text(), 'ID')]",
                    )
                    candidate_info["Location"] = location_div.text.strip()
                except Exception:
                    try:
                        location_divs = section.find_elements(
                            By.CSS_SELECTOR, "div.text-base"
                        )
                        for div in location_divs:
                            text = div.text.strip()
                            if "," in text and ("ID" in text or "Java" in text):
                                candidate_info["Location"] = text
                                break
                    except Exception:
                        pass

                candidates_data.append(candidate_info)
                print(f"    ✓ {candidate_info['Name']} | {candidate_info['Status']}")

            except Exception as e:
                print(f"    ⚠️ Error: {str(e)}")
                candidates_data.append(candidate_info)
                continue

    except Exception as e:
        print(f"  Error scraping candidates on current page: {str(e)}")

    # Final verification
    actual_count = len(candidates_data)
    if "expected_candidate_count" in locals():
        print(
            f"  ✅ Verification: Scraped {actual_count} / {expected_candidate_count} candidates"
        )
        if actual_count < expected_candidate_count:
            print(
                f"  ⚠️  WARNING: Missing {expected_candidate_count - actual_count} candidates!"
            )
        elif actual_count > expected_candidate_count:
            print(
                f"  ⚠️  WARNING: Got {actual_count - expected_candidate_count} extra candidates (possible duplicates)!"
            )

    return candidates_data


# Function to navigate to next candidate page
def go_to_next_candidate_page(driver, current_page):
    """
    Navigate to the next page of candidates within a job details page
    Returns True if navigation successful, False if no more pages
    """
    try:
        # Look for pagination buttons
        time.sleep(1)  # Wait for pagination to render

        pagination_buttons = driver.find_elements(
            By.CSS_SELECTOR, "button.btn.join-item"
        )

        print(f"  Found {len(pagination_buttons)} pagination buttons")

        # Debug: Show all button texts
        button_texts = [btn.text.strip() for btn in pagination_buttons]
        print(f"  Button texts: {button_texts}")

        # Find the next page number (current_page + 1)
        next_page_num = current_page + 1

        for button in pagination_buttons:
            button_text = button.text.strip()
            if button_text.isdigit() and int(button_text) == next_page_num:
                print(f"  → Clicking candidate page {next_page_num}")

                # Scroll to button
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)

                # Click the button
                driver.execute_script("arguments[0].click();", button)

                # Wait for new content to load - INCREASED WAIT
                print(f"  ⏳ Waiting for page {next_page_num} to load...")
                time.sleep(5)  # Increased from 3 to 5 seconds

                # Verify new content loaded by checking for email buttons
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//button[contains(text(), 'Lihat email')]")
                        )
                    )
                    print(f"  ✅ Page {next_page_num} loaded successfully")
                except Exception:
                    print(f"  ⚠️  Warning: Could not verify page {next_page_num} loaded")
                    time.sleep(2)  # Additional wait

                return True

        # If we didn't find the next page button, we're at the end
        print(f"  No next page button found (looked for page {next_page_num})")
        return False

    except Exception as e:
        print(f"  Error navigating to next candidate page: {str(e)}")
        return False


# Login function
def login_jobstreet(driver, username, password):
    try:
        driver.get("https://employer.jobstreetexpress.com/id/home")

        username_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-testid="login-form-email"]')
            )
        )
        username_field.click()
        username_field.clear()
        username_field.send_keys(username)

        try:
            password_field = driver.find_element(
                By.CSS_SELECTOR, '[data-testid="login-form-password"]'
            )
        except Exception:
            password_field = driver.find_element(
                By.CSS_SELECTOR, 'input[type="password"]'
            )

        password_field.click()
        password_field.clear()
        password_field.send_keys(password)

        login_button = driver.find_element(By.CSS_SELECTOR, '[role="button"]')
        login_button.click()

        WebDriverWait(driver, 15).until(
            EC.url_changes("https://employer.jobstreetexpress.com/id/home")
        )

        return True

    except Exception as e:
        print(f"Login failed: {str(e)}")
        return False


# Function to scrape job listings from current page
def scrape_current_page(driver, page_num, processed_job_urls=None):
    """
    Scrape job listings from current page
    processed_job_urls: set of URLs already processed (to avoid duplicates)
    Returns: (jobs_data, has_tayang_jobs)
    """
    if processed_job_urls is None:
        processed_job_urls = set()

    has_tayang_jobs = False  # Track if we found any Tayang jobs
    jobs_data = []

    try:
        # Wait for job listings to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section"))
        )

        # Save the current jobs list URL at the beginning
        jobs_list_url = driver.current_url

        # Process jobs one by one, re-finding sections after each navigation
        job_index = 0

        while True:
            # Re-find all job sections to avoid stale elements
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "section.border-l-8")
                    )
                )
                job_sections = driver.find_elements(
                    By.CSS_SELECTOR, "section.border-l-8"
                )
            except Exception as e:
                print(f"Error finding job sections: {str(e)}")
                break

            # Check if we've processed all jobs on this page
            if job_index >= len(job_sections):
                print(
                    f"  ✓ Finished processing all {len(job_sections)} jobs on page {page_num}"
                )
                break

            section = job_sections[job_index]
            i = job_index  # Keep original index for display
            try:
                job_status = "N/A"

                # Try method 1: Look for badge elements with class 'badge-primary'
                badge_elements = section.find_elements(
                    By.CSS_SELECTOR, ".badge.badge-primary"
                )
                if badge_elements:
                    for badge in badge_elements:
                        badge_text = badge.text.strip()
                        print(f"    🔍 Found badge-primary: '{badge_text}'")
                        if badge_text in ["Tayang", "Kadaluarsa"]:
                            job_status = badge_text
                            print(f"    ✅ Status found: {job_status}")
                            break

                # Try method 2: Look for any badge elements
                if job_status == "N/A":
                    all_badges = section.find_elements(By.CSS_SELECTOR, ".badge")
                    for badge in all_badges:
                        badge_text = badge.text.strip()
                        print(f"    🔍 Found badge: '{badge_text}'")
                        if badge_text in ["Tayang", "Kadaluarsa"]:
                            job_status = badge_text
                            print(f"    ✅ Status found: {job_status}")
                            break

                # Try method 3: Look for div elements with badge classes
                if job_status == "N/A":
                    div_badges = section.find_elements(
                        By.CSS_SELECTOR, "div.badge, div[class*='badge']"
                    )
                    for badge in div_badges:
                        badge_text = badge.text.strip()
                        print(f"    🔍 Found div badge: '{badge_text}'")
                        if badge_text in ["Tayang", "Kadaluarsa"]:
                            job_status = badge_text
                            print(f"    ✅ Status found: {job_status}")
                            break

                # Try method 4: Look for any element containing 'Tayang' or 'Kadaluarsa' text
                if job_status == "N/A":
                    status_elements = section.find_elements(
                        By.XPATH,
                        ".//*[contains(text(), 'Tayang') or contains(text(), 'Kadaluarsa')]",
                    )
                    for elem in status_elements:
                        elem_text = elem.text.strip()
                        print(f"    🔍 Found text element: '{elem_text}'")
                        if elem_text == "Tayang":
                            job_status = "Tayang"
                            print(f"    ✅ Status found: {job_status}")
                            break
                        elif elem_text == "Kadaluarsa":
                            job_status = "Kadaluarsa"
                            print(f"    ✅ Status found: {job_status}")
                            break

                # Try method 5: Look for span elements with specific classes that might contain status
                if job_status == "N/A":
                    span_elements = section.find_elements(
                        By.CSS_SELECTOR,
                        "span[class*='bg-'], span[class*='text-'], span",
                    )
                    for span in span_elements:
                        span_text = span.text.strip()
                        if span_text in ["Tayang", "Kadaluarsa"]:
                            job_status = span_text
                            print(f"    ✅ Status found in span: {job_status}")
                            break

                # Try method 6: Look for any element containing status text (case insensitive)
                if job_status == "N/A":
                    all_elements = section.find_elements(By.XPATH, ".//*")
                    for elem in all_elements:
                        elem_text = elem.text.strip()
                        if elem_text.lower() in ["tayang", "kadaluarsa"]:
                            job_status = elem_text.title()  # Capitalize first letter
                            print(
                                f"    ✅ Status found (case insensitive): {job_status}"
                            )
                            break

                if job_status == "N/A":
                    print(f"    ⚠️ No status found for job {i + 1}")
                    # Let's debug what's in this section
                    print(
                        f"    📝 Section HTML preview: {section.get_attribute('outerHTML')[:200]}..."
                    )

                creation_date = "N/A"
                try:
                    date_elements = section.find_elements(
                        By.CSS_SELECTOR, ".font-extralight"
                    )
                    for elem in date_elements:
                        text = elem.text.strip()
                        if "Dibuat" in text or "Created" in text:
                            creation_date = text
                            break
                except Exception:
                    pass

                job_title = "N/A"
                try:
                    title_elements = section.find_elements(
                        By.CSS_SELECTOR, ".text-base.font-normal"
                    )
                    for elem in title_elements:
                        text = elem.text.strip()
                        if (
                            text
                            and len(text) > 0
                            and "RedDoorz" not in text
                            and "Jakasampurna" not in text
                            and len(text) < 100
                        ):
                            job_title = text
                            break
                except Exception:
                    pass

                company_name = "N/A"
                location = "N/A"
                try:
                    company_elements = section.find_elements(
                        By.CSS_SELECTOR, "span.flex.gap-2.text-base.font-normal"
                    )
                    if company_elements:
                        company_name = company_elements[0].text.strip()

                    location_elements = section.find_elements(
                        By.CSS_SELECTOR, "span.text-md.text-sm.font-light"
                    )
                    if location_elements:
                        location = location_elements[0].text.strip()
                except Exception:
                    pass

                candidates = "N/A"
                try:
                    candidate_elements = section.find_elements(
                        By.XPATH, ".//span[contains(text(), 'Kandidat')]"
                    )
                    if candidate_elements:
                        candidates = candidate_elements[0].text.strip()
                except Exception:
                    pass

                job_data = {
                    "Page": page_num,
                    "Status": job_status,
                    "Creation Date": creation_date,
                    "Job Title": job_title,
                    "Company": company_name,
                    "Location": location,
                    "Candidates": candidates,
                    "Job URL": "N/A",
                }

                # Get job URL from the link
                try:
                    job_link = section.find_element(
                        By.CSS_SELECTOR, "a[href*='/jobs/']"
                    )
                    job_url = job_link.get_attribute("href")
                    job_data["Job URL"] = job_url
                except Exception:
                    pass

                jobs_data.append(job_data)
                print(f"Page {page_num} - Job {i + 1}: {job_status} | {job_title}")

                # If job status is "Tayang", click and scrape candidates
                if job_status == "Tayang" and job_data["Job URL"] != "N/A":
                    has_tayang_jobs = True  # Mark that we found at least one Tayang job
                    job_url = job_data["Job URL"]

                    # Check if we've already processed this job URL
                    if job_url in processed_job_urls:
                        print("  ⏭️  Skipping - already processed this job")
                        print("-" * 30)
                        job_index += 1  # Move to next job
                        continue

                    print("  🔍 Job is 'Tayang' - clicking to view candidates...")
                    processed_job_urls.add(job_url)  # Mark as processed

                    candidates_list = scrape_candidates_from_job_details(
                        driver, job_title, job_url, jobs_list_url
                    )
                    # Store candidates data separately
                    for candidate in candidates_list:
                        candidate["Page"] = page_num
                        candidate["Job Status"] = job_status
                        candidate["Job Creation Date"] = creation_date
                        candidate["Company"] = company_name

                    # Add candidates to a separate list (we'll return both)
                    if not hasattr(scrape_current_page, "all_candidates"):
                        scrape_current_page.all_candidates = []
                    scrape_current_page.all_candidates.extend(candidates_list)

                print("-" * 30)
                job_index += 1  # Move to next job

            except Exception as e:
                print(f"Error processing job {i + 1} on page {page_num}: {str(e)}")
                job_index += 1  # Move to next job even if there's an error
                continue

        return jobs_data, has_tayang_jobs

    except Exception as e:
        print(f"Error scraping page {page_num}: {str(e)}")
        return [], False


# Function to navigate to next page
def go_to_next_page(driver):
    try:
        # Get current page URL before clicking
        current_url = driver.current_url

        # Look for pagination buttons with multiple selectors
        pagination_buttons = driver.find_elements(By.CSS_SELECTOR, ".btn.join-item")

        if not pagination_buttons:
            # Try alternative selectors
            pagination_buttons = driver.find_elements(
                By.CSS_SELECTOR, "button[class*='btn']"
            )

        print(f"Found {len(pagination_buttons)} pagination buttons")

        # Debug: Print all button texts
        button_texts = []
        for i, btn in enumerate(pagination_buttons):
            btn_text = btn.text.strip()
            button_texts.append(btn_text)
            print(
                f"Button {i}: text='{btn_text}', class='{btn.get_attribute('class')}'"
            )

        # Find the current active page and next page
        current_page_num = None
        next_page_button = None
        max_page_num = None

        # Extract all numeric page numbers to find the maximum
        numeric_pages = []
        for btn in pagination_buttons:
            if btn.text.strip().isdigit():
                numeric_pages.append(int(btn.text.strip()))

        if numeric_pages:
            max_page_num = max(numeric_pages)
            print(f"📄 Maximum page number visible: {max_page_num}")

        # Method 1: Look for active button (btn-primary indicates current page)
        for i, button in enumerate(pagination_buttons):
            button_class = button.get_attribute("class") or ""
            button_text = button.text.strip()

            # btn-primary indicates the current active page
            if "btn-primary" in button_class:
                print(
                    f"Found active button: '{button_text}' with class '{button_class}'"
                )
                if button_text.isdigit():
                    current_page_num = int(button_text)

                    # Check if we're on the maximum page
                    if max_page_num and current_page_num >= max_page_num:
                        print(
                            f"🛑 Currently on page {current_page_num} - this is the last page (max: {max_page_num})"
                        )
                        print("⚠️  STOPPING - Will NOT loop back to page 1")
                        return False

                    # Look for next page (current + 1)
                    for next_btn in pagination_buttons:
                        if (
                            next_btn.text.strip().isdigit()
                            and int(next_btn.text.strip()) == current_page_num + 1
                        ):
                            next_page_button = next_btn
                            print(f"Found next page button: {next_btn.text}")
                            break
                break

        # Method 2: If no btn-primary found, look for other active indicators
        if not next_page_button and not current_page_num:
            print("No btn-primary found, looking for other active indicators...")
            for i, button in enumerate(pagination_buttons):
                button_class = button.get_attribute("class") or ""
                button_text = button.text.strip()

                if (
                    "btn-active" in button_class
                    or "active" in button_class
                    or "current" in button_class
                ):
                    print(
                        f"Found active button: '{button_text}' with class '{button_class}'"
                    )
                    if button_text.isdigit():
                        current_page_num = int(button_text)
                        # Look for next page (current + 1)
                        for next_btn in pagination_buttons:
                            if (
                                next_btn.text.strip().isdigit()
                                and int(next_btn.text.strip()) == current_page_num + 1
                            ):
                                next_page_button = next_btn
                                print(f"Found next page button: {next_btn.text}")
                                break
                    break

        # Method 3: If still no active button found, look for clickable numeric buttons
        if not next_page_button and not current_page_num:
            print(
                "No active button found, looking for next available numeric button..."
            )
            for button in pagination_buttons:
                if button.text.strip().isdigit():
                    try:
                        if button.is_enabled() and button.is_displayed():
                            next_page_button = button
                            print(f"Found clickable numeric button: {button.text}")
                            break
                    except Exception:
                        continue

        # Method 4: Look for "Next", ">", or "»" buttons
        if not next_page_button:
            print("Looking for Next/> buttons...")
            next_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(text(), 'Next')] | //button[contains(text(), '>')] | //button[contains(text(), '»')] | //button[contains(@aria-label, 'next')]",
            )
            if next_buttons:
                for btn in next_buttons:
                    # Check if button is enabled (not disabled)
                    is_disabled = btn.get_attribute("disabled")
                    btn_class = btn.get_attribute("class") or ""

                    if (
                        is_disabled
                        or "disabled" in btn_class
                        or "btn-disabled" in btn_class
                    ):
                        print("🛑 Next button is disabled - reached the last page")
                        return False

                    if btn.is_enabled() and btn.is_displayed():
                        next_page_button = btn
                        print(
                            f"Found next button: '{btn.text}' or aria-label: '{btn.get_attribute('aria-label')}'"
                        )
                        break

        if next_page_button:
            print(f"Clicking next page button: '{next_page_button.text}'")
            # Scroll to button first
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", next_page_button
            )
            time.sleep(1)

            # Click the next page button
            driver.execute_script("arguments[0].click();", next_page_button)

            # Wait for page to change
            try:
                # Wait for URL to change
                WebDriverWait(driver, 10).until(EC.url_changes(current_url))
                print("URL changed successfully")
            except Exception:
                try:
                    # If URL doesn't change, wait for page content to reload
                    WebDriverWait(driver, 10).until(
                        EC.staleness_of(pagination_buttons[0])
                    )
                    print("Page content reloaded")
                except Exception:
                    print("Waiting for content to load...")
                    time.sleep(3)

            # Additional wait for new content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.border-l-8"))
            )

            print("Successfully navigated to next page")
            return True
        else:
            print("No next page button found - reached end of pagination")
            return False

    except Exception as e:
        print(f"Error navigating to next page: {str(e)}")
        return False


# Function to scrape all pages
def navigate_to_job_list(driver, list_number):
    """
    Navigate to a specific job list tab on the home page
    list_number: 1 for first list, 2 for second list, etc.
    """
    try:
        driver.get("https://employer.jobstreetexpress.com/id/home")
        time.sleep(3)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section"))
        )

        # Look for list tabs/buttons (adjust selectors based on actual page structure)
        # Common patterns: tabs, role="tab", data-list, etc.

        # Try to find and click on the list tab
        # This might need adjustment based on actual HTML structure
        list_tabs = driver.find_elements(
            By.CSS_SELECTOR, "[role='tab'], .tab, button[data-list]"
        )

        if list_tabs and len(list_tabs) >= list_number:
            target_tab = list_tabs[list_number - 1]
            print(f"  ✓ Found list tab {list_number}: {target_tab.text}")
            driver.execute_script("arguments[0].scrollIntoView(true);", target_tab)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", target_tab)
            time.sleep(3)  # Wait for list to load
            print(f"  ✓ Switched to job list {list_number}")
            return True
        else:
            print(f"  ℹ️ List tabs not found or list {list_number} doesn't exist")
            print("  🛑 No more lists to scrape - stopping")
            return False  # Stop scraping, no more lists

    except Exception as e:
        print(f"  ⚠️ Error navigating to list {list_number}: {str(e)}")
        return False


def scrape_all_pages(driver, max_pages_per_list=None):
    """
    Scrape job listings across multiple lists
    max_pages_per_list: Maximum pages to scrape per list (None = scrape all)
    """
    all_jobs_data = []

    # Track which job URLs we've already processed to avoid duplicates
    processed_job_urls = set()

    # List 1: Scrape only page 1
    print(f"\n{'=' * 60}")
    print("SCRAPING JOB LIST 1 - PAGE 1 ONLY")
    print(f"{'=' * 60}")

    page_num = 1
    print(f"\n{'=' * 50}")
    print(f"SCRAPING PAGE {page_num} OF LIST 1")
    print(f"{'=' * 50}")

    # Scrape page 1 of list 1 (with candidate details for Tayang jobs)
    page_data, has_tayang = scrape_current_page(driver, page_num, processed_job_urls)
    all_jobs_data.extend(page_data)
    print(f"\nList 1 - Page {page_num} completed: {len(page_data)} jobs found")
    print(f"Total unique jobs processed so far: {len(processed_job_urls)}")

    if not has_tayang:
        print("\n⚠️  No 'Tayang' jobs found on List 1 Page 1.")
        print("🛑 All jobs appear to be 'Kadaluarsa' (expired). Ending scrape.")
        return all_jobs_data

    # After completing list 1, continue with list 2, 3, 4, etc.
    list_num = 2
    max_lists_to_try = 10  # Try up to 10 lists (adjust if needed)

    while list_num <= max_lists_to_try:
        print(f"\n{'=' * 60}")
        print(f"RETURNING TO HOME PAGE AND SWITCHING TO JOB LIST {list_num}")
        print(f"{'=' * 60}")

        if navigate_to_job_list(driver, list_num):
            # Scrape all pages from this list
            page_num = 1
            list_has_jobs = False
            list_has_tayang = False  # Track if this list has any Tayang jobs

            while True:
                print(f"\n{'=' * 50}")
                print(f"SCRAPING PAGE {page_num} OF LIST {list_num}")
                print(f"{'=' * 50}")

                # Scrape current page (with candidate details for Tayang jobs)
                page_data, has_tayang = scrape_current_page(
                    driver, page_num, processed_job_urls
                )

                if len(page_data) > 0:
                    list_has_jobs = True
                    if has_tayang:
                        list_has_tayang = True
                    all_jobs_data.extend(page_data)
                    print(
                        f"\nList {list_num} - Page {page_num} completed: {len(page_data)} jobs found"
                    )
                    if has_tayang:
                        print("  ✓ Page has 'Tayang' (active) jobs")
                    else:
                        print("  ⚠️  Page has only 'Kadaluarsa' (expired) jobs")
                        print(
                            "  🛑 No active jobs on this page - stopping pagination for this list"
                        )
                        break  # Stop pagination if page has no Tayang jobs
                    print(
                        f"Total unique jobs processed so far: {len(processed_job_urls)}"
                    )
                else:
                    print(f"\nList {list_num} - Page {page_num}: No jobs found")
                    break  # No jobs on this page, stop pagination for this list

                # Try to go to next page
                page_continue = go_to_next_page(driver)

                if page_continue:
                    page_num += 1
                    time.sleep(2)  # Small delay between pages
                else:
                    print(f"\n{'=' * 60}")
                    print(f"🛑 REACHED MAX PAGE OR END OF LIST {list_num}")
                    print(f"📄 Last page scraped: Page {page_num}")
                    print(f"✅ Stopping pagination for List {list_num}")
                    print(f"{'=' * 60}")
                    break  # Stop pagination - do NOT loop back to page 1

            if not list_has_jobs:
                print(
                    f"\n✓ List {list_num} had no jobs. Assuming this is the last list."
                )
                break  # No jobs found in this list, probably reached the end

            # Check if this list had NO Tayang jobs at all
            if not list_has_tayang:
                print(
                    f"\n⚠️  List {list_num} had NO 'Tayang' jobs (all were 'Kadaluarsa')."
                )
                print("🛑 No more active jobs to process. Ending scrape.")
                break  # Stop if no Tayang jobs in entire list

            # Move to next list
            list_num += 1
        else:
            print(
                f"\n✓ Could not switch to List {list_num}. Assuming all lists have been processed."
            )
            break

    print(f"\n{'=' * 60}")
    print(f"COMPLETED SCRAPING ALL {list_num - 1} JOB LISTS")
    print(f"{'=' * 60}")

    return all_jobs_data


# Main scraping function
def scrape_jobstreet():
    USERNAME = "christine.adikusumo@reddoorz.com"
    PASSWORD = "123456Abc#"

    driver = setup_driver()

    try:
        if login_jobstreet(driver, USERNAME, PASSWORD):
            print("Logged in successfully!")

            current_url = driver.current_url
            print(f"Current URL: {current_url}")

            page_title = driver.title
            print(f"Page title: {page_title}")

            # Initialize candidates list
            scrape_current_page.all_candidates = []

            # Scrape all pages
            print("\nStarting to scrape all job listings...")
            all_jobs_data = scrape_all_pages(driver)

            # Get all candidates data
            all_candidates_data = scrape_current_page.all_candidates

            # Save jobs to CSV
            if all_jobs_data:
                df = pd.DataFrame(all_jobs_data)
                job_street_listing_details(df, code_for="job_listing_details")
                # df.to_csv("jobstreet_all_listings.csv", index=False)
                print(f"\n{'=' * 50}")
                print("SCRAPING COMPLETED!")
                print(f"Total jobs scraped: {len(all_jobs_data)}")
                print("Data saved to: jobstreet_all_listings.csv")

                # Summary by page
                pages_summary = df.groupby("Page").size()
                print("\nJobs per page:")
                for page, count in pages_summary.items():
                    print(f"  Page {page}: {count} jobs")

                # Summary by status
                status_counts = {}
                for job in all_jobs_data:
                    status = job["Status"]
                    status_counts[status] = status_counts.get(status, 0) + 1

                print("\nJob Status summary:")
                for status, count in status_counts.items():
                    print(f"  {status}: {count} jobs")

            # Save candidates to separate CSV
            if all_candidates_data:
                
                df_candidates = pd.DataFrame(all_candidates_data)
                df_candidates["Phone"] = df_candidates["Phone"].apply(normalize_indonesian_phone)
                job_street_listing_details(df_candidates, "candidate_detais")
                # df_candidates.to_csv("jobstreet_candidates.csv", index=False)
                print(f"\n{'=' * 50}")
                print("CANDIDATES DATA:")
                print(f"Total candidates scraped: {len(all_candidates_data)}")
                print("Data saved to: jobstreet_candidates.csv")

                # Summary by candidate status
                candidate_status_counts = {}
                for candidate in all_candidates_data:
                    status = candidate["Status"]
                    candidate_status_counts[status] = (
                        candidate_status_counts.get(status, 0) + 1
                    )

                print("\nCandidate Status summary:")
                for status, count in candidate_status_counts.items():
                    print(f"  {status}: {count} candidates")

            print(f"{'=' * 50}")

        else:
            print("Failed to login")

    except Exception as e:
        print(f"Error during scraping: {str(e)}")

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_jobstreet()
