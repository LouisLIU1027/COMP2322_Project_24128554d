# COMP 2322 - Multi-threaded Web Server

**Name:** LIU HONGXUAN  
**Student ID:** 24128554d

## How to Run

### Requirements
- Python 3.8 or higher
- No external libraries needed (only built-in modules)

### Steps

1. Open a terminal and navigate to the `src/` folder:

```bash
cd src




Start: python server.py


Interview...
=======================================================
  COMP 2322 — Multi-threaded Web Server
=======================================================
  Address:    http://127.0.0.1:8080/
  Root dir:   .../test_files
  Methods:    GET, HEAD
  Statuses:   200, 304, 400, 403, 404
  Connection: keep-alive & close
=======================================================




Open a browser and go to http://127.0.0.1:8080/
Press Ctrl+C to stop the server.




Testing with curl
# 200 OK
curl -I http://127.0.0.1:8080/

# 304 Not Modified
curl -I -H "If-Modified-Since: <last-modified-time>" http://127.0.0.1:8080/

# 400 Bad Request
curl -X BADMETHOD http://127.0.0.1:8080/

# 403 Forbidden
curl http://127.0.0.1:8080/../secret.txt

# 404 Not Found
curl http://127.0.0.1:8080/nonexistent.html

# Keep-alive
curl -v -H "Connection: keep-alive" http://127.0.0.1:8080/ http://127.0.0.1:8080/