import webview
from backend import app

window = webview.create_window('Influx Global', app)

if __name__ == '__main__':
    webview.start()