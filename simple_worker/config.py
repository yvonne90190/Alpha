import os
from enum import Enum
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGIN = 'https://api.worldquantbrain.com/authentication'
SIMULATION = 'https://api.worldquantbrain.com/simulations'
ALPHA = 'https://api.worldquantbrain.com/alphas'

SESSION_CACHE = './session.pkl'

retry = Retry(total=5,
              backoff_factor=0.1,
              status_forcelist=[500, 502, 503, 504],
              allowed_methods=["POST"])
adapter = HTTPAdapter(max_retries=retry)