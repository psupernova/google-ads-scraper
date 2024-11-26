from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from typing import List
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class SearchRequest(BaseModel):
    search_term: str

class AdExtension(BaseModel):
    text: str
    type: str

class Advertisement(BaseModel):
    timestamp: str
    termo_busca: str
    titulo: str
    descricao: str
    link_destino: str
    link_exibido: str
    extensoes: List[AdExtension]

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    return webdriver.Chrome(options=chrome_options)

@app.get("/")
async def root():
    return {"message": "Google Ads Scraper API is running"}

@app.get("/test")
async def test():
    try:
        driver = setup_driver()
        driver.quit()
        return {"message": "Selenium setup successful"}
    except Exception as e:
        logger.error(f"Selenium setup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape")
async def scrape(request: SearchRequest):
    logger.info(f"Received search request for term: {request.search_term}")
    try:
        driver = setup_driver()
        logger.info("Driver setup successful")
        
        url = f"https://www.google.com.br/search?q={request.search_term}&hl=pt-BR&gl=BR"
        logger.info(f"Accessing URL: {url}")
        
        driver.get(url)
        logger.info("Page loaded successfully")
        
        # Esperar pelos anúncios
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.uEierd"))
        )
        logger.info("Found ad elements")
        
        ads = driver.find_elements(By.CSS_SELECTOR, "div.uEierd")
        results = []
        
        for index, ad in enumerate(ads):
            try:
                titulo = ad.find_element(By.CSS_SELECTOR, "div.CCgQ5").text
                descricao = ad.find_element(By.CSS_SELECTOR, "div.MUxGbd.yDYNvb.lyLwlc").text
                link_element = ad.find_element(By.CSS_SELECTOR, "a.sVXRqc")
                link_destino = link_element.get_attribute("href")
                link_exibido = ad.find_element(By.CSS_SELECTOR, "span.VuuXrf").text
                
                extensoes = []
                try:
                    extension_elements = ad.find_elements(By.CSS_SELECTOR, "span.r0bn4c.rQMQod")
                    for ext in extension_elements:
                        extensoes.append(AdExtension(
                            text=ext.text,
                            type="extension"
                        ))
                except Exception as e:
                    logger.warning(f"Failed to extract extensions for ad {index}: {str(e)}")
                
                results.append(Advertisement(
                    timestamp=datetime.now().isoformat(),
                    termo_busca=request.search_term,
                    titulo=titulo,
                    descricao=descricao,
                    link_destino=link_destino,
                    link_exibido=link_exibido,
                    extensoes=extensoes
                ))
                logger.info(f"Successfully processed ad {index}")
            except Exception as e:
                logger.error(f"Error processing ad {index}: {str(e)}")
                continue
        
        driver.quit()
        logger.info(f"Scraping completed. Found {len(results)} ads")
        return results
    
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
