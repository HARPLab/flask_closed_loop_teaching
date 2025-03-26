class WebSocketBlocker:
    """Middleware to block WebSocket upgrades on login POST requests"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        request_method = environ.get('REQUEST_METHOD', '')
        
        # Block WebSocket upgrades on login POST requests
        if '/login' in path_info and request_method == 'POST':
            # Remove WebSocket headers
            for key in list(environ.keys()):
                if key.startswith('HTTP_') and ('UPGRADE' in key.upper() or 'WEBSOCKET' in key.upper()):
                    environ.pop(key, None)
            
            # Also remove the connection header that might trigger upgrades
            environ.pop('HTTP_CONNECTION', None)
            
            # Custom start_response to filter out upgrade headers in the response
            def custom_start_response(status, headers, exc_info=None):
                filtered_headers = [(name, value) for name, value in headers 
                                   if name.lower() != 'upgrade' and 
                                      (name.lower() != 'connection' or value.lower() != 'upgrade')]
                return start_response(status, filtered_headers, exc_info)
            
            return self.app(environ, custom_start_response)
        
        return self.app(environ, start_response)