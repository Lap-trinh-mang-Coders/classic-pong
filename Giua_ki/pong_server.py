# pong_server.py (phiên bản đã sửa)
import socket
import threading
import pickle
import time

# --- HẰNG SỐ CƠ BẢN ---
WIDTH, HEIGHT = 700, 500
BALL_X, BALL_Y = WIDTH // 2, HEIGHT // 2
BALL_SPEED_X, BALL_SPEED_Y = 3, 3
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 60
PADDLE_SPEED = 5
SERVER = "0.0.0.0"
PORT = 5555

# --- LỚP GAME ---
class Game:
    def __init__(self):
        self.ball = [BALL_X, BALL_Y, BALL_SPEED_X, BALL_SPEED_Y]
        self.paddles = [
            [50, HEIGHT // 2 - PADDLE_HEIGHT // 2],  # Paddle 1
            [WIDTH - 50 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2]  # Paddle 2
        ]
        self.scores = [0, 0]
        self.game_state = {
            "ball": self.ball,
            "paddles": self.paddles,
            "scores": self.scores
        }
    
    def move_ball(self):
        self.ball[0] += self.ball[2]
        self.ball[1] += self.ball[3]
        
        if self.ball[1] <= 0 or self.ball[1] >= HEIGHT:
            self.ball[3] *= -1
            
        if (self.ball[0] <= self.paddles[0][0] + PADDLE_WIDTH and
            self.paddles[0][1] <= self.ball[1] <= self.paddles[0][1] + PADDLE_HEIGHT):
            self.ball[2] *= -1
        if (self.ball[0] >= self.paddles[1][0] - PADDLE_WIDTH and
            self.paddles[1][1] <= self.ball[1] <= self.paddles[1][1] + PADDLE_HEIGHT):
            self.ball[2] *= -1
            
        if self.ball[0] < 0:
            self.scores[1] += 1
            self.reset_ball()
        elif self.ball[0] > WIDTH:
            self.scores[0] += 1
            self.reset_ball()

    def reset_ball(self):
        self.ball[0] = BALL_X
        self.ball[1] = BALL_Y
        self.ball[2] *= -1
    
    def update_paddles(self, player_id, direction):
        if direction == "up":
            self.paddles[player_id][1] -= PADDLE_SPEED
        elif direction == "down":
            self.paddles[player_id][1] += PADDLE_SPEED
        self.paddles[player_id][1] = max(0, min(self.paddles[player_id][1], HEIGHT - PADDLE_HEIGHT))

    def get_game_state(self):
        return self.game_state

# --- THIẾT LẬP SOCKET VÀ LUỒNG ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER, PORT))
server_socket.listen(2)
print("Server is waiting for connections...")

clients = []
game = Game()
game_lock = threading.Lock()
start_game_event = threading.Event() # Dùng Event để đồng bộ hóa

def handle_client(conn, addr, player_id):
    print(f"[{addr}] connected as Player {player_id + 1}")
    
    # Gửi ID người chơi đến client
    conn.send(str(player_id).encode())
    
    # Chờ cho đến khi cả hai người chơi đã kết nối
    start_game_event.wait()
    
    while True:
        try:
            # Nhận dữ liệu từ client
            data = conn.recv(4096).decode()
            if not data:
                print(f"[{addr}] disconnected.")
                break
            
            with game_lock:
                game.update_paddles(player_id, data)
                
        except (socket.error, ConnectionResetError):
            print(f"[{addr}] disconnected.")
            break
        
    conn.close()
    
def game_loop():
    while True:
        # Kiểm tra xem game đã bắt đầu chưa
        if start_game_event.is_set():
            with game_lock:
                game.move_ball()
                state = game.get_game_state()
            
            # Gửi trạng thái game đến cả hai client
            try:
                clients[0].sendall(pickle.dumps(state))
                clients[1].sendall(pickle.dumps(state))
            except (socket.error, ConnectionResetError):
                print("Error sending data to clients.")
                break
            
            time.sleep(0.01) # Tốc độ cập nhật game (100 FPS)

def main():
    threading.Thread(target=game_loop, daemon=True).start()
    
    player_id_counter = 0
    while player_id_counter < 2:
        conn, addr = server_socket.accept()
        clients.append(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr, player_id_counter))
        thread.start()
        player_id_counter += 1
        
    # Sau khi có đủ 2 người chơi, set cờ để bắt đầu game
    print("Two players connected. Starting game...")
    start_game_event.set()
    
if __name__ == "__main__":
    main()