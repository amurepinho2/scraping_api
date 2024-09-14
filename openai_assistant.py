import openai
import json
import requests

openai.api_key = 'sua_api_key_aqui'

def assistant_with_function_calling(user_message):
    # Definir a função de raspagem
    function_definitions = [
        {
            "name": "scrape_article",
            "description": "Raspa o conteúdo de um artigo a partir de uma URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "A URL do artigo a ser raspado"
                    }
                },
                "required": ["url"]
            }
        }
    ]

    # Enviar a mensagem do usuário e a definição da função para o assistente
    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[{"role": "user", "content": user_message}],
        functions=function_definitions,
        function_call="auto"  # O modelo decide quando chamar a função
    )

    # Verificar se uma função foi chamada
    if "choices" in response and response["choices"][0]["finish_reason"] == "function_call":
        function_call = response["choices"][0]["message"]["function_call"]

        # Extrair o nome da função e os argumentos
        function_name = function_call["name"]
        arguments = json.loads(function_call["arguments"])

        if function_name == "scrape_article":
            url = arguments["url"]

            # Fazer uma requisição para sua API Flask com a URL
            api_response = requests.post('http://<YOUR_API_HOST>/function_call', json={"url": url})

            # Retornar a resposta do Flask para o usuário
            return api_response.json()

    # Caso a função não tenha sido chamada, retornar a resposta padrão
    return response["choices"][0]["message"]["content"]

# Exemplo de uso
user_message = "Me dê um resumo deste artigo: https://exemplo.com/artigo"
result = assistant_with_function_calling(user_message)
print(result)
