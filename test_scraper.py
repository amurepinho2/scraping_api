import pytest
from bs4 import BeautifulSoup
from app import scrape_source, fetch_article, extract_source
import json

# URLs reais de teste para cada veículo
test_urls = {
    "NeoFeed": "https://neofeed.com.br/startups/gv-angels-tokeniza-r-50-milhoes-em-investimentos-em-parceria-com-mercado-bitcoin/",
    "PEGN": "https://revistapegn.globo.com/startups/noticia/2024/08/easyjur-capta-r-14-milhao-para-ampliar-tecnologias-e-fortalecer-posicao-no-mercado.ghtml",
    "Valor Econômico": "https://valor.globo.com/financas/criptomoedas/noticia/2024/08/19/startup-superopa-capta-mais-de-r-1-milho-com-dvida-tokenizada.ghtml",
    "Pipeline Valor": "https://pipelinevalor.globo.com/negocios/noticia/amd-faz-aquisicao-de-us-49-bi-para-se-fortalecer-em-disputa-com-nvidia.ghtml",
    "Startups": "https://startups.com.br/rodada-de-investimento/altscore-capta-r-47m-para-expandir-na-america-latina-e-brasil/",
    "Infomoney": "https://www.infomoney.com.br/business/aporte-de-r-100-milhoes-leva-a-beep-saude-a-uma-valorizacao-bilionaria/",
    "Brazil Journal": "https://braziljournal.com/unico-compra-startups-no-mexico-e-em-dubai-uma-delas-e-pra-combater-o-deepfake/",
    "Startupi": "https://startupi.com.br/autoagromachines-aporta-8-milhoes-reflorestamento/",
    "Exame": "https://exame.com/negocios/exclusivo-grupo-marista-prepara-fundo-de-r-30-mi-para-investir-em-startups-de-educacao-e-saude/"
}

# Função para salvar status em um arquivo JSON
def save_status(status):
    try:
        with open("status.json", "w") as f:
            json.dump(status, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar status.json: {e}")

# Função para testar o scraping de uma URL real
def test_url(url, vehicle):
    try:
        html_raw = fetch_article(url)  # Faz a requisição HTTP para buscar o HTML
        soup = BeautifulSoup(html_raw, 'html.parser')
        content, author, published_date = scrape_source(url, soup)  # Extração
        return content, author, published_date, "OK"
    except Exception as e:
        return None, None, None, f"Erro: {str(e)}"

# Função principal para rodar os testes em URLs reais e salvar o status
def run_tests_and_save_status():
    status = {}

    for vehicle, url in test_urls.items():
        print(f"Testando {vehicle}...")
        content, author, published_date, result = test_url(url, vehicle)
        
        if result == "OK":
            print(f"{vehicle}: OK")
        else:
            print(f"{vehicle}: {result}")
        
        # Salva o resultado no status
        status[vehicle] = {
            "status": result,
            "author": author,
            "published_date": published_date
        }

    # Salva o status no arquivo JSON
    save_status(status)

# Executa os testes e salva o status
if __name__ == "__main__":
    run_tests_and_save_status()
