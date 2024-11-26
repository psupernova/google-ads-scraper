from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import random
import time
from urllib.parse import quote
import urllib3
import json
from fake_useragent import UserAgent
import redis
import hashlib
import os

# Desabilitar avisos SSL
urllib3.disable_warnings()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuração do Redis
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# Configuração do scrape.do
SCRAPE_DO_TOKEN = "292e31943f0a4e9d83ecd521934fb885ee24c38eac6"

# Lista de proxies residenciais do scrape.do
PROXY_LIST = [
    "br.residential.proxy.scrape.do",
    "us.residential.proxy.scrape.do",
    "uk.residential.proxy.scrape.do",
    "de.residential.proxy.scrape.do",
    "fr.residential.proxy.scrape.do"
]

# Configuração do cache
CACHE_EXPIRATION = 3600  # 1 hora em segundos

def get_cache_key(search_term):
    """Gera uma chave única para o cache baseada no termo de pesquisa"""
    return f"google_ads:{hashlib.md5(search_term.encode()).hexdigest()}"

def get_from_cache(search_term):
    """Tenta obter resultados do cache"""
    try:
        cache_key = get_cache_key(search_term)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit para termo: {search_term}")
            return json.loads(cached_data)
            
        logger.info(f"Cache miss para termo: {search_term}")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao acessar cache: {str(e)}")
        return None

def save_to_cache(search_term, data):
    """Salva os resultados no cache"""
    try:
        cache_key = get_cache_key(search_term)
        redis_client.setex(
            cache_key,
            CACHE_EXPIRATION,
            json.dumps(data)
        )
        logger.info(f"Dados salvos no cache para termo: {search_term}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar no cache: {str(e)}")

def get_random_headers():
    ua = UserAgent()
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Sec-Ch-Ua': '"Chromium";v="119", "Not?A_Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }

def make_request(url, max_retries=5):
    for attempt in range(max_retries):
        try:
            # Escolher um proxy aleatório
            proxy = random.choice(PROXY_LIST)
            
            # Configurar proxy do scrape.do
            proxies = {
                'http': f'http://{SCRAPE_DO_TOKEN}:@{proxy}:8080',
                'https': f'http://{SCRAPE_DO_TOKEN}:@{proxy}:8080'
            }
            
            # Delay aleatório entre requisições
            wait_time = random.uniform(5, 15)
            logger.info(f"Aguardando {wait_time:.2f} segundos antes da requisição")
            time.sleep(wait_time)
            
            logger.info(f"Tentativa {attempt + 1} de {max_retries} usando proxy: {proxy}")
            
            # Fazer a requisição com headers aleatórios
            response = requests.get(
                url,
                headers=get_random_headers(),
                proxies=proxies,
                verify=False,
                timeout=30
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code == 429:  # Too Many Requests
                logger.warning("Limite de requisições atingido, aguardando mais tempo")
                time.sleep(random.uniform(30, 60))
                continue
                
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
                wait_time = random.uniform(10, 30)
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
        
        # Tentar obter do cache primeiro
        cached_results = get_from_cache(search_term)
        if cached_results:
            logger.info("Retornando resultados do cache")
            return jsonify(cached_results)

        # Construir URL de pesquisa com parâmetros adicionais
        search_url = (
            f"https://www.google.com.br/search?"
            f"q={quote(search_term)}"
            f"&hl=pt-BR"
            f"&gl=BR"
            f"&source=hp"
            f"&ie=UTF-8"
            f"&gbv=1"  # Versão mais simples do Google
        )
        
        # Fazer requisição
        html_content = make_request(search_url)
        
        # Parsear HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Debug: Salvar HTML para análise
        with open('debug.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info("Procurando anúncios...")
        
        # Encontrar anúncios - tentativa com vários seletores
        ads = []
        selectors = [
            {'element': ['div', 'li'], 'class': ['uEierd', 'ads-fr']},
            {'element': 'div', 'class': 'commercial-unit-desktop-top'},
            {'element': 'div', 'class': 'ads-ad'},
            {'element': 'div', 'id': 'tads'},
            {'element': 'div', 'class': 'cu-container'},
            {'element': 'div', 'class': 'g'},  # Seletor mais genérico
            {'element': 'div', 'class': 'adcontainer'}  # Outro seletor comum
        ]
        
        for selector in selectors:
            logger.info(f"Tentando seletor: {selector}")
            elements = soup.find_all(selector['element'], 
                                   class_=selector.get('class'),
                                   id=selector.get('id'))
            logger.info(f"Encontrados {len(elements)} elementos com este seletor")
            
            for ad in elements:
                logger.info(f"Processando elemento: {ad.get('class', '')}")
                ad_data = {
                    "timestamp": datetime.now().isoformat(),
                    "search_term": search_term,
                    "title": "",
                    "description": "",
                    "destination_link": "",
                    "displayed_link": "",
                    "extensions": []
                }
                
                # Título - múltiplas tentativas
                title_selectors = [
                    (['div', 'h3'], {'role': 'heading'}),
                    (['div', 'h3'], {'class': ['CCgQ5', 'cfxYMc']}),
                    ('div', {'class': 'vdQmEd'}),
                    ('div', {'class': 'ad-title'}),
                    ('h3', {})  # Seletor mais genérico
                ]
                
                for title_elem, attrs in title_selectors:
                    title = ad.find(title_elem, attrs)
                    if title:
                        ad_data["title"] = title.get_text().strip()
                        break
                
                # Link de destino - múltiplas tentativas
                link_selectors = [
                    ('a', {}),
                    ('a', {'class': 'ad-link'}),
                    ('a', {'jsname': 'UWckNb'})
                ]
                
                for elem, attrs in link_selectors:
                    link = ad.find(elem, attrs)
                    if link and link.get('href'):
                        ad_data["destination_link"] = link.get('href').strip()
                        break
                
                # Link exibido - múltiplas tentativas
                display_selectors = [
                    ('span', {'class': ['VuuXrf', 'qzEoUe']}),
                    ('div', {'class': 'UdQCqe'}),
                    ('cite', {}),
                    ('span', {'class': 'ad-display-link'})
                ]
                
                for elem, attrs in display_selectors:
                    display = ad.find(elem, attrs)
                    if display:
                        ad_data["displayed_link"] = display.get_text().strip()
                        break
                
                # Descrição - múltiplas tentativas
                desc_selectors = [
                    ('div', {'class': ['VwiC3b', 'yDYNvb']}),
                    ('div', {'class': 'MUxGbd'}),
                    ('div', {'class': 'ad-description'}),
                    ('div', {'class': 'ad-creative'}),
                    ('div', {'class': 'ad-text'})  # Seletor mais genérico
                ]
                
                for elem, attrs in desc_selectors:
                    desc = ad.find(elem, attrs)
                    if desc:
                        ad_data["description"] = desc.get_text().strip()
                        break
                
                # Extensões
                extensions = ad.find_all(['div', 'span'], {'class': ['MUxGbd', 'r0bn4c', 'ad-extension']})
                ad_data["extensions"] = [ext.get_text().strip() for ext in extensions if ext.get_text().strip()]
                
                # Só adiciona se tiver conteúdo relevante
                if any([ad_data["title"], ad_data["description"], ad_data["destination_link"]]):
                    logger.info(f"Anúncio encontrado: {json.dumps(ad_data, ensure_ascii=False)}")
                    ads.append(ad_data)
        
        if not ads:
            logger.warning("Nenhum anúncio encontrado na página")
            return jsonify({
                "success": False,
                "error": "Nenhum anúncio encontrado para este termo",
                "debug_info": {
                    "selectors_tried": selectors,
                    "html_saved": True
                }
            }), 404
        
        # Preparar resposta
        response_data = {
            "success": True,
            "search_term": search_term,
            "ads_count": len(ads),
            "ads": ads,
            "cached": False,
            "cache_expires_in": CACHE_EXPIRATION
        }
        
        # Salvar no cache
        save_to_cache(search_term, response_data)
        
        logger.info(f"Encontrados {len(ads)} anúncios")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Erro ao fazer scraping: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run()
