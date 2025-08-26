#!/bin/bash

# Copy the optimized rate limiter to replace the original
cp src/utils/rate_limiter_optimized.py src/utils/rate_limiter.py

echo "Rate limiter optimization applied successfully!"
echo "Original backed up as src/utils/rate_limiter_backup.py"
echo "Optimized version is now src/utils/rate_limiter.py"