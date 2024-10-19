import socket
import os

class Cluster:
    DIRETORIO_IMAGENS = "imagens"  # Diretório onde as imagens serão armazenadas

    def __init__(self, host='localhost', porta=7000):
        # Se o diretório de imagens não existir, ele será criado
        if not os.path.exists(self.DIRETORIO_IMAGENS):
            os.makedirs(self.DIRETORIO_IMAGENS)

        # Cria o socket do cluster (TCP/IP) e associa-o ao endereço e porta
        self.cluster_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cluster_socket.bind((host, porta))
        self.cluster_socket.listen(5)  # Coloca o socket em modo de escuta, aceitando até 5 conexões pendentes
        print(f"[DEBUG] Cluster ouvindo em {host}:{porta}")

    def tratar_requisicao(self, server_socket):
        """
        Recebe e trata as requisições enviadas pelo servidor. Este método é executado
        em loop até que o cliente se desconecte ou ocorra um erro.
        """
        try:
            while True:
                # Recebe a requisição do servidor (com até 1024 bytes)
                requisicao = server_socket.recv(1024)
                if not requisicao:
                    print("[DEBUG] Cliente desconectado")
                    break
                requisicao = requisicao.decode()  # Decodifica a mensagem recebida
                print(f"[DEBUG] Requisição recebida: {requisicao}")
                self.processar_comando(requisicao, server_socket)  # Processa a requisição
        except Exception as e:
            print(f"[DEBUG] Erro ao tratar cliente: {e}")
        finally:
            # Fecha a conexão do socket ao final
            server_socket.close()

    def processar_comando(self, requisicao, server_socket):
        """
        Processa os comandos enviados pelo servidor, como upload, listagem, download e delete.
        """
        comando, *args = requisicao.split()

        # Dependendo do comando recebido, chama o método apropriado
        if comando == "UPLOAD":
            self.upload_imagem(server_socket, args)
        elif comando == "LIST":
            self.listar_imagens(server_socket)
        elif comando == "DOWNLOAD":
            self.download_imagem(server_socket, args)
        elif comando == "DELETE":
            self.deletar_imagem(server_socket, args)
        else:
            print("[DEBUG] Comando inválido.")

    def upload_imagem(self, server_socket, args):
        """
        Recebe um arquivo de imagem do servidor e o armazena no diretório especificado.
        """
        nome_arquivo = args[0]  # Nome do arquivo a ser salvo
        caminho_arquivo = os.path.join(self.DIRETORIO_IMAGENS, nome_arquivo)

        # Abre um arquivo binário para escrita
        with open(caminho_arquivo, 'wb') as f:
            while True:
                try:
                    # Recebe os dados da imagem em blocos de 4096 bytes
                    dados = server_socket.recv(4096)
                    if not dados:
                        break
                    # Verifica se o marcador 'FIM' foi recebido (indicando o final da transmissão)
                    if dados.endswith(b"FIM"):
                        print(f"[DEBUG] Recebido marcador 'FIM' do cluster. Transmissão concluída.")
                        break
                    f.write(dados)  # Escreve os dados recebidos no arquivo
                except Exception as e:
                    print(f"[DEBUG] Erro ao receber dados: {e}")
                    break
        print(f"[DEBUG] Imagem {nome_arquivo} recebida no cluster.")

    def listar_imagens(self, server_socket):
        """
        Envia ao servidor a lista de todas as imagens armazenadas no cluster.
        """
        imagens = os.listdir(self.DIRETORIO_IMAGENS)  # Lista todas as imagens no diretório
        if not imagens:
            print("[DEBUG] Nenhuma imagem encontrada no cluster.")
            server_socket.send("Nenhuma imagem encontrada.".encode())  # Informa que não há imagens
        else:
            imagens_str = ", ".join(imagens)  # Concatena os nomes das imagens em uma string
            print(f"[DEBUG] Enviando lista de imagens: {imagens_str}")
            server_socket.send(imagens_str.encode())  # Envia a lista de imagens ao servidor

    def download_imagem(self, server_socket, args):
        """
        Envia um arquivo de imagem específico solicitado pelo servidor.
        """
        nome_arquivo = args[0]
        caminho_arquivo = os.path.join(self.DIRETORIO_IMAGENS, nome_arquivo)

        # Verifica se o arquivo solicitado existe no diretório
        if os.path.exists(caminho_arquivo):
            # Abre o arquivo em modo binário para leitura
            with open(caminho_arquivo, 'rb') as f:
                while True:
                    # Lê os dados em blocos de 4096 bytes
                    dados = f.read(4096)
                    if not dados:
                        break
                    # Verifica se o marcador 'FIM' foi atingido
                    if dados.endswith(b"FIM"):
                        server_socket.send(dados[:-3])
                        break
                    server_socket.send(dados)  # Envia os dados para o servidor
            # Envia o marcador 'FIM' ao servidor para indicar que a transmissão acabou
            server_socket.send(b"FIM")
            print(f"[DEBUG] Imagem {nome_arquivo} enviada para o servidor.")
        else:
            # Se o arquivo não for encontrado, envia uma mensagem de erro
            server_socket.send(b"Arquivo nao encontrado")

    def deletar_imagem(self, server_socket, args):
        """
        Deleta um arquivo de imagem especificado pelo servidor.
        """
        nome_arquivo = args[0]
        caminho_arquivo = os.path.join(self.DIRETORIO_IMAGENS, nome_arquivo)
        # Verifica se o arquivo existe
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)  # Remove o arquivo
            server_socket.send(f"Imagem {nome_arquivo} deletada".encode())  # Confirma a remoção
        else:
            server_socket.send(f"Imagem {nome_arquivo} não encontrada".encode())  # Informa que o arquivo não foi encontrado

    def iniciar(self):
        """
        Método principal que inicia o cluster e fica aguardando conexões do servidor.
        """
        while True:
            # Aceita uma nova conexão do servidor
            server_socket, endereco = self.cluster_socket.accept()
            print(f"[DEBUG] Conexão recebida de {endereco}")
            self.tratar_requisicao(server_socket)  # Processa as requisições recebidas

# Inicializa o cluster ao executar o script
if __name__ == "__main__":
    cluster = Cluster()  # Instancia o objeto Cluster
    cluster.iniciar()  # Inicia o loop de espera por conexões