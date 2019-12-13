"""Sending handshake messages."""

from struct import Struct
import random
import logging

from encryption import StreamEncrypter
from . import PROTOCOL_VERSION, SECRET


logger = logging.getLogger(__name__)

# protocol version, ID/nonce
handshake_struct = Struct('!IQ')
uint64 = Struct('!Q')


def handshake(wfile, rfile, wdata):
    outgoing = handshake_struct.pack(PROTOCOL_VERSION, wdata)
    wfile.write(outgoing)
    wfile.flush()
    incoming = rfile.read(handshake_struct.size)
    version, rdata = handshake_struct.unpack(incoming)
    return version, rdata


def handshake_serverside(wfile, rfile):
    nonce = random.randint(0, 2 ** 64)
    version, agent_mac = handshake(wfile, rfile, nonce)
    logger.debug('Connection from agent %X, protocol %d', agent_mac, version)
    if version > PROTOCOL_VERSION or version <= 0:
            raise Exception('Protocol %d not supported; disconnecting %X' % (
                version,
                agent_mac,
            ))
    encrypt_write, read_decrypt = init_encryption(wfile, rfile,
                                                  agent_mac, nonce)
    return (version, agent_mac, encrypt_write, read_decrypt)


def handshake_clientside(wfile, rfile, agent_mac):
    serverside_version, nonce = handshake(wfile, rfile, agent_mac)
    if serverside_version != PROTOCOL_VERSION:
        logger.debug('Protocol versions differ: Client: %d, server: %d' % (
            PROTOCOL_VERSION,
            serverside_version
        ))
    # we use version from client anyway
    encrypt_write, read_decrypt = init_encryption(wfile, rfile,
                                                  agent_mac, nonce)
    return encrypt_write, read_decrypt


def init_encryption(wfile, rfile, agent_mac, nonce):
    # initialise encryption state with nonce + secret + incoming data
    key_bytes = bytearray(SECRET)
    id_bytes = bytearray(uint64.pack(agent_mac))
    nonce_bytes = bytearray(uint64.pack(nonce))
    for i in range(len(nonce_bytes)):
        key_bytes[i] = key_bytes[i] ^ id_bytes[i] ^ nonce_bytes[i]
    encrypt_write = StreamEncrypter(key_bytes, wfile)
    read_decrypt = StreamEncrypter(key_bytes, rfile)
    return encrypt_write, read_decrypt
