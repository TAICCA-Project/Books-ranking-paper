class Config:
    # Google API Configuration
    GOOGLE_API_KEY = 'YOUR_GOOGLE_API_KEY_HERE'
    
    # Books.com.tw Login Credentials
    BOOKSCOM_ACCOUNT = "your_email@example.com"
    BOOKSCOM_PASSWORD = "your_password"
    
    # Sanmin (三民書局) Login Credentials
    SANMIN_ACCOUNT = "your_account"
    SANMIN_PASSWORD = "your_password"
    
    # Eslite (誠品) Login Credentials
    ESLITE_ACCOUNT = "your_phone_or_account"
    ESLITE_PASSWORD = "your_password"
    
    # Selenium Configuration
    SCALE_FACTOR = 1

class TorConfig:
    """
    Tor proxy configuration for advanced users
    Only needed if you want to use Tor for request anonymization
    """
    TOR_PASSWORD = 'your_tor_password'
    TOR_CONTROL_PORTS = [9053, 9055, 9057, 9059, 9061, 9063, 9065, 9067, 9069, 9071, 9073, 9075, 9077]
    
    TOR_INFO = [
        {'http': 'socks5h://127.0.0.1:9052', 'https': 'socks5h://127.0.0.1:9052'},
        {'http': 'socks5h://127.0.0.1:9054', 'https': 'socks5h://127.0.0.1:9054'},
        {'http': 'socks5h://127.0.0.1:9056', 'https': 'socks5h://127.0.0.1:9056'},
        {'http': 'socks5h://127.0.0.1:9058', 'https': 'socks5h://127.0.0.1:9058'},
        {'http': 'socks5h://127.0.0.1:9060', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9062', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9064', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9066', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9068', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9070', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9072', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9074', 'https': 'socks5h://127.0.0.1:9060'},
        {'http': 'socks5h://127.0.0.1:9076', 'https': 'socks5h://127.0.0.1:9060'},
    ]
