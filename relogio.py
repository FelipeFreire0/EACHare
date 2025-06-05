# Classe responsável por manter o relógio lógico de Lamport
# Esse relógio é usado para manter uma ordem parcial entre eventos distribuídos

class Relogio:
    def __init__(self):
        # Inicializa o clock com valor 0
        self.valor = 0

    def antes_de_enviar(self):
        # Atualiza o relógio antes de enviar uma mensagem
        # Incrementa o clock local, pois o envio é um evento local importante
        self.valor += 1
        self._exibir()
        return self.valor

    def ao_receber(self, mensagem_clock=None):
        # Atualiza o relógio ao receber uma mensagem
        # Se fornecido um valor de clock de mensagem, atualiza para o maior valor
        if mensagem_clock is not None:
            self.valor = max(self.valor, mensagem_clock)
        
        # Incrementa o valor do relógio
        self.valor += 1
        self._exibir()
        return self.valor

    def _exibir(self):
        print(f"=> Atualizando relogio para {self.valor}")

    def obter_valor(self):
        return self.valor

