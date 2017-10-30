# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from os.path import exists, join
import os
import base64
from OpenSSL import crypto


def create_self_signed_certificate(device_id, valid_days, cert_output_dir):
    cert_file = device_id + '-cert.pem'
    key_file = device_id + '-key.pem'

    # create a key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().CN = device_id
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(valid_days * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    cert_dump = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8')
    key_dump = crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode('utf-8')
    thumbprint = cert.digest('sha1').replace(b':', b'').decode('utf-8')

    if cert_output_dir is not None and exists(cert_output_dir):
        open(join(cert_output_dir, cert_file), "wt").write(cert_dump)
        open(join(cert_output_dir, key_file), "wt").write(key_dump)

    return {
        'certificate': cert_dump,
        'privateKey': key_dump,
        'thumbprint': thumbprint
    }


def open_certificate(certificate_path):
    certificate = ""
    if certificate_path.endswith('.pem') or certificate_path.endswith('.cer'):
        with open(certificate_path, "rb") as cert_file:
            certificate = cert_file.read()
            try:
                certificate = certificate.decode("utf-8")
            except UnicodeError:
                certificate = base64.b64encode(certificate).decode("utf-8")
    return certificate


def _create_test_cert(cert_file, key_file, subject, valid_days, serial_number):
    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2046)

    # create a self-signed cert with some basic constraints
    cert = crypto.X509()
    cert.get_subject().CN = subject
    cert.gmtime_adj_notBefore(-1 * 24 * 60 * 60)
    cert.gmtime_adj_notAfter(valid_days * 24 * 60 * 60)
    cert.set_version(2)
    cert.set_serial_number(serial_number)
    cert.add_extensions([
        crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:1"),
        crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash",
                             subject=cert),
    ])
    cert.add_extensions([
        crypto.X509Extension(b"authorityKeyIdentifier", False, b"keyid:always",
                             issuer=cert)
    ])
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    cert_str = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('ascii')
    key_str = crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode('ascii')

    open(cert_file, 'w').write(cert_str)
    open(key_file, 'w').write(key_str)


def _delete_test_cert(cert_file, key_file, verification_file):
    if exists(cert_file) and exists(key_file):
        os.remove(cert_file)
        os.remove(key_file)

    if exists(verification_file):
        os.remove(verification_file)


def _create_verification_cert(cert_file, key_file, verification_file, nonce, valid_days, serial_number):
    if exists(cert_file) and exists(key_file):
        # create a key pair
        public_key = crypto.PKey()
        public_key.generate_key(crypto.TYPE_RSA, 2046)

        # open the root cert and key
        signing_cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_file).read())
        k = crypto.load_privatekey(crypto.FILETYPE_PEM, open(key_file).read())

        # create a cert signed by the root
        verification_cert = crypto.X509()
        verification_cert.get_subject().CN = nonce
        verification_cert.gmtime_adj_notBefore(0)
        verification_cert.gmtime_adj_notAfter(valid_days * 24 * 60 * 60)
        verification_cert.set_version(2)
        verification_cert.set_serial_number(serial_number)

        verification_cert.set_pubkey(public_key)
        verification_cert.set_issuer(signing_cert.get_subject())
        verification_cert.add_extensions([
            crypto.X509Extension(b"authorityKeyIdentifier", False, b"keyid:always",
                                 issuer=signing_cert)
        ])
        verification_cert.sign(k, 'sha256')

        verification_cert_str = crypto.dump_certificate(crypto.FILETYPE_PEM, verification_cert).decode('ascii')

        open(verification_file, 'w').write(verification_cert_str)
