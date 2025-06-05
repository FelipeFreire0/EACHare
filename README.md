# EACHare – EP Parte 1 (ACH2147)

Este projeto implementa a Parte 1 do sistema distribuído EACHare, um sistema peer-to-peer (P2P) simples, conforme o enunciado da disciplina **ACH2147 – Desenvolvimento de Sistemas de Informação Distribuídos**.

## Estrutura esperada do projeto

```
eachare/
├── __init__.py
├── main.py
├── peer.py
├── menu.py
├── mensagem.py
├── README.md
├── RelatórioEP1.pdf
├── relogio.py
├── vizinhos_9001.txt
├── vizinhos_9002.txt
├── vizinhos_9003.txt
├── compartilhados_peer1/
│   ├── arquivo.txt    
│   ├── arquivo_teste.txt 
│   └── teste.txt
├── compartilhados_peer2/
│   ├── 2.txt    
│   ├── arquivo_teste2.txt 
│   └── teste2.txt
├── compartilhados_peer3/
│   ├── 3.txt    
│   ├── arquivo_teste3.txt 
│   └── teste3.txt
├── __pycache__/
```

## Requisitos

- Python 3.7 ou superior
- Nenhuma biblioteca externa é necessária

## Como executar um peer

```
python main.py <endereço>:<porta> <arquivo_de_vizinhos> <diretório_compartilhado>
```

### Exemplo:

```
python main.py 127.0.0.1:9001 vizinhos_9001.txt compartilhados_peer1/
```

## Testar com múltiplos peers

Abra 3 terminais e execute:

```bash
# Terminal 1
python main.py 127.0.0.1:9001 vizinhos_9001.txt compartilhados_peer1/

# Terminal 2
python main.py 127.0.0.1:9002 vizinhos_9002.txt compartilhados_peer2/

# Terminal 3
python main.py 127.0.0.1:9003 vizinhos_9003.txt compartilhados_peer3/
```

### Exemplo de `vizinhos_9001.txt`
```
127.0.0.1:9002
```

## Comandos do Menu

Quando o peer está ativo, o menu exibe:

```
Escolha um comando:
[1] Listar peers
[2] Obter peers
[3] Listar arquivos locais
[4] Buscar arquivos
[9] Sair
```

- `[1]`: Exibe a lista de peers e envia `HELLO`
- `[2]`: Envia `GET_PEERS` e atualiza a lista de peers
- `[3]`: Lista arquivos do diretório compartilhado
- `[4]`: Busca arquivos do diretório compartilhado para download
- `[9]`: Envia `BYE` para peers ONLINE e encerra o programa
