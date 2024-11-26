// Função principal para fazer o scraping
async function scrapeGoogleAds(items) {
    // Pegar dados do input
    const searchTerm = items[0].json.search_term;
    const apiKey = items[0].json.SCRAPEOPS_API_KEY;
    
    if (!searchTerm || !apiKey) {
        return [{
            json: {
                erro: 'search_term e SCRAPEOPS_API_KEY são obrigatórios',
                timestamp: new Date().toISOString()
            }
        }];
    }

    try {
        // Preparar URL do Google
        const targetUrl = `https://www.google.com.br/search?q=${encodeURIComponent(searchTerm)}&hl=pt-BR&gl=BR`;
        
        // Construir URL do ScrapeOps manualmente
        const scrapeopsUrl = 'https://proxy.scrapeops.io/v1/?' + [
            `api_key=${encodeURIComponent(apiKey)}`,
            `url=${encodeURIComponent(targetUrl)}`,
            'country=br',
            'render_js=true'
        ].join('&');

        // Fazer a requisição
        const response = await $http.get(scrapeopsUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
            }
        });

        const html = response.data;

        // Encontrar anúncios usando regex
        const results = [];
        const adsPattern = /<div class="uEierd">(.*?)<\/div>\s*<\/div>\s*<\/div>/g;
        let adMatch;

        while ((adMatch = adsPattern.exec(html)) !== null) {
            const adHtml = adMatch[1];
            
            // Extrair dados usando regex
            const titulo = extractText(/<div class="CCgQ5[^"]*"[^>]*>(.*?)<\/div>/, adHtml);
            const descricao = extractText(/<div class="MUxGbd yDYNvb lyLwlc"[^>]*>(.*?)<\/div>/, adHtml);
            
            if (titulo || descricao) {
                // Extrair extensões
                const extensoes = [];
                const extensoesPattern = /<span class="r0bn4c rQMQod"[^>]*>(.*?)<\/span>/g;
                let extMatch;
                
                while ((extMatch = extensoesPattern.exec(adHtml)) !== null) {
                    extensoes.push(extMatch[1].trim());
                }

                results.push({
                    json: {
                        timestamp: new Date().toISOString(),
                        termo_busca: searchTerm,
                        titulo: titulo,
                        descricao: descricao,
                        link_destino: extractText(/<a class="sVXRqc"[^>]*href="([^"]*)"/, adHtml),
                        link_exibido: extractText(/<span class="VuuXrf"[^>]*>(.*?)<\/span>/, adHtml),
                        extensoes: extensoes
                    }
                });
            }
        }

        if (results.length === 0) {
            return [{
                json: {
                    erro: 'Nenhum anúncio encontrado',
                    termo_busca: searchTerm,
                    timestamp: new Date().toISOString()
                }
            }];
        }

        return results;

    } catch (error) {
        return [{
            json: {
                erro: error.message,
                termo_busca: searchTerm,
                timestamp: new Date().toISOString()
            }
        }];
    }
}

// Função auxiliar para extrair texto usando regex
function extractText(pattern, text) {
    const match = text.match(pattern);
    return match ? match[1].trim() : '';
}

// Exportar a função para o n8n
return await scrapeGoogleAds(items);
