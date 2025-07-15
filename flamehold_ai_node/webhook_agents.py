from flask import Flask, request
import threading

def create_agent(name, port):
    app = Flask(name)

    @app.route(f"/{name.lower()}", methods=["POST"])
    def receive():
        payload = request.get_json()
        print(f"🛰️ [{name}] Received Payload:")
        print(payload)
        return {"status": f"{name} online and acknowledged"}, 200

    thread = threading.Thread(target=app.run, kwargs={"port": port})
    thread.daemon = True
    thread.start()

if __name__ == "__main__":
    agents = {
        "SERA": 9530,
        "AVIS": 9531,
        "SARA": 9532,
        "G-SERA": 9533,
        "Lennox": 9534,
        "GroundControl": 9535,
        "TheMechanic": 9536,
        "TheDirector": 9537,
        "AnonymousBenefactor": 9538
    }

    for name, port in agents.items():
        create_agent(name, port)

    print("🧠 All BRD953 Agent Webhook Servers Active.")
    input("🔁 Press Enter to terminate relay.\n")
