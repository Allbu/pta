import logging
import os
import socket

import colorlog

# Configuration
PORT = 11550
# Valid clients are stored in a file users.txt
VALID_CLIENTS = open("users.txt").read().splitlines()
FILES_DIR = "./files"

# Set up logging
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "[%(log_color)s%(levelname)s%(reset)s] - %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)

logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def handle_cump(parts, client_socket, seq_num):
    if len(parts) != 3:
        client_socket.send(f"{seq_num} NOK".encode())
        return False
    client_name = parts[2]
    if client_name in VALID_CLIENTS:
        client_socket.send(f"{seq_num} OK".encode())
        return True
    else:
        client_socket.send(f"{seq_num} NOK".encode())
        return False


def handle_list(parts, client_socket, seq_num):
    try:
        files = os.listdir(FILES_DIR)
        files_list = ",".join(files)
        client_socket.send(f"{seq_num} ARQS {len(files)} {files_list}".encode())
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        client_socket.send(f"{seq_num} NOK".encode())


def handle_pega(parts, client_socket, seq_num):
    if len(parts) != 3:
        client_socket.send(f"{seq_num} NOK".encode())
        return
    file_name = parts[2]
    file_path = os.path.join(FILES_DIR, file_name)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            file_data = f.read()
        logger.info(f"Sending file {file_name} to client.")
        if file_data == b"":
            logger.warning(f"File is empty {file_name}.")
        client_socket.send(
            f"{seq_num} ARQ {len(file_data)} {file_data.decode()}".encode()
        )
    else:
        logger.debug(f"File {file_name} not found.")
        client_socket.send(f"{seq_num} NOK".encode())


def handle_term(parts, client_socket, seq_num):
    client_socket.send(f"{seq_num} OK".encode())
    return True


def handle_client(client_socket):
    seq_num = 0
    authenticated = False
    command_map = {
        "CUMP": handle_cump,
        "LIST": handle_list,
        "PEGA": handle_pega,
        "TERM": handle_term,
    }

    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                logger.info("No message received, closing connection.")
                break

            parts = message.split(" ")
            if len(parts) < 2:
                client_socket.send(f"{seq_num} NOK".encode())
                continue

            seq_num = int(parts[0])
            command = parts[1]

            if command in command_map:
                if command == "CUMP":
                    authenticated = command_map[command](parts, client_socket, seq_num)
                    if not authenticated:
                        logger.error(
                            "Client authentication failed, closing connection."
                        )
                        break
                elif authenticated:
                    command_map[command](parts, client_socket, seq_num)
                    if command == "TERM":
                        logger.info("Received TERM command, closing connection.")
                        break
                else:
                    client_socket.send(f"{seq_num} NOK".encode())
                    logger.warning(
                        "Received command before authentication, closing connection."
                    )
                    break
            else:
                client_socket.send(f"{seq_num} NOK".encode())
                logger.warning("Received unknown command, closing connection.")
                break
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            client_socket.send(f"{seq_num} NOK".encode())
            break

    client_socket.close()
    logger.info("Client connection closed.")


def start_server():
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("0.0.0.0", PORT))
        server_socket.listen(5)
        logger.info(f"Server listening on port {PORT}")

        while True:
            client_socket, addr = server_socket.accept()
            logger.info(f"Connection from {addr}")
            handle_client(client_socket)
    except Exception as e:
        logger.critical(f"Error starting server: {e}")


if __name__ == "__main__":
    start_server()
