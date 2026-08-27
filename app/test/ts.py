import socket

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Задаем время ожидания соединения
        s.settimeout(1)
        # Попытка соединения с портом
        conn = s.connect_ex(('localhost', port))
        # Если соединение установлено, порт считается занятым
        if conn == 0:
            return True
        else:
            return False

port = 3000
if check_port(port):
    print(f"Порт {port} занят")
else:
    print(f"Порт {port} свободен")