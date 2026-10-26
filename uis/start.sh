#!/bin/sh
# start.sh – serve static UI folders with http-server
# Run both UI sites in background and wait for them.

# Serve website on port 3000
echo "Starting website on http://0.0.0.0:3000"
http-server ./website -p 3000 &
WEBSITE_PID=$!

# Serve backoffice on port 3001
echo "Starting backoffice on http://0.0.0.0:3001"
http-server ./backoffice -p 3001 &
BACKOFFICE_PID=$!

# Wait for both processes to exit (container stops when any exits)
wait $WEBSITE_PID $BACKOFFICE_PID
