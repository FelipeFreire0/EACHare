from mensagem import Mensagem, exibir_envio
from relogio import Relogio
import socket
import os
import statistics
import time
import base64

# Variável global para o tamanho do chunk
chunk_size = 256
estatisticas_download = []  # cada item: (chunk_size, n_peers, tam_arquivo, tempo)

# Função principal do menu interativo
# Permite ao usuário interagir com o peer e executar comandos
def menu_interativo(peer):
    global chunk_size
    relogio = Relogio()

    while True:
        print("\nEscolha um comando:")
        print("[1] Listar peers")
        print("[2] Obter peers")
        print("[3] Listar arquivos locais")
        print("[4] Buscar arquivos")
        print("[5] Exibir estatisticas")
        print("[6] Alterar tamanho de chunk")
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

        elif opcao == "5":
            exibir_estatisticas(peer, relogio)

        elif opcao == "6":
            novo = input("Digite novo tamanho de chunk:\n>")
            try:
                chunk_size = int(novo)
                print(f"Tamanho de chunk alterado: {chunk_size}")
            except ValueError:
                print("Valor inválido.")

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
    global chunk_size

    # {(nome, tamanho): [peer1, peer2, ...]}
    arquivos_disponiveis = {}

    # 1. Busca arquivos em todos os peers ONLINE
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
                    # Atualiza status
                    if destino not in peer.peers_conhecidos:
                        peer.peers_conhecidos[destino] = {"status": "ONLINE", "clock": resposta_msg.clock}
                    else:
                        info = peer.peers_conhecidos[destino]
                        info["status"] = "ONLINE"
                        if resposta_msg.clock > info["clock"]:
                            info["clock"] = resposta_msg.clock
                    print(f"Atualizando peer {destino} status ONLINE")
                    # Processa LS_LIST
                    if resposta_msg.tipo == "LS_LIST":
                        for i in range(1, len(resposta_msg.argumentos)):
                            nome, tamanho = resposta_msg.argumentos[i].split(":", 1)
                            chave = (nome, int(tamanho))
                            if chave not in arquivos_disponiveis:
                                arquivos_disponiveis[chave] = []
                            arquivos_disponiveis[chave].append(destino)
            except Exception as e:
                peer.peers_conhecidos[destino]["status"] = "OFFLINE"
                print(f"Atualizando peer {destino} status OFFLINE")
                print(f"Erro: {e}")

    if not arquivos_disponiveis:
        print("Nenhum arquivo disponível nos peers online.")
        return

    # 2. Exibe arquivos agrupados
    print("\nArquivos encontrados na rede:")
    print("  | {:<3} | {:<30} | {:<10} | {:<30} |".format("Nº", "Nome", "Tamanho", "Peers"))
    print("  " + "-" * 82)
    print("  | {:<3} | {:<30} | {:<10} | {:<30} |".format("0", "<Cancelar>", "", ""))

    arquivos_lista = []
    index = 1
    for (nome, tamanho), peers_lista in arquivos_disponiveis.items():
        print("  | {:<3} | {:<30} | {:<10} | {:<30} |".format(index, nome, tamanho, ", ".join(peers_lista)))
        arquivos_lista.append((nome, tamanho, peers_lista))
        index += 1

    # 3. Escolha do arquivo
    escolha = input("\nDigite o numero do arquivo para fazer o download:\n>")
    if escolha == "0":
        return
    try:
        escolha = int(escolha)
        if escolha < 1 or escolha >= index:
            print("Opção inválida.")
            return
        arquivo_nome, arquivo_tamanho, peers_arquivo = arquivos_lista[escolha - 1]
        print(f"arquivo escolhido {arquivo_nome}")
    except Exception:
        print("Opção inválida.")
        return

    # 4. Download fragmentado em chunks de vários peers
    num_chunks = (arquivo_tamanho + chunk_size - 1) // chunk_size
    chunks = [None] * num_chunks
    peers_ciclo = peers_arquivo * ((num_chunks + len(peers_arquivo) - 1) // len(peers_arquivo))
    peers_ciclo = peers_ciclo[:num_chunks]

    tempo_inicio = time.time()
    for idx in range(num_chunks):
        peer_destino = peers_ciclo[idx]
        clock = relogio.antes_de_enviar()
        msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "DL", [arquivo_nome, str(chunk_size), str(idx)])
        exibir_envio(msg, peer_destino)
        try:
            ip, porta = peer_destino.split(":")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, int(porta)))
                s.sendall(msg.codificar().encode())
                resposta = s.recv(8192).decode().strip()
                # Não exibe a mensagem FILE completa para não poluir a saída
                if resposta.startswith(""):
                    print(f"Resposta recebida: <FILE>")
                else:
                    print(f"Resposta recebida: \"{resposta[:60]}...\"")
                resposta_msg = Mensagem.decodificar(resposta)
                relogio.ao_receber(resposta_msg.clock)
                # Atualiza status
                if peer_destino in peer.peers_conhecidos:
                    info = peer.peers_conhecidos[peer_destino]
                    info["status"] = "ONLINE"
                    if resposta_msg.clock > info["clock"]:
                        info["clock"] = resposta_msg.clock
                print(f"Atualizando peer {peer_destino} status ONLINE")
                # Processa FILE
                if resposta_msg.tipo == "FILE" and len(resposta_msg.argumentos) >= 4:
                    idx_chunk = int(resposta_msg.argumentos[2])
                    chunk_b64 = resposta_msg.argumentos[3]
                    chunk_bytes = base64.b64decode(chunk_b64)
                    chunks[idx_chunk] = chunk_bytes
        except Exception as e:
            print(f"[ERRO] Falha ao baixar chunk {idx} de {peer_destino}: {e}")
            return
    tempo_fim = time.time()

    # 5. Junta e salva o arquivo
    file_path = os.path.join(peer.diretorio, arquivo_nome)
    # Salva estatística ANTES de escrever o arquivo em disco
    estatisticas_download.append((chunk_size, len(peers_arquivo), arquivo_tamanho, tempo_fim - tempo_inicio))
    with open(file_path, 'wb') as f:
        for chunk in chunks:
            if chunk is not None:
                f.write(chunk)
    print(f"Download do arquivo {arquivo_nome} finalizado.")
    print(f"Tempo de download: {tempo_fim - tempo_inicio:.4f} segundos.")

# Comando [5]: exibe estatísticas sobre os peers e arquivos
def exibir_estatisticas(peer, relogio):
    print("\nEstatísticas de Download:")
    if not estatisticas_download:
        print("Nenhum download realizado ainda.")
        return

    # Agrupa por (chunk_size, n_peers, tam_arquivo)
    agrupado = {}
    for chunk, n_peers, tam, tempo in estatisticas_download:
        chave = (chunk, n_peers, tam)
        if chave not in agrupado:
            agrupado[chave] = []
        agrupado[chave].append(tempo)

    print("Tam. chunk | N peers | Tam. arquivo | N | Tempo [s] | Desvio")
    for (chunk, n_peers, tam), tempos in agrupado.items():
        n = len(tempos)
        media = sum(tempos) / n
        desvio = statistics.stdev(tempos) if n > 1 else 0
        print(f"{chunk:<10} | {n_peers:<7} | {tam:<11} | {n:<1} | {media:.5f} | {desvio:.5f}")

# Comando [6]: altera o tamanho do chunk para transferências
def alterar_tamanho_chunk(novo_tamanho):
    global chunk_size
    try:
        novo_tamanho = int(novo_tamanho)
        if novo_tamanho > 0:
            chunk_size = novo_tamanho
            print(f"Tamanho do chunk alterado para: {chunk_size} bytes")
        else:
            print("O tamanho do chunk deve ser maior que 0.")
    except ValueError:
        print("Valor inválido para o tamanho do chunk.")

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