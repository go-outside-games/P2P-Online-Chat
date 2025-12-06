import pygame
import socket
import threading
import json
import time
from datetime import datetime

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
BLUE = (70, 130, 255)
GREEN = (50, 200, 50)
RED = (255, 70, 70)
MAX_CLIENTS = 10
PORT = 5555

# Fonts
font = pygame.font.Font(None, 24)
small_font = pygame.font.Font(None, 20)
title_font = pygame.font.Font(None, 36)

class ChatServer:
    def __init__(self, port=PORT):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.port = port
        self.clients = []
        self.usernames = {}
        self.running = False
        
    def start(self):
        try:
            self.server.bind(('0.0.0.0', self.port))
            self.server.listen(MAX_CLIENTS)
            self.running = True
            threading.Thread(target=self.accept_clients, daemon=True).start()
            return True
        except:
            return False
    
    def accept_clients(self):
        while self.running:
            try:
                self.server.settimeout(1)
                client, addr = self.server.accept()
                if len(self.clients) < MAX_CLIENTS:
                    self.clients.append(client)
                    threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
                else:
                    client.close()
            except socket.timeout:
                continue
            except:
                break
    
    def handle_client(self, client):
        try:
            # Receive username
            username = client.recv(1024).decode('utf-8')
            self.usernames[client] = username
            self.broadcast(f"[SERVER] {username} joined the chat!", None)
            
            while self.running:
                msg = client.recv(1024).decode('utf-8')
                if msg:
                    self.broadcast(f"{username}: {msg}", client)
                else:
                    break
        except:
            pass
        finally:
            if client in self.clients:
                self.clients.remove(client)
                username = self.usernames.pop(client, "Unknown")
                self.broadcast(f"[SERVER] {username} left the chat.", None)
                client.close()
    
    def broadcast(self, msg, sender):
        for client in self.clients[:]:
            if client != sender:
                try:
                    client.send(msg.encode('utf-8'))
                except:
                    self.clients.remove(client)
    
    def stop(self):
        self.running = False
        for client in self.clients:
            client.close()
        self.server.close()

class ChatClient:
    def __init__(self):
        self.client = None
        self.connected = False
        self.messages = []
        
    def connect(self, host, port, username):
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((host, port))
            self.client.send(username.encode('utf-8'))
            self.connected = True
            threading.Thread(target=self.receive_messages, daemon=True).start()
            return True
        except:
            return False
    
    def receive_messages(self):
        while self.connected:
            try:
                msg = self.client.recv(1024).decode('utf-8')
                if msg:
                    timestamp = datetime.now().strftime("%H:%M")
                    self.messages.append(f"[{timestamp}] {msg}")
            except:
                self.connected = False
                break
    
    def send_message(self, msg):
        if self.connected:
            try:
                self.client.send(msg.encode('utf-8'))
                timestamp = datetime.now().strftime("%H:%M")
                self.messages.append(f"[{timestamp}] You: {msg}")
            except:
                self.connected = False
    
    def disconnect(self):
        self.connected = False
        if self.client:
            self.client.close()

class Button:
    def __init__(self, x, y, w, h, text, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover = False
    
    def draw(self, screen):
        color = tuple(min(c + 30, 255) for c in self.color) if self.hover else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=5)
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class InputBox:
    def __init__(self, x, y, w, h, placeholder=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ''
        self.placeholder = placeholder
        self.active = False
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return True
            elif len(self.text) < 30:
                self.text += event.unicode
        return False
    
    def draw(self, screen):
        color = BLUE if self.active else GRAY
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, color, self.rect, 2, border_radius=3)
        display_text = self.text if self.text else self.placeholder
        text_color = BLACK if self.text else DARK_GRAY
        text_surf = font.render(display_text, True, text_color)
        screen.blit(text_surf, (self.rect.x + 5, self.rect.y + 10))

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("P2P")
    clock = pygame.time.Clock()
    
    # State management
    state = "menu"  # menu, host, join, chat
    server = None
    client = ChatClient()
    
    # UI Elements
    host_btn = Button(250, 250, 300, 50, "Host Server", GREEN)
    join_btn = Button(250, 320, 300, 50, "Join Server", BLUE)
    back_btn = Button(50, 500, 150, 40, "Back", GRAY)
    
    username_input = InputBox(250, 200, 300, 40, "Enter username...")
    host_input = InputBox(250, 270, 300, 40, "Server IP (e.g., 192.168.1.100)")
    port_input = InputBox(250, 320, 300, 40, f"Port (default: {PORT})")
    
    connect_btn = Button(250, 380, 300, 50, "Connect", GREEN)
    start_server_btn = Button(250, 380, 300, 50, "Start Server", GREEN)
    
    message_input = InputBox(10, 540, 680, 40, "Type your message...")
    send_btn = Button(700, 540, 90, 40, "Send", BLUE)
    disconnect_btn = Button(650, 10, 140, 40, "Disconnect", RED)
    
    scroll_offset = 0
    status_msg = ""
    status_time = 0
    
    running = True
    while running:
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if state == "menu":
                if host_btn.handle_event(event):
                    state = "host"
                if join_btn.handle_event(event):
                    state = "join"
            
            elif state == "host":
                username_input.handle_event(event)
                if back_btn.handle_event(event):
                    state = "menu"
                if start_server_btn.handle_event(event) and username_input.text:
                    server = ChatServer(PORT)
                    if server.start():
                        if client.connect("127.0.0.1", PORT, username_input.text):
                            state = "chat"
                            hostname = socket.gethostname()
                            local_ip = socket.gethostbyname(hostname)
                            status_msg = f"Server started on {local_ip}:{PORT}"
                            status_time = time.time()
                        else:
                            status_msg = "Failed to connect to own server"
                            status_time = time.time()
                    else:
                        status_msg = "Failed to start server"
                        status_time = time.time()
            
            elif state == "join":
                username_input.handle_event(event)
                host_input.handle_event(event)
                port_input.handle_event(event)
                if back_btn.handle_event(event):
                    state = "menu"
                if connect_btn.handle_event(event) and username_input.text and host_input.text:
                    port = int(port_input.text) if port_input.text.isdigit() else PORT
                    if client.connect(host_input.text, port, username_input.text):
                        state = "chat"
                    else:
                        status_msg = "Connection failed"
                        status_time = time.time()
            
            elif state == "chat":
                if message_input.handle_event(event) and message_input.text:
                    client.send_message(message_input.text)
                    message_input.text = ""
                if send_btn.handle_event(event) and message_input.text:
                    client.send_message(message_input.text)
                    message_input.text = ""
                if disconnect_btn.handle_event(event):
                    client.disconnect()
                    if server:
                        server.stop()
                        server = None
                    state = "menu"
                    client = ChatClient()
                
                if event.type == pygame.MOUSEWHEEL:
                    scroll_offset = max(0, scroll_offset - event.y * 20)
        
        # Drawing
        screen.fill(WHITE)
        
        if state == "menu":
            title = title_font.render("P2P", True, BLACK)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
            host_btn.draw(screen)
            join_btn.draw(screen)
            
            info = small_font.render("Host: Create a server on your computer", True, DARK_GRAY)
            screen.blit(info, (WIDTH//2 - info.get_width()//2, 400))
            info2 = small_font.render("Join: Connect to someone else's server", True, DARK_GRAY)
            screen.blit(info2, (WIDTH//2 - info2.get_width()//2, 425))
        
        elif state == "host":
            title = title_font.render("Host Server", True, BLACK)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
            username_input.draw(screen)
            start_server_btn.draw(screen)
            back_btn.draw(screen)
            
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            info = small_font.render(f"Your IP: {local_ip} | Port: {PORT}", True, DARK_GRAY)
            screen.blit(info, (WIDTH//2 - info.get_width()//2, 450))
        
        elif state == "join":
            title = title_font.render("Join Server", True, BLACK)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
            username_input.draw(screen)
            host_input.draw(screen)
            port_input.draw(screen)
            connect_btn.draw(screen)
            back_btn.draw(screen)
        
        elif state == "chat":
            # Chat header
            pygame.draw.rect(screen, DARK_GRAY, (0, 0, WIDTH, 60))
            header_text = font.render(f"Connected as {username_input.text}", True, WHITE)
            screen.blit(header_text, (20, 18))
            disconnect_btn.draw(screen)
            
            # Messages area
            pygame.draw.rect(screen, GRAY, (10, 70, 780, 460))
            
            y_pos = 480 - scroll_offset
            for msg in reversed(client.messages[-100:]):
                msg_surf = small_font.render(msg, True, BLACK)
                if y_pos > 70 and y_pos < 520:
                    screen.blit(msg_surf, (20, y_pos))
                y_pos -= 25
            
            # Input area
            message_input.draw(screen)
            send_btn.draw(screen)
        
        # Status message
        if status_msg and time.time() - status_time < 3:
            status_surf = font.render(status_msg, True, RED)
            screen.blit(status_surf, (WIDTH//2 - status_surf.get_width()//2, 480))
        
        pygame.display.flip()
    
    # Cleanup
    client.disconnect()
    if server:
        server.stop()
    pygame.quit()

if __name__ == "__main__":
    main()
