#!/bin/bash

CONFIG_FILE="/home/cezar/automagik/automagik-omni/src/config.py"
BACKUP_FILE="/home/cezar/automagik/automagik-omni/src/config.py.backup"
TEMP_FILE="/home/cezar/automagik/automagik-omni/src/config.py.temp"

echo "🔧 Applying CORS configuration fix..."

# Create backup
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "✅ Backup created: $BACKUP_FILE"

# Create the CORS config class content
CORS_CONFIG='class CorsConfig(BaseModel):
    """CORS configuration for API server."""

    allowed_origins: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_ORIGINS", "*").split(",")
    )
    allow_credentials: bool = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_CREDENTIALS", "true").lower() == "true"
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: os.getenv("AUTOMAGIK_OMNI_CORS_HEADERS", "*").split(",")
    )


'

# Step 1: Insert CorsConfig class before Config class
sed "/^class Config(BaseModel):$/i\\
$CORS_CONFIG" "$CONFIG_FILE" > "$TEMP_FILE"

# Step 2: Add cors attribute to Config class
sed 's/timezone: TimezoneConfig = TimezoneConfig()/timezone: TimezoneConfig = TimezoneConfig()\
    cors: CorsConfig = CorsConfig()/' "$TEMP_FILE" > "$CONFIG_FILE"

# Clean up temp file
rm "$TEMP_FILE"

echo "✅ CORS configuration fix applied!"
echo "✅ Added CorsConfig class with environment variable support"
echo "✅ Added cors attribute to main Config class"
echo ""
echo "🚀 PM2 should now restart the API successfully!"
echo ""
echo "Environment variables for CORS configuration:"
echo "  - AUTOMAGIK_OMNI_CORS_ORIGINS (default: *)"
echo "  - AUTOMAGIK_OMNI_CORS_CREDENTIALS (default: true)"
echo "  - AUTOMAGIK_OMNI_CORS_METHODS (default: GET,POST,PUT,DELETE,OPTIONS)"
echo "  - AUTOMAGIK_OMNI_CORS_HEADERS (default: *)"