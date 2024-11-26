from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Lista de User-Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

class AdExtension:
    def __init__(self, text, type):
        self.text = text
        self.type = type

class Advertisement:
    def __init__(self, timestamp, termo_busca, titulo, descricao, link_destino, link_exibido, extensoes):
        self.timestamp = timestamp
        self.termo_busca = termo_busca
        self.titulo = titulo
        self.descricao = descricao
        self.link_destino = link_destino
        self.link_exibido = link_exibido
        self.extensoes = extensoes

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    return webdriver.Chrome(options=chrome_options)

@app.route('/')
def home():
    return jsonify({
        "message": "Google Ads Scraper API",
        "endpoints": {
            "/": "Esta mensagem",
            "/scrape": "POST - Recebe search_term e retorna anúncios do Google"
        }
    })

@app.route('/scrape', methods=['POST'])
def scrape_ads():
    try:
        data = request.get_json()
        if not data or 'search_term' not in data:
            return jsonify({"error": "search_term é obrigatório"}), 400

        search_term = data['search_term']
        logger.info(f"Iniciando scraping para: {search_term}")

        # Construir URL de pesquisa
        search_url = f"https://www.google.com.br/search?q={search_term}&hl=pt-BR&gl=BR"
        
        # Fazer requisição
        driver = setup_driver()
        driver.get(search_url)
        
        # Esperar pelos anúncios
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.uEierd"))
        )
        
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
                    termo_busca=search_term,
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
        return jsonify({
            "success": True,
            "search_term": search_term,
            "ads_count": len(results),
            "ads": [
                {
                    "timestamp": ad.timestamp,
                    "search_term": ad.termo_busca,
                    "title": ad.titulo,
                    "description": ad.descricao,
                    "destination_link": ad.link_destino,
                    "displayed_link": ad.link_exibido,
                    "extensions": [
                        {
                            "text": ext.text,
                            "type": ext.type
                        } for ext in ad.extensoes
                    ]
                } for ad in results
            ]
        })

    except Exception as e:
        logger.error(f"Erro ao fazer scraping: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run()
