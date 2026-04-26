"""
COMP 2322 Computer Networking Project
‘Multi-thread Web Server’
Name: LIU HONGXUAN
Student ID: 24128554d


Version 2: Multi-threaded, supports GET for text and image files, HEAD method, and request logging.
"""
import socket
import os
import threading
from datetime import datetime


HOST = '127.0.0.1'      # localhost IP address
PORT = 8080              # Port to listen on

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_files') # test_files folder is in the parent directory of src/


# Thread-safe lock for writing to the log file
log_lock = threading.Lock()

def log_request(client_ip, request_line, status_code):
    """
    Write one line to the server log file for each request.
    Format: IP - [timestamp] "request line" status_code
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f'{client_ip} - [{timestamp}] "{request_line}" {status_code}\n'
    
    # Use a lock so multiple threads don't write to the file at the same time
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server.log')
    with log_lock:
        with open(log_path, 'a') as log_file:
            log_file.write(log_line)




def handle_request(client_socket, client_address):
    """
    Deal with one client request in a separate thread.
    Supports GET (text + image files) and HEAD methods.

    """
    client_ip = client_address[0]


    try:
        # Read the HTTP request from the client
        request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
        
        # If we got nothing, just close and move on
        if not request_data:
            client_socket.close()
            return
        
        # The first line of the request tells us what the client wants
        # Example: "GET /index.html HTTP/1.1"
        request_line = request_data.splitlines()[0]
        print(f"[{client_ip}] {request_line}")
        
        parts = request_line.split()
        if len(parts) < 2:
            client_socket.close()
            return
        
        method = parts[0].upper()   # GET, HEAD, etc.
        path = parts[1]     # /index.html or /images/photo.jpg

        # Default to index.html if path is /
        if path == '/':
            path = '/index.html'
        
        # Build file path
        file_path = os.path.join(BASE_DIR, path.lstrip('/'))
        
        # ---- Check file status ----
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            # File not found -> 404
            error_body = "<h1>404 Not Found</h1><p>The file you requested does not exist.</p>"
            response = build_response(404, "Not Found", error_body)
            log_request(client_ip, request_line, 404)
        
        elif method == 'HEAD':
            # HEAD: same headers as GET, but no body
            content_type = get_content_type(file_path)
            file_size = os.path.getsize(file_path)
            response = build_head_response(200, "OK", content_type, file_size)
            log_request(client_ip, request_line, 200)
        
        elif method == 'GET':
            # GET: read file and send it
            content_type = get_content_type(file_path)
            
            # Check if it's a text file or binary file
            if content_type.startswith('text/') or content_type in ['application/javascript', 'text/css']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    body = f.read()
                response = build_response(200, "OK", body, content_type)
            else:
                # Binary files (images etc.)
                with open(file_path, 'rb') as f:
                    body = f.read()
                response = build_response(200, "OK", body, content_type)
            
            log_request(client_ip, request_line, 200)
        
        else:
            # Method not supported -> 400
            error_body = "<h1>400 Bad Request</h1><p>This server only supports GET and HEAD.</p>"
            response = build_response(400, "Bad Request", error_body)
            log_request(client_ip, request_line, 400)
        
        # Send the response
        client_socket.sendall(response)
    except Exception as e:
        print(f"  Error handling {client_ip}: {e}")
    finally:
        client_socket.close()


def build_response(status_code, status_text, body, content_type="text/html"):
    """
    Build an HTTP response with a body.
    """
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    status_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
    
    headers = ""
    headers += f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body)}\r\n"
    headers += "Connection: close\r\n"
    headers += "\r\n"
    
    return status_line.encode('utf-8') + headers.encode('utf-8') + body



def build_head_response(status_code, status_text, content_type, file_size):
    """
    Build a response for HEAD requests — headers only, no body.
    """
    status_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
    
    headers = ""
    headers += f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {file_size}\r\n"
    headers += "Connection: close\r\n"
    headers += "\r\n"
    
    return status_line.encode('utf-8') + headers.encode('utf-8')


def get_content_type(file_path):
    """
    Figure out MIME type from file extension.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    mime_map = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.txt': 'text/plain',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }
    
    return mime_map.get(ext, 'application/octet-stream')



def main():
    """
    Start the multi-threaded web server.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print("=" * 50)
    print("  COMP 2322 Web Server - Version 2")
    print("=" * 50)
    print(f"  Listening on: http://{HOST}:{PORT}/")
    print(f"  Serving files from: {BASE_DIR}")
    print(f"  Multi-threaded: YES")
    print(f"  Supported methods: GET, HEAD")
    print("=" * 50)
    print()
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"\nConnection from {client_address[0]}:{client_address[1]}")
            
            # Create a new thread for each client
            client_thread = threading.Thread(
                target=handle_request,
                args=(client_socket, client_address)
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    finally:
        server_socket.close()
        print("Socket closed. Goodbye!")


if __name__ == '__main__':
    main()


