run:   ; cd backend && python3 -m resourceleak
test:  ; cd backend && python3 -m unittest discover -s tests -v
reset: ; curl -s -X POST localhost:8000/api/reset -d '{}'
