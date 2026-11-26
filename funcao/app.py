"""Emite uma guia didática a partir de dados de uma solicitação Hemobit."""

import base64
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

    try:
        corpo = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            corpo = base64.b64decode(corpo, validate=True)
        pedido = json.loads(corpo)
    except (TypeError, ValueError):
        return resposta(400, {"erro": "Corpo JSON inválido"})

    if not isinstance(pedido, dict):
        return resposta(400, {"erro": "O corpo deve ser um objeto JSON"})

    requisicao = pedido.get("requisicaoId")
    if not isinstance(requisicao, str) or not requisicao.strip():
        return resposta(400, {"erro": "requisicaoId obrigatório"})

    hospital = pedido.get("hospital")
    bolsas = pedido.get("bolsas", [])
    if hospital is not None and not isinstance(hospital, str):
        return resposta(400, {"erro": "hospital deve ser texto"})
    if not isinstance(bolsas, list) or any(
        not isinstance(codigo, str) or not codigo.strip() for codigo in bolsas
    ):
        return resposta(400, {"erro": "bolsas deve ser uma lista de códigos"})
    demorar = pedido.get("demorar", False)
    if not isinstance(demorar, bool):
        return resposta(400, {"erro": "demorar deve ser booleano"})

    if demorar:
        time.sleep(5)

    return resposta(201, {
        "guia": f"G-{requisicao.strip()}",
        "hospital": hospital,
        "bolsas": bolsas,
        "invocacaoNesteAmbiente": contador,
    })
