import http.client
import threading

from recoverx.agent import make_server


def request(server, headers):
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("GET", "/health", headers=headers)
    response = conn.getresponse()
    response.read()
    status = response.status
    conn.close()
    thread.join(5)
    return status


def test_pairing_host_origin_and_token():
    token = "t" * 40
    server = make_server(":memory:", "a" * 32, "https://recoverx.example", token)
    try:
        good = {"Origin": "https://recoverx.example", "Authorization": f"Bearer {token}"}
        assert request(server, good) == 200
        assert request(server, {"Origin": "https://recoverx.example"}) == 401
        assert request(server, {**good, "Origin": "https://attacker.example"}) == 403
        assert request(server, {**good, "Host": "attacker.example"}) == 403
    finally:
        server.server_close()
