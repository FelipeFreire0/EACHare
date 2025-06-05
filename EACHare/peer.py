# peer.py

import socket
import os
import threading
from mensagem import Mensagem
from relogio import Relogio

# Classe que representa um peer ativo na rede P2P
# Gerencia conexões, envio e recebimento de mensagens, relógio e lista de vizinhos
class Peer:
    # Inicializa o peer com endereço, porta, lista de vizinhos e diretório compartilhado
    def __init__(self, endereco, porta, vizinhos_arquivo, diretorio):
        self.endereco = endereco
        self.porta = porta
        self.vizinhos_arquivo = vizinhos_arquivo
        self.diretorio = diretorio
        self.peers_conhecidos = {}  # { "ip:porta": {"status": "ONLINE"/"OFFLINE", "relogio": <int>} }
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
                    self.peers_conhecidos[peer] = "OFFLINE"
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
            self.relogio.ao_receber(mensagem.clock)

            origem = mensagem.origem

            if mensagem.tipo == "HELLO":
                if origem not in self.peers_conhecidos:
                    self.peers_conhecidos[origem] = "ONLINE"
                    print(f"Adicionando novo peer {origem} status ONLINE")
                else:
                    self.peers_conhecidos[origem] = "ONLINE"
                    print(f"Atualizando peer {origem} status ONLINE")

            elif mensagem.tipo == "GET_PEERS":
                if origem not in self.peers_conhecidos:
                    self.peers_conhecidos[origem] = "ONLINE"
                    print(f"Adicionando novo peer {origem} status ONLINE")
                else:
                    self.peers_conhecidos[origem] = "ONLINE"
                    print(f"Atualizando peer {origem} status ONLINE")

            elif mensagem.tipo == "BYE":
                if origem in self.peers_conhecidos:
                    self.peers_conhecidos[origem] = "OFFLINE"
                    print(f"Atualizando peer {origem} status OFFLINE")


                # Enviar lista de peers conhecidos
                lista_peers = []
                for p, status in self.peers_conhecidos.items():
                    if p != origem:
                        lista_peers.append(f"{p}:{status}:0")

                total = len(lista_peers)
                clock = self.relogio.antes_de_enviar()
                resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "PEER_LIST", [str(total)] + lista_peers)
                conn.sendall(resposta.codificar().encode())

        except Exception as e:
            print(f"[ERRO] Erro ao tratar conexão: {e}")
        finally:
            conn.close()