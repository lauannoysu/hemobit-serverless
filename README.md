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

### 1. O que acontece na fase Init?

Nessa fase de início, o ambiente é inicializado, o Python é carregado e as variáveis globais são definidas, como o `contador = 0`. Durante os testes, o SAM também precisou criar um contêiner para executar a função.

Na primeira chamada, o tempo total foi de 9.047 ms e, na segunda, de 14.063 ms. Nas duas chamadas, ocorreu a fase Init e o contador retornou 1, pois foram executadas em ambientes separados.

Vale lembrar que esse tempo também inclui a preparação do SAM e do Docker. Já no teste HTTP com reaproveitamento do ambiente, foi possível perceber que a primeira chamada demorou mais do que as seguintes.

### 2. O que o contador diz sobre o estado?

O contador mostra que, quando um novo ambiente é criado, a variável volta ao seu valor inicial. Ao utilizar o modo `LAZY`, o mesmo contêiner pode ser reaproveitado, fazendo com que o contador continue aumentando a cada chamada.

Porém, não podemos garantir que esse ambiente sempre será mantido, já que o Lambda pode descartá-lo ou criar outros. Por isso, informações importantes, como os dados de uma solicitação ou o registro de uma guia, devem ser salvas em um banco de dados.

### 3. O que mudou no teste lento?

Nesse teste, utilizei o parâmetro `demorar` para fazer a função esperar 5 segundos antes de finalizar. Quando o limite estava configurado para 3 segundos, a função não conseguiu terminar e a API retornou um erro. Se aumentar o limite para 10 segundos, a função conseguiu finalizar normalmente e emitir a guia.

O tempo máximo de execução de uma função Lambda é de 15 minutos. Caso seja necessário executar uma tarefa que demore mais do que isso, uma alternativa seria dividir o processamento em etapas menores, utilizando filas ou o AWS Step Functions. Se não for possível dividir a tarefa, seria melhor utilizar outros serviços, como o ECS ou o AWS Batch.

[Documentação oficial sobre os limites do Lambda](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)

### 4. Quanto custa um milhão de execuções?

Considerando os valores fornecidos no enunciado, temos:

- **Memória utilizada:** 128 MB = 0,125 GB;
- **Tempo de execução:** 100 ms = 0,1 segundo;
- **Quantidade de execuções:** 1.000.000.

Primeiro, vamos calcular o consumo total:

`1.000.000 × 0,125 × 0,1 = 12.500 GB-s`

Depois, calculamos o custo de processamento:

`12.500 × US$ 0,0000166667 = US$ 0,20833375`

Somando o custo de processamento com o custo das requisições:

`US$ 0,20833375 + US$ 0,20 = US$ 0,40833375`

Portanto, um milhão de execuções custaria aproximadamente **US$ 0,41**, sem considerar a franquia gratuita e os custos de outros serviços, como o API Gateway.

### 5. Onde faz sentido?

No Hemobit, acredito que o uso do Lambda faz sentido para tarefas rápidas e específicas, como a geração de uma guia após a definição do destino e a reserva das bolsas de sangue.

Já para atividades que precisam funcionar continuamente, como o recebimento de dados de telemetria e o controle de estoque entre diferentes solicitações, considero mais adequado manter essas responsabilidades no serviço principal do sistema.

Também seria importante salvar as guias emitidas em um banco de dados e garantir que uma mesma solicitação não gere guias duplicadas, mesmo que a função seja executada mais de uma vez.

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
