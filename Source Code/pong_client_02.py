import pygame
import socket
import pickle
import threading
import time

WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 60
BALL_RADIUS = 7
FPS = 60
SERVER = "127.0.0.1"
PORT = 5555


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Pong")
clock = pygame.time.Clock()


game_state = {}
my_id = -1
is_connected = False
game_running = False

font_small = pygame.font.SysFont("comicsans", 28)
font_medium = pygame.font.SysFont("comicsans", 30)
font_large = pygame.font.SysFont("comicsans", 60)

def draw_game(screen, state):
    screen.fill(BLACK)
    
    pygame.draw.rect(screen, WHITE, (state["paddles"][0][0], state["paddles"][0][1], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.rect(screen, WHITE, (state["paddles"][1][0], state["paddles"][1][1], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.circle(screen, WHITE, (int(state["ball"][0]), int(state["ball"][1])), BALL_RADIUS)
    pygame.draw.aaline(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT))
    
    name1_text = font_small.render(state["player_names"][0], True, GREEN)
    score1_text = font_medium.render(str(state["scores"][0]), True, WHITE)
    name2_text = font_small.render(state["player_names"][1], True, RED)
    score2_text = font_medium.render(str(state["scores"][1]), True, WHITE)
    
    screen.blit(name1_text, (WIDTH // 4 - name1_text.get_width() // 2, 60))
    screen.blit(score1_text, (WIDTH // 4 - score1_text.get_width() // 2, 10))
    screen.blit(name2_text, (WIDTH * 3 // 4 - name2_text.get_width() // 2, 60))
    screen.blit(score2_text, (WIDTH * 3 // 4 - score2_text.get_width() // 2, 10))
    
    match_score_text = font_medium.render(f"{state['match_scores'][0]} - {state['match_scores'][1]}", True, WHITE)
    screen.blit(match_score_text, (WIDTH // 2 - match_score_text.get_width() // 2, 10))
    
    if state["game_over"]:
        winner_name = state["player_names"][state["winner_id"]]
        winner_text = font_large.render(f"{winner_name} WINS!", True, YELLOW)
        text_rect = winner_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(winner_text, text_rect)
        
    pygame.display.update()


def draw_menu(screen, input_text, difficulty, player_id, status_text=""):
    screen.fill(BLACK)
    
    title_text = font_large.render("PING PONG", True, YELLOW)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    screen.blit(title_text, title_rect)
    
    if player_id == 0:
        instruction_text = font_small.render("Enter your name & choose difficulty. Press ENTER to start.", True, WHITE)
        difficulty_text = font_small.render(f"Difficulty: {['Easy', 'Medium', 'Hard'][difficulty]}", True, BLUE)
        diff_rect = difficulty_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
        screen.blit(difficulty_text, diff_rect)
    else:
        instruction_text = font_small.render("Enter your name. Waiting for Player 1...", True, WHITE)
        
    instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(instruction_text, instruction_rect)

    pygame.draw.rect(screen, WHITE, (WIDTH // 2 - 150, HEIGHT // 2, 300, 50), 2)
    input_box_text = font_medium.render(input_text, True, WHITE)
    screen.blit(input_box_text, (WIDTH // 2 - 140, HEIGHT // 2 + 5))
    
    status_surface = font_small.render(status_text, True, WHITE)
    status_rect = status_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
    screen.blit(status_surface, status_rect)
    
    pygame.display.update()

def connect():
    global my_id, is_connected
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((SERVER, PORT))
        my_id_str = client.recv(1024).decode()
        my_id = int(my_id_str)
        is_connected = True
        print(f"Connected as Player {my_id + 1}")
        return client
    except socket.error as e:
        print(f"Error connecting to server: {e}")
        return None

def receive_data(client):
    global game_state, is_connected
    while is_connected:
        try:
            data = client.recv(4096)
            if not data:
                break
            try:
                if data.decode() == "start":
                    print("Received 'start' signal from server. Starting game...")
                    continue
            except UnicodeDecodeError:
                pass 

            game_state = pickle.loads(data)
        except (socket.error, ConnectionResetError, EOFError, pickle.UnpicklingError) as e:
            print(f"Lost connection to server: {e}")
            is_connected = False
            break

def main():
    global my_id, is_connected, game_state, game_running
    
    client_socket = connect()
    if not client_socket:
        return

    input_text = ""
    difficulty = 1
    menu_running = True
    while menu_running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                menu_running = False
                pygame.quit()
                client_socket.close()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if my_id == 0:
                        data = {"name": input_text if input_text else "Player 1", "difficulty": difficulty}
                    else:
                        data = input_text if input_text else "Player 2"
                    try:
                        client_socket.send(pickle.dumps(data))
                        response = client_socket.recv(1024).decode()
                        if response == "start":
                            menu_running = False
                    except (socket.error, ConnectionResetError) as e:
                        print(f"Error sending data or receiving start signal: {e}")
                        menu_running = False
                        break
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_UP and my_id == 0:
                    difficulty = (difficulty + 1) % 3
                elif event.key == pygame.K_DOWN and my_id == 0:
                    difficulty = (difficulty - 1) % 3
                else:
                    input_text += event.unicode
        
        draw_menu(screen, input_text, difficulty, my_id, "Connected. Enter your name and press ENTER.")
    
    game_running = True
    recv_thread = threading.Thread(target=receive_data, args=(client_socket,), daemon=True)
    recv_thread.start()
    
    while game_running:
        clock.tick(FPS)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
        
        if is_connected:
            keys = pygame.key.get_pressed()
            move_cmd = ""
            if keys[pygame.K_UP]:
                move_cmd = "up"
            if keys[pygame.K_DOWN]:
                move_cmd = "down"
            
            if move_cmd:
                try:
                    client_socket.send(move_cmd.encode())
                except socket.error as e:
                    print(f"Error sending data: {e}")
                    is_connected = False
            
            if game_state:
                draw_game(screen, game_state)
        
        else:
            font = pygame.font.SysFont("comicsans", 30)
            text = font.render("Disconnected from server...", True, WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.fill(BLACK)
            screen.blit(text, text_rect)
            pygame.display.update()
            
            if not is_connected:
                game_running = False

    pygame.quit()
    client_socket.close()

if __name__ == "__main__":
    main()