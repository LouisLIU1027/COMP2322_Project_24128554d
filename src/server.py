"""
COMP 2322 Computer Networking Project
‘Multi-thread Web Server’
Name: LIU HONGXUAN
Student ID: 24128554d


Final Version
"""


import socket
import os
import threading
from datetime import datetime, timezone

# ========== Server Settings ==========
HOST = '127.0.0.1'
PORT = 8080

# test_files folder is one level up from src/
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_files')

# Lock for writing to log file safely from multiple threads
log_lock = threading.Lock()


# ============================================================
#  LOGGING
# ============================================================

def log_request(client_ip, request_line, status_code):
    """
    Append one line to server.log for each request.
    Format: IP - [timestamp] "request line" status_code
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f'{client_ip} - [{timestamp}] "{request_line}" {status_code}\n'

    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server.log')
    with log_lock:
        with open(log_path, 'a') as f:
            f.write(log_line)


# ============================================================
#  HTTP DATE HELPERS (for caching / 304)
# ============================================================

def format_http_time(ts):
    """
    Convert a Unix timestamp (seconds) to HTTP-date format.
    Example output: Sun, 26 Apr 2026 12:00:00 GMT
    """
    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def parse_http_time(s):
    """
    Parse an HTTP-date string back to an integer Unix timestamp.
    Returns 0 if the string is in a weird format we can't parse.
    """
    try:
        dt = datetime.strptime(s.strip(), '%a, %d %b %Y %H:%M:%S GMT')
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return 0


# ============================================================
#  MIME TYPE LOOKUP
# ============================================================

def get_content_type(file_path):
    """
    Guess the MIME type from the file extension.
    Browsers need this to know how to render the content.
    """
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        '.html': 'text/html',
        '.htm':  'text/html',
        '.txt':  'text/plain',
        '.css':  'text/css',
        '.js':   'application/javascript',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png':  'image/png',
        '.gif':  'image/gif',
    }
    return mime_map.get(ext, 'application/octet-stream')


# ============================================================
#  RESPONSE BUILDERS
# ============================================================

def build_response(status, text, body, content_type='text/html',
                   last_modified=None, connection='close'):
    """
    Build a full HTTP response with status line, headers, and body.
    Used for normal GET responses and error pages.
    """
    if isinstance(body, str):
        body = body.encode('utf-8')

    resp = f'HTTP/1.1 {status} {text}\r\n'
    resp += f'Content-Type: {content_type}\r\n'
    resp += f'Content-Length: {len(body)}\r\n'
    if last_modified:
        resp += f'Last-Modified: {last_modified}\r\n'
    resp += f'Connection: {connection}\r\n'
    resp += '\r\n'

    return resp.encode('utf-8') + body


def build_head_response(status, text, content_type, file_size,
                        last_modified=None, connection='close'):
    """
    Build a response with headers only (no body) — used for HEAD requests.
    """
    resp = f'HTTP/1.1 {status} {text}\r\n'
    resp += f'Content-Type: {content_type}\r\n'
    resp += f'Content-Length: {file_size}\r\n'
    if last_modified:
        resp += f'Last-Modified: {last_modified}\r\n'
    resp += f'Connection: {connection}\r\n'
    resp += '\r\n'

    return resp.encode('utf-8')


def build_304_response(last_modified, connection='close'):
    """
    Build a 304 Not Modified response — headers only, no body.
    """
    resp = 'HTTP/1.1 304 Not Modified\r\n'
    resp += f'Last-Modified: {last_modified}\r\n'
    resp += f'Connection: {connection}\r\n'
    resp += '\r\n'
    return resp.encode('utf-8')


# ============================================================
#  REQUEST HANDLER (runs in a separate thread for each client)
# ============================================================

def handle_request(client_socket, client_address):
    """
    The main function that handles one client connection.
    It reads the request, figures out what to do, sends a response,
    and respects the Connection header for keep-alive or close.
    """
    client_ip = client_address[0]
    keep_alive = False

    try:
        # --- read the request ---
        request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
        if not request_data:
            client_socket.close()
            return

        lines = request_data.splitlines()
        request_line = lines[0]
        print(f'[{client_ip}] {request_line}')

        # --- parse request line ---
        parts = request_line.split()
        if len(parts) < 2:
            body = '<h1>400 Bad Request</h1><p>Malformed request line.</p>'
            resp = build_response(400, 'Bad Request', body)
            client_socket.sendall(resp)
            log_request(client_ip, request_line, 400)
            client_socket.close()
            return

        method = parts[0].upper()
        path = parts[1]

        # --- parse headers ---
        if_modified_since = None
        connection_header = 'close'

        for line in lines[1:]:
            if line.lower().startswith('if-modified-since:'):
                if_modified_since = line.split(':', 1)[1].strip()
            if line.lower().startswith('connection:'):
                connection_header = line.split(':', 1)[1].strip().lower()

        if connection_header == 'keep-alive':
            keep_alive = True

        # --- default path ---
        if path == '/':
            path = '/index.html'

        file_path = os.path.join(BASE_DIR, path.lstrip('/'))

        # --- security: block directory traversal ---
        real_path = os.path.realpath(file_path)
        real_base = os.path.realpath(BASE_DIR)
        if not real_path.startswith(real_base):
            body = '<h1>403 Forbidden</h1><p>Access denied.</p>'
            resp = build_response(403, 'Forbidden', body)
            client_socket.sendall(resp)
            log_request(client_ip, request_line, 403)
            client_socket.close()
            return

        # --- 404: file not found ---
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            body = '<h1>404 Not Found</h1><p>That file does not exist.</p>'
            resp = build_response(404, 'Not Found', body,
                                  connection='keep-alive' if keep_alive else 'close')
            log_request(client_ip, request_line, 404)

        # --- 403: no permission to read ---
        elif not os.access(file_path, os.R_OK):
            body = '<h1>403 Forbidden</h1><p>Permission denied.</p>'
            resp = build_response(403, 'Forbidden', body,
                                  connection='keep-alive' if keep_alive else 'close')
            log_request(client_ip, request_line, 403)

        else:
            # --- get last modified time ---
            last_mod_ts = os.path.getmtime(file_path)
            last_mod_str = format_http_time(last_mod_ts)

            # --- check 304 ---
            if if_modified_since:
                client_ts = parse_http_time(if_modified_since)
                if client_ts and client_ts >= int(last_mod_ts):
                    resp = build_304_response(last_mod_str,
                                              connection='keep-alive' if keep_alive else 'close')
                    log_request(client_ip, request_line, 304)
                    client_socket.sendall(resp)
                    if not keep_alive:
                        client_socket.close()
                    return

            # --- GET ---
            if method == 'GET':
                content_type = get_content_type(file_path)
                if content_type.startswith('text/') or content_type in ['application/javascript', 'text/css']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        body = f.read()
                else:
                    with open(file_path, 'rb') as f:
                        body = f.read()
                resp = build_response(200, 'OK', body, content_type,
                                      last_modified=last_mod_str,
                                      connection='keep-alive' if keep_alive else 'close')
                log_request(client_ip, request_line, 200)

            # --- HEAD ---
            elif method == 'HEAD':
                content_type = get_content_type(file_path)
                file_size = os.path.getsize(file_path)
                resp = build_head_response(200, 'OK', content_type, file_size,
                                           last_modified=last_mod_str,
                                           connection='keep-alive' if keep_alive else 'close')
                log_request(client_ip, request_line, 200)

            # --- anything else -> 400 ---
            else:
                body = '<h1>400 Bad Request</h1><p>Only GET and HEAD are supported.</p>'
                resp = build_response(400, 'Bad Request', body,
                                      connection='keep-alive' if keep_alive else 'close')
                log_request(client_ip, request_line, 400)

        # --- send response ---
        client_socket.sendall(resp)

        # --- handle keep-alive: read next request from same connection ---
        while keep_alive:
            try:
                client_socket.settimeout(5)
                request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
                if not request_data:
                    break

                lines = request_data.splitlines()
                request_line = lines[0]
                print(f'[{client_ip}] (keep-alive) {request_line}')

                parts = request_line.split()
                if len(parts) < 2:
                    break
                path = parts[1]
                if path == '/':
                    path = '/index.html'
                file_path = os.path.join(BASE_DIR, path.lstrip('/'))

                if os.path.exists(file_path) and os.path.isfile(file_path) and os.access(file_path, os.R_OK):
                    content_type = get_content_type(file_path)
                    if content_type.startswith('text/') or content_type in ['application/javascript', 'text/css']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            body = f.read()
                    else:
                        with open(file_path, 'rb') as f:
                            body = f.read()
                    last_mod_str = format_http_time(os.path.getmtime(file_path))
                    resp = build_response(200, 'OK', body, content_type,
                                          last_modified=last_mod_str,
                                          connection='keep-alive')
                    log_request(client_ip, request_line, 200)
                else:
                    body = '<h1>404 Not Found</h1>'
                    resp = build_response(404, 'Not Found', body, connection='keep-alive')
                    log_request(client_ip, request_line, 404)

                client_socket.sendall(resp)

            except socket.timeout:
                break

        client_socket.close()

    except Exception as e:
        print(f'  Error with {client_ip}: {e}')
    finally:
        try:
            client_socket.close()
        except:
            pass


# ============================================================
#  MAIN SERVER LOOP
# ============================================================

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print('=' * 55)
    print('  COMP 2322 — Multi-threaded Web Server')
    print('=' * 55)
    print(f'  Address:    http://{HOST}:{PORT}/')
    print(f'  Root dir:   {BASE_DIR}')
    print(f'  Methods:    GET, HEAD')
    print(f'  Statuses:   200, 304, 400, 403, 404')
    print(f'  Connection: keep-alive & close')
    print('=' * 55)
    print()

    try:
        while True:
            client_sock, client_addr = server_socket.accept()
            print(f'\n--> Connection from {client_addr[0]}:{client_addr[1]}')
            t = threading.Thread(target=handle_request,
                                 args=(client_sock, client_addr))
            t.start()
    except KeyboardInterrupt:
        print('\nServer stopped.')
    finally:
        server_socket.close()
        print('Socket closed.')


if __name__ == '__main__':
    main()


