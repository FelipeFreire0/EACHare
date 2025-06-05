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
            self.relogio.ao_receber(mensagem.clock)
            
            origem = mensagem.origem
            
            # Update clock value for sender if message clock is greater
            novo_status = "OFFLINE" if mensagem.tipo == "BYE" else "ONLINE"
            
            if origem not in self.peers_conhecidos:
                self.peers_conhecidos[origem] = {"status": novo_status, "clock": mensagem.clock}
                print(f"Adicionando novo peer {origem} status {novo_status}")
            else:
                # Always update status for direct messages
                info_peer = self.peers_conhecidos[origem]
                if mensagem.clock > info_peer["clock"]:
                    info_peer["clock"] = mensagem.clock
                info_peer["status"] = novo_status
                print(f"Atualizando peer {origem} status {novo_status}")

            # Handle specific message types
            if mensagem.tipo == "GET_PEERS":
                # Send list of known peers
                lista_peers = []
                for p, info in self.peers_conhecidos.items():
                    if p != origem:
                        lista_peers.append(f"{p}:{info['status']}:{info['clock']}")

                total = len(lista_peers)
                clock = self.relogio.antes_de_enviar()
                resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "PEER_LIST", [str(total)] + lista_peers)
                conn.sendall(resposta.codificar().encode())
                
            # Handle LS message - list shared files
            elif mensagem.tipo == "LS":
                # Get list of files in shared directory
                arquivos = os.listdir(self.diretorio)
                lista_arquivos = []
                
                for nome in arquivos:
                    file_path = os.path.join(self.diretorio, nome)
                    if os.path.isfile(file_path):
                        tamanho = os.path.getsize(file_path)
                        lista_arquivos.append(f"{nome}:{tamanho}")
                
                total = len(lista_arquivos)
                clock = self.relogio.antes_de_enviar()
                resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "LS_LIST", [str(total)] + lista_arquivos)
                conn.sendall(resposta.codificar().encode())
                
            # Handle DL message - send file
            elif mensagem.tipo == "DL":
                if len(mensagem.argumentos) >= 3:
                    arquivo_nome = mensagem.argumentos[0]
                    param1 = mensagem.argumentos[1]
                    param2 = mensagem.argumentos[2]
                    
                    file_path = os.path.join(self.diretorio, arquivo_nome)
                    
                    # Check if file exists
                    if os.path.isfile(file_path):
                        # Read file in binary mode
                        import base64
                        with open(file_path, 'rb') as f:
                            conteudo = f.read()
                        
                        # Encode content to base64
                        conteudo_base64 = base64.b64encode(conteudo).decode('utf-8')
                        
                        # Send file
                        clock = self.relogio.antes_de_enviar()
                        resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "FILE", 
                                           [arquivo_nome, param1, param2, conteudo_base64])
                        conn.sendall(resposta.codificar().encode())
                    else:
                        # File not found
                        clock = self.relogio.antes_de_enviar()
                        resposta = Mensagem(f"{self.endereco}:{self.porta}", clock, "ERROR", ["FILE_NOT_FOUND"])
                        conn.sendall(resposta.codificar().encode())
        
        except Exception as e:
            print(f"[ERRO] Erro ao tratar conexão: {e}")
        finally:
            conn.close()