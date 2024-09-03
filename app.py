import os
import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, abort
from bs4 import BeautifulSoup
import requests
from dateutil import parser
import re

app = Flask(__name__)

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Armazena os últimos 10 links pesquisados
recent_searches = []

# Mapeamento de meses em português para inglês
MONTHS_PT_BR = {
    "janeiro": "January",
    "fevereiro": "February",
    "março": "March",
    "abril": "April",
    "maio": "May",
    "junho": "June",
    "julho": "July",
    "agosto": "August",
    "setembro": "September",
    "outubro": "October",
    "novembro": "November",
    "dezembro": "December"
}

def fetch_article(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

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

def sanitize_date(date_str):
    try:
        parsed_date = parser.parse(date_str)
        return parsed_date.isoformat()
    except Exception as e:
        logger.warning(f"Erro ao converter a data: {date_str} - {str(e)}")
        return date_str

def parse_custom_date_format(date_str, source):
    try:
        if source == "Exame":
            # Padrão para Exame: "Publicado em 21 de agosto de 2024 às 11h29."
            match = re.search(r"Publicado em (\d{2}) de (\w+) de (\d{4}) às (\d{2})h(\d{2})", date_str)
            if match:
                day, month_pt, year, hour, minute = match.groups()
                month = MONTHS_PT_BR.get(month_pt.lower(), month_pt)
                date_str = f"{day} {month} {year} {hour}:{minute}"
                return sanitize_date(date_str)

        elif source == "Brazil Journal" or source == "Startups":
            match = re.search(r"(\d{2}) de (\w+) de (\d{4})", date_str)
            if match:
                day, month_pt, year = match.groups()
                month = MONTHS_PT_BR.get(month_pt.lower(), month_pt)
                date_str = f"{day} {month} {year}"
                return sanitize_date(date_str)
        
        return sanitize_date(date_str)
    except Exception as e:
        logger.warning(f"Erro ao formatar data personalizada: {date_str} - {str(e)}")
        return date_str

def extract_author_date(soup, author_selector, date_selector, source=None):
    author_tag = soup.select_one(author_selector)
    date_tag = soup.select_one(date_selector)

    published_date = date_tag.get_text().strip() if date_tag else "Data de publicação não encontrada"
    if source:
        published_date = parse_custom_date_format(published_date, source)
    else:
        published_date = sanitize_date(published_date)

    author = author_tag.get_text().strip() if author_tag else "Autor não encontrado"
    
    # Se o autor for extraído do título do link, remova "Por" e outros prefixos indesejados
    if author_tag and author_tag.get('title'):
        author = author_tag['title'].strip()
    
    return author, published_date

def extract_source(url):
    if "revistapegn.globo.com" in url:
        return "PEGN"
    elif "braziljournal.com" in url:
        return "Brazil Journal"
    elif "neofeed.com.br" in url:
        return "NeoFeed"
    elif "pipelinevalor.globo.com" in url:
        return "Pipeline Valor"
    elif "valor.globo.com" in url:
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
    source = extract_source(url)

    if source == "PEGN":
        content = extract_content(soup, ["div.no-paywall", "div.wall.protected-content"])
        author, published_date = extract_author_date(soup, 
            "address[itemprop='author'] span[itemprop='name']",  # Ajuste para autor no PEGN
            "time[itemprop='datePublished']")

    elif source == "Brazil Journal":
        content = extract_content(soup, ["div.post-content-text"])
        author, published_date = extract_author_date(soup, 
            "span.pp-author-boxes-name a", 
            "time.post-time", source="Brazil Journal")

    elif source == "NeoFeed":
        content = extract_content(soup, ["div.box-content.post-content.td-post-content"])
        author, published_date = extract_author_date(soup, 
            "span.autor_name", 
            "span.date.interna")

    elif source == "Pipeline Valor":
        content = extract_content(soup, ["div.no-paywall", "div.wall.protected-content"])
        author, published_date = extract_author_date(soup, 
            "address[itemprop='author'] span[itemprop='name']", 
            "time[itemprop='datePublished']")

    elif source == "Valor Econômico":
        content = extract_content(soup, ["div.no-paywall", "div.wall.protected-content"])
        author, published_date = extract_author_date(soup, 
            "address[itemprop='author'] span[itemprop='name']", 
            "time[itemprop='datePublished']")

    elif source == "Exame":
        content = extract_content(soup, ["div#news-body"])
        author, published_date = extract_author_date(soup, 
            "a.m-0.p-0.text-colors-text.lg\\:text-pretty.label-small.hover\\:underline", 
            "p.m-0.p-0.text-colors-text.lg\\:text-pretty.body-small", source="Exame")

    elif source == "Startupi":
        content = extract_content(soup, ["div.post-content"])
        author, published_date = extract_author_date(soup, 
            "a[rel='author']", 
            "time.post-date")

    elif source == "Startups":
        content = extract_content(soup, ["div.TheContent"])
        author, published_date = extract_author_date(soup, 
            "a[title]",  # Seleciona o autor
            "time", source="Startups")

    else:
        content, author, published_date = "Fonte não reconhecida", "Autor desconhecido", "Data desconhecida"

    return content, author, published_date

@app.before_request
def block_invalid_requests():
    if request.method not in ['GET', 'POST']:
        logger.warning(f"Blocked invalid request method: {request.method}")
        abort(405)
    
    if request.endpoint != 'index' and request.endpoint != 'scrape':
        logger.warning(f"Blocked access to invalid endpoint: {request.endpoint}")
        abort(404)
    
    logger.info(f"Received request: {request.method} {request.url}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        logger.info(f"Processing URL: {url}")
        return redirect(url_for('scrape', url=url, new_search=True))
    return render_template('index.html', recent_searches=recent_searches)

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    new_search = request.args.get('new_search', default=False, type=bool)

    if not url:
        logger.error("No URL provided in the request")
        return jsonify({"error": "URL is required"}), 400

    try:
        soup = fetch_article(url)
        title, description = extract_meta_data(soup)
        content, author, published_date = scrape_source(url, soup)
        image_url = extract_image(soup)
        source = extract_source(url)

        if new_search:
            recent_searches.insert(0, {
                "title": title,
                "url": url,
                "source": source,
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

        logger.info(f"Scraped content from {url}")
        return render_template('article.html', title=title, description=description, 
                               author=author, published_date=published_date, 
                               content=content, image_url=image_url,
                               json_summary=json_summary, url=url)

    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if os.environ.get("FLASK_ENV") == "production":
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    else:
        app.run(debug=True)
