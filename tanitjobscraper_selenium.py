from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import json
import time
from datetime import datetime, timedelta

def scrape_tanitjobs():
    # Setup undetected Chrome to bypass Cloudflare
    print("Launching Chrome (undetected mode)...")
    driver = uc.Chrome()
    
    try:
        # Navigate to the jobs page
        print("Navigating to TanitJobs...")
        driver.get("https://www.tanitjobs.com/jobs/")
        
        # Get today's date for comparison
        today = datetime.now().strftime("%d/%m/%Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        print(f"Scraping jobs from today ({today}) and yesterday ({yesterday})")
        
        # Wait for Cloudflare to pass automatically (undetected-chromedriver handles this)
        print("Waiting for Cloudflare check to pass automatically (15-20 seconds)...")
        try:
            WebDriverWait(driver, 25).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.media.well.listing-item, [class*="listing-item"]'))
            )
            print("✓ Cloudflare passed! Page loaded successfully.")
        except:
            print("⚠ Timeout waiting for page, continuing anyway...")
        
        time.sleep(2)
        
        jobs_data = []
        page_num = 1
        reached_yesterday = False
        
        # Pagination loop
        while not reached_yesterday:
            print(f"\n--- Page {page_num} ---")
            
            # Find all job listings on current page
            print("Looking for job listings...")
            
            # Try different selectors
            job_elements = driver.find_elements(By.CSS_SELECTOR, '.listing-item__jobs')
            
            if not job_elements:
                job_elements = driver.find_elements(By.CSS_SELECTOR, '.media.well.listing-item')
            
            if not job_elements:
                job_elements = driver.find_elements(By.CSS_SELECTOR, '[class*="listing-item"]')
            
            print(f"Found {len(job_elements)} job listings")
            
            # Extract data from each job
            for index, job in enumerate(job_elements, 1):
                try:
                    job_info = {}
                    
                    # Extract job title and URL
                    try:
                        title_element = job.find_element(By.CSS_SELECTOR, 'h3 a, .listing-item__title a, h3')
                        job_info['title'] = title_element.text.strip()
                        if title_element.tag_name == 'a':
                            job_info['url'] = title_element.get_attribute('href')
                    except:
                        pass
                    
                    # Extract company name
                    try:
                        company_element = job.find_element(By.CSS_SELECTOR, '.listing-item__company, .company-name, [class*="company"]')
                        job_info['company'] = company_element.text.strip()
                    except:
                        pass
                    
                    # Extract location
                    try:
                        location_element = job.find_element(By.CSS_SELECTOR, '.listing-item__location, .location, [class*="location"]')
                        job_info['location'] = location_element.text.strip()
                    except:
                        pass
                    
                    # Extract job type
                    try:
                        job_type_element = job.find_element(By.CSS_SELECTOR, '.listing-item__job-type, .job-type, [class*="job-type"]')
                        job_info['job_type'] = job_type_element.text.strip()
                    except:
                        pass
                    
                    # Extract description
                    try:
                        description_element = job.find_element(By.CSS_SELECTOR, '.listing-item__desc.hidden-sm.hidden-xs')
                        job_info['description'] = description_element.text.strip()
                    except:
                        # Fallback to truncated mobile description if full one not found
                        try:
                            description_element = job.find_element(By.CSS_SELECTOR, '.listing-item__desc')
                            job_info['description'] = description_element.text.strip()
                        except:
                            pass
                    
                    # Extract date posted
                    date_posted = ""
                    try:
                        date_element = job.find_element(By.CSS_SELECTOR, '.listing-item__date, .date, time')
                        date_posted = date_element.text.strip()
                        job_info['date_posted'] = date_posted
                    except:
                        pass
                    
                    # Extract salary
                    try:
                        salary_element = job.find_element(By.CSS_SELECTOR, '.listing-item__salary, .salary')
                        job_info['salary'] = salary_element.text.strip()
                    except:
                        pass
                    
                    # Only add if we got at least a title and it's from today or yesterday
                    if job_info.get('title') and date_posted in [today, yesterday]:
                        job_info['source'] = 'tanitjobs'
                        jobs_data.append(job_info)
                        print(f"✓ Scraped job {index}: {job_info['title']}")
                    elif job_info.get('title') and date_posted and date_posted not in [today, yesterday, ""]:
                        # We've reached jobs older than yesterday
                        print(f"✗ Job is from {date_posted}, stopping pagination...")
                        reached_yesterday = True
                        break
                    
                except Exception as e:
                    print(f"✗ Error scraping job {index}: {str(e)}")
                    continue
            
            # Look for next page button if we haven't reached yesterday
            if not reached_yesterday:
                try:
                    # Find the next page number link (not the arrow)
                    next_page_num = page_num + 1
                    next_page_links = driver.find_elements(By.CSS_SELECTOR, '#list_nav a')
                    next_found = False
                    
                    for link in next_page_links:
                        if link.text.strip() == str(next_page_num):
                            print(f"Moving to page {next_page_num}...")
                            # Scroll to element and use JavaScript click to avoid interception
                            driver.execute_script("arguments[0].scrollIntoView(true);", link)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(4)  # Wait for next page to load
                            page_num += 1
                            next_found = True
                            break
                    
                    if not next_found:
                        print("No more pages available")
                        reached_yesterday = True
                        
                except Exception as e:
                    print(f"Error navigating to next page: {str(e)}")
                    reached_yesterday = True
        
        return jobs_data
        
    finally:
        # Close browser
        print("\nClosing browser...")
        driver.quit()

def save_to_json(data, filename='tanitjobs_data.json'):
    """Save scraped data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Data saved to {filename}")

def save_to_csv(data, filename='tanitjobs_data.csv'):
    """Save scraped data to CSV file"""
    import csv
    
    if not data:
        print("No data to save to CSV")
        return
    
    # Get all unique keys from all jobs
    keys = set()
    for job in data:
        keys.update(job.keys())
    keys = sorted(keys)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✓ Data saved to {filename}")

if __name__ == "__main__":
    print("="*60)
    print("TanitJobs Scraper (Selenium)")
    print("="*60)
    
    # Scrape the jobs
    jobs = scrape_tanitjobs()
    
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE - Total jobs: {len(jobs)}")
    print("="*60)
    
    if jobs:
        # Save to JSON
        save_to_json(jobs)

        
        # Save to CSV
        save_to_csv(jobs)
        
        # Print first 3 jobs as sample
        print("\n--- Sample Jobs ---")
        for i, job in enumerate(jobs[:3], 1):
            print(f"\n{i}. {job.get('title', 'N/A')}")
            print(f"   Company: {job.get('company', 'N/A')}")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   URL: {job.get('url', 'N/A')}")
    else:
        print("\n⚠ No jobs were scraped. Please check the selectors.")
