const express = require('express');
const puppeteer = require('puppeteer');
const app = express();

app.use(express.json());

async function scrapeGoogleAds(searchTerm) {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        
        // Configurar como navegador desktop
        await page.setViewport({ width: 1366, height: 768 });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36');
        
        // Ir para o Google
        await page.goto(`https://www.google.com.br/search?q=${encodeURIComponent(searchTerm)}&hl=pt-BR&gl=BR`, {
            waitUntil: 'networkidle0'
        });

        // Extrair anúncios
        const ads = await page.evaluate(() => {
            const results = [];
            
            // Pegar todos os containers de anúncios
            const adContainers = document.querySelectorAll('div.uEierd');
            
            adContainers.forEach(ad => {
                const titulo = ad.querySelector('div[role="heading"]')?.innerText || '';
                const descricao = ad.querySelector('div.MUxGbd')?.innerText || '';
                
                if (titulo || descricao) {
                    // Pegar extensões
                    const extensoesElements = ad.querySelectorAll('span.r0bn4c.rQMQod');
                    const extensoes = Array.from(extensoesElements).map(ext => ext.innerText.trim());
                    
                    results.push({
                        timestamp: new Date().toISOString(),
                        titulo,
                        descricao,
                        link_destino: ad.querySelector('a.sVXRqc')?.href || '',
                        link_exibido: ad.querySelector('span.VuuXrf')?.innerText || '',
                        extensoes
                    });
                }
            });
            
            return results;
        });

        return ads;

    } catch (error) {
        console.error('Erro ao fazer scraping:', error);
        throw error;
    } finally {
        await browser.close();
    }
}

app.post('/scrape', async (req, res) => {
    try {
        const { search_term } = req.body;
        
        if (!search_term) {
            return res.status(400).json({
                erro: 'search_term é obrigatório',
                timestamp: new Date().toISOString()
            });
        }
        
        const results = await scrapeGoogleAds(search_term);
        
        if (results.length === 0) {
            return res.status(404).json({
                erro: 'Nenhum anúncio encontrado',
                termo_busca: search_term,
                timestamp: new Date().toISOString()
            });
        }
        
        res.json(results.map(result => ({
            json: {
                ...result,
                termo_busca: search_term
            }
        })));
        
    } catch (error) {
        res.status(500).json({
            erro: error.message,
            termo_busca: req.body.search_term,
            timestamp: new Date().toISOString()
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
});
