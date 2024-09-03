import os
from flask import Flask, jsonify, request, render_template, redirect, url_for
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)

# Armazena os últimos 10 links pesquisados
recent_searches = []

def fetch_article(url):
    # Configurando o Selenium WebDriver com Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Executar em modo headless, sem abrir a janela do navegador
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # Ajuste o caminho conforme necessário

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Navega até a URL e obtém o conteúdo
    driver.get(url)

    # Simula clique no botão "Veja Mais" em sites da PEGN e Valor Econômico
    if "revistapegn.globo.com" in url or "valor.globo.com" in url:
        try:
            see_more_button = driver.find_element("id", "mc-read-more-btn")
            driver.execute_script("arguments[0].click();", see_more_button)
        except Exception as e:
            print(f"Erro ao clicar no botão 'Veja Mais': {str(e)}")

    # Obtém o conteúdo da página após o carregamento completo
    page_source = driver.page_source
    driver.quit()  # Fecha o navegador

    return BeautifulSoup(page_source, 'html.parser')

def extract_meta_data(soup):
    title = soup.find("meta", property="og:title") or soup.title
    description = soup.find("meta", property="og:description")
    title = title["content"] if title else "Título não encontrado"
    description = description["content"] if description else "Descrição não encontrada"
    return title, description

def extract_content(soup, selectors):
    content = ""
    for selector in selectors:
        content_div = soup.select_one(selector)
        if content_div:
            paragraphs = content_div.find_all("p")
            content += "\n\n".join([p.get_text() for p in paragraphs])
            content += "\n\n"
    return content or "Conteúdo do artigo não encontrado"

def extract_image(soup):
    image = soup.find("meta", property="og:image")
    if image:
        return image.get("content", "Imagem não encontrada")
    image_tag = soup.find("img")
    return image_tag["src"] if image_tag and "src" in image_tag.attrs else "Imagem não encontrada"

def extract_author_date(soup, author_selector, date_selector):
    author_tag = soup.select_one(author_selector)
    date_tag = soup.select_one(date_selector)
    author = author_tag.get_text().strip() if author_tag else "Autor não encontrado"
    published_date = date_tag.get_text().strip() if date_tag else "Data de publicação não encontrada"
    return author, published_date

def extract_source(url):
    if "revistapegn.globo.com" in url:
        return "PEGN"
    elif "braziljournal.com" in url:
        return "Brazil Journal"
    elif "neofeed.com.br" in url:
        return "NeoFeed"
    elif "pipelinevalor.globo.com" in url or "valor.globo.com" in url:
        return "Valor Econômico"
    elif "exame.com" in url:
        return "Exame"
    elif "startupi.com.br" in url:
        return "Startupi"
    elif "startups.com.br" in url:
        return "Startups"
    else:
        return "Fonte Desconhecida"

def scrape_source(url, soup):
    if "revistapegn.globo.com" in url or "valor.globo.com" in url:
        # Extrai conteúdo de ambas as partes (antes e depois do paywall)
        content = extract_content(soup, [
            "div.no-paywall",  # Parte antes do paywall
            "div.wall.protected-content"  # Parte depois do paywall
        ])
        author, published_date = extract_author_date(soup, 
            "div.content-publication-data__from span[itemprop='name']", 
            "time[itemprop='datePublished']")

    elif "braziljournal.com" in url:
        content = extract_content(soup, ["div.post-content-text"])
        author, published_date = extract_author_date(soup, 
            "span.pp-author-boxes-name a", 
            "time.post-time")

    elif "neofeed.com.br" in url:
        # Atualiza a extração de autor e data no NeoFeed
        content = extract_content(soup, ["div.box-content.post-content.td-post-content"])
        author, published_date = extract_author_date(soup, 
            "span.autor_name",  # Ajuste para autor
            "span.date.interna")  # Ajuste para data

    elif "pipelinevalor.globo.com" in url:
        content = extract_content(soup, ["div.mc-column.content-text.active-extra-styles"])
        author, published_date = extract_author_date(soup, 
            "div.content-publication-data__from span[itemprop='name']", 
            "time[itemprop='datePublished']")

    elif "exame.com" in url:
        content = extract_content(soup, ["div#news-body"])
        author, published_date = extract_author_date(soup, 
            "a.m-0.p-0.text-colors-text.lg\\:text-pretty.label-small.hover\\:underline", 
            "p.m-0.p-0.text-colors-text.lg\\:text-pretty.body-small")

    elif "startupi.com.br" in url:
        content = extract_content(soup, ["div.post-content"])
        author, published_date = extract_author_date(soup, 
            "a[rel='author']", 
            "time.post-date")

    elif "startups.com.br" in url:
        content = extract_content(soup, ["div.TheContent"])
        author, published_date = extract_author_date(soup, 
            "a[title]",  # Seleciona o autor
            "time")  # Seleciona o elemento de data

    else:
        content, author, published_date = "Fonte não reconhecida", "Autor desconhecido", "Data desconhecida"

    return content, author, published_date

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        return redirect(url_for('scrape', url=url, new_search=True))
    return render_template('index.html', recent_searches=recent_searches)

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    new_search = request.args.get('new_search', default=False, type=bool)

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        soup = fetch_article(url)
        title, description = extract_meta_data(soup)
        content, author, published_date = scrape_source(url, soup)
        image_url = extract_image(soup)
        source = extract_source(url)  # Extraímos o veículo aqui

        if new_search:
            recent_searches.insert(0, {
                "title": title,
                "url": url,
                "source": source,  # Adicionamos o veículo à pesquisa recente
                "published_date": published_date,
                "author": author
            })
            if len(recent_searches) > 10:
                recent_searches.pop()

        json_summary = {
            "title": title,
            "description": description,
            "author": author,
            "published_date": published_date,
            "image_url": image_url
        }

        return render_template('article.html', title=title, description=description, 
                               author=author, published_date=published_date, 
                               content=content, image_url=image_url,
                               json_summary=json_summary, url=url)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
