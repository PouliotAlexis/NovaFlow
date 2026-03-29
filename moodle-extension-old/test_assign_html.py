import json, urllib.request, websocket

try:
    req = urllib.request.Request('http://localhost:9222/json')
    with urllib.request.urlopen(req) as response:
        targets = json.loads(response.read())

    ws_url = next((t['webSocketDebuggerUrl'] for t in targets if 'moodle.usherbrooke' in t.get('url', '')), None)

    if ws_url:
        ws = websocket.create_connection(ws_url, suppress_origin=True)
        
        script = """
        new Promise(async (resolve) => {
            try {
                const res1 = await fetch('https://moodle.usherbrooke.ca/mod/assign/view.php?id=3022003');
                const html1 = await res1.text();
                
                const res2 = await fetch('https://moodle.usherbrooke.ca/mod/assign/view.php?id=3037258');
                const html2 = await res2.text();
                
                // Extraire TOUT ce qui ressemble à pluginfile.php
                const regex = /href="(https?:\\/\\/[^\\/]+\\/pluginfile\\.php\\/[^"]+)"/g;
                let links1 = [];
                let links2 = [];
                let match;
                
                while ((match = regex.exec(html1)) !== null) links1.push(match[1]);
                while ((match = regex.exec(html2)) !== null) links2.push(match[1]);
                
                resolve(JSON.stringify({ Dev1: links1, Dev2: links2 }));
            } catch(e) { resolve(e.toString()); }
        })
        """
        
        ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {'expression': script, 'awaitPromise': True, 'returnByValue': True}
        }))
        
        result = json.loads(ws.recv())
        ws.close()
        
        val = result.get('result', {}).get('result', {}).get('value')
        if val:
            data = json.loads(val)
            print("Extracted Links:", json.dumps(data, indent=2))
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
