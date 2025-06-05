import sys
from peer import Peer
from menu import menu_interativo

# Função principal que inicializa e executa o peer
def main():
    # Verifica se os argumentos foram passados corretamente na linha de comando
    if len(sys.argv) != 4:
        print("Uso: python main.py <endereço>:<porta> <vizinhos.txt> <diretório>")
        exit(1)
    # Extrai os parâmetros de inicialização: endereço:porta, arquivo de vizinhos e diretório compartilhado
    ip_porta = sys.argv[1]
    vizinhos = sys.argv[2]
    diretorio = sys.argv[3]

    try:
        # Separa o endereço e a porta do argumento ip_porta
        endereco, porta = ip_porta.split(":")
        porta = int(porta)
    except:
        print("Erro: endereço deve estar no formato <ip>:<porta>")
        exit(1)
    # Instancia um novo objeto Peer com os parâmetros fornecidos
    peer = Peer(endereco, porta, vizinhos, diretorio)

    # Inicializa o peer e aguarda conexões
    peer.inicializar()

    # Inicia o loop de escuta por conexões
    peer.aguardar_conexoes()

    # Inicia o menu interativo para o usuário
    menu_interativo(peer)

# Ponto de entrada do programa
if __name__ == "__main__":
    main()

