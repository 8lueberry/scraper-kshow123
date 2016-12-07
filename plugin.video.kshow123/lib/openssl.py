import base64
from hashlib import md5
from Crypto.Cipher import AES

def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

def decrypt(data, password, key_length=32):
    data_enc = base64.b64decode(data)
    salt = data_enc[8:16]
    enc = data_enc[16:]
    key, iv = derive_key_and_iv(password, salt, key_length, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    result = cipher.decrypt(enc)
    return result

def print_data(data):
    snip = ''
    for bit in data[:32]:
        snip += str(ord(bit)) + ' '

    return 'DATA (len=' + str(len(data)) + ' snip=' + snip + '...)'