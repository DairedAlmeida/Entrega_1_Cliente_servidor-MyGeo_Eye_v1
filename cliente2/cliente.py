import socket
import os

class Client:
    def __init__(self, host='localhost', port=6000):
        """
        Inicializa o cliente conectando-se ao servidor no endereço e porta especificados.
        Cria um socket para comunicação e realiza a conexão.
        """
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Cria o socket TCP
        self.client_socket.connect((self.host, self.port))  # Conecta ao servidor
        print("[DEBUG] Conectado ao servidor")

    def upload_image(self, file_path):
        """
        Faz o upload de uma imagem para o servidor.
        O caminho do arquivo deve ser especificado. Envia o nome e o conteúdo do arquivo em blocos.
        """
        if os.path.exists(file_path):  # Verifica se o arquivo existe
            file_name = os.path.basename(file_path)  # Obtém apenas o nome do arquivo (sem o caminho)
            self.client_socket.send(f"UPLOAD {file_name}".encode())  # Envia o comando UPLOAD e o nome do arquivo
            print(f"[DEBUG] Enviando arquivo: {file_name}")

            # Abre o arquivo em modo binário e envia seu conteúdo em blocos de 4096 bytes
            with open(file_path, 'rb') as f:
                while True:
                    dados = f.read(4096)
                    if not dados:
                        break
                    self.client_socket.send(dados)  # Envia os dados do arquivo
            self.client_socket.send(b"FIM")  # Marca o fim da transmissão com o marcador "FIM"
            print(self.client_socket.recv(1024).decode())  # Exibe a resposta do servidor
        else:
            print("Arquivo não encontrado. Tente novamente.")

    def list_images(self):
        """
        Solicita ao servidor a lista de imagens armazenadas e as exibe.
        """
        print("[DEBUG] Solicitando lista de imagens...")
        self.client_socket.send("LIST".encode())  # Envia o comando LIST para o servidor
        images = self.client_socket.recv(1024).decode()  # Recebe a lista de imagens
        print(f"Imagens: {images}")

    def download_image(self, file_name):
        """
        Solicita ao servidor o download de uma imagem específica.
        Recebe e armazena a imagem no diretório local.
        """
        print(f"[DEBUG] Solicitando download da imagem: {file_name}")
        self.client_socket.send(f"DOWNLOAD {file_name}".encode())  # Envia o comando DOWNLOAD e o nome do arquivo

        # Recebe a primeira resposta do servidor
        response = self.client_socket.recv(1024)
        if response == b"Arquivo nao encontrado":
            print("[DEBUG] O arquivo solicitado não foi encontrado no servidor.")
            print("Erro: Arquivo não encontrado.")
        else:
            print("[DEBUG] Iniciando o download da imagem...")

            # Se a imagem existir, cria um novo arquivo localmente para salvar a imagem recebida
            with open(file_name, 'wb') as f:
                while True:
                    dados = self.client_socket.recv(4096)  # Recebe os dados da imagem em blocos de 4096 bytes
                    if dados.endswith(b"FIM"):  # Verifica se o marcador de fim "FIM" foi recebido
                        f.write(dados[:-3])  # Remove o "FIM" do final dos dados recebidos
                        break
                    f.write(dados)  # Escreve os dados no arquivo
            
            print(f"Imagem {file_name} baixada com sucesso.")

    def delete_image(self, file_name):
        """
        Solicita ao servidor que delete uma imagem específica.
        Exibe a resposta do servidor (confirmação ou erro).
        """
        print(f"[DEBUG] Solicitando deleção da imagem: {file_name}")
        self.client_socket.send(f"DELETE {file_name}".encode())  # Envia o comando DELETE e o nome do arquivo
        print(self.client_socket.recv(1024).decode())  # Exibe a resposta do servidor

    def close(self):
        """
        Fecha a conexão do socket com o servidor.
        """
        print("[DEBUG] Fechando conexão com o servidor")
        self.client_socket.close()  # Fecha o socket de comunicação

    def run(self):
        """
        Executa o loop principal do cliente, que permite ao usuário escolher entre
        as opções de upload, listagem, download, deleção de imagens ou sair.
        """
        while True:
            # Menu de opções para o usuário
            print("\nEscolha uma opção:")
            print("1. Upload um arquivo de imagem de satélite")
            print("2. Listar as imagens inseridas")
            print("3. Baixar uma imagem inserida")
            print("4. Deletar uma imagem")
            print("5. Sair")

            choice = input("Digite sua escolha (1-5): ")

            # Dependendo da escolha, chama o método correspondente
            if choice == '1':
                file_path = input("Digite o caminho do arquivo de imagem: ")
                self.upload_image(file_path)

            elif choice == '2':
                self.list_images()

            elif choice == '3':
                file_name = input("Digite o nome da imagem a ser baixada: ")
                self.download_image(file_name)

            elif choice == '4':
                file_name = input("Digite o nome da imagem a ser deletada: ")
                self.delete_image(file_name)

            elif choice == '5':
                print("Saindo...")
                self.close()  # Fecha a conexão com o servidor e encerra o cliente
                break

            else:
                print("Escolha inválida. Tente novamente.")

# Inicializa o cliente e inicia o loop de interação
if __name__ == "__main__":
    client = Client()  # Cria uma instância do cliente
    client.run()  # Inicia o loop de interação com o usuário