import os
from flask import Flask, jsonify, request, render_template
from bs4 import BeautifulSoup
import requests
import json

app = Flask(__name__)

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    format_type = request.args.get('format', 'html')  # Padrão é 'html' se não especificado

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Captura o título
        title = soup.title.string if soup.title else "Título não encontrado"

        # Captura a descrição a partir da tag <meta name="description">
        description = soup.find("meta", attrs={"name": "description"})
        description = description["content"] if description else "Descrição não encontrada"

        # Captura o autor a partir da tag <meta name="author">
        author = soup.find("meta", attrs={"name": "author"})
        author = author["content"] if author else "Autor não encontrado"

        # Captura a data de publicação a partir de uma tag específica, exemplo <meta property="article:published_time">
        published_date = soup.find("meta", attrs={"property": "article:published_time"})
        published_date = published_date["content"] if published_date else "Data de publicação não encontrada"

        # Captura o conteúdo do artigo
        article_content = ""

        # Nova opção: Capturar conteúdo dentro de <div class="TheContent">
        content_div = soup.find("div", class_="TheContent")
        if content_div:
            paragraphs = content_div.find_all("p")
            article_content = "\n\n".join([p.get_text() for p in paragraphs])
        
        # Se não encontrar, tenta capturar dentro de outras tags
        if not article_content:
            # Capturar conteúdo de <article class="Card">
            article_tag = soup.find("article", class_="Card")
            if article_tag:
                paragraphs = article_tag.find_all("p")
                article_content = "\n\n".join([p.get_text() for p in paragraphs])
            else:
                # Capturar conteúdo de <article> genérico
                article_tag = soup.find("article")
                if article_tag:
                    paragraphs = article_tag.find_all("p")
                    article_content = "\n\n".join([p.get_text() for p in paragraphs])

                # Se não encontrar em <article>, tenta outras divs comuns
                if not article_content:
                    content_div = soup.find("div", class_="article-content")
                    if not content_div:
                        content_div = soup.find("div", class_="content")
                    if not content_div:
                        content_div = soup.find("div", class_="entry-content")
                    if content_div:
                        paragraphs = content_div.find_all("p")
                        article_content = "\n\n".join([p.get_text() for p in paragraphs])
                    else:
                        article_content = "Conteúdo do artigo não encontrado"

        # Captura a imagem do artigo (buscando dentro da estrutura correta)
        image_url = ""
        
        # Tenta capturar a imagem dentro da div "TheContent"
        image_tag = content_div.find("img") if content_div else None
        if not image_tag:
            # Se não encontrar, tenta capturar no article ou em outra div
            article_tag = soup.find("article", class_="Card")
            if article_tag:
                image_tag = article_tag.find("img")
            if not image_tag:
                image_tag = soup.find("img")
        
        if image_tag and "src" in image_tag.attrs:
            image_url = image_tag["src"]

        # Retorna JSON ou renderiza HTML, dependendo do parâmetro 'format'
        if format_type == 'json':
            return jsonify({
                "title": title,
                "description": description,
                "author": author,
                "published_date": published_date,
                "content": article_content,
                "image_url": image_url
            })
        else:
            return render_template('article.html', title=title, description=description, 
                                   author=author, published_date=published_date, 
                                   content=article_content, image_url=image_url)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
