# Array of configuration files
configs=(
    "configs/OpenTitan/gpt4o_mini_refine_tool.json"
    "configs/OpenTitan/gpt4o_mini_refineonly.json"
    "configs/OpenTitan/gpt4o_mini_toolonly.json"
    "configs/OpenTitan/gpt35_refine_tool.json"
    "configs/OpenTitan/gpt35_refineonly.json"
    "configs/OpenTitan/gpt35_toolonly.json"
    "configs/OpenTitan/gpt41_nano_refine_tool.json"
    "configs/OpenTitan/gpt41_nano_refineonly.json"
    "configs/OpenTitan/gpt41_nano_toolonly.json"
)

echo "Starting evaluation runs for all configurations..."
echo "Total configurations: ${#configs[@]}"

# Run each configuration in the background
for i in "${!configs[@]}"; do
    config="${configs[$i]}"
    echo "[$((i+1))/${#configs[@]}] Starting: $config"
    
    # Extract config name for log file (remove path and extension)
    config_name=$(basename "$config" .json)
    log_file="logs/${config_name}.log"
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Run the command in background and redirect output to log file
    python scripts/evaluate.py --config "$config" > "$log_file" 2>&1 &
    
    # Store the process ID
    pid=$!
    echo "  → Started with PID: $pid (log: $log_file)"
done

echo ""
echo "All processes started in background!"
echo "Monitor progress with: tail -f logs/<config_name>.log"
echo "Check running processes with: jobs"
echo "View all log files: ls -la logs/"