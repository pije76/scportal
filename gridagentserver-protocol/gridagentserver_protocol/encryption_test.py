import unittest

from binascii import a2b_hex

from encryption import Encryption
from StringIO import StringIO


# RC4 test vectors from http://en.wikipedia.org/wiki/RC4#Test_vectors ...
examples = [
    {
        'key': 'Key',
        'plain': 'Plaintext',
        'cipher': a2b_hex('BBF316E8D940AF0AD3'),
    },
    {
        'key': 'Wiki',
        'plain': 'pedia',
        'cipher': a2b_hex('1021BF0420'),
    },
    {
        'key': 'Secret',
        'plain': 'Attack at dawn',
        'cipher': a2b_hex('45A01F645FC35B383552544B9BF5'),
    }
]


class TestEncryption(unittest.TestCase):
    def test_encrypt(self):
        for e in examples:
            encrypt = Encryption(e['key'], None)
            self.assertEqual(encrypt._crypt(e['plain']), e['cipher'])
            self.assertNotEqual(encrypt._crypt(e['plain']), e['cipher'])

    def test_decrypt(self):
        for e in examples:
            encrypt = Encryption(e['key'], None)
            self.assertEqual(encrypt._crypt(e['cipher']), e['plain'])
            self.assertNotEqual(encrypt._crypt(e['cipher']), e['plain'])

    def test_stream_decrypt(self):
        for e in examples:
            encrypt = Encryption(e['key'], StringIO(e['cipher']))
            self.assertEqual(encrypt.read(len(e['plain'])), e['plain'])

    def test_stream_encrypt(self):
        for e in examples:
            stream = StringIO()
            encrypt = Encryption(e['key'], stream)
            encrypt.write(e['plain'])
            self.assertEqual(stream.getvalue(), e['cipher'])

    def test_recursive(self):
        # encrypt, then decrypt with same key...
        for e in examples:
            stream = StringIO()
            estream = Encryption(e['key'], stream)
            encrypt = Encryption(e['key'], estream)
            encrypt.write(e['plain'])
            self.assertEqual(stream.getvalue(), e['plain'])
