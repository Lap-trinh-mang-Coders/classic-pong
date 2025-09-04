import socket
import threading
import pickle
import time

WIDTH, HEIGHT = 700, 500
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 60
SERVER = "0.0.0.0"
PORT = 5555

class Game:
    def __init__(self):
        self.ball = [WIDTH // 2, HEIGHT // 2, 3, 3]
        self.paddles = [
            [50, HEIGHT // 2 - PADDLE_HEIGHT // 2],
            [WIDTH - 50 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2]
        ]
        self.scores = [0, 0]
        self.match_scores = [0, 0]
        self.player_names = ["Player 1", "Player 2"]
        self.game_over = False
        self.winner_id = -1
        self.difficulty = 1
        self.ball_speed_base = 2 + self.difficulty

    def move_ball(self):
        if self.game_over:
            return
        
        self.ball[0] += self.ball[2] * self.ball_speed_base
        self.ball[1] += self.ball[3] * self.ball_speed_base
        
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
            if self.scores[1] >= 10:
                self.match_scores[1] += 1
                self.scores = [0, 0]
            self.reset_ball()
        elif self.ball[0] > WIDTH:
            self.scores[0] += 1
            if self.scores[0] >= 10:
                self.match_scores[0] += 1
                self.scores = [0, 0]
            self.reset_ball()

        if self.match_scores[0] >= 3:
            self.game_over = True
            self.winner_id = 0
        elif self.match_scores[1] >= 3:
            self.game_over = True
            self.winner_id = 1

    def reset_ball(self):
        self.ball[0] = WIDTH // 2
        self.ball[1] = HEIGHT // 2
        self.ball[2] *= -1
    
    def update_paddles(self, player_id, direction):
        PADDLE_SPEED = 5 + (self.difficulty - 1) * 1
        if direction == "up":
            self.paddles[player_id][1] -= PADDLE_SPEED
        elif direction == "down":
            self.paddles[player_id][1] += PADDLE_SPEED
        self.paddles[player_id][1] = max(0, min(self.paddles[player_id][1], HEIGHT - PADDLE_HEIGHT))

    def get_game_state(self):
        return {
            "ball": self.ball,
            "paddles": self.paddles,
            "scores": self.scores,
            "match_scores": self.match_scores,
            "player_names": self.player_names,
            "game_over": self.game_over,
            "winner_id": self.winner_id
        }

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER, PORT))
server_socket.listen(2)
print("Server is waiting for connections...")

clients = []
game = Game()
game_lock = threading.Lock()
start_game_event = threading.Event()
players_data_received_count = 0
players_data_lock = threading.Lock()

def handle_client(conn, addr, player_id):
    global players_data_received_count
    print(f"[{addr}] connected as Player {player_id + 1}")
    
    conn.send(str(player_id).encode())
    
    try:
        data = conn.recv(1024)
        if not data:
            print(f"[{addr}] disconnected before sending data.")
            conn.close()
            return

        received_data = pickle.loads(data)
        with game_lock:
            if player_id == 0:
                game.player_names[0] = received_data["name"]
                game.difficulty = received_data["difficulty"]
                game.ball_speed_base = 2 + game.difficulty
            else:
                game.player_names[1] = received_data
        
        with players_data_lock:
            players_data_received_count += 1
            if players_data_received_count == 2:
                print("All players ready. Setting game start event.")
                start_game_event.set()
                clients[0].send("start".encode())
                clients[1].send("start".encode())
    except (socket.error, ConnectionResetError) as e:
        print(f"Error receiving initial data: {e}")
        conn.close()
        return

    start_game_event.wait()
    
    while True:
        try:
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
    start_game_event.wait()
    while True:
        with game_lock:
            game.move_ball()
            state = game.get_game_state()
        
        try:
            clients[0].sendall(pickle.dumps(state))
            clients[1].sendall(pickle.dumps(state))
        except (socket.error, ConnectionResetError):
            print("Error sending data to clients.")
            break
        
        time.sleep(0.01)

def main():
    threading.Thread(target=game_loop, daemon=True).start()
    
    player_id_counter = 0
    client_threads = []
    while player_id_counter < 2:
        conn, addr = server_socket.accept()
        clients.append(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr, player_id_counter))
        thread.daemon = True
        thread.start()
        client_threads.append(thread)
        player_id_counter += 1

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()