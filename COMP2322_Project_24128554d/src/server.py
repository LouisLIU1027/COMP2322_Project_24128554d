"""
COMP 2322 Computer Networking Project
‘Multi-thread Web Server’
Name: LIU HONGXUAN
Student ID: 24128554d

"""
import socket
import os
import threading

HOST = '127.0.0.1'      # localhost IP address
PORT = 8080              # Port to listen on

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_files')

def handle_request(client_socket):
    """
    Deal with one client request.
    Reads what the browser sent, figures out which file it wants,
    and sends back either the file or a 404 error page.
    """
    try:
        # Read the HTTP request from the client
        request_data = client_socket.recv(1024).decode('utf-8')
        
        # If we got nothing, just close and move on
        if not request_data:
            client_socket.close()
            return
        
        # The first line of the request tells us what the client wants
        # Example: "GET /index.html HTTP/1.1"
        request_line = request_data.splitlines()[0]
        print(f"Got request: {request_line}")
        
        parts = request_line.split()
        if len(parts) < 2:
            client_socket.close()
            return
        
        method = parts[0]   # GET, HEAD, etc.
        path = parts[1]     # /index.html or /images/photo.jpg
        
        # For now, I'm only handling GET requests
        if method != 'GET':
            error_msg = "<h1>400 Bad Request</h1><p>This server only supports GET for now.</p>"
            response = build_response(400, "Bad Request", error_msg)
            client_socket.sendall(response)
            client_socket.close()
            return
        
        # If the user just goes to "/", show them index.html by default
        if path == '/':
            path = '/index.html'
        
        # Build the actual file path on my computer
        # Remove the leading "/" so os.path.join works correctly
        file_path = os.path.join(BASE_DIR, path.lstrip('/'))
        
        # Check: does the file actually exist?
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # Yes! Read it and send it back
            with open(file_path, 'rb') as f:
                content = f.read()
            
            content_type = get_content_type(file_path)
            response = build_response(200, "OK", content, content_type)
            print(f"  -> 200 OK, {len(content)} bytes")
        else:
            # File not found, send a 404 page
            error_html = "<h1>404 Not Found</h1><p>Sorry, that file doesn't exist on this server.</p>"
            response = build_response(404, "Not Found", error_html)
            print(f"  -> 404 Not Found")
        
        # Send the response back to the browser
        client_socket.sendall(response)
        
    except Exception as e:
        print(f"Oops, something went wrong: {e}")
    finally:
        # Always close the connection when we're done
        client_socket.close()


def build_response(status_code, status_text, body, content_type="text/html"):
    """
    Build a proper HTTP response message.
    status_code: 200, 404, etc.
    status_text: "OK", "Not Found", etc.
    body: the actual content (html, text, or image bytes)
    content_type: the MIME type like "text/html" or "image/png"
    """
    # Make sure the body is bytes, not a string
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    # The status line
    status_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
    
    # Headers
    headers = ""
    headers += f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body)}\r\n"
    headers += "Connection: close\r\n"   # close after each request (non-persistent for now)
    headers += "\r\n"                    # blank line = end of headers
    
    # Put it all together as bytes
    response = status_line.encode('utf-8') + headers.encode('utf-8') + body
    return response


def get_content_type(file_path):
    """
    Figure out the MIME type based on the file extension.
    Browsers need this to know how to display the content.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # A simple mapping of extensions to MIME types
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
    Start the web server and keep it running.
    """
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # This option lets us reuse the port immediately after stopping the server
    # Without it, sometimes you get "Address already in use" errors
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to our host and port
    server_socket.bind((HOST, PORT))
    
    # Start listening for connections (backlog of 5)
    server_socket.listen(5)
    
    print("=" * 50)
    print("  COMP 2322 Web Server - Version 1")
    print("=" * 50)
    print(f"  Listening on: http://{HOST}:{PORT}/")
    print(f"  Serving files from: {BASE_DIR}")
    print("=" * 50)
    print()
    
    try:
        while True:
            # Wait for someone to connect
            client_socket, client_address = server_socket.accept()
            print(f"\nNew connection from {client_address[0]}:{client_address[1]}")
            
            # Handle their request
            handle_request(client_socket)
            
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("\nServer stopped by user.")
    finally:
        server_socket.close()
        print("Socket closed. Goodbye!")


# This is the entry point when you run the script directly
if __name__ == '__main__':
    main()