import os.path
import socket
import zlib
import threading
import time
import tqdm
from tkinter import Tk
from tkinter import filedialog

ACK = 1
SYN = 2
FIN = 4
Error = 8
KeepAlive = 16
Subor = 32
Sprava = 0
Pos_fragment = 64
KLIENT_UDP_IP = socket.gethostbyname(socket.gethostname())
SERVER_PORT = 5005
SERVER_UDP_IP = "localhost"
SERVER = (SERVER_UDP_IP, SERVER_PORT)
VELKOST_HLAVICKY = 5
FORMAT = 'utf-8'
cas_poslania_paketu = 0
CAS_KEEPALIVE = 5
# S_SEMAFOR = False
SEMAFOR = False
velkost_fragmentu = 0

# keep alive od zaciatku

# def server_keepalive(server):
#     global S_SEMAFOR
#
#     while True:
#         time.sleep(2)
#         while S_SEMAFOR:
#             data, addr = server.recvfrom(1500)
#             if dostal_som_signal(KeepAlive, data):
#                 posli_signal(KeepAlive, addr, server)
#                 print("Maintaining communication")
#
#             elif dostal_som_signal(Sprava, data):
#                 S_SEMAFOR = False
#
#             elif dostal_som_signal(Subor, data):
#                 S_SEMAFOR = False
#
#             elif dostal_som_signal(FIN, data):
#                 S_SEMAFOR = False


def dostal_som_signal(signal, data):
    if int.from_bytes(data[0:1], "big") == signal:
        return True
    else:
        return False


def porovnaj_checksum(hlavicka, data):
    checksum = hlavicka[1:]
    if int.from_bytes(checksum, "big") == zlib.crc32(data):
        return True
    return False


def over_checksum(addr, hlavicka, fragment, server):
    counter = 0

    while not porovnaj_checksum(hlavicka, fragment):
        print("Corrupted fragment received, sending Error")
        posli_signal(Error, addr, server)
        data, addr = server.recvfrom(1500)
        counter += 1
        hlavicka = data[0:VELKOST_HLAVICKY]
        fragment = data[VELKOST_HLAVICKY:]

    if dostal_som_signal(Subor, hlavicka) or dostal_som_signal(Pos_fragment + Subor, hlavicka):
        return fragment, counter

    return fragment.decode(FORMAT), counter


def posli_signal(signal, addr, sender):
    hlavicka = signal
    sender.sendto(hlavicka.to_bytes(1, "big"), addr)


def prijmi_spravu(addr, server):
    sprava = ""
    counter = 0

    while True:
        posli_signal(ACK, addr, server)
        data, addr = server.recvfrom(1500)
        counter += 1

        tmp_sprava, tmp_counter = over_checksum(addr, data[0:VELKOST_HLAVICKY], data[VELKOST_HLAVICKY:], server)
        sprava += tmp_sprava
        counter += tmp_counter

        print("Fragment received, Sending Acknowledgement")

        if dostal_som_signal(Pos_fragment, data):
            posli_signal(ACK, addr, server)
            break

    print(f"Massage recieved [from {addr}, length-{len(sprava)}, fragments-{counter}]: {sprava}")  # dorobit counter


def prijmi_subor(addr, server, subor, velkost_suboru):
    counter = 0
    posielanie = tqdm.tqdm(range(velkost_suboru), f"Receiving {os.path.basename(subor)}", unit="B", unit_scale=True, unit_divisor=1024)
    with open(subor, "wb") as s:
        while True:
            posli_signal(ACK, addr, server)
            fragment, addr = server.recvfrom(1500)
            counter += 1
            hlavicka = fragment[0:VELKOST_HLAVICKY]

            fragment, tmp_counter = over_checksum(addr, fragment[0:VELKOST_HLAVICKY], fragment[VELKOST_HLAVICKY:], server)
            counter += tmp_counter

            s.write(fragment)

            posielanie.update(len(fragment))
            if dostal_som_signal(Pos_fragment + Subor, hlavicka):
                posli_signal(ACK, addr, server)
                break

    print(f"File recieved [from {addr}, length-{velkost_suboru}, fragments-{counter}]: {subor}")


def zacni_prijimat(server):
    # global S_SEMAFOR
    #
    # t1 = threading.Thread(target=server_keepalive, args=(server,))
    # t1.daemon = True
    # t1.start()

    while True:
        data, addr = server.recvfrom(1500)

        if dostal_som_signal(Subor, data):
            subor = data[1:].decode(FORMAT)
            velkost_suboru = os.path.getsize(subor)
            subor = os.path.basename(subor)
            Tk().withdraw()
            ciel = filedialog.askdirectory()
            subor = os.path.join(ciel, subor)

            prijmi_subor(addr, server, subor, velkost_suboru)

        elif dostal_som_signal(Sprava, data):
            prijmi_spravu(addr, server)

        elif dostal_som_signal(FIN, data):
            posli_signal(FIN + ACK, addr, server)
            print(f"Connection terminated [with {addr}]")
            break

        elif dostal_som_signal(KeepAlive, data):
            posli_signal(KeepAlive, addr, server)
            print("Maintaining communication")

        # S_SEMAFOR = True


def naviaz_spojenie(server):
    while True:
        data, addr = server.recvfrom(1500)
        if dostal_som_signal(SYN, data):
            posli_signal(SYN+ACK, addr, server)
            print(f"Connection Established [with {addr}]")

            zacni_prijimat(server)
            break


def zapni_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((SERVER_UDP_IP, SERVER_PORT))

    print(f"Starting [as {SERVER}")
    naviaz_spojenie(server)


def keepalive(sock):
    while True:
        time.sleep(5)
        while SEMAFOR:
            if time.time() - cas_poslania_paketu > CAS_KEEPALIVE:
                posli_signal(KeepAlive, SERVER, sock)
                cakaj_na(KeepAlive, sock)
                updatni_cas()
                time.sleep(1)


def cakaj_na(flagy, sock):
    while True:
        data, addr = sock.recvfrom(1500)
        if int.from_bytes(data, "big") == flagy:
            return True
        elif int.from_bytes(data, "big") == Error:
            return False


def vyp_checksum(data):
    return (zlib.crc32(data)).to_bytes(4, "big")


def poskod_paket(data, counter, corrupt):
    if counter == 0 and corrupt == 1:
        data = data[1:] + b'1'
    return data


def posli_paket(signal, fragment, pozicia, addr, sender, counter, corrupt):
    hlavicka = signal
    data = fragment[pozicia: velkost_fragmentu + pozicia]
    checksum = vyp_checksum(data)

    data = poskod_paket(data, counter, corrupt)
    sender.sendto(hlavicka.to_bytes(1, "big") + checksum + data, addr)
    updatni_cas()


def posli_spravu(sock):
    cakaj_na(ACK, sock)
    corrupt = int(input("Odsimulovat poškodenie paketu? 1-ano, 0-nie: "))
    sprava = input("Zadaj spravu:").encode(FORMAT)
    dlzka_spravy = len(sprava)

    pozicia = 0
    counter = 0
    while dlzka_spravy > velkost_fragmentu:
        posli_paket(Sprava, sprava, pozicia, SERVER, sock, counter, corrupt)
        counter += 1
        print(f"Fragment n.{counter} sent")

        if not cakaj_na(ACK, sock):
            print("Received Error, sending the same fragment")
            continue

        pozicia += velkost_fragmentu
        dlzka_spravy -= velkost_fragmentu

    while True:
        posli_paket(Pos_fragment, sprava, pozicia, SERVER, sock, counter, corrupt)
        counter += 1
        print(f"Fragment n.{counter} sent")
        if not cakaj_na(ACK, sock):
            print("Received Error, sending the same fragment")
            continue
        break


def posli_subor(sock, subor):
    cakaj_na(ACK, sock)
    velkost_suboru = os.path.getsize(subor)
    counter = 0
    pozicia = 0
    corrupt = int(input("Odsimulovat poškodenie paketu? 1-ano, 0-nie: "))
    posielanie = tqdm.tqdm(range(velkost_suboru), f"Sending {os.path.basename(subor)}", unit="B", unit_scale=True, unit_divisor=1024)
    with open(subor, "rb") as s:
        cely_subor = s.read(velkost_suboru)
        while True:

            while velkost_suboru > velkost_fragmentu:
                posli_paket(Subor, cely_subor, pozicia, SERVER, sock, counter, corrupt)
                counter += 1

                if not cakaj_na(ACK, sock):
                    print("Received Error, sending the same fragment")
                    continue

                pozicia += velkost_fragmentu
                velkost_suboru -= velkost_fragmentu
                posielanie.update(len(cely_subor[pozicia:velkost_fragmentu + pozicia]))

            posli_paket(Pos_fragment + Subor, cely_subor, pozicia, SERVER, sock, counter, corrupt)
            counter += 1

            if cakaj_na(ACK, sock):
                posielanie.update()
                break
            else:
                print("\nReceived Error, sending the same fragment")



def updatni_cas():
    global cas_poslania_paketu
    cas_poslania_paketu = time.time()


def zacni_posielat(sock):
    global SEMAFOR

    t1 = threading.Thread(target=keepalive, args=(sock,))
    t1.daemon = True
    t1.start()

    while True:
        tmp = int(input("Pre poslanie suboru zadaj 1, pre správu 0, pre odpojenie 3: "))
        SEMAFOR = False
        time.sleep(0.3)
        updatni_cas()

        if tmp == 0:
            posli_signal(Sprava, SERVER, sock)
            posli_spravu(sock)

        elif tmp == 1:
            Tk().withdraw()
            subor = filedialog.askopenfilename()

            hlavicka = Subor
            sock.sendto(hlavicka.to_bytes(1, "big") + subor.encode(FORMAT), SERVER)

            posli_subor(sock, subor)

        elif tmp == 3:
            print("Terminating connection")
            posli_signal(FIN, SERVER, sock)
            cakaj_na(FIN + ACK, sock)
            exit(1)

        SEMAFOR = True
        time.sleep(1)


def pripoj_na_server(sock):
    posli_signal(SYN, SERVER, sock)
    while True:
        data, addr = sock.recvfrom(1500)

        if dostal_som_signal(SYN + ACK, data):
            print(f"Connection Established [with {addr}]")
            zacni_posielat(sock)
            break


def klient():
    global velkost_fragmentu

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((SERVER_UDP_IP, SERVER_PORT))

    while True:
        velkost_fragmentu = int(input(f"Zvol velkost najvacsieho fragmentu (MAX {1518-18-20-8-VELKOST_HLAVICKY}): "))
        if velkost_fragmentu <= 1518-18-20-8-VELKOST_HLAVICKY:
            pripoj_na_server(sock)
        else:
            print("Zadaj si zlu velkost fragemntu")


temp = int(input("1-server, 2-klient: "))
if temp == 1:
    zapni_server()
elif temp == 2:
    klient()
