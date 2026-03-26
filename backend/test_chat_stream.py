import requests
import json

def test_chat():
    url = "http://127.0.0.1:8000/api/chat/stream"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGV4aGFycG91QGdtYWlsLmNvbSIsImV4cCI6MTc3NDUwMDkyOH0.4gTHI5H9nrK2bIaQ8WKDHsz7quDrLWMbB_ghtZYwuT8"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "Bonjour, parle-moi de mécanique quantique (très brièvement).",
        "system_prompt": "Tu es NovaFlow.",
        "use_rag": False
    }
    
    print(f"Envoi de la requête à {url}...")
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Erreur: {response.text}")
            return

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"RECVD: {decoded_line}")
                if "error" in decoded_line.lower():
                   print("💥 ERREUR DÉTECTÉE DANS LE FLUX")
    except Exception as e:
        print(f"Erreur lors de la requête: {e}")

if __name__ == "__main__":
    test_chat()
