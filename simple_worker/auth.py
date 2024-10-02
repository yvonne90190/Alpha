import requests
import os
import pickle
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin
from .config import LOGIN, SESSION_CACHE, adapter

def get_session() -> requests.Session:
    if os.path.isfile(SESSION_CACHE) and (time.time() - os.path.getmtime(SESSION_CACHE) < 60 * 60 * 4):
        with open(SESSION_CACHE, 'rb') as h:
            return pickle.load(h)

    sess = requests.Session()
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    with open(os.path.expanduser('./brain_credentials.json'), 'r') as f:
        credentials = tuple(json.load(f))
        sess.auth = credentials

    response = sess.post(LOGIN)

    if response.status_code == requests.codes.unauthorized:
        if "WWW-Authenticate" in response.headers and response.headers["WWW-Authenticate"] == "persona":
            auth_url = urljoin(response.url, response.headers["Location"])
            input(f"Complete biometrics authentication and press any key to continue: {auth_url}")
            auth_response = sess.post(auth_url)
            if auth_response.status_code == 201:
                print("Biometric authentication successful.")
            else:
                print("Biometric authentication failed.")
        else:
            print("Incorrect email and password.")
    elif response.status_code == 201:
        print("Login successful.")

    with open(SESSION_CACHE, 'wb') as h:
        pickle.dump(sess, h)
    return sess
