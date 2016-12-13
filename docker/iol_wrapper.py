#!/usr/bin/env python3

import getopt, os, select, socket, sys

UDP_PORT = 5005
UDP_BUFFER = 10000
IOL_BUFFER = 1600
DEBUG = False

def usage():
    print("Usage: {} [OPTIONS]".format(sys.argv[0]))
    print("  -g hostname")
    print("     switcherd hostname or IP address")
    print("  -i iol_id")
    print("     IOL device ID")
    print("  -l label")
    print("     Node label")

def decodeIOLPacket(iol_datagram):
    # IOL datagram format (maximum observed size is 1555):
    # - 16 bits for the destination IOL ID
    # - 16 bits for the source IOL ID
    # - 8 bits for the destination interface (z = x/y -> z = x + 3 * 16)
    # - 8 bits for the source interface (z = x/y -> z = x + y * 16)
    # - 16 bits equals to 0x0100
    dst_id = int.from_bytes(iol_datagram[0:1], byteorder='big')
    src_id = int.from_bytes(iol_datagram[2:3], byteorder='big')
    dst_if = iol_datagram[4]
    src_if = iol_datagram[5]
    padding = 256 * iol_datagram[6] + iol_datagram[7]
    payload = iol_datagram[8:]
    if DEBUG: print("DEBUG: IOL packet src={}:{} dst={}:{} padding={} payload={}".format(src_id, src_if, dst_id, dst_if, padding, sys.getsizeof(payload)))
    return src_id, src_if, dst_id, dst_if, padding, payload

def encodeIOLPacket(src_id, dst_id, iface, payload):
    return dst_id.to_bytes(2, byteorder='big') + src_id.to_bytes(2, byteorder='big') + iface.to_bytes(1, byteorder='big') + iface.to_bytes(1, byteorder='big') + (256).to_bytes(2, byteorder='big') + payload

def decodeUDPPacket(udp_datagram):
    # UDP datagram format:
    # - 24 bits for the node LABEL (up to 16M of nodes)
    # - 8 bits for the interface ID (up to 256 of per node interfaces)
    label = int.from_bytes(udp_datagram[0:2], byteorder='little')
    iface = int(udp_datagram[3])
    payload = udp_datagram[4:]
    if DEBUG: print("DEBUG: UDP packet label={} iface={} payload={}".format(label, iface, sys.getsizeof(payload)))
    return label, iface, payload

def encodeUDPPacket(label, iface, payload):
    return label.to_bytes(3, byteorder='little') + iface.to_bytes(1, byteorder='little') + payload

def main():
    # Reading options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "g:i:l:n:")
    except getopt.GetoptError as err:
        sys.stderr.write("ERROR: {}\n".format(err))
        usage()
        sys.exit(1)

    # Parsing options
    for o, a in opts:
        if o == "-g":
            switcherd = a
        elif o == "-i":
            iol_id = int(a)
        elif o == "-l":
            label = int(a)
        else:
            assert False, "unhandled option"

    # Checking options
    if "iol_id" not in locals():
        sys.stderr.write("ERROR: missing iol_id\n")
        usage()
        sys.exit(1)
    if iol_id < 1 or iol_id > 1024:
        sys.stderr.write("ERROR: iol_id must be between 1 and 1024\n")
        usage()
        sys.exit(1)
    if "switcherd" not in locals():
        sys.stderr.write("ERROR: missing switcherid\n")
        usage()
        sys.exit(1)
    if "label" not in locals():
        sys.stderr.write("ERROR: missing label\n")
        usage()
        sys.exit(1)

    # Setting parameters
    if iol_id == 1024:
        wrapper_id = 1
    else:
        wrapper_id = iol_id + 1

    read_fsocket = "/tmp/netio0/{}".format(wrapper_id)
    write_fsocket = "/tmp/netio0/{}".format(iol_id)

    # Writing NETMAP
    #try:
    #    os.unlink("NETMAP")
    #except OSError:
    #    if os.path.exists("NETMAP"):
    #        raise
    #netmap = open('NETMAP', 'w')
    #for i in range(0, 63):
    #    netmap.write("{}:{} {}:{}\n".format(iol_id, i, wrapper_id, i))
    #netmap.close()

    # Preparing socket (IOL -> wrapper)
    try:
        os.unlink(read_fsocket)
    except OSError:
        if os.path.exists(read_fsocket):
            sys.stderr.write("ERROR: cannot delete existent socket")
            sys.exit(1)
    from_iol = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    from_iol.bind(read_fsocket)

    # Preparing socket (wrapper -> IOL)
    if not os.path.exists(read_fsocket):
        sys.stderr.write("ERROR: IOL node not running\n")

    # Preparing socket (switcherd -> wrapper)
    from_switcherd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    from_switcherd.bind(('', UDP_PORT))

    # Preparing socket (wrapper -> switcherd)
    to_switcherd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    inputs = [ from_iol, from_switcherd ]
    outputs = [ ]

    while inputs:
        if DEBUG: print("DEBUG: waiting for data")
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        for s in readable:
            if s is from_iol:
                if DEBUG: print("DEBUG: data from IOL")
                iol_datagram = from_iol.recv(IOL_BUFFER)
                if not iol_datagram:
                    sys.stderr.write("ERROR: cannot receive data from IOL node\n")
                    break
                else:
                    try:
                        src_id, src_if, dst_id, dst_if, padding, payload = decodeIOLPacket(iol_datagram)
                        to_switcherd.sendto(encodeUDPPacket(label, src_if, payload), (switcherd, UDP_PORT))
                    except Exception as err:
                        sys.stderr.write("ERROR: cannot send data to switcherd\n")
                        sys.exit(2)
            elif s is from_switcherd:
                if DEBUG: print("DEBUG: data from UDP")
                udp_datagram, src_addr = from_switcherd.recvfrom(UDP_BUFFER)
                if not udp_datagram:
                    sys.stderr.write("ERROR: cannot receive data from switcherd\n")
                    break
                else:
                    if "to_iol" not in locals():
                        try:
                            to_iol = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                            to_iol.connect(write_fsocket)
                        except Exception as err:
                            sys.stderr.write("ERROR: cannot connect to IOL socket, packet dropped\n")
                            del(to_iol)
                            pass
                    if "to_iol" in locals():
                        try:
                            label, iface, payload = decodeUDPPacket(udp_datagram)
                            to_iol.send(encodeIOLPacket(wrapper_id, iol_id, iface, payload))
                        except Exception as err:
                            sys.stderr.write("ERROR: cannot send data to IOL node\n")
                            sys.exit(2)
            else:
                sys.stderr.write("ERROR: unknown source from select\n")

if __name__ == "__main__":
    main()
