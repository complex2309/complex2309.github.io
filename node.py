import socket, json, threading, re
import string
from pathlib import Path

host = "0.0.0.0"
port = 18018
PEERS_FILE = Path("/app/data/peers.json")
PEERS_FILE.parent.mkdir(parents=True, exist_ok=True)

hello = {"type": "hello",
         "version": "0.10.0",
         "agent": "to infinity and beyond"}
getpeers = {"type": "getpeers"}

def save_peers_file(data):
    tmp = PEERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(PEERS_FILE)

def load_peers_file():
    try:
        data = json.loads(PEERS_FILE.read_text())
        if isinstance(data, dict) and isinstance(data.get("peers"), list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {"type": "peers", "peers": []}

def send_msg(sock, msg):
    encjsonmsg = json.dumps(msg).encode("utf-8") + b"\n"
    sock.sendall(encjsonmsg)

def bootstrap():
    bootstrap_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bootstrap_socket.connect(('128.130.122.101', 18018))
    send_msg(bootstrap_socket, hello)
    send_msg(bootstrap_socket, getpeers)

    with open(PEERS_FILE, 'w') as j:
        for i in range(10):
            data = bootstrap_socket.recv(5096)
            data = data.decode("utf-8")
            for line in data.splitlines():
                if line.strip():
                    dump = json.loads(line)
                    print(dump)
                    if dump['type'] == 'peers':
                        if "kermano.gleeze.com:18018" not in dump['peers']:
                            dump['peers'].append('kermano.gleeze.com:18018')
                        json.dump(dump, j)
                    j.flush()
                    if dump['type'] == 'peers':
                        return

def send_error(sock, error, msg):
    error = {'type': 'error',
             'msg': msg,
             'name': error}
    send_msg(sock, error)

def read_lines(sock):
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line.strip():
                yield line

def read_peers(data):
    known = load_peers_file()
    for peer in data.get("peers", []):
        if peer not in known["peers"]:
            known["peers"].append(peer)
    if "kermano.gleeze.com:18018" not in known["peers"]:
        known["peers"].append("kermano.gleeze.com:18018")
    save_peers_file(known)

def handle_connection(sock):
    send_msg(sock, hello)
    send_msg(sock, getpeers)
    handshake = False
    for msg in read_lines(sock):
        try:
            msg = msg.decode("utf-8")
            msg = json.loads(msg)
            if not handshake:
                if msg['type'] == 'hello' and 'version' in msg and re.fullmatch(r"0.10.\d", msg['version']) and 'agent' in msg and len(msg['agent']) < 128 and all(c in string.printable for c in msg['agent']):
                    handshake = True
                else:
                    send_error(sock, "INVALID_HANDSHAKE", "incorrect hello")
                continue
            try:
                match msg['type']:
                    case 'peers':
                        read_peers(msg)
                        peers_check()
                    case 'getpeers':
                        send_msg(sock, load_peers_file())
                    case 'hello':
                        send_error(sock, "INVALID_HANDSHAKE", "already shaken!")
                    case _:
                        error = "INVALID_FORMAT"
                        send_error(sock, error, "command isn't peers or getpeers")
            except Exception as e:
                send_error(sock, "INVALID_FORMAT", "mistake was " + e.__str__())
        except json.decoder.JSONDecodeError:
            send_error(sock, "INVALID_HANDSHAKE", "Message type is not 'hello'!")


def peers_check():
    with open(PEERS_FILE, 'r') as j:
        peers_local = json.load(j)
        for peer in peers_local['peers']:
            ip, port = peer.split(":")
            if re.fullmatch(r"[a-zA-Z\d._-]{3,50}", ip) is None:
                peers_local['peers'].remove(peer)
            if not 1 <= int(port) <= 65535:
                peers_local['peers'].remove(peer)


def main():
    if not load_peers_file()["peers"]:
        bootstrap()
    print("done with bootstrapping")
    peers_check()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    while True:
        sock, addr = server.accept()
        threading.Thread(target=handle_connection, args=(sock,), daemon=True).start()

if __name__ == '__main__':
    main()
