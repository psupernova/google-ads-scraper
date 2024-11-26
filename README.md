# Google Ads Scraper API

API para fazer scraping de anúncios do Google Ads usando Python, FastAPI e Selenium.

## Características

- Scraping de anúncios do Google Ads usando Selenium
- API REST com FastAPI
- Containerização com Docker
- Suporte a execução em ambientes cloud

## Endpoints

### POST /scrape

Realiza o scraping dos anúncios do Google baseado no termo de busca.

**Request Body:**
```json
{
    "search_term": "seu termo de busca aqui"
}
```

**Response:**
```json
[
    {
        "timestamp": "2023-11-15T10:00:00",
        "termo_busca": "seu termo de busca aqui",
        "titulo": "Título do anúncio",
        "descricao": "Descrição do anúncio",
        "link_destino": "https://...",
        "link_exibido": "www.exemplo.com",
        "extensoes": [
            {
                "text": "Texto da extensão",
                "type": "extension"
            }
        ]
    }
]
```

## Como usar

### Localmente

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute a aplicação:
```bash
uvicorn google_scraper:app --host 0.0.0.0 --port 8000
```

### Com Docker

1. Construa a imagem:
```bash
docker build -t google-ads-scraper .
```

2. Execute o container:
```bash
docker run -p 8000:8000 google-ads-scraper
```

## Integração com n8n

Para integrar com n8n, use o nó HTTP Request com as seguintes configurações:

1. Method: POST
2. URL: http://seu-servidor:8000/scrape
3. Body:
```json
{
    "search_term": "{{$node.previous_node.data.search_term}}"
}
```

## Documentação da API

Após iniciar o servidor, acesse a documentação interativa em:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
