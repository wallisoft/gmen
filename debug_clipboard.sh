#!/bin/bash
echo "🔍 Clipboard Sync Diagnostic"
echo "==========================="

echo "1. Network discovery:"
python3 -c "
from network.discovery import LANDiscovery
d = LANDiscovery()
peers = d.get_peers()
print(f'  Peers: {len(peers)}')
for p in peers.values():
    print(f'    - {p[\"hostname\"]} ({p[\"ip\"]})')
"

echo -e "\n2. Clipboard API:"
curl -s http://localhost:8721/clipboard | python3 -m json.tool

echo -e "\n3. pyperclip test:"
python3 -c "
try:
    import pyperclip
    pyperclip.copy('diagnostic test')
    print(f'  OK: \"{pyperclip.paste()}\"')
except Exception as e:
    print(f'  FAILED: {e}')
"

echo -e "\n4. Port accessibility:"
timeout 2 curl -s http://localhost:8721/clipboard >/dev/null && echo "  ✅ Port 8721 accessible" || echo "  ❌ Port 8721 not accessible"

echo -e "\n5. From other machine (if known IP):"
if [ -n \"$1\" ]; then
    timeout 3 curl -s http://$1:8721/clipboard >/dev/null && echo "  ✅ Can reach $1:8721" || echo "  ❌ Cannot reach $1:8721"
fi
