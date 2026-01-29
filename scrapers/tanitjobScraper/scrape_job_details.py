import json
from pathlib import Path
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

DATA_FILE = Path("tanitjobs_data.json")
CS_JOBS_DETAILS_FILE = Path("cs_jobs_details.json")

def scrape_job_detail(driver, job_url):
    """Scrape detailed information from a job detail page"""
    try:
        driver.get(job_url)
        
        # Wait longer for Cloudflare to pass and page to fully load
        time.sleep(3)
        
        # Wait for the main content to load (infos_job_details or details-body)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "details-header__title"))
            )
        except:
            pass
        
        # Additional wait to ensure all content is rendered
        time.sleep(1)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check if we got a Cloudflare block page
        if 'Just a moment' in html or 'Checking your browser' in html:
            print(f"    Warning: Cloudflare challenge detected")
            return {}
        
        details = {}
        
        # Extract applicants and open positions from header
        applicants_div = soup.find('div', class_='applicants-num')
        details['applicants'] = applicants_div.get_text(strip=True) if applicants_div else None
        
        vacancies_span = soup.find('span', class_='vacancies-num')
        details['open_positions'] = vacancies_span.get_text(strip=True) if vacancies_span else None
        
        # Extract job info details (employment type, experience, education, salary, languages, etc.)
        job_info = {}
        infos_section = soup.find('div', class_='infos_job_details')
        if infos_section:
            dl_elements = infos_section.find_all('dl')
            for dl in dl_elements:
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd:
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    job_info[key] = value
        
        details['job_info'] = job_info
        
        # Extract job descriptions from details-body__content sections
        content_sections = soup.find_all('div', class_='details-body__content content-text')
        if len(content_sections) > 0:
            details['job_description'] = content_sections[0].get_text(strip=True)
        else:
            details['job_description'] = None
            
        if len(content_sections) > 1:
            details['profile_requirements'] = content_sections[1].get_text(strip=True)
        else:
            details['profile_requirements'] = None
        
        # Show success if we got data
        if job_info or details['job_description']:
            print(f"    ✓ Successfully scraped")
        
        return details
        
    except Exception as e:
        print(f"    Error: {e}")
        return {}

def main():
    # Load all jobs
    data = json.load(open(DATA_FILE, encoding='utf-8'))
    
    # Filter only CS jobs
    cs_jobs = [job for job in data if job.get('is_cs')]
    print(f"Found {len(cs_jobs)} CS jobs to scrape details for\n")
    
    # Initialize driver
    driver = uc.Chrome()
    cs_jobs_detailed = []
    
    try:
        # First, visit the main TanitJobs page to pass Cloudflare
        print("Passing Cloudflare on main page...")
        driver.get("https://www.tanitjobs.com/")
        time.sleep(5)  # Wait for Cloudflare to pass
        print("Cloudflare passed, starting to scrape job details...\n")
        
        for i, job in enumerate(cs_jobs):
            print(f"[{i+1}/{len(cs_jobs)}] Scraping: {job['title']}")
            job_url = job.get('url')
            
            if job_url:
                details = scrape_job_detail(driver, job_url)
                
                # Combine original job info with scraped details
                job_with_details = {
                    'title': job.get('title'),
                    'company': job.get('company'),
                    'location': job.get('location'),
                    'url': job.get('url'),
                    'description': job.get('description'),
                    'date_posted': job.get('date_posted'),
                    'cs_category': job.get('cs_category'),
                    'source': job.get('source'),
                    'applicants': details.get('applicants'),
                    'open_positions': details.get('open_positions'),
                    'job_info': details.get('job_info'),
                    'job_description': details.get('job_description'),
                    'profile_requirements': details.get('profile_requirements')
                }
                cs_jobs_detailed.append(job_with_details)
                time.sleep(2)  # Longer delay between requests
            else:
                print(f"    No URL found")
    
    finally:
        driver.quit()
    
    # Save CS jobs with details to separate file
    CS_JOBS_DETAILS_FILE.write_text(json.dumps(cs_jobs_detailed, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nDone: saved {len(cs_jobs_detailed)} CS jobs to {CS_JOBS_DETAILS_FILE}")

if __name__ == "__main__":
    main()



