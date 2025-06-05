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
        print("[9] Sair")
        opcao = input(">")

        if opcao == "1":
            listar_peers(peer, relogio)
        
        elif opcao == "2":
            obter_peers(peer, relogio)

        elif opcao == "3":
            listar_arquivos_locais(peer)

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
    print("[0] Voltar ao menu")

    for i, (end, status) in enumerate(peers, 1):
        print(f"[{i}] {end} {status}")

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
        peer.peers_conhecidos[destino] = "ONLINE"
        print(f"Atualizando peer {destino} status ONLINE")
    except:
        peer.peers_conhecidos[destino] = "OFFLINE"
        print(f"Atualizando peer {destino} status OFFLINE")

# Comando [2]: envia GET_PEERS para os peers conhecidos para descobrir novos peers
def obter_peers(peer, relogio):
    for destino in list(peer.peers_conhecidos.keys()):
        clock = relogio.antes_de_enviar()
        msg = Mensagem(f"{peer.endereco}:{peer.porta}", clock, "GET_PEERS")

        try:
            ip, porta = destino.split(":")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, int(porta)))
                s.sendall(msg.codificar().encode())

                resposta = s.recv(4096).decode().strip()
                print(f"Resposta recebida: \"{resposta}\"")
                resposta_msg = Mensagem.decodificar(resposta)
                relogio.ao_receber(resposta_msg.clock)

                # Atualiza o status do peer destino
                peer.peers_conhecidos[destino] = "ONLINE"
                print(f"Atualizando peer {destino} status ONLINE")

                # Processa a lista de peers recebida
                if resposta_msg.tipo.startswith("PEER_LIST"):
                    total = int(resposta_msg.argumentos[0])
                    novos_peers = resposta_msg.argumentos[1:]

                    for peer_str in novos_peers:
                        end, status, _ = peer_str.rsplit(":", 2)
                        if end == f"{peer.endereco}:{peer.porta}":
                            continue
                        if end not in peer.peers_conhecidos:
                            peer.peers_conhecidos[end] = status
                            print(f"Adicionando novo peer {end} status {status}")
                        else:
                            peer.peers_conhecidos[end] = status
                            print(f"Atualizando peer {end} status {status}")

        except:
            peer.peers_conhecidos[destino] = "OFFLINE"
            print(f"Atualizando peer {destino} status OFFLINE")
        
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


# Comando [9]: envia BYE para peers ONLINE e finaliza a execução do programa
def sair(peer):
    print("Saindo...")

    for destino, status in peer.peers_conhecidos.items():
        if status == "ONLINE":
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