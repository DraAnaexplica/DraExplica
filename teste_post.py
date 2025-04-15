import requests

dados = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "5517999999999",
                                "text": {
                                    "body": "Oi Dra Ana"
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

res = requests.post("http://localhost:5000/webhook", json=dados)
print("Status:", res.status_code)
print("Texto:", res.text)
