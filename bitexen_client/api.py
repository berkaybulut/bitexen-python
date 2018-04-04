import requests
from requests.auth import AuthBase
import hmac
import hashlib
import time

from . import version
from bitexen_client.settings import settings
from bitexen_client.utils.dotdict import dotdict

#ToDo: Missing error handling
#ToDo: Missing non-success return value handling

class API(object):
    
    class AuthHeaderForAPI(AuthBase):
        def __init__(self, apikey, username, pass_phrase, timestamp, secretkey):
            self.apikey = apikey
            self.username = username
            self.pass_phrase = pass_phrase
            self.timestamp = timestamp
            self.secretkey = secretkey

        def get_hash(self, request):
            #data = json.loads(request.body.decode('utf-8'))
            #data = json.dumps(data)
            #print(data)
            if request.body:
                data = request.body.decode('utf-8')
                message = self.apikey + self.username + self.pass_phrase + self.timestamp + data
            else:
                message = self.apikey + self.username + self.pass_phrase + self.timestamp + "{}"

            signature = hmac.new(str.encode(self.secretkey),
                                msg=str.encode(message),
                                digestmod=hashlib.sha256).hexdigest().upper()
            return signature

        def __call__(self, request):
            request.headers.update({
                "ACCESS-USER": self.username,
                "ACCESS-PASSPHRASE": self.pass_phrase,
                "ACCESS-TIMESTAMP": self.timestamp,
                "ACCESS-SIGN": self.get_hash(request),
                "ACCESS-KEY": self.apikey,
                'Content-Type': 'application/json'
            })
            return request

    def __init__(self, uri=None, key=None, secret=None, pass_phrase=None, username=None):
        """ Create an object with authentication information.
        :param key: (optional) key identifier for queries to the API
        :type key: str
        :param secret: (optional) actual private key used to sign messages
        :type secret: str
        :returns: None
        """
        self.key = key or settings.key
        self.secret = secret or settings.secret
        self.uri = uri or settings.api_uri
        self.pass_phrase = pass_phrase or settings.pass_phrase
        self.username = username or settings.username
        self.api_path = '/api/v1/'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'bitexen-python/' + version.__version__ + ' (+' + version.__url__ + ')'
        })
        self.response = None
        self._json_options = {}
        return

    def _query(self, urlpath, data, auth=None, timeout=None):
        if data is None:
            data = {}

        url = self.uri + urlpath

        if data=={}:
            self.response = self.session.get(url, auth = auth,
                                          timeout = timeout)
        else:
            self.response = self.session.post(url, json = data, auth = auth,
                                          timeout = timeout)

        if self.response.status_code not in (200, 201, 202):
            self.response.raise_for_status()

        return self.response.json(**self._json_options)

    def _query_public(self, method, data=None, timeout=None):
        if data is None:
            data = {}

        urlpath = self.api_path + method

        return self._query(urlpath, data, timeout = timeout)

    def _query_private(self, method, data=None, timeout=None):
        if data is None:
            data = {}

        if not self.key or not self.secret:
            raise Exception('Either key or secret is not set! (Use `load_key()`.')

        urlpath = self.api_path + method

        auth = self.AuthHeaderForAPI(self.key, self.username, self.pass_phrase, str(time.time()), self.secret)

        return self._query(urlpath, data, auth = auth, timeout = timeout)

    def _get_orders(self, account_name='Main', status='', market_code=''):
        method = 'orders/' + str(account_name) + '/' + status + '/' + market_code + '/'
        result = dotdict(self._query_private(method))

        if result.status == 'success':
            orders = []
            for order in result.data['orders']:
                orders.append(dotdict(order))
            return orders 
        else:
            return None

    def get_market_info(self, market_code=''):
        method = 'market_info/' + market_code + '/'
        result = dotdict(self._query_public(method))
        if result.status=='success' and market_code == '':
            markets = []
            for market in result.data['markets']:
                markets.append(dotdict(market))
            return markets 
        elif result.status == 'success': 
            return dotdict(result.data['markets'])
        else:
            return None
        
    def get_balance(self, account_name=''):
        method = 'balance/' + str(account_name) + '/'
        result = dotdict(self._query_private(method))

        if result.status == 'success':
            balances = []
            for balance in result.data['balances']:
                balances.append(dotdict(balance))
            return balances 
        else:
            return None

    def get_open_orders(self, account_name='Main', market_code=''):
        return self._get_orders(account_name=account_name, status='O', market_code=market_code)

    def get_closed_orders(self, account_name='Main', market_code=''):
        return self._get_orders(account_name=account_name, status='C', market_code=market_code)

    def cancel_order(self, order_number):
        method = 'cancel_order/' + str(order_number) + '/'
        result = dotdict(self._query_private(method, {'order_number':order_number}))

        if result.status == 'success':
            return True
        else:
            return False

    def create_order(self, order_type, market_code, volume, buy_sell, price='0', client_id=0, post_only=False, account_name='Main'):
        method = 'orders/'
        data = { 'order_type':order_type, 'market_code': market_code, 'volume':str(volume), 'buy_sell':buy_sell, 'price':str(price), 
                                   'client_id':client_id, 'post_only':post_only, 'account_name':account_name }
        
        result = dotdict(self._query_private(method, data))

        if result.status == 'success':
            return result.data['order_number']
        else:
            return None





        

    
        