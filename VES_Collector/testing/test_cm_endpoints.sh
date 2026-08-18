#!/bin/bash

BASE_URL="http://localhost:8080/api/cm"
DEVICE_ID="pnf001"

echo "=== 1. CONNECT ==="
curl -s -X POST "$BASE_URL/connect" -H "Content-Type: application/json" \
  -d "{\"device_id\":\"$DEVICE_ID\",\"host\":\"127.0.0.1\",\"port\":830,\"username\":\"archon\",\"key_filename\":\"/home/archon/.ssh/id_rsa\"}"
echo -e "\n"

echo "=== 2. SESSIONS ==="
curl -s "$BASE_URL/sessions"
echo -e "\n"

echo "=== 3. CAPABILITIES ==="
curl -s "$BASE_URL/capabilities/$DEVICE_ID"
echo -e "\n"

echo "=== 4. MODULES ==="
curl -s "$BASE_URL/modules?device_id=$DEVICE_ID"
echo -e "\n"

echo "=== 5. GET CONFIG ==="
curl -s "$BASE_URL/config?device_id=$DEVICE_ID&datastore=running"
echo -e "\n"

echo "=== 6. EDIT CONFIG (CANDIDATE) ==="
curl -s -X POST "$BASE_URL/config" -H "Content-Type: application/json" \
  -d "{\"device_id\":\"$DEVICE_ID\",\"datastore\":\"candidate\",\"config\":\"<config xmlns=\\\"urn:ietf:params:xml:ns:netconf:base:1.0\\\"><pnf xmlns=\\\"urn:ves:pnf-registration\\\"><serial-number>AUTOMATED-TEST</serial-number></pnf></config>\"}"
echo -e "\n"

echo "=== 7. VALIDATE ==="
curl -s -X POST "$BASE_URL/validate" -H "Content-Type: application/json" \
  -d "{\"device_id\":\"$DEVICE_ID\",\"datastore\":\"candidate\"}"
echo -e "\n"

echo "=== 8. COMMIT ==="
curl -s -X POST "$BASE_URL/commit" -H "Content-Type: application/json" \
  -d "{\"device_id\":\"$DEVICE_ID\"}"
echo -e "\n"

echo "=== 9. DISCONNECT ==="
curl -s -X POST "$BASE_URL/disconnect" -H "Content-Type: application/json" \
  -d "{\"device_id\":\"$DEVICE_ID\"}"
echo -e "\n"

echo "All tests finished!"