import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

def load_and_process_data(file_paths):
    """
    Load JSON files and process them into a structured format for plotting.
    
    Args:
        file_paths: List of paths to JSON files
    
    Returns:
        pandas.DataFrame with processed benchmark data
    """
    all_data = []
    
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract configuration info
        model = data['model']
        no_self_refine = data['no_self_refine']
        no_verilator_tool = data['no_verilator_tool']
        
        # Determine configuration type
        # If no_self_refine=True, then self-refine is DISABLED
        # If no_verilator_tool=True, then verilator tool is DISABLED
        if not no_self_refine and not no_verilator_tool:
            config_type = "refine+tool"  # both enabled
        elif not no_self_refine and no_verilator_tool:
            config_type = "refine only"  # only self-refine enabled
        elif no_self_refine and not no_verilator_tool:
            config_type = "tool only"   # only verilator tool enabled
        else:
            config_type = "baseline"    # both disabled
        
        # Calculate success rate
        total_tasks = len(data['results'])
        successful_tasks = sum(1 for result in data['results'] if result['success'])
        success_rate = (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        # Get average time
        avg_time = data['average_time_s']
        
        all_data.append({
            'model': model,
            'config_type': config_type,
            'success_rate': success_rate,
            'avg_time': avg_time,
            'no_self_refine': no_self_refine,
            'no_verilator_tool': no_verilator_tool
        })
    
    return pd.DataFrame(all_data)

def create_benchmark_plots(df, figsize=(15, 6)):
    """
    Create benchmark plots with reddish-orange themed colors.
    
    Args:
        df: DataFrame with benchmark data
        figsize: Figure size tuple
    """
    # Set up the plotting style
    plt.style.use('default')
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    # Define black and orange themed colors (tech/circuit board inspired)
    colors = {
        'refine+tool': '#FF6600',   # Bright orange
        'refine only': '#FF8C42',   # Medium orange
        'tool only': '#2C2C2C'     # Dark charcoal/black
    }
    
    # Define hatching patterns for better distinction
    patterns = {
        'refine+tool': '',        # solid (brightest color)
        'refine only': '///',     # diagonal lines
        'tool only': 'xxx'       # crosses (darkest color)
    }
    
    # Get unique models and sort them
    models = sorted(df['model'].unique())
    
    # Plot 1: Success Rate
    x_pos = np.arange(len(models)) * 2  # Increase spacing between model groups
    width = 0.5  # Make bars wider
    
    for i, config in enumerate(['refine+tool', 'refine only', 'tool only']):
        config_data = df[df['config_type'] == config]
        values = []
        for model in models:
            model_data = config_data[config_data['model'] == model]
            if len(model_data) > 0:
                values.append(model_data['success_rate'].iloc[0])
            else:
                values.append(0)
        
        bars = ax1.bar(x_pos + i*width, values, width, 
                      color=colors[config], 
                      hatch=patterns[config],
                      label=config,
                      alpha=0.9,
                      edgecolor='#000000',  # Black edges
                      linewidth=1.2)
        
        # Add value labels on top of bars
        for j, (bar, value) in enumerate(zip(bars, values)):
            if value > 0:  # Only show label if there's a value
                ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                        f'{value:.1f}%', ha='center', va='bottom', 
                        fontweight='bold', fontsize=9, color='#333333')
    
    ax1.set_xlabel('Model', fontweight='bold')
    ax1.set_ylabel('Performance (%)\nOut of 20 tasks', fontweight='bold')
    ax1.set_title('Benchmark\nSuccess %', fontweight='bold', fontsize=14)
    ax1.set_xticks(x_pos + width)  # Center the labels
    ax1.set_xticklabels(models)
    ax1.legend(frameon=True, fancybox=True, shadow=True, facecolor='#F5F5F5')
    ax1.grid(True, alpha=0.3, color='#666666')  # Gray grid
    ax1.set_ylim(0, 110)  # Increased to accommodate labels
    ax1.set_facecolor('#FAFAFA')  # Light gray background
    
    # Plot 2: Average Time
    for i, config in enumerate(['refine+tool', 'refine only', 'tool only']):
        config_data = df[df['config_type'] == config]
        values = []
        for model in models:
            model_data = config_data[config_data['model'] == model]
            if len(model_data) > 0:
                values.append(model_data['avg_time'].iloc[0])
            else:
                values.append(0)
        
        bars = ax2.bar(x_pos + i*width, values, width, 
                      color=colors[config], 
                      hatch=patterns[config],
                      label=config,
                      alpha=0.9,
                      edgecolor='#000000',  # Black edges
                      linewidth=1.2)
        
        # Add value labels on top of bars
        for j, (bar, value) in enumerate(zip(bars, values)):
            if value > 0:  # Only show label if there's a value
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(values) * 0.01,
                        f'{value:.1f}s', ha='center', va='bottom', 
                        fontweight='bold', fontsize=9, color='#333333')
    
    ax2.set_xlabel('Model', fontweight='bold')
    ax2.set_ylabel('Avg Time (s)\nof 20 tasks', fontweight='bold')
    ax2.set_title('Benchmark Avg\nTime', fontweight='bold', fontsize=14)
    ax2.set_xticks(x_pos + width)  # Center the labels
    ax2.set_xticklabels(models)
    ax2.legend(frameon=True, fancybox=True, shadow=True, facecolor='#F5F5F5')
    ax2.grid(True, alpha=0.3, color='#666666')  # Gray grid
    ax2.set_facecolor('#FAFAFA')  # Light gray background
    
    # Set overall figure background
    fig.patch.set_facecolor('#FFFFFF')  # Clean white background
    
    plt.tight_layout()
    return fig

def plot_benchmarks_from_files(file_paths, save_path=None, show_plot=True):
    """
    Complete pipeline to load data and create benchmark plots.
    
    Args:
        file_paths: List of paths to JSON files
        save_path: Optional path to save the plot
        show_plot: Whether to display the plot
    """
    # Load and process data
    df = load_and_process_data(file_paths)
    
    # Create plots
    fig = create_benchmark_plots(df)
    
    # Save if requested
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
        print(f"Plot saved to {save_path}")
    
    # Show if requested
    if show_plot:
        plt.show()
    
    return fig, df

# Example usage:
if __name__ == "__main__":
    # Example file paths - replace with your actual file paths
    file_paths = [
        "results/OpenTitan/refine_tool_gpt35.json",
        "results/OpenTitan/refineonly_gpt35.json",
        "results/OpenTitan/toolonly_gpt35.json",
        "results/OpenTitan/refine_tool_gpt41_nano.json",
        "results/OpenTitan/refineonly_gpt41_nano.json",
        "results/OpenTitan/toolonly_gpt41_nano.json",
        "results/OpenTitan/refine_tool_gpt4o_mini.json",
        "results/OpenTitan/refineonly_gpt4o_mini.json",
        "results/OpenTitan/toolonly_gpt4o_mini.json"
    ]
    
    # Create the plots
    try:
        fig, df = plot_benchmarks_from_files(file_paths, save_path="plots/benchmark_results.png")
        
        # Print summary statistics
        print("\nSummary Statistics:")
        print(df.groupby(['model', 'config_type'])[['success_rate', 'avg_time']].describe())
        
    except FileNotFoundError as e:
        print(f"Error: Could not find one or more files. Please check file paths.")
        print("Example of how to use this code:")
        print("1. Save your JSON files with descriptive names")
        print("2. Update the file_paths list with your actual file names")
        print("3. Run the script")
        
        # Show what the data structure should look like
        print("\nExpected JSON structure:")
        example_json = {
            "model": "gpt-4o-mini",
            "no_self_refine": False,
            "no_verilator_tool": True,
            "average_time_s": 16.063923597335815,
            "results": [
                {
                    "task": "task_00",
                    "success": True,
                    "attempts": 1,
                    "final_stderr": "",
                    "time_s": 23.56610083580017
                }
            ]
        }
        print(json.dumps(example_json, indent=2))