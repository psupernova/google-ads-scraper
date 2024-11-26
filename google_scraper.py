from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_scraping_ant_response(url):
    api_key = "72e2a2bb8f724d0586b5596fb8b51612"
    scraping_ant_url = 'https://api.scrapingant.com/v2/general'
    
    headers = {
        'x-api-key': api_key
    }
    
    params = {
        'url': url,
        'proxy_country': 'br'
    }
    
    response = requests.get(scraping_ant_url, headers=headers, params=params)
    return response

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
        
        # Fazer requisição usando Scraping Ant
        response = get_scraping_ant_response(search_url)
        
        if response.status_code != 200:
            logger.error(f"Erro Scraping Ant: Status {response.status_code}, Resposta: {response.text}")
            return jsonify({
                "success": False,
                "error": f"Erro ao fazer requisição: {response.status_code}",
                "details": response.text
            }), 500
        
        # Parsear HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
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
