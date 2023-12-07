from backend import app
import waitress

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    # waitress.serve(app, host='127.0.0.1', port=5000)