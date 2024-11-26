from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import random
import time
from urllib.parse import quote
import urllib3

# Desabilitar avisos SSL
urllib3.disable_warnings()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuração do scrape.do
SCRAPE_DO_TOKEN = "292e31943f0a4e9d83ecd521934fb885ee24c38eac6"

def make_request(url, max_retries=3):
    # URL da API do scrape.do
    scrape_do_url = f"https://api.scrape.do/?token={SCRAPE_DO_TOKEN}&url={quote(url)}"
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Tentativa {attempt + 1} de {max_retries} para URL: {url}")
            
            response = requests.get(
                scrape_do_url,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                error_msg = f"Erro na requisição: {response.status_code}"
                try:
                    error_msg += f" - {response.json()}"
                except:
                    error_msg += f" - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 5)
                logger.info(f"Aguardando {wait_time:.2f} segundos antes da próxima tentativa")
                time.sleep(wait_time)
            else:
                raise

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
        search_url = f"https://www.google.com.br/search?q={quote(search_term)}&hl=pt-BR&gl=BR"
        
        # Fazer requisição
        html_content = make_request(search_url)
        
        # Parsear HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Encontrar anúncios
        ads = []
        ad_divs = soup.find_all(['div', 'li'], {'class': ['uEierd', 'ads-fr']})
        
        for ad in ad_divs:
            ad_data = {
                "timestamp": datetime.now().isoformat(),
                "search_term": search_term,
                "title": "",
                "description": "",
                "destination_link": "",
                "displayed_link": "",
                "extensions": []
            }
            
            # Título
            title_elem = ad.find(['div', 'h3'], {'role': 'heading'}) or ad.find(['div', 'h3'], {'class': ['CCgQ5', 'cfxYMc']})
            if title_elem:
                ad_data["title"] = title_elem.get_text().strip()
            
            # Link de destino
            link_elem = ad.find('a')
            if link_elem:
                ad_data["destination_link"] = link_elem.get('href', '').strip()
            
            # Link exibido
            displayed_link = ad.find('span', {'class': ['VuuXrf', 'qzEoUe']})
            if displayed_link:
                ad_data["displayed_link"] = displayed_link.get_text().strip()
            
            # Descrição
            description = ad.find('div', {'class': ['VwiC3b', 'yDYNvb']}) or ad.find('div', {'class': 'MUxGbd'})
            if description:
                ad_data["description"] = description.get_text().strip()
            
            # Extensões
            extensions = ad.find_all(['div', 'span'], {'class': ['MUxGbd', 'r0bn4c']})
            ad_data["extensions"] = [ext.get_text().strip() for ext in extensions if ext.get_text().strip()]
            
            if ad_data["title"] or ad_data["description"]:  # Só adiciona se tiver pelo menos título ou descrição
                ads.append(ad_data)
        
        if not ads:
            logger.warning("Nenhum anúncio encontrado na página")
            # Para debug, vamos salvar o HTML quando não encontrar anúncios
            with open('debug.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            return jsonify({
                "success": False,
                "error": "Nenhum anúncio encontrado para este termo"
            }), 404
        
        logger.info(f"Encontrados {len(ads)} anúncios")
        return jsonify({
            "success": True,
            "search_term": search_term,
            "ads_count": len(ads),
            "ads": ads
        })

    except Exception as e:
        logger.error(f"Erro ao fazer scraping: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run()
