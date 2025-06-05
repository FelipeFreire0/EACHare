<<<<<<< HEAD
# Classe responsável por representar e manipular mensagens trocadas entre peers
# Cada mensagem possui: origem, clock, tipo e uma lista de argumentos
class Mensagem:
    # Inicializa uma mensagem com seus componentes básicos
    def __init__(self, origem, clock, tipo, argumentos=None):
        self.origem = origem
        self.clock = clock
        self.tipo = tipo
        self.argumentos = argumentos or []
    
    # Codifica a mensagem para o formato de string a ser enviada pela rede
    # Formato: <origem> <clock> <tipo> [argumentos...]
    def codificar(self):
        partes = [self.origem, str(self.clock), self.tipo] + self.argumentos
        return " ".join(partes) + "\n"

    # Converte uma string recebida pela rede de volta para um objeto Mensagem
    @staticmethod
    def decodificar(mensagem_str):
        partes = mensagem_str.strip().split()
        if len(partes) < 3:
            raise ValueError("Mensagem inválida")
        origem = partes[0]
        clock = int(partes[1])
        tipo = partes[2]
        argumentos = partes[3:]
        return Mensagem(origem, clock, tipo, argumentos)

    def __str__(self):
        return self.codificar().strip()

# Exibe no terminal uma mensagem de envio com relógio lógico
def exibir_envio(mensagem, destino):
=======
# Classe responsável por representar e manipular mensagens trocadas entre peers
# Cada mensagem possui: origem, clock, tipo e uma lista de argumentos
class Mensagem:
    # Inicializa uma mensagem com seus componentes básicos
    def __init__(self, origem, clock, tipo, argumentos=None):
        self.origem = origem
        self.clock = clock
        self.tipo = tipo
        self.argumentos = argumentos or []
    
    # Codifica a mensagem para o formato de string a ser enviada pela rede
    # Formato: <origem> <clock> <tipo> [argumentos...]
    def codificar(self):
        partes = [self.origem, str(self.clock), self.tipo] + self.argumentos
        return " ".join(partes) + "\n"

    # Converte uma string recebida pela rede de volta para um objeto Mensagem
    @staticmethod
    def decodificar(mensagem_str):
        partes = mensagem_str.strip().split()
        if len(partes) < 3:
            raise ValueError("Mensagem inválida")
        origem = partes[0]
        clock = int(partes[1])
        tipo = partes[2]
        argumentos = partes[3:]
        return Mensagem(origem, clock, tipo, argumentos)

    def __str__(self):
        return self.codificar().strip()

# Exibe no terminal uma mensagem de envio com relógio lógico
def exibir_envio(mensagem, destino):
>>>>>>> bb6761be13c15cc9ef9b7fdb2e8e2eac7253da15
    print(f'Encaminhando mensagem "{mensagem}" para {destino}')