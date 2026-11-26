import base64
import binascii
import json
import time

contador = 0


def resposta(status, dados):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(dados, ensure_ascii=False),
    }


def lambda_handler(event, context):
    global contador
    contador += 1

    corpo = event.get("body") or "{}"
    try:
        if event.get("isBase64Encoded"):
            corpo = base64.b64decode(corpo, validate=True)
        pedido = json.loads(corpo)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        return resposta(400, {"erro": "Corpo JSON inválido"})

    if not isinstance(pedido, dict):
        return resposta(400, {"erro": "O corpo deve ser um objeto JSON"})

    codigo = pedido.get("requisicaoId")
    if not isinstance(codigo, str) or not codigo.strip():
        return resposta(400, {"erro": "requisicaoId obrigatório"})

    hospital = pedido.get("hospital")
    if hospital is not None and not isinstance(hospital, str):
        return resposta(400, {"erro": "hospital deve ser texto"})

    bolsas = pedido.get("bolsas", [])
    if not isinstance(bolsas, list) or any(
        not isinstance(bolsa, str) or not bolsa.strip() for bolsa in bolsas
    ):
        return resposta(400, {"erro": "bolsas deve ser uma lista de códigos"})

    demorar = pedido.get("demorar", False)
    if not isinstance(demorar, bool):
        return resposta(400, {"erro": "demorar deve ser booleano"})
    if demorar:
        time.sleep(5)

    guia = {
        "guia": f"G-{codigo.strip()}",
        "hospital": hospital,
        "bolsas": bolsas,
        "invocacaoNesteAmbiente": contador,
    }
    return resposta(201, guia)
