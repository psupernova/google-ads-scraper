from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import random
import logging
from datetime import datetime
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Lista de User-Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Edge/119.0.0.0'
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

def get_proxy():
    try:
        response = requests.get('https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=BR&ssl=all&anonymity=all')
        proxies = response.text.strip().split('\n')
        if proxies:
            proxy = random.choice(proxies)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
    except Exception as e:
        logger.error(f"Erro ao obter proxy: {str(e)}")
    return None

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
        search_url = f"https://www.google.com.br/search?q={search_term}&hl=pt-BR&gl=BR&uule=w+CAIQICINVW5pdGVkIFN0YXRlcw"
        
        # Tentar algumas vezes com diferentes proxies
        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = get_random_headers()
                proxies = get_proxy()
                
                # Fazer requisição
                response = requests.get(
                    search_url, 
                    headers=headers,
                    proxies=proxies,
                    timeout=30,
                    verify=False  # Ignorar SSL para proxies
                )
                response.raise_for_status()
                
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
                
                if ads:  # Se encontrou anúncios, retorna
                    logger.info(f"Encontrados {len(ads)} anúncios")
                    return jsonify({
                        "success": True,
                        "search_term": search_term,
                        "ads_count": len(ads),
                        "ads": ads
                    })
                
                logger.warning(f"Tentativa {attempt + 1}: Nenhum anúncio encontrado, tentando novamente...")
                time.sleep(random.uniform(1, 3))  # Espera aleatória entre tentativas
                
            except Exception as e:
                logger.error(f"Erro na tentativa {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:  # Se não for a última tentativa
                    time.sleep(random.uniform(1, 3))  # Espera aleatória entre tentativas
                continue
        
        # Se chegou aqui, todas as tentativas falharam
        return jsonify({
            "success": False,
            "error": "Não foi possível encontrar anúncios após várias tentativas"
        }), 500

    except Exception as e:
        logger.error(f"Erro ao fazer scraping: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run()
