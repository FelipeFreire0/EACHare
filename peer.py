import socket
import os
import threading
from mensagem import Mensagem
from relogio import Relogio
import base64

# Classe que representa um peer ativo na rede P2P
# Gerencia conexões, envio e recebimento de mensagens, relógio e lista de vizinhos
class Peer:
    # Inicializa o peer com endereço, porta, lista de vizinhos e diretório compartilhado
    def __init__(self, endereco, porta, vizinhos_arquivo, diretorio):
        self.endereco = endereco
        self.porta = porta
        self.vizinhos_arquivo = vizinhos_arquivo
        self.diretorio = diretorio
        self.peers_conhecidos = {}  # { "ip:porta": {"status": "ONLINE"/"OFFLINE", "clock": valor} }
        self.socket = None
        self.relogio = Relogio()

    # Inicia o socket, carrega os vizinhos do arquivo e verifica o diretório
    def inicializar(self):
        # Criar socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.endereco, self.porta))
        self.socket.listen()
        print(f"Peer iniciado em {self.endereco}:{self.porta}")

        # Ler vizinhos
        with open(self.vizinhos_arquivo, "r") as f:
            for linha in f:
                peer = linha.strip()
                if peer and peer != f"{self.endereco}:{self.porta}":
                    self.peers_conhecidos[peer] = {"status": "OFFLINE", "clock": 0}
                    print(f"Adicionando novo peer {peer} status OFFLINE")

        # Validar diretório
        if not os.path.isdir(self.diretorio) or not os.access(self.diretorio, os.R_OK):
            print(f"[ERRO] Diretório '{self.diretorio}' inválido ou não legível.")
            exit(1)
    
    # Cria uma thread para escutar conexões de entrada de outros peers
    def aguardar_conexoes(self):
        print(f"Aguardando conexões em {self.endereco}:{self.porta}...")
        thread = threading.Thread(target=self._loop_servidor, daemon=True)
        thread.start()

    # Loop principal do servidor que aceita conexões continuamente
    def _loop_servidor(self):
        while True:
            try:
                conn, addr = self.socket.accept()
                threading.Thread(target=self._tratar_conexao, args=(conn,), daemon=True).start()
            except:
                break

    # Trata cada conexão recebida individualmente em uma thread separada
    def _tratar_conexao(self, conn):
        try:
            dados = conn.recv(4096)
            if not dados:
                return
            mensagem_str = dados.decode().strip()
            print(f"Mensagem recebida: \"{mensagem_str}\"")

            mensagem = Mensagem.decodificar(mensagem_str)
            # Atualiza relógio local conforme Lamport
            self.relogio.ao_receber(mensagem.clock)

            origem = mensagem.origem
            novo_status = "OFFLINE" if mensagem.tipo == "BYE" else "ONLINE"

            # Atualiza status sempre, relógio só se clock recebido for maior
            if origem not in self.peers_conhecidos:
                self.peers_conhecidos[origem] = {"status": novo_status, "clock": mensagem.clock}
                print(f"Adicionando novo peer {origem} status {novo_status}")
            else:
                info_peer = self.peers_conhecidos[origem]
                # Atualiza relógio apenas se clock recebido for maior
                if mensagem.clock > info_peer["clock"]:
                    info_peer["clock"] = mensagem.clock
                # Atualiza status sempre para mensagem direta
                info_peer["status"] = novo_status
                print(f"Atualizando peer {origem} status {novo_status}")

            # GET_PEERS: responde com lista de peers conhecidos
            if mensagem.tipo == "GET_PEERS":
                lista_peers = []
                for p, info in self.peers_conhecidos.items():
                    if p != origem:
                        lista_peers.append(f"{p}:{info['status']}:{info['clock']}")
                total = len(lista_peers)
                clock = self.relogio.antes_de_enviar()
                resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "PEER_LIST", [str(total)] + lista_peers)
                conn.sendall(resposta.codificar().encode())

            # LS: responde com lista de arquivos compartilhados
            elif mensagem.tipo == "LS":
                try:
                    arquivos = os.listdir(self.diretorio)
                    argumentos = [str(len(arquivos))]
                    for nome in arquivos:
                        caminho = os.path.join(self.diretorio, nome)
                        tamanho = os.path.getsize(caminho)
                        argumentos.append(f"{nome}:{tamanho}")
                    clock = self.relogio.antes_de_enviar()
                    resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "LS_LIST", argumentos)
                    conn.sendall(resposta.codificar().encode())
                except Exception as e:
                    print(f"[ERRO] Falha ao listar arquivos: {e}")

            # DL: faz o download de um arquivo solicitado
            elif mensagem.tipo == "DL":
                nome_arquivo = mensagem.argumentos[0]
                chunk_size = int(mensagem.argumentos[1])
                idx_chunk = int(mensagem.argumentos[2])
                caminho_arquivo = os.path.join(self.diretorio, nome_arquivo)

                # Verifica se o arquivo existe e é legível
                if not os.path.isfile(caminho_arquivo) or not os.access(caminho_arquivo, os.R_OK):
                    print(f"[ERRO] Arquivo '{caminho_arquivo}' não encontrado ou não é legível.")
                    # Envia uma resposta de erro
                    clock = self.relogio.antes_de_enviar()
                    resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "FILE", [nome_arquivo, "0", "ERRO", ""])
                    conn.sendall(resposta.codificar().encode())
                    return
                try:
                    with open(caminho_arquivo, "rb") as f:
                        f.seek(idx_chunk * chunk_size)
                        chunk_bytes = f.read(chunk_size)

                    chunk_b64 = base64.b64encode(chunk_bytes).decode()
                    clock = self.relogio.antes_de_enviar()

                    resposta = Mensagem(
                        f"{self.endereco}:{self.porta}", 
                        clock, 
                        "FILE", 
                        [nome_arquivo, str(len(chunk_bytes)), str(idx_chunk), chunk_b64]
                    )
                    conn.sendall(resposta.codificar().encode())
                    print(f"Chunk {idx_chunk} do arquivo '{nome_arquivo}' enviado para {mensagem.origem}.")
            
                except Exception as e:
                   print(f"[ERRO] Falha ao enviar chunk do arquivo: {e}")
        except Exception as e:
            print(f"[ERRO] Erro ao tratar conexão: {e}")
        finally:
            conn.close()