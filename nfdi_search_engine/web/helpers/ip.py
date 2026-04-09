from flask import request

def get_client_ip() -> str:
    client_ip = request.remote_addr or ""
    if "X-Forwarded-For" in request.headers:
        # first IP in chain
        client_ip = request.headers.getlist("X-Forwarded-For")[0]
    return client_ip
