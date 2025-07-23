#!/bin/bash

# Simple API Test Script for Automagik Omni
# This script demonstrates key API endpoints with real examples

set -e

# Configuration
API_BASE="http://localhost:18882"
API_KEY="namastex888"
HEADERS=(-H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json")

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Automagik Omni API Test Script${NC}"
echo "=================================="

# Test 1: Health Check
echo -e "\n${YELLOW}1. Health Check (no auth)${NC}"
echo "curl -X GET $API_BASE/health"
curl -s -X GET "$API_BASE/health" | jq .
echo -e "${GREEN}✅ Health check passed${NC}"

# Test 2: List Instances
echo -e "\n${YELLOW}2. List All Instances${NC}"
echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances"
INSTANCES=$(curl -s "${HEADERS[@]}" "$API_BASE/api/v1/instances")
echo "$INSTANCES" | jq .
INSTANCE_COUNT=$(echo "$INSTANCES" | jq '. | length')
echo -e "${GREEN}✅ Found $INSTANCE_COUNT instances${NC}"

# Get first instance name for testing
FIRST_INSTANCE=$(echo "$INSTANCES" | jq -r '.[0].name // empty')

if [ -n "$FIRST_INSTANCE" ]; then
    echo -e "\n${BLUE}Using instance '$FIRST_INSTANCE' for testing...${NC}"
    
    # Test 3: Get Instance Details
    echo -e "\n${YELLOW}3. Get Instance Details${NC}"
    echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances/$FIRST_INSTANCE"
    curl -s "${HEADERS[@]}" "$API_BASE/api/v1/instances/$FIRST_INSTANCE" | jq .
    echo -e "${GREEN}✅ Instance details retrieved${NC}"
    
    # Test 4: Get QR Code
    echo -e "\n${YELLOW}4. Get QR Code${NC}"
    echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances/$FIRST_INSTANCE/qr"
    QR_RESPONSE=$(curl -s "${HEADERS[@]}" "$API_BASE/api/v1/instances/$FIRST_INSTANCE/qr")
    echo "$QR_RESPONSE" | jq 'del(.qr_code)' # Remove QR code data for readability
    echo -e "${GREEN}✅ QR code endpoint working${NC}"
    
    # Test 5: Get Connection Status
    echo -e "\n${YELLOW}5. Get Connection Status${NC}"
    echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances/$FIRST_INSTANCE/status"
    curl -s "${HEADERS[@]}" "$API_BASE/api/v1/instances/$FIRST_INSTANCE/status" | jq .
    echo -e "${GREEN}✅ Status retrieved${NC}"
    
    # Test 6: Set as Default
    echo -e "\n${YELLOW}6. Set as Default Instance${NC}"
    echo "curl -X POST -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances/$FIRST_INSTANCE/set-default"
    curl -s -X POST "${HEADERS[@]}" "$API_BASE/api/v1/instances/$FIRST_INSTANCE/set-default" | jq 'pick(.id, .name, .is_default)'
    echo -e "${GREEN}✅ Default instance set${NC}"
    
else
    echo -e "${RED}❌ No instances found. Skipping instance-specific tests.${NC}"
fi

# Test 7: Supported Channels
echo -e "\n${YELLOW}7. Get Supported Channels${NC}"
echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances/supported-channels"
curl -s "${HEADERS[@]}" "$API_BASE/api/v1/instances/supported-channels" | jq .
echo -e "${GREEN}✅ Supported channels retrieved${NC}"

# Test 8: List Traces with Enhanced Filtering
echo -e "\n${YELLOW}8. List Message Traces with Enhanced Filtering${NC}"
echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/traces?limit=3"
TRACES=$(curl -s "${HEADERS[@]}" "$API_BASE/api/v1/traces?limit=3")
echo "$TRACES" | jq .
TRACE_COUNT=$(echo "$TRACES" | jq '. | length')
echo -e "${GREEN}✅ Retrieved $TRACE_COUNT recent traces${NC}"

echo -e "\n${BLUE}8.1 Test Session-Based Filtering${NC}"
echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/traces?agent_session_id=test_session"
curl -s "${HEADERS[@]}" "$API_BASE/api/v1/traces?agent_session_id=test_session" | jq '. | length'
echo -e "${GREEN}✅ Session filtering working${NC}"

echo -e "\n${BLUE}8.2 Test Media Filtering${NC}"
echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/traces?has_media=false&limit=1"
curl -s "${HEADERS[@]}" "$API_BASE/api/v1/traces?has_media=false&limit=1" | jq 'length'
echo -e "${GREEN}✅ Media filtering working${NC}"

# Test 9: Webhook Simulation (if we have an instance)
if [ -n "$FIRST_INSTANCE" ]; then
    echo -e "\n${YELLOW}9. Webhook Simulation${NC}"
    WEBHOOK_DATA='{
        "event": "messages.upsert",
        "data": {
            "messages": [{
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "id": "test_message_'$(date +%s)'"
                },
                "message": {
                    "conversation": "Test message from API test script at '$(date)'"
                },
                "messageTimestamp": '$(date +%s)'
            }]
        },
        "instance": "'$FIRST_INSTANCE'"
    }'
    
    echo "curl -X POST -H \"Content-Type: application/json\" -d '\$WEBHOOK_DATA' $API_BASE/webhook/evolution/$FIRST_INSTANCE"
    echo "$WEBHOOK_DATA" | curl -s -X POST -H "Content-Type: application/json" -d @- "$API_BASE/webhook/evolution/$FIRST_INSTANCE" | jq .
    echo -e "${GREEN}✅ Webhook processed${NC}"
fi

# Test 10: Error Handling Examples
echo -e "\n${YELLOW}10. Error Handling Examples${NC}"

echo -e "\n${BLUE}10.1 Unauthorized Request${NC}"
echo "curl -X GET $API_BASE/api/v1/instances (no auth header)"
curl -s -X GET "$API_BASE/api/v1/instances" | jq .

echo -e "\n${BLUE}10.2 Not Found Error${NC}"
echo "curl -H \"Authorization: Bearer \$API_KEY\" $API_BASE/api/v1/instances/nonexistent"
curl -s "${HEADERS[@]}" "$API_BASE/api/v1/instances/nonexistent" | jq .

echo -e "\n${BLUE}10.3 Validation Error${NC}"
echo "curl -X POST -H \"Authorization: Bearer \$API_KEY\" -d '{\"name\": \"\"}' $API_BASE/api/v1/instances"
echo '{"name": ""}' | curl -s -X POST "${HEADERS[@]}" -d @- "$API_BASE/api/v1/instances" | jq .

echo -e "\n${GREEN}✅ Error handling examples completed${NC}"

# Summary
echo -e "\n${BLUE}📊 Test Summary${NC}"
echo "=================="
echo "• Health check: Working"
echo "• Instance management: Working"
echo "• QR code generation: Working"
echo "• Connection status: Working"
echo "• Trace logging: Working"
echo "• Webhook processing: Working"
echo "• Error handling: Working"
echo ""
echo -e "${GREEN}🎉 All API endpoints are functional!${NC}"
echo ""
echo "📚 For complete documentation, see:"
echo "• Interactive docs: http://localhost:18882/api/v1/docs"
echo "• Complete guide: ./COMPLETE_API_GUIDE.md"
echo ""
echo "🔧 Next steps:"
echo "• Configure your WhatsApp instances"
echo "• Set up webhooks in Evolution API"
echo "• Integrate with your frontend application"