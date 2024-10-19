import socket
import threading
import time  # Adiciona o time para permitir o sleep entre tentativas de reconexão

class Servidor:
    def __init__(self, host='localhost', porta=6000, cluster_host='localhost', cluster_porta=7000):
        # Inicializa o servidor com as informações do host e porta para comunicação com clientes e cluster
        self.host = host
        self.porta = porta
        self.cluster_host = cluster_host
        self.cluster_porta = cluster_porta
        self.servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Associa o socket ao endereço e porta especificados
        self.servidor_socket.bind((self.host, self.porta))
        # Coloca o servidor em modo de escuta para até 5 conexões pendentes
        self.servidor_socket.listen(5)
        print(f"[DEBUG] Servidor ouvindo em {self.host}:{self.porta}")

        self.cluster_socket = None  # Socket para conexão com o cluster
        self.conectar_cluster()  # Tenta conectar ao cluster no início

    def conectar_cluster(self):
        """Tenta conectar ao cluster com reconexões automáticas."""
        while self.cluster_socket is None:
            try:
                print(f"[DEBUG] Tentando conectar ao cluster em {self.cluster_host}:{self.cluster_porta}...")
                # Cria um socket e tenta conectar ao cluster
                self.cluster_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cluster_socket.connect((self.cluster_host, self.cluster_porta))
                print(f"[DEBUG] Conexão com o cluster estabelecida")
            except ConnectionRefusedError:
                # Caso a conexão falhe, espera 5 segundos e tenta novamente
                print(f"[DEBUG] Conexão recusada. Tentando novamente em 5 segundos...")
                self.cluster_socket = None
                time.sleep(5)

    def reconectar_cluster(self):
        """Tenta reconectar ao cluster caso a conexão caia."""
        print("[DEBUG] Tentando reconectar ao cluster...")
        self.desconectar_cluster()  # Desconecta o socket atual
        self.conectar_cluster()  # Tenta se conectar novamente

    def desconectar_cluster(self):
        """Desconecta do cluster."""
        if self.cluster_socket:
            print("[DEBUG] Desconectando do cluster")
            self.cluster_socket.close()  # Fecha a conexão
            self.cluster_socket = None  # Define como None para tentar reconectar

    def tratar_cliente(self, cliente_socket):
        """Gerencia a comunicação com o cliente conectado."""
        try:
            while True:
                # Recebe dados do cliente (tamanho máximo 1024 bytes)
                requisicao = cliente_socket.recv(1024)
                if not requisicao:
                    print("[DEBUG] Cliente desconectado")
                    break
                # Decodifica a requisição recebida e processa
                requisicao = requisicao.decode()
                print(f"[DEBUG] Requisição recebida: {requisicao}")
                self.processar_comando(requisicao, cliente_socket)
        except Exception as e:
            print(f"[DEBUG] Erro ao tratar cliente: {e}")
        finally:
            # Fecha a conexão com o cliente após a comunicação
            cliente_socket.close()

    def processar_comando(self, requisicao, cliente_socket):
        """Processa o comando enviado pelo cliente."""
        comando, *args = requisicao.split()  # Separa o comando dos argumentos

        # Identifica o comando e chama o método correspondente
        if comando == "UPLOAD":
            self.processar_upload(args, cliente_socket)
        elif comando == "LIST":
            self.processar_list(cliente_socket)
        elif comando == "DOWNLOAD":
            self.processar_download(args, cliente_socket)
        elif comando == "DELETE":
            self.processar_delete(args, cliente_socket)
        else:
            cliente_socket.send("Comando inválido".encode())  # Responde com erro se o comando não for reconhecido

    def verificar_conexao_cluster(self):
        """Verifica se a conexão com o cluster está ativa."""
        try:
            # Tenta enviar uma mensagem "PING" para verificar a conexão com o cluster
            self.cluster_socket.send(b"PING")
        except (BrokenPipeError, ConnectionResetError):
            print("[DEBUG] Conexão com o cluster perdida. Reconectando...")
            self.reconectar_cluster()  # Se a conexão estiver quebrada, tenta reconectar

    def processar_upload(self, args, cliente_socket):
        """Gerencia o upload de uma imagem do cliente para o cluster."""
        nome_arquivo = args[0]  # Nome do arquivo a ser enviado
        print(f"[DEBUG] Recebendo imagem {nome_arquivo} do cliente e enviando para o cluster...")

        self.verificar_conexao_cluster()  # Verifica se a conexão com o cluster está ativa
        # Envia a requisição de upload para o cluster
        self.cluster_socket.send(f"UPLOAD {nome_arquivo}".encode())

        # Recebe os dados da imagem do cliente e envia para o cluster
        while True:
            dados = cliente_socket.recv(4096)  # Tamanho do buffer de recebimento
            if not dados:
                print("[DEBUG] Nenhum dado recebido, encerrando transmissão.")
                break
            if dados.endswith(b"FIM"):
                # Se os dados terminarem com "FIM", indica o fim da transmissão
                self.cluster_socket.send(dados[:-3])  # Envia todos os dados, exceto "FIM"
                print(f"[DEBUG] Recebido marcador 'FIM'. Transmissão concluída.")
                break
            self.cluster_socket.send(dados)

        # Envia "FIM" ao cluster para indicar o término da transmissão
        self.cluster_socket.send(b"FIM")
        cliente_socket.send("Upload bem-sucedido".encode())  # Informa ao cliente que o upload foi bem-sucedido
        print(f"[DEBUG] Imagem {nome_arquivo} enviada para o cluster")

    def processar_list(self, cliente_socket):
        """Solicita ao cluster a lista de imagens disponíveis."""
        print("[DEBUG] Solicitando lista de imagens ao cluster...")
        self.verificar_conexao_cluster()  # Verifica se a conexão com o cluster está ativa
        self.cluster_socket.send("LIST".encode())  # Envia a solicitação de listagem ao cluster
        imagens = self.cluster_socket.recv(1024).decode()  # Recebe a lista de imagens do cluster
        print(f"[DEBUG] Imagens recebidas do cluster: {imagens}")
        cliente_socket.send(imagens.encode())  # Envia a lista de imagens ao cliente

    def processar_download(self, args, cliente_socket):
        """Gerencia o download de uma imagem do cluster para o cliente."""
        nome_arquivo = args[0]
        try:
            self.verificar_conexao_cluster()  # Verifica a conexão com o cluster
            self.cluster_socket.send(f"DOWNLOAD {nome_arquivo}".encode())  # Solicita o download ao cluster
            print(f"[DEBUG] Solicitando a imagem {nome_arquivo} ao cluster...")

            response = self.cluster_socket.recv(4096)  # Recebe a resposta inicial do cluster
            if response == b"Arquivo nao encontrado":
                # Se o arquivo não for encontrado, envia a resposta de erro ao cliente
                print(f"[DEBUG] Arquivo {nome_arquivo} não encontrado no cluster.")
                cliente_socket.send("Arquivo nao encontrado".encode())
            else:
                # Se o arquivo for encontrado, começa a enviar os dados para o cliente
                print(f"[DEBUG] Enviando imagem {nome_arquivo} para o cliente.")
                while True:
                    dados = self.cluster_socket.recv(4096)  # Recebe dados do cluster
                    if not dados:
                        print("[DEBUG] Nenhum dado recebido, encerrando transmissão.")
                        break
                    if dados.endswith(b"FIM"):
                        # Envia os dados até o marcador "FIM"
                        cliente_socket.send(dados[:-3])
                        print(f"[DEBUG] Recebido marcador 'FIM'. Transmissão concluída.")
                        break
                    cliente_socket.send(dados)
                cliente_socket.send(b"FIM")  # Envia "FIM" ao cliente para finalizar
                print(f"Imagem {nome_arquivo} enviada com sucesso ao cliente.")
        except FileNotFoundError:
            cliente_socket.send("Arquivo não encontrado".encode())  # Envia erro se o arquivo não for encontrado

    def processar_delete(self, args, cliente_socket):
        """Gerencia a remoção de uma imagem no cluster."""
        nome_arquivo = args[0]
        self.verificar_conexao_cluster()  # Verifica a conexão com o cluster
        # Solicita ao cluster a remoção do arquivo
        self.cluster_socket.send(f"DELETE {nome_arquivo}".encode())
        resposta = self.cluster_socket.recv(1024).decode()  # Recebe a resposta do cluster
        cliente_socket.send(resposta.encode())  # Envia a resposta ao cliente

    def iniciar(self):
        """Inicia o servidor e aceita conexões de clientes."""
        while True:
            cliente_socket, endereco = self.servidor_socket.accept()  # Aguarda novas conexões de clientes
            print(f"[DEBUG] Conexão de {endereco}")
            # Cria uma nova thread para lidar com o cliente
            tratador_cliente = threading.Thread(target=self.tratar_cliente, args=(cliente_socket,))
            tratador_cliente.start()  # Inicia a thread para tratar o cliente

if __name__ == "__main__":  
    servidor = Servidor()  # Cria uma instância do servidor
    servidor.iniciar()  # Inicia o servidor, esperando por conexões de clientes