from mensagem import Mensagem, exibir_envio
from relogio import Relogio
import socket
import os

# Função principal do menu interativo
# Permite ao usuário interagir com o peer e executar comandos
def menu_interativo(peer):
    relogio = Relogio()

    while True:
        print("\nEscolha um comando:")
        print("[1] Listar peers")
        print("[2] Obter peers")
        print("[3] Listar arquivos locais")
        print("[4] Buscar arquivos")
        print("[9] Sair")
        opcao = input(">")

        if opcao == "1":
            listar_peers(peer, relogio)
        
        elif opcao == "2":
            obter_peers(peer, relogio)

        elif opcao == "3":
            listar_arquivos_locais(peer)

        elif opcao == "4":
            buscar_arquivos(peer, relogio)

        elif opcao == "9":
            sair(peer)
            break

        else:
            print("Opção inválida.")

# Comando [1]: lista os peers conhecidos e permite envio de HELLO para um peer selecionado
def listar_peers(peer, relogio):
    peers = list(peer.peers_conhecidos.items())
    if not peers:
        print("Nenhum peer conhecido.")
        return

    print("\nLista de peers:")
    
    # Create table headers
    print("\n  | {:<20} | {:<10} | {:<8} |".format("Peer", "Status", "Relógio"))
    print("  " + "-" * 46)
    
    # Print each peer in table format
    for i, (end, info) in enumerate(peers, 1):
        print(f"{i:2d}| {end:<20} | {info['status']:<10} | {info['clock']:<8} |")
    
    print("\n[0] Voltar ao menu")

    escolha = input(">")
    if escolha == "0":
        return

    try:
        escolha = int(escolha)
        destino = peers[escolha - 1][0]
    except:
        print("Opção inválida.")
        return

    # Prepara e envia a mensagem HELLO ao peer escolhido
    clock = relogio.antes_de_enviar()
    msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "HELLO")
    try:
        ip, porta = destino.split(":")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, int(porta)))
            s.sendall(msg.codificar().encode())
        exibir_envio(msg, destino)
        peer.peers_conhecidos[destino] = {"status": "ONLINE", "clock": clock}
        print(f"Atualizando peer {destino} status ONLINE")
    except:
        peer.peers_conhecidos[destino] = {"status": "OFFLINE", "clock": clock}
        print(f"Atualizando peer {destino} status OFFLINE")

# Comando [2]: envia GET_PEERS para os peers conhecidos para descobrir novos peers
def obter_peers(peer, relogio):
    for destino in list(peer.peers_conhecidos.keys()):
        clock = relogio.antes_de_enviar()
        msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "GET_PEERS")
        exibir_envio(msg, destino)

        try:
            ip, porta = destino.split(":")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, int(porta)))
                s.sendall(msg.codificar().encode())

                resposta = s.recv(4096).decode().strip()
                print(f"Resposta recebida: \"{resposta}\"")
                resposta_msg = Mensagem.decodificar(resposta)
                relogio.ao_receber(resposta_msg.clock)

                # Direct message - always update status
                if destino not in peer.peers_conhecidos:
                    peer.peers_conhecidos[destino] = {"status": "ONLINE", "clock": resposta_msg.clock}
                else:
                    info = peer.peers_conhecidos[destino]
                    info["status"] = "ONLINE"
                    if resposta_msg.clock > info["clock"]:
                        info["clock"] = resposta_msg.clock
                print(f"Atualizando peer {destino} status ONLINE")

                # Process peer list with clock-based consistency
                if resposta_msg.tipo.startswith("PEER_LIST"):
                    total = int(resposta_msg.argumentos[0])
                    novos_peers = resposta_msg.argumentos[1:]

                    for peer_str in novos_peers:
                        # Use rsplit to split from right, preserving the IP:port format
                        parts = peer_str.split(":")
                        if len(parts) >= 4:  # Ensure we have enough parts
                            end = parts[0] + ":" + parts[1]  # Reassemble the endpoint
                            status = parts[2]
                            clock_str = parts[3]
                            remote_clock = int(clock_str)
                            
                            # Skip own address
                            if end == f"{peer.endereco}:{peer.porta}":
                                continue
                                
                            # Add new peer
                            if end not in peer.peers_conhecidos:
                                peer.peers_conhecidos[end] = {"status": status, "clock": remote_clock}
                                print(f"Adicionando novo peer {end} status {status}")
                            # Update existing peer if remote clock is greater
                            else:
                                info = peer.peers_conhecidos[end]
                                if remote_clock > info["clock"]:
                                    info["status"] = status
                                    info["clock"] = remote_clock
                                    print(f"Atualizando peer {end} status {status}")

        except Exception as e:
            peer.peers_conhecidos[destino]["status"] = "OFFLINE"
            print(f"Atualizando peer {destino} status OFFLINE")
            print(f"Erro: {e}")
        
# Comando [3]: exibe os arquivos presentes no diretório compartilhado local
def listar_arquivos_locais(peer):
    print("\nArquivos locais no diretório compartilhado:")

    try:
        arquivos = os.listdir(peer.diretorio)
        if not arquivos:
            print("(nenhum arquivo encontrado)")
        else:
            for nome in arquivos:
                print(nome)
    except Exception as e:
        print(f"[ERRO] Falha ao acessar o diretório: {e}")

# Comando [4]: busca arquivos disponíveis em peers online e permite download
def buscar_arquivos(peer, relogio):
    # Dictionary to store found files and their sources
    arquivos_disponiveis = {}  # {filename: [(peer, size), (peer, size), ...]}
    
    # Search for files in all ONLINE peers
    for destino, info in peer.peers_conhecidos.items():
        if info["status"] == "ONLINE":
            clock = relogio.antes_de_enviar()
            msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "LS")
            exibir_envio(msg, destino)

            try:
                ip, porta = destino.split(":")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, int(porta)))
                    s.sendall(msg.codificar().encode())

                    resposta = s.recv(4096).decode().strip()
                    print(f"Resposta recebida: \"{resposta}\"")
                    resposta_msg = Mensagem.decodificar(resposta)
                    relogio.ao_receber(resposta_msg.clock)
                    
                    # Update peer status on direct response
                    if destino not in peer.peers_conhecidos:
                        peer.peers_conhecidos[destino] = {"status": "ONLINE", "clock": resposta_msg.clock}
                    else:
                        info = peer.peers_conhecidos[destino]
                        info["status"] = "ONLINE"
                        if resposta_msg.clock > info["clock"]:
                            info["clock"] = resposta_msg.clock
                    print(f"Atualizando peer {destino} status ONLINE")
                    
                    # Process LS_LIST response
                    if resposta_msg.tipo == "LS_LIST":
                        total_arquivos = int(resposta_msg.argumentos[0])
                        for i in range(1, len(resposta_msg.argumentos)):
                            arquivo_info = resposta_msg.argumentos[i]
                            # Parse file info (name:size)
                            nome, tamanho = arquivo_info.split(":", 1)
                            
                            # Add file to available files dict
                            if nome not in arquivos_disponiveis:
                                arquivos_disponiveis[nome] = []
                            arquivos_disponiveis[nome].append((destino, int(tamanho)))
                    
            except Exception as e:
                peer.peers_conhecidos[destino]["status"] = "OFFLINE"
                print(f"Atualizando peer {destino} status OFFLINE")
                print(f"Erro: {e}")
    
    # Display available files
    if not arquivos_disponiveis:
        print("Nenhum arquivo disponível nos peers online.")
        return
    
    # New format as requested
    print("\nArquivos encontrados na rede:")
    print("  | {:<3} | {:<30} | {:<10} | {:<21} |".format("Nº", "Nome", "Tamanho", "Peer"))
    print("  " + "-" * 74)
    print("  | {:<3} | {:<30} | {:<10} | {:<21} |".format("0", "<Cancelar>", "", ""))
    
    # Create a list of all file-peer combinations
    arquivos_lista = []
    index = 1
    
    for nome, fontes in arquivos_disponiveis.items():
        for destino, tamanho in fontes:
            print("  | {:<3} | {:<30} | {:<10} | {:<21} |".format(index, nome, tamanho, destino))
            arquivos_lista.append((nome, destino, tamanho))
            index += 1
    
    # Handle file download
    escolha = input("\nDigite o numero do arquivo para fazer o download:\n>")
    if escolha == "0":
        return
    
    try:
        escolha = int(escolha)
        if escolha < 1 or escolha >= index:
            print("Opção inválida.")
            return
            
        arquivo_nome, destino, _ = arquivos_lista[escolha - 1]
        print(f"arquivo escolhido {arquivo_nome}")
        
        # Send download request
        clock = relogio.antes_de_enviar()
        msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "DL", [arquivo_nome, "0", "0"])
        exibir_envio(msg, destino)
        
        # Connect and send download request
        ip, porta = destino.split(":")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, int(porta)))
            s.sendall(msg.codificar().encode())
            
            resposta = s.recv(8192).decode().strip()  
            print(f"Resposta recebida: \"{resposta}\"")
            resposta_msg = Mensagem.decodificar(resposta)
            relogio.ao_receber(resposta_msg.clock)
            
            # Update peer status
            if destino in peer.peers_conhecidos:
                info = peer.peers_conhecidos[destino]
                info["status"] = "ONLINE"
                if resposta_msg.clock > info["clock"]:
                    info["clock"] = resposta_msg.clock
            print(f"Atualizando peer {destino} status ONLINE")
            
            # Process FILE response
            if resposta_msg.tipo == "FILE" and len(resposta_msg.argumentos) >= 4:
                # Extract file content in base64
                file_nome = resposta_msg.argumentos[0]
                file_content_b64 = resposta_msg.argumentos[3]
                
                # Decode base64 content
                import base64
                file_content = base64.b64decode(file_content_b64)
                
                # Save file to local shared directory
                file_path = os.path.join(peer.diretorio, file_nome)
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                
                print(f"Download do arquivo {file_nome} finalizado.")
                
    except Exception as e:
        print(f"[ERRO] Falha ao fazer download: {e}")

# Comando [9]: envia BYE para peers ONLINE e finaliza a execução do programa
def sair(peer):
    print("Saindo...")

    for destino, info in peer.peers_conhecidos.items():
        if info["status"] == "ONLINE":
            clock = peer.relogio.antes_de_enviar()
            msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "BYE")
            try:
                ip, porta = destino.split(":")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, int(porta)))
                    s.sendall(msg.codificar().encode())
                exibir_envio(msg, destino)
            except:
                print(f"[ERRO] Não foi possível enviar BYE para {destino}")

    print("Encerrando o programa.")