# Hemobit · Guia de transporte serverless

Atividade individual 1 da Unidade II de Infraestrutura de Software, ADS, CESAR School, 2026.2.

## Fluxo escolhido

Uma solicitação do Hemobit pode ter um hospital de destino e bolsas reservadas. A função emite uma guia didática com os dados que recebe em `POST /guias`. O contrato usa `requisicaoId`, `hospital` e `bolsas`. No Hemobit, os campos correspondentes são o ID e o nome da unidade de saúde da solicitação e os códigos de bolsas obtidos em `GET /solicitacoes/{id}/bolsas`.

Os exemplos são fictícios. A função só gera o JSON da guia. Ela não altera estoque, não confirma transporte, não consulta o banco e não é chamada automaticamente pelo Hemobit.

## Como rodar

Usei o **Caminho A** do enunciado, com AWS SAM CLI, Docker e Python 3.12. Os comandos abaixo usam Bash, inclusive Git Bash no Windows. Use `curl.exe` se o PowerShell mapear `curl` para outro comando.

```bash
docker info
sam --version
python --version
sam build
sam local generate-event apigateway aws-proxy --method POST --path guias \
  --body "$(cat events/pedido-body.json)" > events/pedido.json
sam local invoke GuiaTransporte -e events/pedido.json
sam local invoke GuiaTransporte -e events/pedido.json
sam local start-api --port 3101
```

No segundo terminal, rode três vezes:

```bash
curl -i -X POST http://127.0.0.1:3101/guias \
  -H 'Content-Type: application/json' --data-binary @events/pedido-http.json
```

Pare o primeiro servidor com Ctrl+C e inicie com `sam local start-api --port 3101 --warm-containers LAZY`. Repita as três chamadas e observe `invocacaoNesteAmbiente`. Um corpo sem `requisicaoId` retorna HTTP 400.

### Limite de tempo

Com o servidor em execução e o limite padrão de 3 s, chame:

```bash
curl -i -X POST http://127.0.0.1:3101/guias \
  -H 'Content-Type: application/json' --data-binary @events/pedido-lento.json
```

Depois, pare o servidor e gere um build separado, com o parâmetro de 10 s. Aponte a API para esse build e repita o comando acima:

```bash
sam build --build-dir .aws-sam/timeout-10 --parameter-overrides TimeoutSegundos=10
sam local start-api --port 3101 --template .aws-sam/timeout-10/template.yaml \
  --parameter-overrides TimeoutSegundos=10
```

## Perguntas do enunciado

1. **O que acontece na fase Init?** Um ambiente novo inicializa o runtime Python, importa o módulo e executa o código de nível global, como `contador = 0`. O SAM também precisa inicializar um contêiner ao simular uma chamada fria. Preparar imagens e montar o código pode aumentar a duração medida no terminal. As duas chamadas independentes de `sam local invoke` usam ambientes separados. Na rodada registrada, a primeira levou 9.047 ms e a segunda 14.063 ms de ponta a ponta. Ambas reportaram Init e contador 1. A latência total inclui o SAM e o Docker, além da execução da função. Já no teste HTTP com reaproveitamento, a primeira chamada foi mais lenta que as seguintes.
2. **O que o contador diz sobre o estado?** Sem contêiner quente, cada chamada HTTP inicia o contador em um ambiente novo. Com `LAZY`, chamadas num mesmo contêiner reaproveitam a variável global. O Lambda pode criar mais ambientes ou descartar o atual. Dados que precisam sobreviver, como o estado de uma solicitação ou um registro oficial de guia, precisam de armazenamento persistente.
3. **O que mudou no teste lento?** O parâmetro `demorar` faz a função esperar 5 s. Com limite de 3 s, o ambiente encerra a execução e a API devolve um erro. Com limite de 10 s, a espera cabe no tempo de execução e a guia é emitida. O limite máximo de uma invocação Lambda é 900 s (15 minutos). Um trabalho maior pode ser dividido em etapas curtas com fila ou Step Functions. Uma tarefa longa indivisível é mais adequada para um serviço de processamento como ECS ou AWS Batch. [Cotas oficiais do Lambda](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
4. **Quanto custa um milhão de execuções?** Pelos preços fornecidos no enunciado, sem aplicar franquia gratuita e sem contar API Gateway ou outros serviços, 128 MB = 0,125 GB, 100 ms = 0,1 s. O consumo é 1.000.000 × 0,125 × 0,1 = **12.500 GB-s**. O processamento custa 12.500 × US$ 0,0000166667 = **US$ 0,20833375**. Somando **US$ 0,20** pelas requisições, o total é **US$ 0,40833375**, aproximadamente **US$ 0,41**.
5. **Onde faz sentido?** No Hemobit, uma função curta faz sentido para montar a guia depois que o sistema já tem o destino e as bolsas reservadas. Para telemetria que recebe dados continuamente ou para coordenar o estado do estoque entre vários pedidos, eu manteria o processamento contínuo e as transações no serviço principal. Cada guia de verdade também precisaria de um registro persistente com emissão idempotente.

## Evidências

Validação em 26/11/2026 (horário de Brasília), AWS SAM CLI 1.174.1, Python 3.12 e Docker Desktop.

| Experimento | Resultado | Captura |
| --- | --- | --- |
| Ambiente, evento gerado e build | SAM CLI 1.174.1 e build concluído | [Ambiente](evidencias/01-ambiente.png) |
| Duas invocações por evento | HTTP 201 nas duas. Tempos totais de 9.047 ms e 14.063 ms. Init de 0,04 ms e 0,06 ms | [Evento](evidencias/02-evento.png) |
| Três chamadas HTTP sem reaproveitamento | HTTP 201, contador 1, 1, 1. A entrada inválida retornou 400 | [HTTP sem reaproveitamento](evidencias/03-http-frio.png) |
| Três chamadas HTTP com LAZY | HTTP 201, contador 1, 2, 3. Tempos de 4.500, 1.062 e 1.047 ms | [HTTP com reaproveitamento](evidencias/04-http-quente.png) |
| Limite de 3 s e ajuste para 10 s | Com 3 s o SAM registrou timeout e a API devolveu 502. Com 10 s a mesma chamada retornou 201 | [Timeout e ajuste](evidencias/05-timeout.png) |

Os tempos HTTP incluem a espera pelo emulador e o processamento da requisição. O tempo total de 11.562 ms na última chamada inclui a preparação do contêiner. O limite de 10 s se aplica à execução da função, que incluiu os cinco segundos de espera.

As capturas mostram trechos da saída registrada na execução. Veja também o [registro completo dos comandos](evidencias/execucao.txt), o [log do timeout](evidencias/02-quente-timeout-3-sam.txt) e o [log da execução com 10 s](evidencias/03-timeout-10-sam.txt).

## Uso de IA

Usei o ChatGPT (Codex) para interpretar o enunciado, preparar a função e o template, organizar os experimentos e elaborar um rascunho das respostas. A ferramenta verificou o comportamento no AWS SAM local com Docker, comparou as respostas HTTP e os contadores, e registrou os comandos e as saídas. Os tempos abaixo das capturas vêm das execuções realizadas. O texto das respostas é um rascunho para revisão individual antes da entrega.
