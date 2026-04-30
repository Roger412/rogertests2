from flask import Flask, render_template
import requests
import json
import schedule
import time
import threading

app = Flask(__name__)
result = None

def call_api():
    global result
    url = 'http://127.0.0.1:8042/restgatewaydemo/getmultcoords'
    data = {}
    headers = {'Content-type': 'application/json'}

    response = requests.post(url, data=json.dumps(data), headers=headers)
    result = response.json()
    result["values"].pop()
    with open('result.json', 'w') as f:
        json.dump(result, f)

def schedule_api_call():
    while True:
        schedule.run_pending()
        time.sleep(1)

        # schedule.cancel_job(call_api)

if __name__ == '__main__':
    call_api()  # Initial call
    schedule.every(0.5).seconds.do(call_api)  # Schedule call every half second

    t = threading.Thread(target=schedule_api_call)
    t.start()

    @app.route('/api/result')
    def get_result():
        return str(result["values"][0]) + "," + str(result["values"][1])

    @app.route('/')
    def show_result():
        return render_template('result.html')

    app.run(debug=True, port=8002)
