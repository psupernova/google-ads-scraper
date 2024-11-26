from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import random
import logging
from datetime import datetime

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
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
    }

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
        search_url = f"https://www.google.com/search?q={search_term}&hl=pt-BR&gl=BR"
        
        # Fazer requisição
        response = requests.get(search_url, headers=get_random_headers())
        response.raise_for_status()
        
        # Parsear HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Encontrar anúncios
        ads = []
        ad_divs = soup.find_all('div', {'class': 'uEierd'})
        
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
            title_elem = ad.find('div', {'role': 'heading'})
            if title_elem:
                ad_data["title"] = title_elem.get_text()
            
            # Link de destino
            link_elem = ad.find('a')
            if link_elem:
                ad_data["destination_link"] = link_elem.get('href', '')
            
            # Link exibido
            displayed_link = ad.find('span', {'class': 'VuuXrf'})
            if displayed_link:
                ad_data["displayed_link"] = displayed_link.get_text()
            
            # Descrição
            description = ad.find('div', {'class': 'VwiC3b'})
            if description:
                ad_data["description"] = description.get_text()
            
            # Extensões
            extensions = ad.find_all('div', {'class': 'MUxGbd'})
            ad_data["extensions"] = [ext.get_text() for ext in extensions if ext.get_text()]
            
            ads.append(ad_data)
        
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
